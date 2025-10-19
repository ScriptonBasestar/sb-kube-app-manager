"""Kubeconfig 정보를 표시하는 유틸리티 함수."""

from pathlib import Path

from rich.table import Table

from sbkube.utils.logger import logger

# kubernetes 패키지를 사용하기 위한 임포트
try:
    from kubernetes import config as kube_config
    from kubernetes.config.config_exception import ConfigException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False


def display_kubeconfig_info(
    kubeconfig_path: str | None = None,
    context_name: str | None = None,
) -> None:
    """Kubeconfig 파일 정보를 파싱하여 현재 컨텍스트, 사용 가능한 컨텍스트 목록 및 연결 방법을 안내합니다."""
    if not KUBERNETES_AVAILABLE:
        logger.error("`kubernetes` 파이썬 패키지를 찾을 수 없습니다.")
        logger.error(
            "`pip install kubernetes` 또는 `poetry add kubernetes`로 설치해주세요.",
        )
        return

    logger.heading("Kubernetes 설정 정보")
    resolved_kubeconfig_path = (
        str(Path(kubeconfig_path).expanduser()) if kubeconfig_path else None
    )
    default_kubeconfig_path_text = "~/.kube/config"
    if resolved_kubeconfig_path and Path(resolved_kubeconfig_path).is_absolute():
        default_kubeconfig_path_text = resolved_kubeconfig_path
    elif kubeconfig_path:  # 상대경로 등이지만 명시된 경우
        default_kubeconfig_path_text = kubeconfig_path

    try:
        contexts, active_context = kube_config.list_kube_config_contexts(
            config_file=resolved_kubeconfig_path,
        )
    except ConfigException as e:
        logger.warning(
            f"Kubeconfig 파일을 로드할 수 없습니다 (경로: {default_kubeconfig_path_text}).",
        )
        logger.verbose(f"오류: {e}")
        logger.info("\n💡 연결 방법 안내:")
        logger.info("   1. KUBECONFIG 환경 변수를 설정하세요:")
        logger.info("      [cyan]export KUBECONFIG=/path/to/your/kubeconfig[/cyan]")
        logger.info("   2. 또는 `sbkube` 명령어에 옵션을 사용하세요:")
        logger.info(
            "      [cyan]sbkube --kubeconfig /path/to/your/kubeconfig <command>[/cyan]",
        )
        logger.info("      [cyan]sbkube --context <your_context_name> <command>[/cyan]")
        return
    except Exception as e:
        logger.error(f"❌ Kubeconfig 정보 로드 중 예상치 못한 오류 발생: {e}")
        return

    if not contexts:
        logger.warning(
            f"사용 가능한 Kubernetes 컨텍스트가 Kubeconfig 파일({default_kubeconfig_path_text})에 없습니다.",
        )
        return

    current_active_display_name = "N/A"
    if active_context:
        current_active_display_name = active_context.get("name", "N/A")

    # 사용자가 --context 옵션으로 특정 컨텍스트를 지정한 경우, 해당 컨텍스트를 활성 컨텍스트처럼 강조
    specified_context_active = False
    if context_name and any(c.get("name") == context_name for c in contexts):
        current_active_display_name = context_name
        specified_context_active = True
        logger.info(f"지정된 컨텍스트: {current_active_display_name}")
    elif active_context:
        logger.info(f"현재 활성 컨텍스트: {current_active_display_name}")
        cluster_name = active_context.get("context", {}).get("cluster")
        if cluster_name:
            logger.verbose(f"Cluster: {cluster_name}")
    else:
        logger.warning("활성 컨텍스트를 확인할 수 없습니다.")

    table = Table(
        title=f"사용 가능한 컨텍스트 (from: {default_kubeconfig_path_text})",
        show_lines=True,
    )
    table.add_column("활성", style="magenta", justify="center")
    table.add_column("컨텍스트 이름", style="cyan", no_wrap=True)
    table.add_column("클러스터", style="green")
    table.add_column("사용자", style="yellow")
    table.add_column("네임스페이스", style="blue")

    for c_info in sorted(contexts, key=lambda x: x.get("name", "")):
        ctx_name = c_info.get("name", "N/A")
        is_active_symbol = ""
        if specified_context_active and ctx_name == context_name:
            is_active_symbol = "* (지정됨)"
        elif (
            not specified_context_active
            and active_context
            and active_context.get("name") == ctx_name
        ):
            is_active_symbol = "*"

        cluster = c_info.get("context", {}).get("cluster", "N/A")
        user = c_info.get("context", {}).get("user", "N/A")
        namespace = c_info.get("context", {}).get("namespace", "default")
        table.add_row(is_active_symbol, ctx_name, cluster, user, namespace)

    logger.console.print(table)
    logger.info("다른 컨텍스트 사용 방법:")
    logger.info("1. `kubectl`로 컨텍스트 변경:")
    logger.info("kubectl config use-context <context_name>")
    logger.info("2. `sbkube` 명령어에 옵션 사용:")
    logger.info("sbkube --context <context_name> <command>")
    logger.info("3. KUBECONFIG 환경 변수 (여러 파일 관리 시):")
    logger.info("export KUBECONFIG=~/.kube/config:/path/to/other/config")
    logger.info(
        "(이 경우 현재 활성 컨텍스트는 첫 번째 유효한 파일의 현재 컨텍스트를 따릅니다)",
    )
