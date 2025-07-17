---
phase: 1
order: 2
source_plan: /tasks/plan/phase1-basic-convenience.md
priority: high
tags: [run-command, step-control, cli-options]
estimated_days: 3
depends_on: [001-sbkube-run-basic-structure]
---

# 📌 작업: sbkube run 단계별 실행 제어 구현

## 🎯 목표
`sbkube run` 명령어에 `--from-step`, `--to-step`, `--only` 옵션을 추가하여 사용자가 원하는 단계만 선택적으로 실행할 수 있도록 합니다.

## 📋 작업 내용

### 1. RunCommand 클래스 확장
```python
# sbkube/commands/run.py 수정
class RunCommand(BaseCommand):
    def __init__(self, base_dir: str, app_config_dir: str, 
                 target_app_name: str = None, config_file_name: str = None,
                 from_step: str = None, to_step: str = None, only_step: str = None):
        super().__init__(base_dir, app_config_dir, target_app_name, config_file_name)
        self.from_step = from_step
        self.to_step = to_step
        self.only_step = only_step
        
    def execute(self):
        """단계별 실행 제어를 적용한 실행"""
        steps = self._determine_steps()
        
        logger.info(f"📋 실행할 단계: {' → '.join(steps)}")
        
        for step in steps:
            logger.info(f"🚀 {step.title()} 단계 시작...")
            self._execute_step(step)
            logger.success(f"✅ {step.title()} 단계 완료")
    
    def _determine_steps(self) -> List[str]:
        """실행할 단계들을 결정"""
        all_steps = ["prepare", "build", "template", "deploy"]
        
        # --only 옵션이 있으면 해당 단계만 실행
        if self.only_step:
            if self.only_step not in all_steps:
                raise ValueError(f"Invalid step: {self.only_step}")
            return [self.only_step]
        
        # 시작/종료 단계 결정
        start_index = 0
        end_index = len(all_steps)
        
        if self.from_step:
            if self.from_step not in all_steps:
                raise ValueError(f"Invalid from-step: {self.from_step}")
            start_index = all_steps.index(self.from_step)
            
        if self.to_step:
            if self.to_step not in all_steps:
                raise ValueError(f"Invalid to-step: {self.to_step}")
            end_index = all_steps.index(self.to_step) + 1
        
        if start_index >= end_index:
            raise ValueError("from-step must come before to-step")
            
        return all_steps[start_index:end_index]
```

### 2. CLI 옵션 추가
```python
# sbkube/commands/run.py의 CLI 인터페이스 수정
@click.command(name="run")
@click.option("--app-dir", default="config", help="앱 설정 디렉토리")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리")
@click.option("--app", help="실행할 특정 앱 이름")
@click.option("--config-file", help="사용할 설정 파일 이름")
@click.option("--from-step", 
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="시작할 단계 지정")
@click.option("--to-step",
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="종료할 단계 지정")
@click.option("--only",
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="특정 단계만 실행")
@click.pass_context
def cmd(ctx, app_dir, base_dir, app, config_file, from_step, to_step, only):
    """전체 워크플로우를 통합 실행합니다.
    
    prepare → build → template → deploy 단계를 순차적으로 실행하며,
    --from-step, --to-step, --only 옵션으로 실행 범위를 제어할 수 있습니다.
    
    예시:
        sbkube run                           # 전체 워크플로우 실행
        sbkube run --from-step template      # template부터 실행
        sbkube run --to-step build           # build까지만 실행
        sbkube run --only template           # template만 실행
    """
    # 옵션 충돌 검사
    if only and (from_step or to_step):
        logger.error("--only 옵션은 --from-step, --to-step과 함께 사용할 수 없습니다.")
        sys.exit(1)
    
    command = RunCommand(
        base_dir=base_dir,
        app_config_dir=app_dir,
        target_app_name=app,
        config_file_name=config_file,
        from_step=from_step,
        to_step=to_step,
        only_step=only
    )
    
    try:
        command.execute()
    except ValueError as e:
        logger.error(f"❌ 옵션 오류: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        sys.exit(1)
```

### 3. 단계 검증 및 의존성 확인
```python
# sbkube/commands/run.py에 추가
def _validate_step_dependencies(self, steps: List[str]):
    """단계별 의존성 확인"""
    dependencies = {
        "build": ["prepare"],
        "template": ["prepare", "build"],
        "deploy": ["prepare", "build", "template"]
    }
    
    for step in steps:
        if step in dependencies:
            missing_deps = []
            for dep in dependencies[step]:
                if dep not in steps and not self._is_step_completed(dep):
                    missing_deps.append(dep)
            
            if missing_deps:
                logger.warning(
                    f"⚠️  {step} 단계 실행 전에 다음 단계가 필요합니다: {', '.join(missing_deps)}"
                )

def _is_step_completed(self, step: str) -> bool:
    """단계 완료 여부 확인 (추후 상태 관리 시스템과 연동)"""
    # 현재는 기본적으로 False 반환
    # Phase 2에서 상태 추적 시스템과 연동
    return False
```

## 🧪 테스트 확장

### 단위 테스트 추가
```python
# tests/unit/commands/test_run.py에 추가
class TestRunCommandStepControl:
    def test_determine_steps_full_workflow(self):
        """전체 워크플로우 단계 결정"""
        cmd = RunCommand(".", "config")
        steps = cmd._determine_steps()
        assert steps == ["prepare", "build", "template", "deploy"]
    
    def test_determine_steps_from_step(self):
        """--from-step 옵션 테스트"""
        cmd = RunCommand(".", "config", from_step="build")
        steps = cmd._determine_steps()
        assert steps == ["build", "template", "deploy"]
    
    def test_determine_steps_to_step(self):
        """--to-step 옵션 테스트"""
        cmd = RunCommand(".", "config", to_step="template")
        steps = cmd._determine_steps()
        assert steps == ["prepare", "build", "template"]
    
    def test_determine_steps_from_to_step(self):
        """--from-step과 --to-step 조합 테스트"""
        cmd = RunCommand(".", "config", from_step="build", to_step="template")
        steps = cmd._determine_steps()
        assert steps == ["build", "template"]
    
    def test_determine_steps_only_step(self):
        """--only 옵션 테스트"""
        cmd = RunCommand(".", "config", only_step="template")
        steps = cmd._determine_steps()
        assert steps == ["template"]
    
    def test_invalid_step_names(self):
        """잘못된 단계 이름 처리"""
        with pytest.raises(ValueError):
            cmd = RunCommand(".", "config", from_step="invalid")
            cmd._determine_steps()
    
    def test_invalid_step_order(self):
        """잘못된 단계 순서 처리"""
        with pytest.raises(ValueError):
            cmd = RunCommand(".", "config", from_step="deploy", to_step="prepare")
            cmd._determine_steps()
```

### CLI 테스트 추가
```python
# tests/integration/test_run_step_control.py
from click.testing import CliRunner
from sbkube.commands.run import cmd

class TestRunStepControl:
    def test_from_step_option(self):
        """--from-step 옵션 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ['--from-step', 'template'])
        assert result.exit_code == 0
        assert 'Template 단계 시작' in result.output
        assert 'Prepare 단계 시작' not in result.output
    
    def test_to_step_option(self):
        """--to-step 옵션 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ['--to-step', 'build'])
        assert result.exit_code == 0
        assert 'Build 단계 시작' in result.output
        assert 'Template 단계 시작' not in result.output
    
    def test_only_option(self):
        """--only 옵션 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ['--only', 'template'])
        assert result.exit_code == 0
        assert 'Template 단계 시작' in result.output
        assert 'Prepare 단계 시작' not in result.output
    
    def test_option_conflict(self):
        """옵션 충돌 테스트"""
        runner = CliRunner()
        result = runner.invoke(cmd, ['--only', 'template', '--from-step', 'build'])
        assert result.exit_code == 1
        assert '옵션 오류' in result.output
```

## ✅ 완료 기준

- [x] `--from-step` 옵션 구현 및 동작 확인
- [x] `--to-step` 옵션 구현 및 동작 확인  
- [x] `--only` 옵션 구현 및 동작 확인
- [x] 옵션 조합 검증 로직 구현
- [x] 단계 의존성 검증 기능 추가
- [x] 확장된 테스트 케이스 통과

## 🔍 검증 명령어

```bash
# 옵션 확인
sbkube run --help

# 각 옵션별 테스트
sbkube run --from-step template --dry-run
sbkube run --to-step build --dry-run
sbkube run --only template --dry-run

# 테스트 실행
pytest tests/unit/commands/test_run.py::TestRunCommandStepControl -v
pytest tests/integration/test_run_step_control.py -v
```

## 📝 예상 결과

```bash
$ sbkube run --from-step template
📋 실행할 단계: template → deploy
🚀 Template 단계 시작...
✅ Template 단계 완료
🚀 Deploy 단계 시작...
✅ Deploy 단계 완료

$ sbkube run --only build
📋 실행할 단계: build
🚀 Build 단계 시작...
✅ Build 단계 완료
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `003-sbkube-run-error-handling.md` - 오류 처리 및 사용자 안내