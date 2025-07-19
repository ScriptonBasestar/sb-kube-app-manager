import asyncio
from datetime import datetime
from typing import Any

from rich.console import Console

from sbkube.models.workflow_model import StepStatus, StepType, Workflow, WorkflowStep
from sbkube.utils.condition_evaluator import ConditionEvaluator
from sbkube.utils.logger import logger


class WorkflowEngine:
    """워크플로우 실행 엔진"""

    def __init__(self, console: Console = None, max_parallel: int = 4):
        self.console = console or Console()
        self.max_parallel = max_parallel
        self.evaluator = ConditionEvaluator()
        self.builtin_commands = {
            "prepare": self._execute_prepare,
            "build": self._execute_build,
            "template": self._execute_template,
            "deploy": self._execute_deploy,
            "validate": self._execute_validate,
        }

        # 실행 상태
        self.current_workflow: Workflow | None = None
        self.step_progress: dict[str, Any] = {}

    async def execute_workflow(
        self, workflow: Workflow, context: dict[str, Any] = None
    ) -> bool:
        """워크플로우 실행"""
        self.current_workflow = workflow
        self.evaluator.update_context(context or {})

        logger.info(f"🚀 워크플로우 '{workflow.name}' 실행 시작")

        workflow.status = StepStatus.RUNNING
        workflow.started_at = datetime.now().isoformat()

        try:
            success = await self._execute_steps(workflow.steps)

            if success:
                workflow.status = StepStatus.COMPLETED
                logger.success("✅ 워크플로우 실행 완료")
            else:
                workflow.status = StepStatus.FAILED
                logger.error("❌ 워크플로우 실행 실패")

            return success

        except Exception as e:
            workflow.status = StepStatus.FAILED
            logger.error(f"❌ 워크플로우 실행 중 오류: {e}")
            return False

        finally:
            workflow.completed_at = datetime.now().isoformat()

    async def _execute_steps(self, steps: list[WorkflowStep]) -> bool:
        """단계들 실행"""
        for step in steps:
            # 조건 확인
            if step.condition and not self.evaluator.evaluate(step.condition):
                step.status = StepStatus.SKIPPED
                logger.info(f"⏭️  단계 건너뛰기: {step.name} (조건 불만족)")
                continue

            # 단계 실행
            if step.parallel and step.apps:
                success = await self._execute_parallel_step(step)
            else:
                success = await self._execute_single_step(step)

            if not success:
                # 실패 처리
                if step.on_failure == "continue":
                    logger.warning(f"⚠️  단계 실패했지만 계속 진행: {step.name}")
                    continue
                elif step.on_failure == "retry" and step.retry_count > 0:
                    logger.info(f"🔄 단계 재시도: {step.name}")
                    step.retry_count -= 1
                    success = await self._execute_single_step(step)
                    if not success:
                        return False
                else:
                    logger.error(f"❌ 단계 실패로 중단: {step.name}")
                    return False

        return True

    async def _execute_single_step(self, step: WorkflowStep) -> bool:
        """단일 단계 실행"""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()

        logger.info(f"🔄 실행 중: {step.name}")

        try:
            if step.type == StepType.BUILTIN:
                success = await self._execute_builtin_step(step)
            elif step.type == StepType.SCRIPT:
                success = await self._execute_script_step(step)
            else:
                logger.error(f"알 수 없는 단계 타입: {step.type}")
                success = False

            if success:
                step.status = StepStatus.COMPLETED
                logger.success(f"✅ 완료: {step.name}")
            else:
                step.status = StepStatus.FAILED
                logger.error(f"❌ 실패: {step.name}")

            return success

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            logger.error(f"❌ 단계 실행 오류 ({step.name}): {e}")
            return False

        finally:
            step.completed_at = datetime.now().isoformat()

    async def _execute_parallel_step(self, step: WorkflowStep) -> bool:
        """병렬 단계 실행"""
        if not step.apps:
            return await self._execute_single_step(step)

        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()

        logger.info(f"🔄 병렬 실행: {step.name} ({len(step.apps)}개 앱)")

        # 앱별로 개별 단계 생성
        parallel_steps = []
        for app in step.apps:
            app_step = WorkflowStep(
                name=f"{step.name}-{app}",
                type=step.type,
                command=step.command,
                script=step.script,
                timeout=step.timeout,
            )
            # 앱 컨텍스트 설정
            app_step.metadata = {"target_app": app}
            parallel_steps.append(app_step)

        # 병렬 실행
        tasks = []
        semaphore = asyncio.Semaphore(self.max_parallel)

        async def execute_with_semaphore(app_step):
            async with semaphore:
                return await self._execute_single_step(app_step)

        for app_step in parallel_steps:
            task = asyncio.create_task(execute_with_semaphore(app_step))
            tasks.append(task)

        # 모든 태스크 완료 대기
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 집계
        success_count = sum(1 for result in results if result is True)
        total_count = len(results)

        if success_count == total_count:
            step.status = StepStatus.COMPLETED
            logger.success(
                f"✅ 병렬 실행 완료: {step.name} ({success_count}/{total_count})"
            )
            return True
        else:
            step.status = StepStatus.FAILED
            step.error = f"병렬 실행 일부 실패: {success_count}/{total_count}"
            logger.error(
                f"❌ 병렬 실행 실패: {step.name} ({success_count}/{total_count})"
            )
            return False

    async def _execute_builtin_step(self, step: WorkflowStep) -> bool:
        """내장 명령어 실행"""
        command = step.command or step.name

        if command in self.builtin_commands:
            return await self.builtin_commands[command](step)
        else:
            logger.error(f"알 수 없는 내장 명령어: {command}")
            return False

    async def _execute_script_step(self, step: WorkflowStep) -> bool:
        """스크립트 실행"""
        if not step.script:
            logger.error("스크립트가 정의되지 않았습니다")
            return False

        try:
            # 비동기 프로세스 실행
            process = await asyncio.create_subprocess_shell(
                step.script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # 타임아웃과 함께 실행
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=step.timeout
            )

            # 결과 저장
            step.output = stdout.decode("utf-8") if stdout else ""
            if stderr:
                step.error = stderr.decode("utf-8")

            return process.returncode == 0

        except TimeoutError:
            step.error = f"스크립트 실행 시간 초과 ({step.timeout}초)"
            return False
        except Exception as e:
            step.error = str(e)
            return False

    # 내장 명령어 구현들
    async def _execute_prepare(self, step: WorkflowStep) -> bool:
        """준비 단계 실행"""
        # 실제 준비 로직 구현
        await asyncio.sleep(1)  # 시뮬레이션
        return True

    async def _execute_build(self, step: WorkflowStep) -> bool:
        """빌드 단계 실행"""
        # 실제 빌드 로직 구현
        target_app = step.metadata.get("target_app")
        if target_app:
            logger.info(f"  📦 빌드 중: {target_app}")

        await asyncio.sleep(2)  # 시뮬레이션
        return True

    async def _execute_template(self, step: WorkflowStep) -> bool:
        """템플릿 단계 실행"""
        # 실제 템플릿 로직 구현
        await asyncio.sleep(1)  # 시뮬레이션
        return True

    async def _execute_deploy(self, step: WorkflowStep) -> bool:
        """배포 단계 실행"""
        # 실제 배포 로직 구현
        target_app = step.metadata.get("target_app")
        if target_app:
            logger.info(f"  🚀 배포 중: {target_app}")

        await asyncio.sleep(3)  # 시뮬레이션
        return True

    async def _execute_validate(self, step: WorkflowStep) -> bool:
        """검증 단계 실행"""
        # 실제 검증 로직 구현
        await asyncio.sleep(1)  # 시뮬레이션
        return True
