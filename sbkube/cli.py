import logging
import shlex
import sys
from typing import ClassVar

import click

from sbkube.commands import (
    apply,
    build,
    check_updates,
    delete,
    deploy,
    doctor,
    history,
    init,
    migrate,
    prepare,
    rollback,
    status,
    template,
    upgrade,
    validate,
    version,
)
from sbkube.exceptions import (
    CliToolExecutionError,
    CliToolNotFoundError,
    SbkubeError,
    format_error_with_suggestions,
)
from sbkube.utils.cli_check import (
    check_helm_installed_or_exit,
    check_kubectl_installed_or_exit,
)
from sbkube.utils.logger import LogLevel, logger


class SbkubeGroup(click.Group):
    """SBKube CLI 그룹 with categorized help display."""

    # 명령어 카테고리 정의
    COMMAND_CATEGORIES: ClassVar[dict[str, list[str]]] = {
        "핵심 워크플로우": ["prepare", "build", "template", "deploy"],
        "통합 명령어": ["apply"],
        "상태 관리": ["status", "history", "rollback"],
        "업그레이드/삭제": ["upgrade", "delete", "check-updates"],
        "유틸리티": ["init", "validate", "doctor", "migrate", "version"],
    }

    # 카테고리별 이모지
    CATEGORY_LABELS: ClassVar[dict[str, str]] = {
        "핵심 워크플로우": "🔄",
        "통합 명령어": "⚡",
        "상태 관리": "📊",
        "업그레이드/삭제": "🔧",
        "유틸리티": "🛠️",
    }

    def format_commands(
        self, ctx: click.Context, formatter: click.HelpFormatter
    ) -> None:
        """Format commands by category."""
        commands = []
        for subcommand in self.list_commands(ctx):
            cmd = self.get_command(ctx, subcommand)
            if cmd is None:
                continue
            if cmd.hidden:
                continue
            help_text = cmd.get_short_help_str(limit=100)
            commands.append((subcommand, help_text))

        if not commands:
            return

        # 카테고리별로 명령어 그룹화
        categorized: dict[str, list[tuple[str, str]]] = {}
        uncategorized: list[tuple[str, str]] = []

        for cmd_name, help_text in commands:
            found = False
            for category, cmd_list in self.COMMAND_CATEGORIES.items():
                if cmd_name in cmd_list:
                    if category not in categorized:
                        categorized[category] = []
                    categorized[category].append((cmd_name, help_text))
                    found = True
                    break
            if not found:
                uncategorized.append((cmd_name, help_text))

        # 카테고리 순서대로 출력
        for category in self.COMMAND_CATEGORIES:
            if category in categorized:
                emoji = self.CATEGORY_LABELS.get(category, "")
                with formatter.section(f"{emoji} {category}"):
                    formatter.write_dl(categorized[category])

        # 미분류 명령어 (있는 경우)
        if uncategorized:
            with formatter.section("기타"):
                formatter.write_dl(uncategorized)

    def invoke(self, ctx: click.Context) -> None:
        # 이 메소드는 invoke_without_command=True 와 main 콜백 로직에 의해
        # 실제 서브커맨드가 실행될 때만 호출됩니다.
        # 'sbkube' 단독 실행 시에는 main 콜백에서 display_kubeconfig_info() 실행 후 ctx.exit() 됩니다.

        if ctx.invoked_subcommand:
            # Kubernetes/Helm 연결이 필요한 명령어들에 대해 검사 수행
            commands_requiring_kubectl_connection = [
                "deploy",
                "upgrade",
                "delete",
                "prepare",
                "apply",
                "migrate",
            ]
            commands_requiring_helm = [
                "template",
                "deploy",
                "upgrade",
                "delete",
                "prepare",
                "build",
                "apply",
                "migrate",
            ]

            try:
                if ctx.invoked_subcommand in commands_requiring_kubectl_connection:
                    check_kubectl_installed_or_exit(
                        kubeconfig=ctx.obj.get("kubeconfig"),
                        kubecontext=ctx.obj.get("context"),
                    )

                if ctx.invoked_subcommand in commands_requiring_helm:
                    check_helm_installed_or_exit()

            except (CliToolNotFoundError, CliToolExecutionError) as e:
                if isinstance(e, SbkubeError):
                    logger.error(format_error_with_suggestions(e))
                else:
                    logger.error(str(e))
                sys.exit(1)

        super().invoke(ctx)


@click.group(cls=SbkubeGroup)
@click.option(
    "--kubeconfig",
    type=click.Path(exists=False, dir_okay=False, resolve_path=False),
    help="Kubeconfig 파일 경로 (sources.yaml 오버라이드). --context와 함께 사용 필수.",
)
@click.option(
    "--context",
    type=str,
    help="Kubectl context 이름 (sources.yaml 오버라이드). --kubeconfig와 함께 사용 필수.",
)
@click.option(
    "--source",
    type=str,
    default="sources.yaml",
    help="Source 파일 이름 (예: sources-dev.yaml). 기본값: sources.yaml",
)
@click.option(
    "--profile",
    type=str,
    help="환경 프로파일 (자동으로 sources-{profile}.yaml 사용). 예: --profile dev → sources-dev.yaml",
)
@click.option(
    "--namespace",
    envvar="KUBE_NAMESPACE",
    help="작업을 수행할 기본 네임스페이스.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["human", "llm", "json", "yaml"], case_sensitive=False),
    envvar="SBKUBE_OUTPUT_FORMAT",
    default="human",
    help="출력 형식 (human: Rich Console, llm: LLM 친화적, json: JSON, yaml: YAML). 환경변수: SBKUBE_OUTPUT_FORMAT",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세).")
@click.option(
    "--log-level",
    "log_level",
    type=click.Choice(["info", "debug", "verbose", "warn"], case_sensitive=False),
    default=None,
    help="로그 레벨 명시 지정. -v/--verbose와 동시 사용 불가.",
)
@click.pass_context
def main(
    ctx: click.Context,
    kubeconfig: str | None,
    context: str | None,
    source: str,
    profile: str | None,
    namespace: str | None,
    output_format: str,
    verbose: int,
    log_level: str | None,
) -> None:
    """sbkube: Kubernetes 애플리케이션 관리를 위한 CLI 도구.

    Helm 차트, YAML 매니페스트, Git 저장소 등을 사용하여 애플리케이션을 준비, 빌드, 배포, 업그레이드, 삭제합니다.
    """
    from sbkube.utils.global_options import LOG_LEVEL_MAP

    ctx.ensure_object(dict)
    ctx.obj["kubeconfig"] = kubeconfig
    ctx.obj["context"] = context
    ctx.obj["namespace"] = namespace
    ctx.obj["format"] = output_format
    ctx.obj["verbose"] = verbose

    # --log-level과 -v 충돌 감지 (그룹 레벨)
    log_level_source = ctx.get_parameter_source("log_level")
    verbose_source = ctx.get_parameter_source("verbose")
    if (
        log_level_source == click.core.ParameterSource.COMMANDLINE
        and verbose_source == click.core.ParameterSource.COMMANDLINE
        and verbose > 0
    ):
        raise click.UsageError(
            "--log-level and -v/--verbose cannot be used together. "
            "Use one or the other."
        )

    # Optional perf profiling (SBKUBE_PERF=1)
    from sbkube.utils.perf import enable_from_env

    enable_from_env(output_format=output_format)

    # --profile 옵션으로 sources 파일명 자동 생성
    if profile:
        ctx.obj["sources_file"] = f"sources-{profile}.yaml"
    else:
        ctx.obj["sources_file"] = source

    # Log level 설정: --log-level 우선, 없으면 -v 사용
    if log_level is not None:
        level = LOG_LEVEL_MAP[log_level]
        logger.set_level(level)
        if level <= LogLevel.DEBUG:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
            )
        ctx.obj["verbose"] = 2 if level <= LogLevel.VERBOSE else (1 if level <= LogLevel.INFO else 0)
    elif verbose >= 2:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )
        logger.set_level(LogLevel.VERBOSE)
        logger.verbose("상세 로깅 활성화됨.")
    elif verbose >= 1:
        logger.set_level(LogLevel.INFO)


# 핵심 워크플로우 명령어
main.add_command(prepare.cmd)
main.add_command(build.cmd)
main.add_command(template.cmd)
main.add_command(deploy.cmd)
main.add_command(apply.cmd)

# 상태 및 히스토리 명령어 (NEW)
main.add_command(status.cmd)
main.add_command(history.cmd)
main.add_command(rollback.cmd)

# 기타 명령어
main.add_command(init.cmd)
main.add_command(upgrade.cmd)
main.add_command(delete.cmd)
main.add_command(check_updates.cmd)
main.add_command(validate.cmd)
main.add_command(version.cmd)
main.add_command(doctor.cmd)
main.add_command(migrate.cmd)


def main_with_exception_handling() -> None:
    """Main entry point with global exception handling."""
    try:
        main()
    except SbkubeError as e:
        from sbkube.utils.error_suggestions import (
            get_quick_fix_command,
            has_placeholder,
            is_auto_recoverable,
        )

        logger.error(format_error_with_suggestions(e))

        # Interactive auto-fix prompt (only in interactive terminal)
        error_type = type(e).__name__
        if sys.stdin.isatty() and is_auto_recoverable(error_type):
            quick_fix = get_quick_fix_command(error_type)
            if quick_fix:
                if has_placeholder(quick_fix):
                    logger.warning(
                        "⚠️ 자동 수정 명령어에 placeholder가 포함되어 있어 "
                        "실행을 건너뜁니다. 수동으로 수정해 실행하세요."
                    )
                else:
                    try:
                        response = (
                            input("\n❓ 자동 수정을 시도하시겠습니까? (y/N): ")
                            .strip()
                            .lower()
                        )
                        if response in ["y", "yes"]:
                            import subprocess

                            logger.info(f"🔧 실행: {quick_fix}")
                            result = subprocess.run(
                                shlex.split(quick_fix), check=False, shell=False
                            )
                            if result.returncode == 0:
                                logger.info(
                                    "✅ 자동 수정이 완료되었습니다. 다시 시도해 주세요."
                                )
                            else:
                                logger.warning(
                                    "⚠️ 자동 수정이 실패했습니다. 수동으로 처리해 주세요."
                                )
                    except (KeyboardInterrupt, EOFError):
                        pass  # User cancelled, just exit normally

        sys.exit(e.exit_code)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)  # Standard exit code for SIGINT
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.verbose(f"Exception details: {type(e).__name__}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main_with_exception_handling()
