import subprocess
import shutil
from pathlib import Path

SAMPLES_DIR = Path("samples/k3scode")
RENDERED_DIR = Path("rendered")
BUILD_DIR = Path("build")
TARGET_APP_NAME = "browserless"

def clean_rendered_dir():
    if RENDERED_DIR.exists():
        shutil.rmtree(RENDERED_DIR)

def test_template_generates_yaml_output():
    clean_rendered_dir()

    result = subprocess.run(
        [
            "sbkube", "template",
            "--apps", str(SAMPLES_DIR / "config-browserless"),
            "--output-dir", str(RENDERED_DIR)
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    # 1. 명령이 정상 종료되었는지 확인
    assert result.returncode == 0, "sbkube template 명령이 실패했습니다."

    # 2. YAML 결과물이 생성되었는지 확인
    output_file = RENDERED_DIR / f"{TARGET_APP_NAME}.yaml"
    assert output_file.exists(), f"{output_file} 파일이 생성되지 않았습니다."

    # 3. YAML 파일에 기본적인 Helm 출력이 포함되었는지 확인
    content = output_file.read_text()
    assert "kind:" in content, "템플릿 출력에 Kubernetes 리소스 정의가 포함되지 않았습니다."
