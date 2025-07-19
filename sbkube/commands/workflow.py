import asyncio
import sys
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from sbkube.utils.logger import logger
from sbkube.utils.workflow_engine import WorkflowEngine
from sbkube.utils.workflow_manager import WorkflowManager

console = Console()


@click.group(name="workflow")
def workflow_group():
    """커스텀 워크플로우 관리"""
    pass


@workflow_group.command("list")
@click.option("--detailed", is_flag=True, help="상세 정보 표시")
def list_workflows(detailed):
    """사용 가능한 워크플로우 목록"""
    try:
        manager = WorkflowManager()
        workflows = manager.list_workflows()

        if not workflows:
            console.print("📋 사용 가능한 워크플로우가 없습니다.")
            return

        if detailed:
            _show_detailed_workflows(workflows)
        else:
            _show_simple_workflows(workflows)

    except Exception as e:
        logger.error(f"❌ 워크플로우 목록 조회 실패: {e}")
        sys.exit(1)


@workflow_group.command("run")
@click.argument("workflow_name")
@click.option("--var", multiple=True, help="변수 설정 (key=value)")
@click.option("--profile", help="사용할 프로파일")
@click.option("--dry-run", is_flag=True, help="실제 실행하지 않고 계획만 표시")
def run_workflow(workflow_name, var, profile, dry_run):
    """워크플로우 실행"""
    try:
        manager = WorkflowManager()
        workflow = manager.load_workflow(workflow_name)

        if not workflow:
            console.print(f"❌ 워크플로우를 찾을 수 없습니다: {workflow_name}")
            sys.exit(1)

        # 변수 파싱
        variables = {}
        for v in var:
            if "=" in v:
                key, value = v.split("=", 1)
                variables[key] = value

        # 실행 컨텍스트 구성
        context = {
            "profile": profile,
            "variables": variables,
            "workflow_name": workflow_name,
        }

        if dry_run:
            _show_workflow_plan(workflow, context)
            return

        # 워크플로우 실행
        engine = WorkflowEngine(console)
        success = asyncio.run(engine.execute_workflow(workflow, context))

        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"❌ 워크플로우 실행 실패: {e}")
        sys.exit(1)


@workflow_group.command("show")
@click.argument("workflow_name")
def show_workflow(workflow_name):
    """워크플로우 상세 정보 표시"""
    try:
        manager = WorkflowManager()
        workflow = manager.load_workflow(workflow_name)

        if not workflow:
            console.print(f"❌ 워크플로우를 찾을 수 없습니다: {workflow_name}")
            sys.exit(1)

        _show_workflow_details(workflow)

    except Exception as e:
        logger.error(f"❌ 워크플로우 조회 실패: {e}")
        sys.exit(1)


def _show_simple_workflows(workflows: list[dict[str, Any]]):
    """간단한 워크플로우 목록"""
    table = Table(title="🔄 사용 가능한 워크플로우")
    table.add_column("이름", style="cyan")
    table.add_column("설명", style="green")
    table.add_column("단계 수", justify="center")
    table.add_column("버전", justify="center")

    for workflow in workflows:
        table.add_row(
            workflow["name"],
            workflow["description"],
            str(workflow["steps_count"]),
            workflow["version"],
        )

    console.print(table)


def _show_detailed_workflows(workflows: list[dict[str, Any]]):
    """상세한 워크플로우 목록"""
    for workflow in workflows:
        panel_content = f"""[bold]설명:[/bold] {workflow["description"]}
[bold]버전:[/bold] {workflow["version"]}
[bold]단계 수:[/bold] {workflow["steps_count"]}
[bold]파일:[/bold] {workflow["file"]}"""

        console.print(
            Panel(panel_content, title=f"🔄 {workflow['name']}", expand=False)
        )


def _show_workflow_plan(workflow, context: dict[str, Any]):
    """워크플로우 실행 계획 표시"""
    console.print(f"🔍 워크플로우 '{workflow.name}' 실행 계획:")
    console.print("━" * 50)

    for i, step in enumerate(workflow.steps, 1):
        step_info = f"{i}. {step.name}"

        if step.type.value != "builtin":
            step_info += f" ({step.type.value})"

        if step.condition:
            step_info += f" [조건: {step.condition}]"

        if step.parallel and step.apps:
            step_info += f" [병렬: {', '.join(step.apps)}]"

        console.print(step_info)

        if step.script:
            console.print(f"   스크립트: {step.script}")
        elif step.command:
            console.print(f"   명령어: {step.command}")

    console.print("\n💡 실제 실행하려면 --dry-run 옵션을 제거하세요.")


def _show_workflow_details(workflow):
    """워크플로우 상세 정보"""
    console.print(f"🔄 워크플로우: {workflow.name}")
    console.print(f"📝 설명: {workflow.description}")
    console.print(f"🏷️  버전: {workflow.version}")

    if workflow.variables:
        console.print("\n📊 변수:")
        for key, value in workflow.variables.items():
            console.print(f"  {key}: {value}")

    console.print("\n📋 단계:")
    for i, step in enumerate(workflow.steps, 1):
        console.print(f"  {i}. {step.name}")
        if step.condition:
            console.print(f"     조건: {step.condition}")
        if step.parallel and step.apps:
            console.print(f"     병렬 실행: {', '.join(step.apps)}")
        if step.script:
            console.print(f"     스크립트: {step.script}")
