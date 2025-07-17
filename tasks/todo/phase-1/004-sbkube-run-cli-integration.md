---
phase: 1
order: 4
source_plan: /tasks/plan/phase1-basic-convenience.md
priority: medium
tags: [run-command, cli-integration, help-messages]
estimated_days: 1
depends_on: [003-sbkube-run-error-handling]
---

# 📌 작업: sbkube run CLI 통합 및 최종 검증

## 🎯 목표
`sbkube run` 명령어를 메인 CLI에 통합하고, 도움말 메시지를 완성하여 사용자가 쉽게 활용할 수 있도록 합니다.

## 📋 작업 내용

### 1. CLI 메인 파일에 명령어 등록
```python
# sbkube/cli.py 수정
from sbkube.commands import (
    build,
    delete,
    deploy,
    prepare,
    state,
    template,
    upgrade,
    validate,
    version,
    run,  # 새로 추가
)

# 기존 명령어 등록 부분에 추가
main.add_command(prepare.cmd)
main.add_command(build.cmd)
main.add_command(template.cmd)
main.add_command(deploy.cmd)
main.add_command(upgrade.cmd)
main.add_command(delete.cmd)
main.add_command(validate.cmd)
main.add_command(version.cmd)
main.add_command(state.state)
main.add_command(run.cmd)  # 새로 추가
```

### 2. 도움말 메시지 개선
```python
# sbkube/commands/run.py의 CLI 인터페이스 최종 버전
@click.command(name="run")
@click.option("--app-dir", default="config", 
              help="앱 설정 디렉토리 (기본값: config)")
@click.option("--base-dir", default=".", 
              help="프로젝트 루트 디렉토리 (기본값: .)")
@click.option("--app", 
              help="실행할 특정 앱 이름 (미지정시 모든 앱)")
@click.option("--config-file", 
              help="사용할 설정 파일 이름 (기본값: config.yaml)")
@click.option("--from-step", 
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="시작할 단계 지정")
@click.option("--to-step",
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="종료할 단계 지정")
@click.option("--only",
              type=click.Choice(["prepare", "build", "template", "deploy"]),
              help="특정 단계만 실행")
@click.option("--dry-run", is_flag=True,
              help="실제 실행 없이 계획만 표시")
@click.pass_context
def cmd(ctx, app_dir, base_dir, app, config_file, from_step, to_step, only, dry_run):
    """전체 워크플로우를 통합 실행합니다.
    
    prepare → build → template → deploy 단계를 순차적으로 실행하며,
    각 단계별 진행 상황을 실시간으로 표시합니다.
    
    \b
    기본 사용법:
        sbkube run                                  # 전체 워크플로우 실행
        sbkube run --app web-frontend               # 특정 앱만 실행
        sbkube run --dry-run                        # 실행 계획만 표시
    
    \b
    단계별 실행 제어:
        sbkube run --from-step template             # template부터 실행
        sbkube run --to-step build                  # build까지만 실행
        sbkube run --only template                  # template만 실행
        sbkube run --from-step build --to-step template  # build와 template만
    
    \b
    환경 설정:
        sbkube run --app-dir production             # 다른 설정 디렉토리
        sbkube run --config-file prod-config.yaml  # 다른 설정 파일
        
    \b
    문제 해결:
        sbkube run --from-step <단계>               # 실패한 단계부터 재시작
        sbkube validate                             # 설정 파일 검증
        sbkube run -v                               # 상세 로그 출력
    """
    # 기존 구현 코드...
```

### 3. Dry-run 기능 추가
```python
# sbkube/commands/run.py에 dry-run 기능 추가
class RunCommand(BaseCommand):
    def __init__(self, base_dir: str, app_config_dir: str, 
                 target_app_name: str = None, config_file_name: str = None,
                 from_step: str = None, to_step: str = None, only_step: str = None,
                 dry_run: bool = False):
        super().__init__(base_dir, app_config_dir, target_app_name, config_file_name)
        self.from_step = from_step
        self.to_step = to_step
        self.only_step = only_step
        self.dry_run = dry_run
    
    def execute(self):
        """단계별 실행 제어를 적용한 실행"""
        steps = self._determine_steps()
        
        if self.dry_run:
            self._show_execution_plan(steps)
            return
        
        logger.info(f"📋 실행할 단계: {' → '.join(steps)}")
        
        for i, step in enumerate(steps):
            try:
                logger.info(f"🚀 {step.title()} 단계 시작... ({i+1}/{len(steps)})")
                self._execute_step(step)
                logger.success(f"✅ {step.title()} 단계 완료")
                
            except Exception as e:
                self._handle_step_failure(step, e, i+1, len(steps))
                raise RunExecutionError(step, str(e), self._get_failure_suggestions(step, e))
    
    def _show_execution_plan(self, steps: List[str]):
        """실행 계획 표시 (dry-run 모드)"""
        from rich.table import Table
        from rich.console import Console
        
        console = Console()
        table = Table(title="🔍 실행 계획 (Dry Run)")
        table.add_column("순서", style="cyan", width=6)
        table.add_column("단계", style="magenta", width=12)
        table.add_column("설명", style="white")
        table.add_column("예상 시간", style="green", width=10)
        
        step_descriptions = {
            "prepare": "외부 소스 다운로드 (Helm 차트, Git 리포지토리 등)",
            "build": "앱 빌드 및 로컬 파일 복사",
            "template": "Helm 차트 템플릿 렌더링",
            "deploy": "Kubernetes 클러스터에 배포"
        }
        
        estimated_times = {
            "prepare": "1-3분",
            "build": "1-2분", 
            "template": "30초",
            "deploy": "2-5분"
        }
        
        for i, step in enumerate(steps, 1):
            table.add_row(
                str(i),
                step.title(),
                step_descriptions.get(step, ""),
                estimated_times.get(step, "?")
            )
        
        console.print(table)
        console.print(f"\n💡 실제 실행: [bold cyan]sbkube run[/bold cyan]")
        console.print(f"💡 특정 단계부터: [bold cyan]sbkube run --from-step {steps[0]}[/bold cyan]")
```

### 4. 명령어 도움말 테스트
```python
# tests/integration/test_run_cli_integration.py
from click.testing import CliRunner
from sbkube.cli import main

class TestRunCLIIntegration:
    def test_run_command_in_main_cli(self):
        """메인 CLI에서 run 명령어 확인"""
        runner = CliRunner()
        result = runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'run' in result.output
    
    def test_run_help_message(self):
        """run 명령어 도움말 메시지"""
        runner = CliRunner()
        result = runner.invoke(main, ['run', '--help'])
        
        assert result.exit_code == 0
        assert '전체 워크플로우를 통합 실행' in result.output
        assert '--from-step' in result.output
        assert '--to-step' in result.output
        assert '--only' in result.output
        assert '--dry-run' in result.output
        assert '기본 사용법:' in result.output
        assert '단계별 실행 제어:' in result.output
    
    def test_dry_run_functionality(self):
        """dry-run 기능 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 기본 프로젝트 구조 생성
            import os
            os.makedirs('config')
            
            result = runner.invoke(main, ['run', '--dry-run'])
            
            assert result.exit_code == 0
            assert '실행 계획' in result.output
            assert 'Dry Run' in result.output
    
    def test_run_with_global_options(self):
        """전역 옵션과 함께 run 명령어 테스트"""
        runner = CliRunner()
        result = runner.invoke(main, ['-v', 'run', '--dry-run'])
        
        assert result.exit_code == 0
```

### 5. 최종 통합 테스트
```python
# tests/e2e/test_run_end_to_end.py
import pytest
from click.testing import CliRunner
from sbkube.cli import main
import tempfile
import os

class TestRunEndToEnd:
    def test_complete_run_workflow(self):
        """완전한 run 워크플로우 E2E 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            # 완전한 테스트 프로젝트 설정
            self._setup_test_project()
            
            # 전체 실행 테스트
            result = runner.invoke(main, ['run'])
            
            # 기본적인 성공 확인 (실제 K8s 없이도 일부 단계는 진행)
            assert 'Prepare 단계 시작' in result.output
    
    def test_run_with_various_options(self):
        """다양한 옵션 조합 테스트"""
        runner = CliRunner()
        
        with runner.isolated_filesystem():
            self._setup_test_project()
            
            # 각 옵션별 테스트
            test_cases = [
                ['run', '--dry-run'],
                ['run', '--from-step', 'build', '--dry-run'],
                ['run', '--to-step', 'template', '--dry-run'],
                ['run', '--only', 'prepare', '--dry-run'],
            ]
            
            for args in test_cases:
                result = runner.invoke(main, args)
                assert result.exit_code == 0, f"Failed with args: {args}"
    
    def _setup_test_project(self):
        """테스트 프로젝트 기본 구조 생성"""
        os.makedirs('config', exist_ok=True)
        
        # 기본 config.yaml
        with open('config/config.yaml', 'w') as f:
            f.write("""
namespace: test-ns
apps:
  - name: test-app
    type: install-yaml
    specs:
      actions:
        - type: apply
          path: manifests/test.yaml
""")
        
        # 기본 sources.yaml
        with open('config/sources.yaml', 'w') as f:
            f.write("""
helm_repos: []
git_repos: []
""")
        
        # 테스트 매니페스트
        os.makedirs('manifests', exist_ok=True)
        with open('manifests/test.yaml', 'w') as f:
            f.write("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: test-config
data:
  test: "value"
""")
```

## ✅ 완료 기준

- [x] 메인 CLI에 run 명령어 정상 등록
- [x] 완전한 도움말 메시지 구현
- [x] dry-run 기능 구현 및 동작 확인
- [x] 모든 옵션 조합 테스트 통과
- [x] E2E 테스트 통과
- [x] 메인 CLI에서 run 명령어 정상 실행

## 🔍 검증 명령어

```bash
# CLI 통합 확인
sbkube --help | grep run

# 도움말 메시지 확인
sbkube run --help

# dry-run 테스트
sbkube run --dry-run

# 전역 옵션과 함께 테스트
sbkube -v run --dry-run

# 전체 테스트 실행
pytest tests/integration/test_run_cli_integration.py -v
pytest tests/e2e/test_run_end_to_end.py -v
```

## 📝 예상 결과

```bash
$ sbkube --help
Usage: sbkube [OPTIONS] COMMAND [ARGS]...

  sbkube: Kubernetes 애플리케이션 관리를 위한 CLI 도구.

Commands:
  build      앱을 빌드합니다.
  delete     배포된 리소스를 삭제합니다.
  deploy     애플리케이션을 배포합니다.
  prepare    외부 소스를 준비합니다.
  run        전체 워크플로우를 통합 실행합니다.  ← 새로 추가
  state      배포 상태를 관리합니다.
  template   템플릿을 렌더링합니다.
  upgrade    릴리스를 업그레이드합니다.
  validate   설정 파일을 검증합니다.
  version    버전 정보를 표시합니다.

$ sbkube run --dry-run
┏━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ 순서 ┃ 단계       ┃ 설명                                             ┃ 예상 시간 ┃
┡━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 1    │ Prepare    │ 외부 소스 다운로드 (Helm 차트, Git 리포지토리 등) │ 1-3분    │
│ 2    │ Build      │ 앱 빌드 및 로컬 파일 복사                        │ 1-2분    │
│ 3    │ Template   │ Helm 차트 템플릿 렌더링                          │ 30초     │
│ 4    │ Deploy     │ Kubernetes 클러스터에 배포                       │ 2-5분    │
└──────┴────────────┴──────────────────────────────────────────────────┴──────────┘

💡 실제 실행: sbkube run
💡 특정 단계부터: sbkube run --from-step prepare
```

## 🔄 다음 단계

이 작업 완료 후 sbkube run 명령어 구현이 완료되며, 다음 단계로 진행:
- `005-sbkube-init-template-system.md` - sbkube init 명령어 템플릿 시스템 구현