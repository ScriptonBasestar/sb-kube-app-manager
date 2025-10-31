import logging
import shlex
import sys

import click

from sbkube.commands import (
    apply,
    build,
    delete,
    deploy,
    doctor,
    history,
    init,
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
from sbkube.utils.logger import logger


class SbkubeGroup(click.Group):
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
            ]
            commands_requiring_helm = [
                "template",
                "deploy",
                "upgrade",
                "delete",
                "prepare",
                "build",
                "apply",
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
@click.option("-v", "--verbose", is_flag=True, help="상세 로깅을 활성화합니다.")
@click.pass_context
def main(
    ctx: click.Context,
    kubeconfig: str | None,
    context: str | None,
    source: str,
    profile: str | None,
    namespace: str | None,
    verbose: bool,
) -> None:
    """sbkube: Kubernetes 애플리케이션 관리를 위한 CLI 도구.

    Helm 차트, YAML 매니페스트, Git 저장소 등을 사용하여 애플리케이션을 준비, 빌드, 배포, 업그레이드, 삭제합니다.
    """
    ctx.ensure_object(dict)
    ctx.obj["kubeconfig"] = kubeconfig
    ctx.obj["context"] = context
    ctx.obj["namespace"] = namespace
    ctx.obj["verbose"] = verbose

    # --profile 옵션으로 sources 파일명 자동 생성
    if profile:
        ctx.obj["sources_file"] = f"sources-{profile}.yaml"
    else:
        ctx.obj["sources_file"] = source

    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )
        logger.verbose("상세 로깅 활성화됨.")


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
main.add_command(validate.cmd)
main.add_command(version.cmd)
main.add_command(doctor.cmd)


def main_with_exception_handling() -> None:
    """Main entry point with global exception handling."""
    try:
        main()
    except SbkubeError as e:
        from sbkube.utils.error_suggestions import (
            get_quick_fix_command,
            is_auto_recoverable,
        )

        logger.error(format_error_with_suggestions(e))

        # Interactive auto-fix prompt (only in interactive terminal)
        error_type = type(e).__name__
        if sys.stdin.isatty() and is_auto_recoverable(error_type):
            quick_fix = get_quick_fix_command(error_type)
            if quick_fix:
                try:
                    response = (
                        input("\n❓ 자동 수정을 시도하시겠습니까? (y/N): ")
                        .strip()
                        .lower()
                    )
                    if response in ["y", "yes"]:
                        import subprocess

                        logger.info(f"🔧 실행: {quick_fix}")
                        result = subprocess.run(shlex.split(quick_fix), shell=False)
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
