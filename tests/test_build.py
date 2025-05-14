import subprocess
import shutil
from pathlib import Path

SAMPLES_DIR = Path("samples/k3scode")
BUILD_DIR = Path("build")
TARGET_APP_NAME = "browserless"  # config-browserless 기준

def clean_build_dir():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

def test_build_command_runs_and_creates_output():
    clean_build_dir()

    result = subprocess.run(
        [
            "sbkube", "build",
            "--apps", str(SAMPLES_DIR / "config-browserless")
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    # 1. 명령 실행 성공
    assert result.returncode == 0, "sbkube build 명령이 실패했습니다."

    # 2. build 디렉토리 존재 확인
    assert BUILD_DIR.exists(), "build 디렉토리가 생성되지 않았습니다."

    # 3. browserless 디렉토리 확인
    target_chart_path = BUILD_DIR / TARGET_APP_NAME / "Chart.yaml"
    assert target_chart_path.exists(), f"{target_chart_path} 파일이 존재하지 않습니다."
