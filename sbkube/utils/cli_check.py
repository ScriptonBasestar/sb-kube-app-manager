import os
import shutil
import subprocess
import sys

from sbkube.exceptions import (
    CliToolExecutionError,
    CliToolNotFoundError,
    KubernetesConnectionError,
)
from sbkube.utils.logger import logger


def check_helm_installed_or_exit() -> None:
    """Helm 설치 확인 (테스트 가능한 버전)."""
    try:
        check_helm_installed()
    except (CliToolNotFoundError, CliToolExecutionError):
        sys.exit(1)


def check_helm_installed() -> None:
    """Helm 설치 확인 (예외 발생 버전)."""
    helm_path = shutil.which("helm")
    if not helm_path:
        logger.error("helm 명령이 시스템에 설치되어 있지 않습니다.")
        msg = "helm"
        raise CliToolNotFoundError(msg, "https://helm.sh/docs/intro/install/")

    try:
        result = subprocess.run(
            ["helm", "version"],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.success(f"helm 확인됨: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        logger.error(f"helm 실행 실패: {e}")
        msg = "helm"
        raise CliToolExecutionError(
            msg,
            ["helm", "version"],
            e.returncode,
            e.stdout,
            e.stderr,
        )
    except PermissionError:
        logger.error(f"helm 바이너리에 실행 권한이 없습니다: {helm_path}")
        msg = "helm"
        raise CliToolExecutionError(
            msg,
            ["helm", "version"],
            126,
            None,
            f"Permission denied: {helm_path}",
        )


def check_kubectl_installed_or_exit(
    kubeconfig: str | None = None,
    kubecontext: str | None = None,
) -> None:
    """Kubectl 설치 확인 (테스트 가능한 버전)."""
    try:
        check_kubectl_installed(kubeconfig, kubecontext)
    except (CliToolNotFoundError, CliToolExecutionError):
        sys.exit(1)


def check_kubectl_installed(
    kubeconfig: str | None = None,
    kubecontext: str | None = None,
) -> None:
    """Kubectl 설치 확인 (예외 발생 버전)."""
    kubectl_path = shutil.which("kubectl")
    if not kubectl_path:
        logger.error("kubectl 명령이 시스템에 설치되어 있지 않습니다.")
        msg = "kubectl"
        raise CliToolNotFoundError(msg, "https://kubernetes.io/docs/tasks/tools/")

    try:
        cmd = ["kubectl", "version", "--client"]
        if kubeconfig:
            cmd.extend(["--kubeconfig", kubeconfig])
        if kubecontext:
            cmd.extend(["--context", kubecontext])

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.success(f"kubectl 확인됨: {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        logger.error(f"kubectl 실행 실패: {e}")
        msg = "kubectl"
        raise CliToolExecutionError(msg, cmd, e.returncode, e.stdout, e.stderr)
    except PermissionError:
        logger.error(f"kubectl 바이너리에 실행 권한이 없습니다: {kubectl_path}")
        msg = "kubectl"
        raise CliToolExecutionError(
            msg,
            cmd,
            126,
            None,
            f"Permission denied: {kubectl_path}",
        )


def print_helm_connection_help() -> None:
    import json
    import os
    import shutil
    import subprocess
    from pathlib import Path

    home = str(Path.home())
    helm_dir = os.path.join(home, ".config", "helm")
    # 0. helm 설치 여부
    if shutil.which("helm") is None:
        logger.error("helm 명령이 시스템에 설치되어 있지 않습니다.")
        logger.info(
            "Helm을 설치하거나, asdf 등 버전 매니저에서 helm 버전을 활성화하세요."
        )
        logger.info("https://helm.sh/docs/intro/install/")
        return
    # 1. repo 목록
    try:
        result = subprocess.run(
            ["helm", "repo", "list", "-o", "json"],
            capture_output=True,
            text=True,
            check=True,
        )
        repos = json.loads(result.stdout)
    except Exception as e:
        logger.warning("helm이 정상적으로 동작하지 않습니다.")
        logger.error(f"에러: {e}")
        logger.info("helm version, helm repo list 명령이 정상 동작하는지 확인하세요.")
        return
    # 2. repo 파일 목록
    try:
        repo_files = []
        if os.path.isdir(helm_dir):
            repo_files = [
                f
                for f in os.listdir(helm_dir)
                if os.path.isfile(os.path.join(helm_dir, f))
            ]
    except Exception:
        repo_files = []
    # 3. 안내 메시지
    if repos:
        logger.info("등록된 helm repo 목록:")
        for repo in repos:
            logger.info(f"  * {repo.get('name', '')}: {repo.get('url', '')}")
        logger.info("helm repo add <name> <url> 명령으로 repo를 추가할 수 있습니다.")
    else:
        logger.info("등록된 helm repo가 없습니다.")
    if repo_files:
        logger.info("~/.config/helm 디렉토리 내 파일:")
        for f in repo_files:
            logger.info(f"  - {f}")
    logger.info("helm version, helm repo list 명령이 정상 동작하는지 확인하세요.")


def check_cluster_connectivity(
    timeout: int = 10,
    kubeconfig: str | None = None,
    kubecontext: str | None = None,
) -> tuple[bool, str]:
    """Kubernetes 클러스터 연결 확인.

    Args:
        timeout: 연결 시도 타임아웃 (초)
        kubeconfig: kubeconfig 파일 경로 (옵션)
        kubecontext: kubectl context (옵션)

    Returns:
        (is_connected, error_message): 연결 성공 시 (True, ""), 실패 시 (False, 오류 메시지)

    """
    try:
        cmd = ["kubectl", "cluster-info", f"--request-timeout={timeout}s"]
        if kubeconfig:
            cmd.extend(["--kubeconfig", kubeconfig])
        if kubecontext:
            cmd.extend(["--context", kubecontext])

        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )

        if result.returncode == 0:
            return (True, "")

        error_msg = result.stderr.strip()
        return (False, error_msg)

    except subprocess.TimeoutExpired:
        return (False, "Connection timeout")
    except Exception as e:
        return (False, str(e))


def check_cluster_connectivity_or_exit(
    timeout: int = 10,
    kubeconfig: str | None = None,
    kubecontext: str | None = None,
) -> None:
    """Kubernetes 클러스터 연결 확인 (연결 실패 시 종료).

    Args:
        timeout: 연결 시도 타임아웃 (초)
        kubeconfig: kubeconfig 파일 경로 (옵션)
        kubecontext: kubectl context (옵션)

    Raises:
        KubernetesConnectionError: 클러스터 연결 실패 시

    """
    is_connected, error_msg = check_cluster_connectivity(
        timeout=timeout,
        kubeconfig=kubeconfig,
        kubecontext=kubecontext,
    )

    if not is_connected:
        logger.error("❌ Kubernetes 클러스터에 연결할 수 없습니다!")
        logger.error(f"상세 오류: {error_msg}")
        logger.info("")
        print_kube_connection_help()
        raise KubernetesConnectionError(
            context=kubecontext,
            kubeconfig=kubeconfig,
            reason=error_msg,
        )

    logger.success("✅ 클러스터 연결 확인됨")


def print_kube_contexts() -> None:
    try:
        result = subprocess.run(
            ["kubectl", "config", "get-contexts", "-o", "name"],
            capture_output=True,
            text=True,
            check=True,
        )
        contexts = result.stdout.strip().splitlines()
        for ctx in contexts:
            pass
    except Exception:
        pass


def print_kube_connection_help() -> None:
    from pathlib import Path

    home = str(Path.home())
    kube_dir = os.path.join(home, ".kube")
    os.path.join(kube_dir, "config")
    # 1. context 목록
    try:
        result = subprocess.run(
            ["kubectl", "config", "get-contexts", "-o", "name"],
            capture_output=True,
            text=True,
            check=True,
        )
        contexts = result.stdout.strip().splitlines()
    except Exception:
        contexts = []
    # 2. ~/.kube 디렉토리 내 파일 목록 (config 제외)
    try:
        files = [
            f
            for f in os.listdir(kube_dir)
            if os.path.isfile(os.path.join(kube_dir, f)) and f != "config"
        ]
    except Exception:
        files = []
    # 3. 안내 메시지
    if contexts:
        for ctx in contexts:
            pass
    else:
        pass
    if files:
        for f in files:
            pass


def get_available_contexts(
    kubeconfig: str | None = None,
) -> tuple[list[str], str | None]:
    """Kubeconfig 파일에서 사용 가능한 contexts 목록을 가져옵니다.

    Args:
        kubeconfig: kubeconfig 파일 경로 (None이면 기본값 사용)

    Returns:
        (contexts, error_message): 성공 시 (["context1", "context2"], None),
                                   실패 시 ([], "error message")

    """
    try:
        cmd = ["kubectl", "config", "get-contexts", "-o", "name"]
        if kubeconfig:
            cmd.extend(["--kubeconfig", kubeconfig])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )
        contexts = [
            ctx.strip() for ctx in result.stdout.strip().splitlines() if ctx.strip()
        ]
        return (contexts, None)

    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.strip() if e.stderr else str(e)
        return ([], error_msg)
    except Exception as e:
        return ([], str(e))


def validate_context_exists(
    context: str,
    kubeconfig: str | None = None,
) -> tuple[bool, list[str], str | None]:
    """지정된 context가 kubeconfig에 존재하는지 검증합니다.

    Args:
        context: 검증할 context 이름
        kubeconfig: kubeconfig 파일 경로 (None이면 기본값 사용)

    Returns:
        (exists, available_contexts, error_message):
            - exists: context가 존재하면 True
            - available_contexts: 사용 가능한 contexts 목록
            - error_message: 오류 발생 시 메시지

    """
    available_contexts, error_msg = get_available_contexts(kubeconfig)

    if error_msg:
        return (False, [], error_msg)

    exists = context in available_contexts
    return (exists, available_contexts, None)
