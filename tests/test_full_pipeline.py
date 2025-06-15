import subprocess
import shutil
from pathlib import Path

EXAMPLES_DIR = Path("examples/k3scode")
BUILD_DIR = Path("build")
RENDERED_DIR = Path("rendered")
TARGET_APP_NAME = "browserless"

def clean_all():
    for d in [BUILD_DIR, RENDERED_DIR]:
        if d.exists():
            shutil.rmtree(d)

def test_full_pipeline_prepare_build_template():
    clean_all()

    # 1. prepare (devops는 pull 타입이 없으므로 ai 사용)
    result = subprocess.run(
        [
            "sbkube", "prepare",
            "--base-dir", str(EXAMPLES_DIR),
            "--app-dir", "ai",
            "--config-file", "config.yaml",
            "--sources-file", "sources.yaml"
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"prepare 실패\n{result.stderr}"

    # 2. build (devops 사용 - copy-app이 있음)
    result = subprocess.run(
        [
            "sbkube", "build",
            "--base-dir", str(EXAMPLES_DIR),
            "--app-dir", "devops",
            "--config-file", "config.yaml"
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"build 실패\n{result.stderr}"

    # 3. template (devops 사용 - install-helm이 있음)
    result = subprocess.run(
        [
            "sbkube", "template",
            "--base-dir", str(EXAMPLES_DIR),
            "--app-dir", "devops",
            "--config-file", "config.yaml",
            "--output-dir", str(RENDERED_DIR)
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"template 실패\n{result.stderr}"

    # 4. 검증: 빌드 및 렌더링 결과물
    chart_file = EXAMPLES_DIR / "devops" / "build" / "proxynd-custom" / "Chart.yaml"
    output_file = EXAMPLES_DIR / "devops" / RENDERED_DIR / "proxynd-custom.yaml"

    assert chart_file.exists(), f"Chart.yaml 누락: {chart_file}"
    assert output_file.exists(), f"렌더링된 YAML 파일 없음: {output_file}"

    # 5. 템플릿 내용 확인
    content = output_file.read_text()
    assert "kind:" in content, "Kubernetes 리소스 정의가 누락됨"
