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

    # 1. prepare
    result = subprocess.run(
        [
            "sbkube", "prepare",
            "--base-dir", str(EXAMPLES_DIR),
            "--app-dir", ".",
            "--config-file", "config-browserless.yml",
            "--sources-file", "sources.yaml"
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"prepare 실패\n{result.stderr}"

    # 2. build
    result = subprocess.run(
        [
            "sbkube", "build",
            "--base-dir", str(EXAMPLES_DIR),
            "--app-dir", ".",
            "--config-file", "config-browserless.yml"
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"build 실패\n{result.stderr}"

    # 3. template
    result = subprocess.run(
        [
            "sbkube", "template",
            "--base-dir", str(EXAMPLES_DIR),
            "--app-dir", ".",
            "--config-file", "config-browserless.yml",
            "--output-dir", str(RENDERED_DIR)
        ],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"template 실패\n{result.stderr}"

    # 4. 검증: 빌드 및 렌더링 결과물
    chart_file = EXAMPLES_DIR / "build" / TARGET_APP_NAME / "Chart.yaml"
    output_file = EXAMPLES_DIR / RENDERED_DIR / f"{TARGET_APP_NAME}.yaml"

    assert chart_file.exists(), f"Chart.yaml 누락: {chart_file}"
    assert output_file.exists(), f"렌더링된 YAML 파일 없음: {output_file}"

    # 5. 템플릿 내용 확인
    content = output_file.read_text()
    assert "kind:" in content, "Kubernetes 리소스 정의가 누락됨"
