import os
import sys
from pathlib import Path

import click
from jinja2 import Environment, FileSystemLoader

from sbkube.utils.base_command import BaseCommand
from sbkube.utils.logger import logger


class InitCommand(BaseCommand):
    """프로젝트 초기화 명령어"""

    def __init__(
        self,
        base_dir: str,
        template_name: str = "basic",
        project_name: str | None = None,
        interactive: bool = True,
    ):
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
                "프로젝트 이름", default=self.base_dir.name, type=str
            )

        self.template_vars.update(
            {
                "project_name": self.project_name,
                "namespace": click.prompt(
                    "기본 네임스페이스", default=self.project_name, type=str
                ),
                "app_name": click.prompt(
                    "앱 이름", default=self.project_name, type=str
                ),
                "app_type": click.prompt(
                    "애플리케이션 타입",
                    type=click.Choice(["helm", "yaml", "http"]),
                    default="helm",
                ),
            }
        )

        # 추가 설정
        if click.confirm("환경별 설정을 생성하시겠습니까?", default=True):
            self.template_vars["create_environments"] = True
            self.template_vars["environments"] = [
                "development",
                "staging",
                "production",
            ]

        if click.confirm("Bitnami Helm 저장소를 추가하시겠습니까?", default=True):
            self.template_vars["use_bitnami"] = True

        if click.confirm("Prometheus 모니터링을 설정하시겠습니까?", default=False):
            self.template_vars["use_prometheus"] = True

    def _set_default_values(self):
        """기본값 설정"""
        self.template_vars.update(
            {
                "project_name": self.project_name or self.base_dir.name,
                "namespace": self.project_name or self.base_dir.name,
                "app_name": self.project_name or self.base_dir.name,
                "app_type": "helm",
                "create_environments": True,
                "environments": ["development", "staging", "production"],
                "use_bitnami": True,
                "use_prometheus": False,
            }
        )

    def _validate_template(self):
        """템플릿 존재 확인"""
        template_dir = self._get_template_dir()
        if not template_dir.exists():
            raise ValueError(
                f"템플릿 '{self.template_name}'을 찾을 수 없습니다: {template_dir}"
            )

    def _create_directory_structure(self):
        """디렉토리 구조 생성"""
        directories = [
            "config",
            "values",
            "manifests",
        ]

        if self.template_vars.get("create_environments"):
            for env in self.template_vars.get("environments", []):
                directories.extend([f"values/{env}", f"config-{env}"])

        for dir_name in directories:
            dir_path = self.base_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.verbose(f"디렉토리 생성: {dir_path}")

    def _render_templates(self):
        """템플릿 렌더링 및 파일 생성"""
        template_dir = self._get_template_dir()
        env = Environment(loader=FileSystemLoader(template_dir), autoescape=True)

        template_files = [
            ("config.yaml.j2", "config/config.yaml"),
            ("sources.yaml.j2", "config/sources.yaml"),
            (
                "values/app-values.yaml.j2",
                f"values/{self.template_vars['app_name']}-values.yaml",
            ),
        ]

        for template_file, output_file in template_files:
            self._render_single_template(env, template_file, output_file)

        # 환경별 설정 파일 생성
        if self.template_vars.get("create_environments"):
            self._create_environment_configs(env)

    def _render_single_template(
        self, env: Environment, template_file: str, output_file: str
    ):
        """단일 템플릿 렌더링"""
        try:
            template = env.get_template(template_file)
            content = template.render(**self.template_vars)

            output_path = self.base_dir / output_file
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"✅ 생성됨: {output_file}")

        except Exception as e:
            logger.error(f"❌ 템플릿 렌더링 실패 ({template_file}): {e}")
            raise

    def _create_environment_configs(self, env: Environment):
        """환경별 설정 파일 생성"""
        base_template = env.get_template("config.yaml.j2")

        for environment in self.template_vars.get("environments", []):
            env_vars = self.template_vars.copy()
            env_vars.update(
                {
                    "environment": environment,
                    "namespace": f"{self.template_vars['project_name']}-{environment}",
                }
            )

            content = base_template.render(**env_vars)
            output_file = f"config/config-{environment}.yaml"
            output_path = self.base_dir / output_file

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)

            logger.info(f"✅ 환경 설정 생성됨: {output_file}")

    def _create_readme(self):
        """README 파일 생성"""
        env_section = ""
        if self.template_vars.get("create_environments"):
            env_section = "- `config/config-*.yaml` - 환경별 설정"

        readme_content = f"""# {self.template_vars["project_name"]}

이 프로젝트는 SBKube로 초기화되었습니다.

## 🚀 빠른 시작

```bash
# 전체 워크플로우 실행
sbkube apply

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
{env_section}

## 💡 사용 예제

```bash
# 특정 환경 배포
sbkube apply --profile production

# 특정 단계만 실행
sbkube apply --only template

# 설정 검증
sbkube validate
```

## 📚 문서

더 자세한 사용법은 [SBKube 문서](docs/INDEX.md)를 참조하세요.
"""

        readme_path = self.base_dir / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
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
        logger.info("   3. sbkube apply로 전체 워크플로우를 실행하세요")
        logger.info("\n📁 생성된 파일:")

        created_files = [
            "config/config.yaml",
            "config/sources.yaml",
            f"values/{self.template_vars['app_name']}-values.yaml",
            "README.md",
        ]

        if self.template_vars.get("create_environments"):
            for env in self.template_vars.get("environments", []):
                created_files.append(f"config/config-{env}.yaml")

        for file_path in created_files:
            if (self.base_dir / file_path).exists():
                logger.info(f"   ✅ {file_path}")


@click.command(name="init")
@click.option(
    "--template",
    default="basic",
    type=click.Choice(["basic", "web-app", "microservice"]),
    help="사용할 템플릿 (기본값: basic)",
)
@click.option("--name", help="프로젝트 이름 (기본값: 현재 디렉토리명)")
@click.option(
    "--non-interactive", is_flag=True, help="대화형 입력 없이 기본값으로 생성"
)
@click.option("--force", is_flag=True, help="기존 파일이 있어도 덮어쓰기")
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
        interactive=not non_interactive,
    )

    try:
        command.execute()
    except Exception as e:
        logger.error(f"❌ 초기화 실패: {e}")
        sys.exit(1)
