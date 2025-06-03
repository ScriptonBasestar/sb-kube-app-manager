import os
import subprocess
import shutil
from pathlib import Path

EXAMPLES_DIR = Path("examples/k3scode")
BUILD_DIR = Path("build")
KUBECONFIG_TEST = Path.home() / ".kube/test-kubeconfig"
RELEASE_NAME = "browserless"

def clean():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

def run_cmd(args, env=None):
    result = subprocess.run(args, capture_output=True, text=True, env=env)
    print(result.stdout)
    print(result.stderr)
    return result

def test_deploy_on_test_cluster():
    clean()

    # 테스트 클러스터 kubeconfig로 설정
    if not KUBECONFIG_TEST.exists():
        raise RuntimeError(f"❌ 테스트 클러스터 kubeconfig가 없습니다: {KUBECONFIG_TEST}")

    env = os.environ.copy()
    env["KUBECONFIG"] = str(KUBECONFIG_TEST)

    # 1. prepare
    assert run_cmd([
        "sbkube", "prepare",
        "--apps", str(EXAMPLES_DIR / "config-browserless"),
        "--sources", str(EXAMPLES_DIR / "sources")
    ], env=env).returncode == 0

    # 2. build
    assert run_cmd([
        "sbkube", "build",
        "--apps", str(EXAMPLES_DIR / "config-browserless")
    ], env=env).returncode == 0

    # 3. deploy
    assert run_cmd([
        "sbkube", "deploy",
        "--apps", str(EXAMPLES_DIR / "config-browserless"),
        "--namespace", "devops"
    ], env=env).returncode == 0

    # 4. 검증: Helm 릴리스 존재 여부
    check = run_cmd(["helm", "ls", "-n", "devops"], env=env)
    assert RELEASE_NAME in check.stdout, f"❌ 릴리스 '{RELEASE_NAME}'이 배포되지 않았습니다."

    # 5. 검증: 리소스 생성 확인
    kget = run_cmd(["kubectl", "get", "all", "-n", "devops"], env=env)
    assert "pod" in kget.stdout or "deployment" in kget.stdout, "❌ 리소스 생성 안됨"
