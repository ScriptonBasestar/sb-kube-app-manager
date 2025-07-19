from unittest.mock import patch

import pytest

from sbkube.models.workflow_model import StepStatus, StepType, Workflow, WorkflowStep
from sbkube.utils.condition_evaluator import ConditionEvaluator
from sbkube.utils.workflow_engine import WorkflowEngine


class TestWorkflowEngine:
    def test_workflow_model_creation(self):
        """워크플로우 모델 생성 테스트"""
        step = WorkflowStep(name="test-step", type=StepType.BUILTIN, command="prepare")

        workflow = Workflow(
            name="test-workflow", description="테스트 워크플로우", steps=[step]
        )

        assert workflow.name == "test-workflow"
        assert len(workflow.steps) == 1
        assert workflow.steps[0].name == "test-step"

    def test_condition_evaluator(self):
        """조건 평가기 테스트"""
        evaluator = ConditionEvaluator(
            {"ENVIRONMENT": "production", "cache": {"charts": True}}
        )

        # 기본 조건
        assert evaluator.evaluate("true") is True
        assert evaluator.evaluate("false") is False

        # 변수 참조
        assert evaluator.evaluate("context.get('ENVIRONMENT') == 'production'") is True

        # 캐시 확인
        assert evaluator.evaluate("cache.get('charts')")

    @pytest.mark.asyncio
    async def test_workflow_execution(self):
        """워크플로우 실행 테스트"""
        step1 = WorkflowStep(name="step1", type=StepType.BUILTIN, command="prepare")
        step2 = WorkflowStep(name="step2", type=StepType.BUILTIN, command="build")

        workflow = Workflow(name="test-workflow", steps=[step1, step2])

        engine = WorkflowEngine()

        # Mock 내장 명령어
        with (
            patch.object(engine, "_execute_prepare", return_value=True),
            patch.object(engine, "_execute_build", return_value=True),
        ):
            success = await engine.execute_workflow(workflow)

            assert success is True
            assert workflow.status == StepStatus.COMPLETED
            assert step1.status == StepStatus.COMPLETED
            assert step2.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """병렬 실행 테스트"""
        step = WorkflowStep(
            name="parallel-build",
            type=StepType.BUILTIN,
            command="build",
            parallel=True,
            apps=["app1", "app2", "app3"],
        )

        workflow = Workflow(name="test", steps=[step])
        engine = WorkflowEngine()

        with patch.object(engine, "_execute_build", return_value=True):
            success = await engine.execute_workflow(workflow)

            assert success is True
            assert step.status == StepStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_condition_skipping(self):
        """조건부 건너뛰기 테스트"""
        step = WorkflowStep(
            name="conditional-step",
            type=StepType.BUILTIN,
            command="prepare",
            condition="false",  # 항상 거짓
        )

        workflow = Workflow(name="test", steps=[step])
        engine = WorkflowEngine()

        success = await engine.execute_workflow(workflow)

        assert success is True
        assert step.status == StepStatus.SKIPPED

    @pytest.mark.asyncio
    async def test_script_execution(self):
        """스크립트 실행 테스트"""
        step = WorkflowStep(
            name="script-step", type=StepType.SCRIPT, script="echo 'Hello World'"
        )

        workflow = Workflow(name="test", steps=[step])
        engine = WorkflowEngine()

        success = await engine.execute_workflow(workflow)

        assert success is True
        assert step.status == StepStatus.COMPLETED
        assert "Hello World" in step.output

    def test_workflow_serialization(self):
        """워크플로우 직렬화 테스트"""
        step = WorkflowStep(name="test-step", type=StepType.BUILTIN, command="prepare")

        workflow = Workflow(
            name="test-workflow", description="테스트 워크플로우", steps=[step]
        )

        # 딕셔너리 변환
        data = workflow.to_dict()

        # 딕셔너리에서 복원
        restored_workflow = Workflow.from_dict(data)

        assert restored_workflow.name == workflow.name
        assert restored_workflow.description == workflow.description
        assert len(restored_workflow.steps) == len(workflow.steps)
        assert restored_workflow.steps[0].name == workflow.steps[0].name
