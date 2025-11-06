"""앱 디렉토리 해석 유틸리티.

sources.yaml 또는 자동 탐색을 통해 앱 그룹 디렉토리 목록을 결정합니다.
"""

from pathlib import Path

from rich.console import Console

from sbkube.models.sources_model import SourceScheme
from sbkube.utils.common import find_all_app_dirs
from sbkube.utils.file_loader import load_config_file

console = Console()


def resolve_app_dirs(
    base_dir: Path,
    app_config_dir_name: str | None,
    config_file_name: str,
    sources_file_name: str = "sources.yaml",
) -> list[Path]:
    """앱 그룹 디렉토리 목록을 결정합니다.

    우선순위:
    1. --app-dir 옵션으로 명시적 지정
    2. sources.yaml의 app_dirs 목록 사용
    3. 자동 탐색 (config.yaml 파일이 있는 모든 하위 디렉토리)

    Args:
        base_dir: 프로젝트 루트 디렉토리
        app_config_dir_name: --app-dir 옵션으로 지정된 디렉토리 이름 (None이면 자동 탐색)
        config_file_name: 설정 파일 이름 (예: config.yaml)
        sources_file_name: 소스 설정 파일 이름 (기본값: sources.yaml)

    Returns:
        list[Path]: 앱 그룹 디렉토리 경로 목록

    Raises:
        ValueError: 앱 디렉토리를 찾을 수 없거나 sources.yaml 오류 시

    """
    # sources.yaml 로드 시도
    sources_file_path = base_dir / sources_file_name
    sources_config = None

    if sources_file_path.exists():
        try:
            sources_data = load_config_file(sources_file_path)
            sources_config = SourceScheme(**sources_data)
        except Exception as e:
            console.print(
                f"[yellow]⚠️  Warning: Could not load {sources_file_name}: {e}[/yellow]"
            )

    # 1. 명시적 --app-dir 옵션
    if app_config_dir_name:
        return [base_dir / app_config_dir_name]

    # 2. sources.yaml의 app_dirs 사용
    if sources_config and sources_config.app_dirs is not None:
        try:
            app_config_dirs = sources_config.get_app_dirs(base_dir, config_file_name)
            console.print(
                f"[cyan]📂 Using app_dirs from {sources_file_name} "
                f"({len(app_config_dirs)} group(s)):[/cyan]"
            )
            for app_dir in app_config_dirs:
                console.print(f"  - {app_dir.name}/")
            return app_config_dirs
        except ValueError as e:
            console.print(f"[red]❌ {e}[/red]")
            raise

    # 3. 자동 탐색 (기본 동작)
    app_config_dirs = find_all_app_dirs(base_dir, config_file_name)
    if not app_config_dirs:
        error_msg = f"No app directories found in: {base_dir}"
        console.print(f"[red]❌ {error_msg}[/red]")
        console.print(
            "[yellow]💡 Tip: Create directories with config.yaml or use --app-dir[/yellow]"
        )
        raise ValueError(error_msg)

    console.print(
        f"[cyan]📂 Found {len(app_config_dirs)} app group(s) (auto-discovery):[/cyan]"
    )
    for app_dir in app_config_dirs:
        console.print(f"  - {app_dir.name}/")

    return app_config_dirs
