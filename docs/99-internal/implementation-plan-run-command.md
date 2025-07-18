# sbkube run 명령어 구현 방안

## 📋 개요

`sbkube run` 명령어는 기존의 4단계 워크플로우(prepare → build → template → deploy)를 하나의 명령어로 통합 실행할 수 있도록 하는 핵심 편의성 기능입니다.

## 🎯 요구사항

### 기본 요구사항

1. **기존 워크플로우 통합**: prepare → build → template → deploy 순차 실행
1. **단계별 실행 제어**: 특정 단계부터 시작 또는 특정 단계까지만 실행
1. **실패 처리**: 실패 시 중단점 저장 및 재시작 지원
1. **진행 상황 표시**: 각 단계별 실행 상태 및 진행률 표시
1. **기존 명령어 호환성**: 모든 기존 옵션과 완전 호환

### 고급 요구사항

1. **병렬 처리**: 가능한 작업들의 병렬 실행
1. **검증 및 의존성 확인**: 각 단계 실행 전 사전 검증
1. **상태 관리**: 실행 상태 저장 및 복원
1. **사용자 상호작용**: 오류 발생 시 사용자 선택 옵션 제공

## 🏗️ 구현 설계

### 1. 명령어 구조

```python
# sbkube/commands/run.py
import click
from sbkube.utils.base_command import BaseCommand
from sbkube.commands import prepare, build, template, deploy

class RunCommand(BaseCommand):
    """통합 실행 명령어"""
    
    def __init__(self, base_dir: str, app_config_dir: str, 
                 target_app_name: str = None, config_file_name: str = None,
                 from_step: str = None, to_step: str = None,
                 continue_from: str = None, dry_run: bool = False):
        super().__init__(base_dir, app_config_dir, target_app_name, config_file_name)
        self.from_step = from_step
        self.to_step = to_step
        self.continue_from = continue_from
        self.dry_run = dry_run
        
    def execute(self):
        """통합 워크플로우 실행"""
        steps = self._determine_steps()
        
        for step_name in steps:
            try:
                self._execute_step(step_name)
                self._save_progress(step_name, "completed")
            except Exception as e:
                self._save_progress(step_name, "failed", str(e))
                self._handle_failure(step_name, e)
                break
```

### 2. 단계별 실행 제어

```python
def _determine_steps(self) -> List[str]:
    """실행할 단계들을 결정"""
    all_steps = ["prepare", "build", "template", "deploy"]
    
    # 재시작 지점 확인
    if self.continue_from:
        start_index = all_steps.index(self.continue_from)
        return all_steps[start_index:]
    
    # 시작/종료 단계 설정
    start_index = 0
    end_index = len(all_steps)
    
    if self.from_step:
        start_index = all_steps.index(self.from_step)
    if self.to_step:
        end_index = all_steps.index(self.to_step) + 1
        
    return all_steps[start_index:end_index]

def _execute_step(self, step_name: str):
    """개별 단계 실행"""
    logger.info(f"🚀 {step_name.title()} 단계 시작...")
    
    if step_name == "prepare":
        cmd = prepare.PrepareCommand(
            self.base_dir, self.app_config_dir, 
            self.target_app_name, self.config_file_name
        )
    elif step_name == "build":
        cmd = build.BuildCommand(
            self.base_dir, self.app_config_dir,
            self.target_app_name, self.config_file_name
        )
    # ... 다른 단계들
    
    cmd.execute()
    logger.success(f"✅ {step_name.title()} 단계 완료")
```

### 3. 상태 관리 시스템

```python
# sbkube/utils/state_manager.py
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class RunStateManager:
    """실행 상태 관리"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.state_file = self.base_dir / ".sbkube" / "run_state.json"
        self.state_file.parent.mkdir(exist_ok=True)
    
    def save_progress(self, step: str, status: str, error: str = None):
        """진행 상황 저장"""
        state = self._load_state()
        state["steps"][step] = {
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "error": error
        }
        state["last_run"] = datetime.now().isoformat()
        self._save_state(state)
    
    def get_last_failed_step(self) -> Optional[str]:
        """마지막 실패한 단계 반환"""
        state = self._load_state()
        for step, info in state.get("steps", {}).items():
            if info.get("status") == "failed":
                return step
        return None
    
    def _load_state(self) -> Dict[str, Any]:
        """상태 파일 로드"""
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"steps": {}, "last_run": None}
    
    def _save_state(self, state: Dict[str, Any]):
        """상태 파일 저장"""
        self.state_file.write_text(json.dumps(state, indent=2))
```

### 4. 진행 상황 표시

```python
# sbkube/utils/progress_display.py
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.console import Console
from typing import Dict, List

class RunProgressDisplay:
    """실행 진행 상황 표시"""
    
    def __init__(self):
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.fields[name]}", justify="right"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            console=self.console
        )
        self.tasks: Dict[str, TaskID] = {}
    
    def start_workflow(self, steps: List[str]):
        """워크플로우 시작"""
        self.progress.start()
        
        for step in steps:
            task_id = self.progress.add_task(
                f"[cyan]{step.title()}",
                name=step,
                total=100
            )
            self.tasks[step] = task_id
    
    def update_step(self, step: str, percentage: int, status: str = "running"):
        """단계 진행 상황 업데이트"""
        if step in self.tasks:
            color = {
                "running": "cyan",
                "completed": "green", 
                "failed": "red"
            }.get(status, "cyan")
            
            self.progress.update(
                self.tasks[step],
                completed=percentage,
                name=f"[{color}]{step.title()}"
            )
    
    def complete_step(self, step: str):
        """단계 완료"""
        self.update_step(step, 100, "completed")
    
    def fail_step(self, step: str):
        """단계 실패"""
        self.update_step(step, 0, "failed")
    
    def stop(self):
        """진행 표시 중단"""
        self.progress.stop()
```

### 5. CLI 인터페이스

```python
# sbkube/commands/run.py
@click.command(name="run")
@click.option("--app-dir", default="config", help="앱 설정 디렉토리")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리")
@click.option("--app", help="실행할 특정 앱 이름")
@click.option("--config-file", help="사용할 설정 파일 이름")
@click.option("--from-step", 
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="시작할 단계")
@click.option("--to-step",
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="종료할 단계")
@click.option("--continue-from",
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="특정 단계부터 재시작")
@click.option("--dry-run", is_flag=True, help="실제 실행 없이 계획만 표시")
@click.option("--auto-retry", is_flag=True, help="실패 시 자동 재시도")
@click.option("--parallel", is_flag=True, help="가능한 작업 병렬 실행")
@click.pass_context
def cmd(ctx, app_dir, base_dir, app, config_file, from_step, to_step, 
        continue_from, dry_run, auto_retry, parallel):
    """전체 워크플로우를 통합 실행합니다.
    
    prepare → build → template → deploy 단계를 순차적으로 실행하며,
    각 단계별 진행 상황을 실시간으로 표시합니다.
    
    예시:
        sbkube run                                  # 전체 워크플로우 실행
        sbkube run --app web-frontend               # 특정 앱만 실행
        sbkube run --from-step template             # template부터 실행
        sbkube run --to-step build                  # build까지만 실행
        sbkube run --continue-from template         # template부터 재시작
    """
    command = RunCommand(
        base_dir=base_dir,
        app_config_dir=app_dir,
        target_app_name=app,
        config_file_name=config_file,
        from_step=from_step,
        to_step=to_step,
        continue_from=continue_from,
        dry_run=dry_run
    )
    
    try:
        command.execute()
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
        sys.exit(130)
```

## 🔧 고급 기능

### 1. 자동 재시도 메커니즘

```python
def _handle_failure(self, step_name: str, error: Exception):
    """실패 처리 및 재시도"""
    if self.auto_retry and self._is_retryable_error(error):
        logger.warning(f"⚠️ {step_name} 실패, 3초 후 재시도...")
        time.sleep(3)
        self._execute_step(step_name)
    else:
        logger.error(f"❌ {step_name} 실패: {error}")
        self._suggest_next_actions(step_name, error)
        raise error

def _suggest_next_actions(self, step_name: str, error: Exception):
    """다음 액션 제안"""
    suggestions = {
        "prepare": [
            "sources.yaml 파일에서 저장소 설정을 확인하세요",
            "네트워크 연결 상태를 확인하세요",
            "sbkube run --continue-from prepare 로 재시작하세요"
        ],
        "build": [
            "config.yaml 파일의 앱 설정을 확인하세요",
            "필요한 소스 파일들이 존재하는지 확인하세요",
            "sbkube run --continue-from build 로 재시작하세요"
        ],
        # ... 다른 단계들
    }
    
    logger.info("\n💡 다음 액션 제안:")
    for suggestion in suggestions.get(step_name, []):
        logger.info(f"   • {suggestion}")
```

### 2. 병렬 처리 지원

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class ParallelRunCommand(RunCommand):
    """병렬 처리 지원 실행 명령어"""
    
    async def execute_parallel(self):
        """병렬 실행 가능한 작업들 식별 및 실행"""
        # 앱별로 독립적인 작업들은 병렬 실행 가능
        apps = self._get_apps_to_process()
        
        if len(apps) > 1:
            await self._execute_apps_parallel(apps)
        else:
            await self._execute_sequential()
    
    async def _execute_apps_parallel(self, apps: List[str]):
        """앱별 병렬 실행"""
        with ThreadPoolExecutor(max_workers=min(len(apps), 4)) as executor:
            tasks = []
            for app in apps:
                task = asyncio.create_task(
                    self._execute_app_workflow(app)
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
```

### 3. 실행 계획 미리보기

```python
def _show_execution_plan(self):
    """실행 계획 표시"""
    steps = self._determine_steps()
    apps = self._get_apps_to_process()
    
    table = Table(title="실행 계획")
    table.add_column("단계", style="cyan")
    table.add_column("대상 앱", style="magenta") 
    table.add_column("예상 시간", style="green")
    table.add_column("설명", style="white")
    
    for step in steps:
        estimated_time = self._estimate_step_time(step, apps)
        description = self._get_step_description(step)
        
        table.add_row(
            step.title(),
            ", ".join(apps) if apps else "전체",
            f"~{estimated_time}s",
            description
        )
    
    console.print(table)
    
    if not click.confirm("계속 진행하시겠습니까?"):
        raise click.Abort()
```

## 🧪 테스트 계획

### 1. 단위 테스트

```python
# tests/unit/commands/test_run.py
import pytest
from sbkube.commands.run import RunCommand
from sbkube.utils.state_manager import RunStateManager

class TestRunCommand:
    """RunCommand 단위 테스트"""
    
    def test_determine_steps_full_workflow(self):
        """전체 워크플로우 단계 결정 테스트"""
        cmd = RunCommand(".", "config")
        steps = cmd._determine_steps()
        assert steps == ["prepare", "build", "template", "deploy"]
    
    def test_determine_steps_from_step(self):
        """특정 단계부터 시작 테스트"""
        cmd = RunCommand(".", "config", from_step="build")
        steps = cmd._determine_steps()
        assert steps == ["build", "template", "deploy"]
    
    def test_determine_steps_to_step(self):
        """특정 단계까지만 실행 테스트"""
        cmd = RunCommand(".", "config", to_step="template")
        steps = cmd._determine_steps()
        assert steps == ["prepare", "build", "template"]
    
    def test_state_manager_save_progress(self):
        """상태 저장 테스트"""
        state_mgr = RunStateManager(".")
        state_mgr.save_progress("prepare", "completed")
        
        state = state_mgr._load_state()
        assert state["steps"]["prepare"]["status"] == "completed"
```

### 2. 통합 테스트

```python
# tests/integration/test_run_workflow.py
import pytest
from click.testing import CliRunner
from sbkube.commands.run import cmd

class TestRunWorkflow:
    """전체 워크플로우 통합 테스트"""
    
    def test_full_workflow_success(self, sample_project):
        """전체 워크플로우 성공 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, [
            "--app-dir", "config",
            "--base-dir", str(sample_project)
        ])
        
        assert result.exit_code == 0
        assert "Prepare 단계 완료" in result.output
        assert "Build 단계 완료" in result.output
        assert "Template 단계 완료" in result.output
        assert "Deploy 단계 완료" in result.output
    
    def test_continue_from_failed_step(self, sample_project):
        """실패한 단계부터 재시작 테스트"""
        # 먼저 실패 상황 생성
        state_mgr = RunStateManager(str(sample_project))
        state_mgr.save_progress("prepare", "completed")
        state_mgr.save_progress("build", "failed", "Mock error")
        
        runner = CliRunner()
        result = runner.invoke(cmd, [
            "--continue-from", "build",
            "--base-dir", str(sample_project)
        ])
        
        assert result.exit_code == 0
        assert "Build 단계 시작" in result.output
```

## 📚 사용 예시

### 기본 사용법

```bash
# 전체 워크플로우 실행
sbkube run

# 특정 앱만 실행  
sbkube run --app web-frontend

# 특정 디렉토리에서 실행
sbkube run --app-dir production --base-dir /path/to/project
```

### 단계별 제어

```bash
# 특정 단계부터 실행
sbkube run --from-step template

# 특정 단계까지만 실행
sbkube run --to-step build

# 실패한 단계부터 재시작
sbkube run --continue-from build
```

### 고급 사용법

```bash
# 실행 계획 미리보기
sbkube run --dry-run

# 병렬 실행 (여러 앱이 있는 경우)
sbkube run --parallel

# 자동 재시도 활성화
sbkube run --auto-retry
```

## 🚀 구현 단계

### 1단계: 기본 구조 (1주)

- [ ] RunCommand 클래스 기본 구조 구현
- [ ] 단계별 실행 로직 구현
- [ ] 기본 CLI 인터페이스 구현

### 2단계: 상태 관리 (1주)

- [ ] RunStateManager 구현
- [ ] 실패 처리 및 재시작 로직 구현
- [ ] 진행 상황 저장/복원 기능 구현

### 3단계: 사용자 인터페이스 (1주)

- [ ] 진행 상황 표시 구현
- [ ] 오류 메시지 및 제안 기능 구현
- [ ] 실행 계획 미리보기 구현

### 4단계: 고급 기능 (1-2주)

- [ ] 병렬 처리 지원 구현
- [ ] 자동 재시도 메커니즘 구현
- [ ] 성능 최적화 및 안정성 개선

### 5단계: 테스트 및 문서화 (1주)

- [ ] 단위 테스트 작성
- [ ] 통합 테스트 작성
- [ ] 사용자 문서 작성
- [ ] 예제 및 튜토리얼 작성

______________________________________________________________________

*이 설계는 기존 SBKube 아키텍처를 최대한 활용하면서 사용자 편의성을 크게 개선하는 것을 목표로 합니다.*
