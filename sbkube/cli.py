import logging
import sys

import click

from sbkube.commands import (
    apply,
    assistant,
    build,
    config,
    delete,
    deploy,
    doctor,
    fix,
    history,
    init,
    prepare,
    profiles,
    state,
    template,
    upgrade,
    validate,
    version,
)

# v0.3.0 명령어 (기본으로 사용)
from sbkube.commands import apply_v3, build_v3, deploy_v3, migrate, prepare_v3, template_v3
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
    envvar="KUBECONFIG",
    type=click.Path(exists=False, dir_okay=False, resolve_path=False),
    help="Kubernetes 설정 파일 경로. KUBECONFIG 환경변수보다 우선 적용됩니다.",
)
@click.option(
    "--context",
    help="사용할 Kubernetes 컨텍스트 이름. KUBECONTEXT 환경변수 또는 현재 활성 컨텍스트를 따릅니다.",
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

    if verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        )
        logger.verbose("상세 로깅 활성화됨.")


# v0.3.0 명령어 (기본으로 사용)
main.add_command(prepare_v3.cmd, name="prepare")
main.add_command(build_v3.cmd, name="build")
main.add_command(template_v3.cmd, name="template")
main.add_command(deploy_v3.cmd, name="deploy")
main.add_command(apply_v3.cmd, name="apply")
main.add_command(migrate.cmd, name="migrate")

# v0.2.x 명령어 (레거시, legacy- 접두사로 제공)
main.add_command(prepare.cmd, name="legacy-prepare")
main.add_command(build.cmd, name="legacy-build")
main.add_command(template.cmd, name="legacy-template")
main.add_command(deploy.cmd, name="legacy-deploy")
main.add_command(apply.cmd, name="legacy-apply")

# 기타 명령어 (버전 무관)
main.add_command(init.cmd)
main.add_command(upgrade.cmd)
main.add_command(delete.cmd)
main.add_command(validate.cmd)
main.add_command(version.cmd)
main.add_command(config.cmd)
main.add_command(state.state)
main.add_command(profiles.cmd)
main.add_command(history.cmd)
main.add_command(history.diagnose_cmd)
main.add_command(doctor.cmd)
main.add_command(fix.cmd)
main.add_command(assistant.cmd)
main.add_command(assistant.history_cmd)


def main_with_exception_handling() -> None:
    """Main entry point with global exception handling."""
    try:
        main()
    except SbkubeError as e:
        logger.error(format_error_with_suggestions(e))
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
