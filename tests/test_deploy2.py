import os
import subprocess
import shutil
from pathlib import Path
import pytest

EXAMPLES_DIR = Path("examples/k3scode")
BUILD_DIR = Path("build")
RELEASE_NAME = "browserless"
NAMESPACE = "devops"
KUBECONFIG_PATH = Path.home() / ".kube/test-kubeconfig"

@pytest.mark.skipif(not KUBECONFIG_PATH.exists(), reason="테스트용 kubeconfig 없음: ~/.kube/test-kubeconfig")
def test_deploy_on_test_cluster():
    # 환경 설정
    env = os.environ.copy()
    env["KUBECONFIG"] = str(KUBECONFIG_PATH)

    # 사전 정리
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    # 네임스페이스 먼저 만들기 (없을 수도 있음)
    subprocess.run(["kubectl", "create", "ns", NAMESPACE], env=env, capture_output=True)

    try:
        # 1. prepare
        result = subprocess.run([
            "sbkube", "prepare",
            "--apps", str(EXAMPLES_DIR / "config-browserless"),
            "--sources", str(EXAMPLES_DIR / "sources")
        ], capture_output=True, text=True, env=env)
        print(result.stdout)
        assert result.returncode == 0

        # 2. build
        result = subprocess.run([
            "sbkube", "build",
            "--apps", str(EXAMPLES_DIR / "config-browserless")
        ], capture_output=True, text=True, env=env)
        print(result.stdout)
        assert result.returncode == 0

        # 3. deploy
        result = subprocess.run([
            "sbkube", "deploy",
            "--apps", str(EXAMPLES_DIR / "config-browserless"),
            "--namespace", NAMESPACE
        ], capture_output=True, text=True, env=env)
        print(result.stdout)
        assert result.returncode == 0

        # 4. helm ls 확인
        result = subprocess.run(["helm", "ls", "-n", NAMESPACE], capture_output=True, text=True, env=env)
        print(result.stdout)
        assert RELEASE_NAME in result.stdout

        # 5. 리소스 존재 확인
        result = subprocess.run(["kubectl", "get", "all", "-n", NAMESPACE], capture_output=True, text=True, env=env)
        print(result.stdout)
        assert "pod" in result.stdout or "deployment" in result.stdout

    finally:
        # 🔥 클린업
        subprocess.run(["helm", "uninstall", RELEASE_NAME, "-n", NAMESPACE], env=env, capture_output=True)
        subprocess.run(["kubectl", "delete", "ns", NAMESPACE], env=env, capture_output=True)
