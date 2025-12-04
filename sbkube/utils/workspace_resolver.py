"""Workspace and directory resolution utilities for SBKube.

This module centralizes the logic for:
- Finding sources.yaml by searching upward from app config directories
- Resolving .sbkube working directory based on sources.yaml location
- Providing a unified SbkubeDirectories dataclass for all path needs

This eliminates code duplication across prepare, build, template, and deploy commands.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class SbkubeDirectories:
    """Resolved SBKube working directories.

    All paths are absolute and resolved. The .sbkube working directory
    is determined by the location of sources.yaml file.

    Attributes:
        base_dir: Project root directory (--base-dir)
        sources_file: Path to sources.yaml if found, None otherwise
        sources_base_dir: Directory containing sources.yaml (or base_dir as fallback)
        sbkube_work_dir: .sbkube working directory
        charts_dir: Downloaded Helm charts directory
        repos_dir: Cloned git repositories directory
        build_dir: Built/modified charts directory
        rendered_dir: Rendered templates directory

    """

    base_dir: Path
    sources_file: Path | None
    sources_base_dir: Path
    sbkube_work_dir: Path
    charts_dir: Path
    repos_dir: Path
    build_dir: Path
    rendered_dir: Path

    @property
    def temp_dir(self) -> Path:
        """Temporary directory for intermediate files."""
        return self.sbkube_work_dir / "temp"

    def ensure_directories(self) -> None:
        """Create all working directories if they don't exist."""
        self.sbkube_work_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.repos_dir.mkdir(parents=True, exist_ok=True)
        self.build_dir.mkdir(parents=True, exist_ok=True)
        self.rendered_dir.mkdir(parents=True, exist_ok=True)

    def ensure_temp_dir(self) -> Path:
        """Create and return temp directory."""
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self.temp_dir


def find_sources_file_upward(
    start_dir: Path,
    sources_file_name: str = "sources.yaml",
    stop_at: Path | None = None,
) -> Path | None:
    """Find sources.yaml by searching upward from start_dir.

    Searches from start_dir upward through parent directories until:
    - sources.yaml is found
    - Root directory is reached
    - stop_at directory is reached (if specified)

    Args:
        start_dir: Directory to start searching from
        sources_file_name: Name of sources file (default: "sources.yaml")
        stop_at: Optional directory to stop searching at (exclusive)

    Returns:
        Path to sources.yaml if found, None otherwise

    Example:
        >>> # Directory structure:
        >>> # /project/
        >>> #   ├── sources.yaml
        >>> #   └── apps/
        >>> #       └── redis/
        >>> #           └── config.yaml
        >>> find_sources_file_upward(Path("/project/apps/redis"))
        Path("/project/sources.yaml")

    """
    search_dir = start_dir.resolve()
    root = Path(search_dir.anchor)

    while search_dir != root:
        # Check if we've reached stop_at
        if stop_at and search_dir == stop_at.resolve():
            break

        candidate = search_dir / sources_file_name
        if candidate.exists():
            return candidate

        # Move to parent
        parent = search_dir.parent
        if parent == search_dir:
            break
        search_dir = parent

    return None


def resolve_sbkube_directories(
    base_dir: Path,
    app_config_dirs: list[Path] | None = None,
    sources_file_name: str = "sources.yaml",
) -> SbkubeDirectories:
    """Resolve all SBKube working directories from sources.yaml location.

    The .sbkube working directory is determined by the location of sources.yaml:
    1. If app_config_dirs provided, search upward from first dir for sources.yaml
    2. .sbkube is placed in the same directory as sources.yaml
    3. If sources.yaml not found, fallback to base_dir

    Args:
        base_dir: Project root directory (--base-dir)
        app_config_dirs: List of app config directories to search from
        sources_file_name: Name of sources file (default: "sources.yaml")

    Returns:
        SbkubeDirectories with all resolved paths

    Example:
        >>> dirs = resolve_sbkube_directories(
        ...     base_dir=Path("/project"),
        ...     app_config_dirs=[Path("/project/apps/redis")],
        ... )
        >>> dirs.charts_dir
        Path("/project/.sbkube/charts")

    """
    base_dir = base_dir.resolve()

    # Find sources.yaml
    sources_file_path: Path | None = None

    if app_config_dirs:
        # Search upward from first app config dir
        sources_file_path = find_sources_file_upward(
            start_dir=app_config_dirs[0],
            sources_file_name=sources_file_name,
        )

    # If not found via upward search, check base_dir directly
    if not sources_file_path:
        base_sources = base_dir / sources_file_name
        if base_sources.exists():
            sources_file_path = base_sources

    # Determine .sbkube location
    if sources_file_path:
        sources_base_dir = sources_file_path.parent
    else:
        sources_base_dir = base_dir

    sbkube_work_dir = sources_base_dir / ".sbkube"

    return SbkubeDirectories(
        base_dir=base_dir,
        sources_file=sources_file_path,
        sources_base_dir=sources_base_dir,
        sbkube_work_dir=sbkube_work_dir,
        charts_dir=sbkube_work_dir / "charts",
        repos_dir=sbkube_work_dir / "repos",
        build_dir=sbkube_work_dir / "build",
        rendered_dir=sbkube_work_dir / "rendered",
    )


def resolve_sources_and_work_dirs(
    base_dir: Path,
    app_config_dirs: list[Path],
    sources_file_name: str = "sources.yaml",
) -> tuple[Path | None, Path, Path, Path, Path]:
    """Legacy compatibility function - returns tuple instead of dataclass.

    This function provides backward compatibility for existing code that
    expects tuple returns. New code should use resolve_sbkube_directories().

    Args:
        base_dir: Project root directory
        app_config_dirs: List of app config directories
        sources_file_name: Name of sources file

    Returns:
        Tuple of (sources_file_path, sbkube_work_dir, charts_dir, build_dir, repos_dir)

    """
    dirs = resolve_sbkube_directories(base_dir, app_config_dirs, sources_file_name)
    return (
        dirs.sources_file,
        dirs.sbkube_work_dir,
        dirs.charts_dir,
        dirs.build_dir,
        dirs.repos_dir,
    )
