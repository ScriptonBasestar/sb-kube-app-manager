---
phase: 1
order: 5
source_plan: /tasks/plan/phase1-basic-convenience.md
priority: high
tags: [init-command, template-system, jinja2]
estimated_days: 4
depends_on: [004-sbkube-run-cli-integration]
completion_date: 2025-07-17
status: COMPLETED
---

# 📌 작업: sbkube init 템플릿 시스템 구현 ✅ 완료

## 🎯 목표 ✅
`sbkube init` 명령어의 기본 템플릿 시스템을 구현하여 사용자가 새 프로젝트를 쉽게 초기화할 수 있도록 합니다.

## 📋 작업 내용

### 1. 기본 템플릿 구조 생성 ✅
```bash
# 템플릿 디렉토리 구조 생성
mkdir -p sbkube/templates/basic
mkdir -p sbkube/templates/web-app
mkdir -p sbkube/templates/microservice
```

### 2. 기본 템플릿 파일 생성 ✅
```yaml
# sbkube/templates/basic/config.yaml.j2
namespace: {{ project_name }}

deps: []

apps:
  - name: {{ app_name }}
    type: {{ app_type }}
    enabled: true
    namespace: {{ namespace or project_name }}
    {% if app_type == 'install-helm' %}
    specs:
      path: {{ app_name }}
      values:
        - {{ app_name }}-values.yaml
    {% elif app_type == 'install-yaml' %}
    specs:
      actions:
        - type: apply
          path: manifests/{{ app_name }}.yaml
    {% endif %}
```

```yaml
# sbkube/templates/basic/sources.yaml.j2
helm_repos:
  {% if use_bitnami %}
  - name: bitnami
    url: https://charts.bitnami.com/bitnami
  {% endif %}
  {% if use_prometheus %}
  - name: prometheus-community
    url: https://prometheus-community.github.io/helm-charts
  {% endif %}

git_repos: []
```

```yaml
# sbkube/templates/basic/values/app-values.yaml.j2
# {{ app_name }} Helm Values
replicaCount: {{ replica_count or 1 }}

image:
  repository: {{ image_repository or 'nginx' }}
  tag: {{ image_tag or 'latest' }}
  pullPolicy: IfNotPresent

service:
  type: {{ service_type or 'ClusterIP' }}
  port: {{ service_port or 80 }}

resources:
  limits:
    cpu: {{ cpu_limit or '100m' }}
    memory: {{ memory_limit or '128Mi' }}
  requests:
    cpu: {{ cpu_request or '100m' }}
    memory: {{ memory_request or '128Mi' }}
```

### 3. InitCommand 클래스 구현 ✅
```python
# sbkube/commands/init.py
import os
from pathlib import Path
from typing import Dict, Any, Optional
import click
from jinja2 import Environment, FileSystemLoader, Template
import yaml

from sbkube.utils.base_command import BaseCommand
from sbkube.utils.logger import logger

class InitCommand(BaseCommand):
    def __init__(self, base_dir: str, template_name: str = "basic", 
                 project_name: str = None, interactive: bool = True):
        self.base_dir = Path(base_dir).resolve()
        self.template_name = template_name
        self.project_name = project_name
        self.interactive = interactive
        self.template_vars = {}
        
    def execute(self):
        """프로젝트 초기화 실행"""
        logger.info("🚀 새 프로젝트 초기화를 시작합니다...")
        
        # 1. 프로젝트 정보 수집
        self._collect_project_info()
        
        # 2. 템플릿 검증
        self._validate_template()
        
        # 3. 디렉토리 구조 생성
        self._create_directory_structure()
        
        # 4. 템플릿 렌더링 및 파일 생성
        self._render_templates()
        
        # 5. README 파일 생성
        self._create_readme()
        
        logger.success("✅ 프로젝트 초기화가 완료되었습니다!")
        self._show_next_steps()
    
    def _collect_project_info(self):
        """프로젝트 정보 수집"""
        if self.interactive:
            self._interactive_input()
        else:
            self._set_default_values()
    
    def _interactive_input(self):
        """대화형 입력"""
        logger.info("📝 프로젝트 정보를 입력해주세요:")
        
        # 기본 정보
        if not self.project_name:
            self.project_name = click.prompt(
                "프로젝트 이름", 
                default=self.base_dir.name,
                type=str
            )
        
        self.template_vars.update({
            'project_name': self.project_name,
            'namespace': click.prompt(
                "기본 네임스페이스", 
                default=self.project_name,
                type=str
            ),
            'app_name': click.prompt(
                "앱 이름", 
                default=self.project_name,
                type=str
            ),
            'app_type': click.prompt(
                "애플리케이션 타입",
                type=click.Choice(['install-helm', 'install-yaml', 'copy-app']),
                default='install-helm'
            )
        })
        
        # 추가 설정
        if click.confirm("환경별 설정을 생성하시겠습니까?", default=True):
            self.template_vars['create_environments'] = True
            self.template_vars['environments'] = ['development', 'staging', 'production']
        
        if click.confirm("Bitnami Helm 저장소를 추가하시겠습니까?", default=True):
            self.template_vars['use_bitnami'] = True
            
        if click.confirm("Prometheus 모니터링을 설정하시겠습니까?", default=False):
            self.template_vars['use_prometheus'] = True
    
    def _set_default_values(self):
        """기본값 설정"""
        self.template_vars.update({
            'project_name': self.project_name or self.base_dir.name,
            'namespace': self.project_name or self.base_dir.name,
            'app_name': self.project_name or self.base_dir.name,
            'app_type': 'install-helm',
            'create_environments': True,
            'environments': ['development', 'staging', 'production'],
            'use_bitnami': True,
            'use_prometheus': False
        })
    
    def _validate_template(self):
        """템플릿 존재 확인"""
        template_dir = self._get_template_dir()
        if not template_dir.exists():
            raise ValueError(f"템플릿 '{self.template_name}'을 찾을 수 없습니다: {template_dir}")
    
    def _create_directory_structure(self):
        """디렉토리 구조 생성"""
        directories = [
            "config",
            "values",
            "manifests",
        ]
        
        if self.template_vars.get('create_environments'):
            for env in self.template_vars.get('environments', []):
                directories.extend([
                    f"values/{env}",
                    f"config-{env}"
                ])
        
        for dir_name in directories:
            dir_path = self.base_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.verbose(f"디렉토리 생성: {dir_path}")
    
    def _render_templates(self):
        """템플릿 렌더링 및 파일 생성"""
        template_dir = self._get_template_dir()
        env = Environment(loader=FileSystemLoader(template_dir))
        
        template_files = [
            ("config.yaml.j2", "config/config.yaml"),
            ("sources.yaml.j2", "config/sources.yaml"),
            ("values/app-values.yaml.j2", f"values/{self.template_vars['app_name']}-values.yaml"),
        ]
        
        for template_file, output_file in template_files:
            self._render_single_template(env, template_file, output_file)
        
        # 환경별 설정 파일 생성
        if self.template_vars.get('create_environments'):
            self._create_environment_configs(env)
    
    def _render_single_template(self, env: Environment, template_file: str, output_file: str):
        """단일 템플릿 렌더링"""
        try:
            template = env.get_template(template_file)
            content = template.render(**self.template_vars)
            
            output_path = self.base_dir / output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ 생성됨: {output_file}")
            
        except Exception as e:
            logger.error(f"❌ 템플릿 렌더링 실패 ({template_file}): {e}")
            raise
    
    def _create_environment_configs(self, env: Environment):
        """환경별 설정 파일 생성"""
        base_template = env.get_template("config.yaml.j2")
        
        for environment in self.template_vars.get('environments', []):
            env_vars = self.template_vars.copy()
            env_vars.update({
                'environment': environment,
                'namespace': f"{self.template_vars['project_name']}-{environment}"
            })
            
            content = base_template.render(**env_vars)
            output_file = f"config/config-{environment}.yaml"
            output_path = self.base_dir / output_file
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ 환경 설정 생성됨: {output_file}")
    
    def _create_readme(self):
        """README 파일 생성"""
        readme_content = f"""# {self.template_vars['project_name']}

이 프로젝트는 SBKube로 초기화되었습니다.

## 🚀 빠른 시작

```bash
# 전체 워크플로우 실행
sbkube run

# 단계별 실행
sbkube prepare
sbkube build
sbkube template
sbkube deploy
```

## 📁 디렉토리 구조

- `config/` - 애플리케이션 설정 파일
- `values/` - Helm values 파일
- `manifests/` - YAML 매니페스트 파일

## 🔧 설정 파일

- `config/config.yaml` - 메인 설정 파일
- `config/sources.yaml` - 외부 소스 설정
{'- `config/config-*.yaml` - 환경별 설정' if self.template_vars.get('create_environments') else ''}

## 💡 사용 예제

```bash
# 특정 환경 배포
sbkube run --profile production

# 특정 단계만 실행
sbkube run --only template

# 설정 검증
sbkube validate
```

## 📚 문서

더 자세한 사용법은 [SBKube 문서](docs/INDEX.md)를 참조하세요.
"""
        
        readme_path = self.base_dir / "README.md"
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info("✅ README.md 생성됨")
    
    def _get_template_dir(self) -> Path:
        """템플릿 디렉토리 경로 반환"""
        # 패키지 내 템플릿 디렉토리
        import sbkube
        package_dir = Path(sbkube.__file__).parent
        return package_dir / "templates" / self.template_name
    
    def _show_next_steps(self):
        """다음 단계 안내"""
        logger.info("\n🎉 프로젝트가 성공적으로 초기화되었습니다!")
        logger.info("\n💡 다음 단계:")
        logger.info("   1. 설정 파일을 검토하고 필요에 따라 수정하세요")
        logger.info("   2. sbkube validate로 설정을 검증하세요")
        logger.info("   3. sbkube run으로 전체 워크플로우를 실행하세요")
        logger.info(f"\n📁 생성된 파일:")
        
        created_files = [
            "config/config.yaml",
            "config/sources.yaml", 
            f"values/{self.template_vars['app_name']}-values.yaml",
            "README.md"
        ]
        
        if self.template_vars.get('create_environments'):
            for env in self.template_vars.get('environments', []):
                created_files.append(f"config/config-{env}.yaml")
        
        for file_path in created_files:
            if (self.base_dir / file_path).exists():
                logger.info(f"   ✅ {file_path}")
```

### 4. CLI 인터페이스 구현 ✅
```python
# sbkube/commands/init.py (계속)
@click.command(name="init")
@click.option("--template", default="basic",
              type=click.Choice(["basic", "web-app", "microservice"]),
              help="사용할 템플릿 (기본값: basic)")
@click.option("--name", 
              help="프로젝트 이름 (기본값: 현재 디렉토리명)")
@click.option("--non-interactive", is_flag=True,
              help="대화형 입력 없이 기본값으로 생성")
@click.option("--force", is_flag=True,
              help="기존 파일이 있어도 덮어쓰기")
@click.pass_context
def cmd(ctx, template, name, non_interactive, force):
    """새 프로젝트를 초기화합니다.
    
    기본 설정 파일들과 디렉토리 구조를 자동으로 생성하여
    새 프로젝트를 빠르게 시작할 수 있도록 도와줍니다.
    
    \b
    사용 예시:
        sbkube init                          # 기본 템플릿으로 대화형 초기화
        sbkube init --template web-app       # 웹앱 템플릿 사용
        sbkube init --name my-project        # 프로젝트명 지정
        sbkube init --non-interactive        # 대화형 입력 없이 생성
    """
    base_dir = os.getcwd()
    
    # 기존 파일 확인
    if not force:
        existing_files = ["config/config.yaml", "config/sources.yaml"]
        found_files = [f for f in existing_files if os.path.exists(f)]
        
        if found_files:
            logger.warning(f"다음 파일들이 이미 존재합니다: {', '.join(found_files)}")
            if not click.confirm("기존 파일을 덮어쓰시겠습니까?"):
                logger.info("초기화가 취소되었습니다.")
                return
    
    command = InitCommand(
        base_dir=base_dir,
        template_name=template,
        project_name=name,
        interactive=not non_interactive
    )
    
    try:
        command.execute()
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}")
        sys.exit(1)
```

## 🧪 테스트 구현 ✅

### 단위 테스트 ✅
```python
# tests/unit/commands/test_init.py
import pytest
import tempfile
from pathlib import Path
from sbkube.commands.init import InitCommand

class TestInitCommand:
    def test_init_basic_template(self):
        """기본 템플릿 초기화 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="test-project",
                interactive=False
            )
            
            cmd.execute()
            
            # 생성된 파일 확인
            assert (Path(tmpdir) / "config" / "config.yaml").exists()
            assert (Path(tmpdir) / "config" / "sources.yaml").exists()
            assert (Path(tmpdir) / "README.md").exists()
    
    def test_template_rendering(self):
        """템플릿 렌더링 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(
                base_dir=tmpdir,
                template_name="basic",
                project_name="my-app",
                interactive=False
            )
            
            cmd.template_vars = {
                'project_name': 'my-app',
                'app_name': 'my-app',
                'namespace': 'my-app',
                'app_type': 'install-helm'
            }
            
            cmd._create_directory_structure()
            cmd._render_templates()
            
            # config.yaml 내용 확인
            config_file = Path(tmpdir) / "config" / "config.yaml"
            content = config_file.read_text()
            
            assert 'namespace: my-app' in content
            assert 'name: my-app' in content
```

## ✅ 완료 기준

- [x] 기본 템플릿 파일들 생성 (config.yaml.j2, sources.yaml.j2, values.yaml.j2)
- [x] InitCommand 클래스 구현
- [x] 대화형 입력 시스템 구현
- [x] 템플릿 렌더링 로직 구현
- [x] CLI 인터페이스 구현
- [x] 환경별 설정 파일 생성 기능
- [x] README 자동 생성 기능
- [x] 기본 테스트 케이스 통과

## 🏆 구현 완료 사항

1. **템플릿 시스템**: `/sbkube/templates/basic/` 디렉토리에 Jinja2 템플릿 파일들 생성
2. **InitCommand 클래스**: 완전한 프로젝트 초기화 로직 구현
3. **CLI 통합**: 메인 CLI에 `init` 명령어 등록 및 모든 옵션 지원
4. **테스트 커버리지**: 단위, 통합, E2E 테스트 모두 구현
5. **환경별 설정**: 개발/스테이징/프로덕션 환경 설정 자동 생성
6. **대화형 UI**: Click 기반 사용자 친화적 입력 시스템

## 🔍 검증 명령어

```bash
# 새 디렉토리에서 테스트
mkdir test-project && cd test-project
sbkube init

# 다양한 옵션 테스트
sbkube init --template basic --name my-project
sbkube init --non-interactive
sbkube init --help

# 생성된 파일 확인
ls -la config/
cat config/config.yaml

# 테스트 실행
pytest tests/unit/commands/test_init.py -v
```

## 📝 예상 결과

```bash
$ sbkube init
🚀 새 프로젝트 초기화를 시작합니다...
📝 프로젝트 정보를 입력해주세요:
프로젝트 이름 [test-project]: my-app
기본 네임스페이스 [my-app]: 
앱 이름 [my-app]: 
애플리케이션 타입 [install-helm]: 
환경별 설정을 생성하시겠습니까? [Y/n]: y
Bitnami Helm 저장소를 추가하시겠습니까? [Y/n]: y

✅ 생성됨: config/config.yaml
✅ 생성됨: config/sources.yaml  
✅ 생성됨: values/my-app-values.yaml
✅ 환경 설정 생성됨: config/config-development.yaml
✅ 환경 설정 생성됨: config/config-staging.yaml
✅ 환경 설정 생성됨: config/config-production.yaml
✅ README.md 생성됨
✅ 프로젝트 초기화가 완료되었습니다!

💡 다음 단계:
   1. 설정 파일을 검토하고 필요에 따라 수정하세요
   2. sbkube validate로 설정을 검증하세요
   3. sbkube run으로 전체 워크플로우를 실행하세요
```

## 🔄 다음 단계

이 작업 완료 후 다음 작업으로 진행:
- `006-profile-system-design.md` - 프로파일 시스템 설계 (Phase 2)

---
**✅ 작업 완료:** 2025-07-17
**🎯 완료율:** 100%
**🧪 테스트:** 통과
**📦 통합:** CLI 등록 완료