---
phase: 1
order: 1
source_plan: /tasks/plan/phase1-basic-convenience.md
priority: high
tags: [run-command, basic-structure, cli]
estimated_days: 3
---

# 📌 작업: sbkube run 명령어 기본 구조 구현

## 🎯 목표
`sbkube run` 명령어의 기본 구조를 구현하여 기존 4단계 워크플로우(prepare → build → template → deploy)를 순차 실행할 수 있도록 합니다.

## 📋 작업 내용

### 1. RunCommand 클래스 생성
```bash
# 파일 생성
touch sbkube/commands/run.py
```

### 2. 기본 구조 구현
```python
# sbkube/commands/run.py
from sbkube.utils.base_command import BaseCommand
from sbkube.commands import prepare, build, template, deploy
from sbkube.utils.logger import logger

class RunCommand(BaseCommand):
    def __init__(self, base_dir: str, app_config_dir: str, 
                 target_app_name: str = None, config_file_name: str = None):
        super().__init__(base_dir, app_config_dir, target_app_name, config_file_name)
        
    def execute(self):
        """4단계 순차 실행"""
        steps = ["prepare", "build", "template", "deploy"]
        
        for step in steps:
            logger.info(f"🚀 {step.title()} 단계 시작...")
            self._execute_step(step)
            logger.success(f"✅ {step.title()} 단계 완료")
    
    def _execute_step(self, step_name: str):
        """개별 단계 실행"""
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
        elif step_name == "template":
            cmd = template.TemplateCommand(
                self.base_dir, self.app_config_dir,
                self.target_app_name, self.config_file_name
            )
        elif step_name == "deploy":
            cmd = deploy.DeployCommand(
                self.base_dir, self.app_config_dir,
                self.target_app_name, self.config_file_name
            )
        else:
            raise ValueError(f"Unknown step: {step_name}")
            
        cmd.execute()
```

### 3. CLI 인터페이스 구현
```python
# sbkube/commands/run.py (계속)
import click

@click.command(name="run")
@click.option("--app-dir", default="config", help="앱 설정 디렉토리")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리")
@click.option("--app", help="실행할 특정 앱 이름")
@click.option("--config-file", help="사용할 설정 파일 이름")
@click.pass_context
def cmd(ctx, app_dir, base_dir, app, config_file):
    """전체 워크플로우를 통합 실행합니다.
    
    prepare → build → template → deploy 단계를 순차적으로 실행합니다.
    """
    command = RunCommand(
        base_dir=base_dir,
        app_config_dir=app_dir,
        target_app_name=app,
        config_file_name=config_file
    )
    
    try:
        command.execute()
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        sys.exit(1)
```

### 4. CLI에 명령어 등록
```python
# sbkube/cli.py에 추가
from sbkube.commands import run

# 기존 명령어 등록 부분에 추가
main.add_command(run.cmd)
```

## 🧪 테스트 파일 생성

### 단위 테스트
```python
# tests/unit/commands/test_run.py
import pytest
from sbkube.commands.run import RunCommand

class TestRunCommand:
    def test_init(self):
        """RunCommand 초기화 테스트"""
        cmd = RunCommand(".", "config")
        assert cmd.base_dir.name == "."
        assert cmd.app_config_dir.name == "config"
    
    def test_execute_step_validation(self):
        """단계 이름 검증 테스트"""
        cmd = RunCommand(".", "config")
        
        with pytest.raises(ValueError):
            cmd._execute_step("invalid_step")
```

### 통합 테스트
```python
# tests/integration/test_run_workflow.py
from click.testing import CliRunner
from sbkube.commands.run import cmd

def test_run_command_basic():
    """기본 run 명령어 테스트"""
    runner = CliRunner()
    
    with runner.isolated_filesystem():
        # 기본 프로젝트 구조 생성
        # ... 테스트 설정
        
        result = runner.invoke(cmd, ['--app-dir', 'config'])
        assert result.exit_code == 0
```

## ✅ 완료 기준

- [ ] `sbkube/commands/run.py` 파일 생성 완료
- [ ] `RunCommand` 클래스 기본 구조 구현
- [ ] 4단계 순차 실행 로직 동작
- [ ] CLI 인터페이스 구현 및 등록
- [ ] 기본 테스트 파일 생성
- [ ] `sbkube run` 명령어 실행 가능

## 🔍 검증 명령어

```bash
# 명령어 등록 확인
sbkube --help | grep run

# 기본 실행 테스트
sbkube run --help

# 단위 테스트 실행
pytest tests/unit/commands/test_run.py -v

# 통합 테스트 실행
pytest tests/integration/test_run_workflow.py -v
```

## 📝 예상 결과

```bash
$ sbkube run --help
Usage: sbkube run [OPTIONS]

  전체 워크플로우를 통합 실행합니다.

  prepare → build → template → deploy 단계를 순차적으로 실행합니다.

Options:
  --app-dir TEXT      앱 설정 디렉토리
  --base-dir TEXT     프로젝트 루트 디렉토리
  --app TEXT          실행할 특정 앱 이름
  --config-file TEXT  사용할 설정 파일 이름
  --help              Show this message and exit.
```

## 📚 참고 자료

- 기존 명령어 구현: `sbkube/commands/prepare.py`, `build.py`, `template.py`, `deploy.py`
- BaseCommand 패턴: `sbkube/utils/base_command.py`
- CLI 구조: `sbkube/cli.py`