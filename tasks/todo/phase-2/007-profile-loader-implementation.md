---
phase: 2
order: 7
source_plan: /tasks/plan/phase2-advanced-features.md
priority: high
tags: [profile-system, cli-integration, configuration]
estimated_days: 3
depends_on: [006-profile-system-design]
---

# 📌 작업: 프로파일 로더 고도화 및 CLI 통합

## 🎯 목표
ProfileManager를 활용하여 모든 명령어에 프로파일 기능을 통합하고 프로파일 관리 명령어를 구현합니다.

## 📋 작업 내용

### 1. 프로파일 로더 클래스 구현
```python
# sbkube/utils/profile_loader.py
from typing import Dict, Any, Optional
from pathlib import Path
import os
from sbkube.utils.profile_manager import ProfileManager
from sbkube.utils.logger import logger

class ProfileLoader:
    """프로파일 로딩과 CLI 통합을 위한 헬퍼 클래스"""
    
    def __init__(self, base_dir: str = None):
        self.base_dir = base_dir or os.getcwd()
        self.profile_manager = ProfileManager(self.base_dir, "config")
    
    def load_with_overrides(self, 
                          profile_name: str = None,
                          cli_overrides: Dict[str, Any] = None,
                          env_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """프로파일과 오버라이드를 적용한 최종 설정 로드"""
        
        # 기본 설정 로드
        base_config = self.profile_manager.load_profile(profile_name)
        
        # 환경변수 오버라이드 수집
        if env_overrides is None:
            env_overrides = self._collect_env_overrides()
        
        # 우선순위 적용
        from sbkube.utils.profile_manager import ConfigPriority
        final_config = ConfigPriority.apply_overrides(
            base_config=base_config,
            env_overrides=env_overrides,
            cli_overrides=cli_overrides or {}
        )
        
        logger.verbose(f"프로파일 '{profile_name or 'default'}' 로드 완료")
        return final_config
    
    def _collect_env_overrides(self) -> Dict[str, Any]:
        """환경변수에서 설정 오버라이드 수집"""
        overrides = {}
        
        # SBKUBE_ 접두사를 가진 환경변수 수집
        for key, value in os.environ.items():
            if key.startswith('SBKUBE_'):
                config_key = key[7:].lower()  # SBKUBE_ 제거 후 소문자 변환
                
                # 점으로 구분된 경로를 중첩 딕셔너리로 변환
                keys = config_key.split('_')
                current = overrides
                
                for k in keys[:-1]:
                    if k not in current:
                        current[k] = {}
                    current = current[k]
                
                # 값 타입 추론
                current[keys[-1]] = self._parse_env_value(value)
        
        return overrides
    
    def _parse_env_value(self, value: str) -> Any:
        """환경변수 값의 타입 파싱"""
        # 불린 값
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # 숫자 값
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # 리스트 값 (쉼표로 구분)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # 문자열 값
        return value
    
    def validate_and_load(self, profile_name: str = None) -> Dict[str, Any]:
        """프로파일 검증 후 로드"""
        if profile_name:
            validation = self.profile_manager.validate_profile(profile_name)
            if not validation['valid']:
                logger.error(f"프로파일 '{profile_name}' 검증 실패:")
                for error in validation['errors']:
                    logger.error(f"  - {error}")
                raise ValueError(f"Invalid profile: {profile_name}")
            
            if validation['warnings']:
                for warning in validation['warnings']:
                    logger.warning(f"  ⚠️  {warning}")
        
        return self.load_with_overrides(profile_name)
    
    def list_available_profiles(self) -> List[Dict[str, Any]]:
        """사용 가능한 프로파일 목록 반환"""
        return self.profile_manager.list_profiles()
```

### 2. 기본 명령어에 프로파일 옵션 추가
```python
# sbkube/utils/base_command.py 수정
from typing import Optional, Dict, Any
from sbkube.utils.profile_loader import ProfileLoader

class BaseCommand:
    def __init__(self, base_dir: str, profile: str = None, **kwargs):
        self.base_dir = base_dir
        self.profile = profile
        self.profile_loader = ProfileLoader(base_dir)
        self.config = None
        
    def load_config(self, cli_overrides: Dict[str, Any] = None) -> Dict[str, Any]:
        """설정 로드 (프로파일 + 오버라이드 적용)"""
        if self.config is None:
            self.config = self.profile_loader.validate_and_load(
                profile_name=self.profile
            )
            
            # CLI 오버라이드 적용
            if cli_overrides:
                from sbkube.utils.profile_manager import ConfigPriority
                self.config = ConfigPriority.apply_overrides(
                    base_config=self.config,
                    cli_overrides=cli_overrides
                )
        
        return self.config
```

### 3. 프로파일 관리 명령어 구현
```python
# sbkube/commands/profiles.py
import click
import sys
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sbkube.utils.profile_loader import ProfileLoader
from sbkube.utils.logger import logger

console = Console()

@click.group(name="profiles")
def profiles_group():
    """프로파일 관리 명령어"""
    pass

@profiles_group.command("list")
@click.option("--detailed", is_flag=True, help="상세 정보 표시")
@click.pass_context
def list_profiles(ctx, detailed):
    """사용 가능한 프로파일 목록 조회"""
    try:
        loader = ProfileLoader()
        profiles = loader.list_available_profiles()
        
        if not profiles:
            console.print("⚠️  사용 가능한 프로파일이 없습니다.")
            console.print("💡 'sbkube init' 명령어로 프로젝트를 초기화하세요.")
            return
        
        if detailed:
            _show_detailed_profiles(profiles)
        else:
            _show_simple_profiles(profiles)
            
    except Exception as e:
        logger.error(f"❌ 프로파일 목록 조회 실패: {e}")
        sys.exit(1)

@profiles_group.command("validate")
@click.argument("profile_name", required=False)
@click.option("--all", is_flag=True, help="모든 프로파일 검증")
@click.pass_context
def validate_profile(ctx, profile_name, all):
    """프로파일 설정 검증"""
    try:
        loader = ProfileLoader()
        
        if all:
            _validate_all_profiles(loader)
        elif profile_name:
            _validate_single_profile(loader, profile_name)
        else:
            # 기본 프로파일 검증
            _validate_single_profile(loader, None)
            
    except Exception as e:
        logger.error(f"❌ 프로파일 검증 실패: {e}")
        sys.exit(1)

@profiles_group.command("show")
@click.argument("profile_name")
@click.option("--merged", is_flag=True, help="병합된 최종 설정 표시")
@click.pass_context
def show_profile(ctx, profile_name, merged):
    """프로파일 설정 내용 표시"""
    try:
        loader = ProfileLoader()
        
        if merged:
            config = loader.load_with_overrides(profile_name)
            console.print(f"\n🔧 프로파일 '{profile_name}' 병합된 설정:")
        else:
            config = loader.profile_manager.load_profile(profile_name)
            console.print(f"\n📋 프로파일 '{profile_name}' 원본 설정:")
        
        import yaml
        yaml_output = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        console.print(Panel(yaml_output, expand=False))
        
    except Exception as e:
        logger.error(f"❌ 프로파일 조회 실패: {e}")
        sys.exit(1)

def _show_simple_profiles(profiles: List[Dict[str, Any]]):
    """간단한 프로파일 목록 표시"""
    table = Table(title="🏷️  사용 가능한 프로파일")
    table.add_column("이름", style="cyan")
    table.add_column("네임스페이스", style="green")
    table.add_column("앱 수", justify="center")
    table.add_column("상태", justify="center")
    
    for profile in profiles:
        status = "✅" if profile["valid"] else "❌"
        table.add_row(
            profile["name"],
            profile["namespace"],
            str(profile["apps_count"]),
            status
        )
    
    console.print(table)

def _show_detailed_profiles(profiles: List[Dict[str, Any]]):
    """상세한 프로파일 정보 표시"""
    for i, profile in enumerate(profiles):
        if i > 0:
            console.print()
        
        status_color = "green" if profile["valid"] else "red"
        status_text = "유효" if profile["valid"] else "오류"
        
        panel_content = f"""[bold]네임스페이스:[/bold] {profile['namespace']}
[bold]앱 개수:[/bold] {profile['apps_count']}
[bold]상태:[/bold] [{status_color}]{status_text}[/{status_color}]
[bold]오류:[/bold] {profile['errors']}개
[bold]경고:[/bold] {profile['warnings']}개"""
        
        if 'error_message' in profile:
            panel_content += f"\n[bold red]오류 메시지:[/bold red] {profile['error_message']}"
        
        console.print(Panel(
            panel_content,
            title=f"📋 {profile['name']}",
            expand=False
        ))

def _validate_single_profile(loader: ProfileLoader, profile_name: str):
    """단일 프로파일 검증"""
    validation = loader.profile_manager.validate_profile(profile_name or "default")
    
    profile_display = profile_name or "기본 설정"
    console.print(f"\n🔍 프로파일 '{profile_display}' 검증 결과:")
    
    if validation["valid"]:
        console.print("✅ 프로파일이 유효합니다!")
    else:
        console.print("❌ 프로파일에 오류가 있습니다:")
        for error in validation["errors"]:
            console.print(f"   • {error}")
    
    if validation["warnings"]:
        console.print("\n⚠️  경고사항:")
        for warning in validation["warnings"]:
            console.print(f"   • {warning}")

def _validate_all_profiles(loader: ProfileLoader):
    """모든 프로파일 검증"""
    profiles = loader.list_available_profiles()
    
    if not profiles:
        console.print("⚠️  검증할 프로파일이 없습니다.")
        return
    
    console.print(f"\n🔍 {len(profiles)}개 프로파일 검증 중...\n")
    
    valid_count = 0
    for profile in profiles:
        status = "✅" if profile["valid"] else "❌"
        console.print(f"{status} {profile['name']}: ", end="")
        
        if profile["valid"]:
            console.print("[green]유효[/green]")
            valid_count += 1
        else:
            console.print(f"[red]{profile['errors']}개 오류[/red]")
    
    console.print(f"\n📊 검증 완료: {valid_count}/{len(profiles)}개 프로파일이 유효합니다.")
```

### 4. 기존 명령어에 프로파일 옵션 통합
```python
# sbkube/commands/run.py 수정
@click.command(name="run")
@click.option("--profile", help="사용할 프로파일 이름")
@click.option("--only", help="특정 단계만 실행")
@click.option("--skip", help="특정 단계 건너뛰기")
@click.option("--namespace", help="네임스페이스 오버라이드")
@click.pass_context
def cmd(ctx, profile, only, skip, namespace):
    """통합 실행 명령어 (프로파일 지원)"""
    
    # CLI 오버라이드 수집
    cli_overrides = {}
    if namespace:
        cli_overrides['namespace'] = namespace
    
    command = RunCommand(
        base_dir=os.getcwd(),
        profile=profile,
        only=only,
        skip=skip
    )
    
    try:
        # 프로파일과 오버라이드가 적용된 설정 로드
        config = command.load_config(cli_overrides)
        logger.info(f"🏷️  프로파일: {profile or 'default'}")
        logger.info(f"🏠 네임스페이스: {config['namespace']}")
        
        command.execute()
        
    except Exception as e:
        logger.error(f"❌ 실행 실패: {e}")
        sys.exit(1)
```

### 5. 환경변수 지원 구현
```python
# sbkube/utils/env_support.py
import os
from typing import Dict, Any, List

class EnvironmentSupport:
    """환경변수 기반 설정 지원"""
    
    SUPPORTED_ENV_VARS = {
        'SBKUBE_PROFILE': 'profile',
        'SBKUBE_NAMESPACE': 'namespace',
        'SBKUBE_DEBUG': 'debug',
        'SBKUBE_VERBOSE': 'verbose',
        'SBKUBE_CONFIG_DIR': 'config_dir',
    }
    
    @classmethod
    def get_profile_from_env(cls) -> str:
        """환경변수에서 기본 프로파일 가져오기"""
        return os.environ.get('SBKUBE_PROFILE')
    
    @classmethod
    def get_cli_defaults(cls) -> Dict[str, Any]:
        """환경변수에서 CLI 기본값 가져오기"""
        defaults = {}
        
        for env_var, config_key in cls.SUPPORTED_ENV_VARS.items():
            value = os.environ.get(env_var)
            if value:
                defaults[config_key] = cls._parse_value(value)
        
        return defaults
    
    @staticmethod
    def _parse_value(value: str) -> Any:
        """환경변수 값 파싱"""
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        try:
            return int(value)
        except ValueError:
            return value
```

## 🧪 테스트 구현

### 단위 테스트
```python
# tests/unit/utils/test_profile_loader.py
import pytest
import tempfile
import os
from pathlib import Path
from sbkube.utils.profile_loader import ProfileLoader

class TestProfileLoader:
    def test_load_with_cli_overrides(self):
        """CLI 오버라이드 적용 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            self._create_test_profile(tmpdir)
            
            loader = ProfileLoader(tmpdir)
            config = loader.load_with_overrides(
                profile_name="development",
                cli_overrides={'namespace': 'override-ns'}
            )
            
            assert config['namespace'] == 'override-ns'
    
    def test_env_override_collection(self):
        """환경변수 오버라이드 수집 테스트"""
        loader = ProfileLoader(".")
        
        # 환경변수 설정
        os.environ['SBKUBE_NAMESPACE'] = 'env-namespace'
        os.environ['SBKUBE_DEBUG'] = 'true'
        
        try:
            overrides = loader._collect_env_overrides()
            assert overrides['namespace'] == 'env-namespace'
            assert overrides['debug'] is True
            
        finally:
            # 환경변수 정리
            os.environ.pop('SBKUBE_NAMESPACE', None)
            os.environ.pop('SBKUBE_DEBUG', None)
    
    def _create_test_profile(self, tmpdir):
        """테스트용 프로파일 생성"""
        config_dir = Path(tmpdir) / "config"
        config_dir.mkdir()
        
        base_config = {
            "namespace": "default",
            "apps": [{"name": "test-app", "type": "install-helm"}]
        }
        
        dev_config = {
            "namespace": "dev",
            "apps": [{"name": "test-app", "specs": {"replicas": 1}}]
        }
        
        import yaml
        with open(config_dir / "config.yaml", 'w') as f:
            yaml.dump(base_config, f)
        
        with open(config_dir / "config-development.yaml", 'w') as f:
            yaml.dump(dev_config, f)
```

## ✅ 완료 기준

- [ ] ProfileLoader 클래스 구현
- [ ] 환경변수 오버라이드 지원
- [ ] 모든 명령어에 --profile 옵션 추가
- [ ] 프로파일 관리 명령어 구현 (list, validate, show)
- [ ] CLI 오버라이드 우선순위 적용
- [ ] 기본 프로파일 지원
- [ ] 단위 테스트 작성 및 통과

## 🔍 검증 명령어

```bash
# 프로파일 목록 조회
sbkube profiles list
sbkube profiles list --detailed

# 프로파일 검증
sbkube profiles validate production
sbkube profiles validate --all

# 프로파일 내용 조회
sbkube profiles show development
sbkube profiles show development --merged

# 프로파일을 사용한 실행
sbkube run --profile production
sbkube deploy --profile staging --namespace custom-ns

# 환경변수 테스트
export SBKUBE_PROFILE=development
export SBKUBE_NAMESPACE=test-env
sbkube run

# 테스트 실행
pytest tests/unit/utils/test_profile_loader.py -v
```

## 📝 예상 결과

```bash
$ sbkube profiles list
🏷️  사용 가능한 프로파일
┌─────────────┬─────────────┬─────┬──────┐
│ 이름        │ 네임스페이스 │ 앱 수│ 상태 │
├─────────────┼─────────────┼─────┼──────┤
│ development │ dev         │  3  │  ✅  │
│ staging     │ staging     │  3  │  ✅  │
│ production  │ prod        │  3  │  ✅  │
└─────────────┴─────────────┴─────┴──────┘

$ sbkube run --profile production
🏷️  프로파일: production
🏠 네임스페이스: prod
🚀 준비 단계 시작...
✅ 준비 완료
🚀 빌드 단계 시작...
✅ 빌드 완료
🚀 템플릿 단계 시작...
✅ 템플릿 완료
🚀 배포 단계 시작...
✅ 배포 완료
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `008-smart-restart-execution-tracker.md` - 실행 상태 추적 시스템 구현