import subprocess
import shutil
from pathlib import Path

SAMPLES_DIR = Path("samples/k3scode")
CHARTS_DIR = Path("charts")
REPOS_DIR = Path("repos")

def clean_output_dirs():
    if CHARTS_DIR.exists():
        shutil.rmtree(CHARTS_DIR)
    if REPOS_DIR.exists():
        shutil.rmtree(REPOS_DIR)

def test_prepare_command_runs_successfully():
    # 🧹 사전 정리
    clean_output_dirs()

    # 📦 prepare 실행
    result = subprocess.run(
        [
            "sbkube", "prepare",
            "--apps", str(SAMPLES_DIR / "config.yaml"),
            "--sources", str(SAMPLES_DIR / "sources.yaml")
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    assert result.returncode == 0, "prepare 명령 실패"

    # ✅ 결과물 확인
    assert CHARTS_DIR.exists(), "charts 디렉토리가 생성되지 않았습니다"
    assert REPOS_DIR.exists(), "repos 디렉토리가 생성되지 않았습니다"

    # 예시: browserless chart가 정상 다운로드되었는지 확인
    browserless_chart = CHARTS_DIR / "browserless" / "Chart.yaml"
    assert browserless_chart.exists(), "browserless Helm 차트가 존재하지 않습니다"
