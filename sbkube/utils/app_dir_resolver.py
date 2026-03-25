"""앱 디렉토리 해석 유틸리티.

sources.yaml 또는 자동 탐색을 통해 앱 그룹 디렉토리 목록을 결정합니다.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from sbkube.models.sources_model import SourceScheme
from sbkube.utils.common import find_all_app_dirs
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.logger import logger

if TYPE_CHECKING:
    from sbkube.utils.output_manager import OutputManager


def resolve_app_dirs(
    base_dir: Path,
    app_config_dir_name: str | None,
    config_file_name: str,
    sources_file_name: str = "sources.yaml",
    output: OutputManager | None = None,
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
        output: OutputManager 인스턴스 (None이면 logger fallback)

    Returns:
        list[Path]: 앱 그룹 디렉토리 경로 목록

    Raises:
        ValueError: 앱 디렉토리를 찾을 수 없거나 sources.yaml 오류 시

    """

    def _print(msg: str, level: str = "info") -> None:
        if output:
            output.print(msg, level=level)
        elif level == "warning":
            logger.warning(msg)
        elif level == "error":
            logger.error(msg)
        else:
            logger.info(msg)

    def _print_warning(msg: str) -> None:
        if output:
            output.print_warning(msg)
        else:
            logger.warning(msg)

    def _print_error(msg: str) -> None:
        if output:
            output.print_error(msg)
        else:
            logger.error(msg)

    # sources.yaml 로드 시도
    sources_file_path = base_dir / sources_file_name
    sources_config = None

    if sources_file_path.exists():
        try:
            sources_data = load_config_file(sources_file_path)
            sources_config = SourceScheme(**sources_data)
        except Exception as e:
            _print_warning(f"Could not load {sources_file_name}: {e}")

    # 1. 명시적 --app-dir 옵션
    if app_config_dir_name:
        app_dir_path = base_dir / app_config_dir_name
        if not app_dir_path.exists():
            error_msg = f"App directory not found: {app_dir_path}"
            _print_error(error_msg)
            available_dirs = find_all_app_dirs(base_dir, config_file_name)
            if available_dirs:
                _print("Available app directories:", level="warning")
                for app_dir in available_dirs:
                    _print(f"  - {app_dir.name}/", level="warning")
            else:
                _print(
                    "Tip: Create directories with config.yaml or omit --app-dir for auto-discovery",
                    level="warning",
                )
            raise ValueError(error_msg)
        if not app_dir_path.is_dir():
            error_msg = f"Not a directory: {app_dir_path}"
            _print_error(error_msg)
            raise ValueError(error_msg)
        return [app_dir_path]

    # 2. sources.yaml의 app_dirs 사용
    if sources_config and sources_config.app_dirs is not None:
        try:
            app_config_dirs = sources_config.get_app_dirs(base_dir, config_file_name)
            _print(
                f"[cyan]📂 Using app_dirs from {sources_file_name} "
                f"({len(app_config_dirs)} group(s)):[/cyan]",
                level="info",
            )
            for app_dir in app_config_dirs:
                _print(f"  - {app_dir.name}/", level="info")
            return app_config_dirs
        except ValueError as e:
            _print_error(str(e))
            raise

    # 3. 자동 탐색 (기본 동작)
    app_config_dirs = find_all_app_dirs(base_dir, config_file_name)
    if not app_config_dirs:
        error_msg = f"No app directories found in: {base_dir}"
        _print_error(error_msg)
        _print(
            "Tip: Create directories with config.yaml or use --app-dir",
            level="warning",
        )
        raise ValueError(error_msg)

    _print(
        f"[cyan]📂 Found {len(app_config_dirs)} app group(s) (auto-discovery):[/cyan]",
        level="info",
    )
    for app_dir in app_config_dirs:
        _print(f"  - {app_dir.name}/", level="info")

    return app_config_dirs
