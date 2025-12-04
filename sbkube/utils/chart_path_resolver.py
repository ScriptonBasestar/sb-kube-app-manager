"""Chart path resolution utilities for SBKube.

This module centralizes the logic for:
- Resolving chart paths for remote and local charts
- Detecting legacy chart directory structures (v0.7.0, v0.7.1)
- Providing migration hints for legacy paths

This eliminates code duplication across build.py and deploy.py commands.
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sbkube.models.config_model import HelmApp
    from sbkube.utils.output_manager import OutputManager


class LegacyVersion(Enum):
    """Legacy chart path versions."""

    V070 = "v0.7.0"  # charts/{chart-name}/{chart-name}/
    V071 = "v0.7.1"  # charts/{chart-name}/
    NONE = None  # No legacy path found


@dataclass
class ChartPathResult:
    """Result of chart path resolution.

    Attributes:
        chart_path: Resolved chart path if found, None otherwise
        found: Whether a valid chart path was found
        legacy_version: If legacy path detected, which version
        legacy_path: Path to legacy chart if detected
        error_message: Error message if chart not found

    """

    chart_path: Path | None
    found: bool
    legacy_version: LegacyVersion = LegacyVersion.NONE
    legacy_path: Path | None = None
    error_message: str | None = None

    @property
    def requires_migration(self) -> bool:
        """Check if legacy migration is required."""
        return self.legacy_version != LegacyVersion.NONE


def check_legacy_chart_paths(
    charts_dir: Path,
    chart_name: str,
) -> tuple[LegacyVersion, Path | None]:
    """Check for legacy chart path structures.

    Args:
        charts_dir: Base charts directory (.sbkube/charts/)
        chart_name: Name of the chart to find

    Returns:
        Tuple of (legacy_version, legacy_path) if found, (NONE, None) otherwise

    """
    # Legacy v0.7.1: charts/{chart-name}/
    legacy_v071_path = charts_dir / chart_name
    if legacy_v071_path.exists() and legacy_v071_path.is_dir():
        # Verify it's actually a chart (has Chart.yaml)
        if (legacy_v071_path / "Chart.yaml").exists():
            return LegacyVersion.V071, legacy_v071_path

    # Legacy v0.7.0: charts/{chart-name}/{chart-name}/
    legacy_v070_path = charts_dir / chart_name / chart_name
    if legacy_v070_path.exists() and legacy_v070_path.is_dir():
        if (legacy_v070_path / "Chart.yaml").exists():
            return LegacyVersion.V070, legacy_v070_path

    return LegacyVersion.NONE, None


def print_legacy_migration_hint(
    output: "OutputManager",
    legacy_version: LegacyVersion,
    legacy_path: Path,
    charts_dir: Path,
) -> None:
    """Print migration hints for legacy chart paths.

    Args:
        output: OutputManager for printing messages
        legacy_version: Detected legacy version
        legacy_path: Path to legacy chart
        charts_dir: Charts directory for removal hint

    """
    version_str = legacy_version.value

    output.print_error(f"Chart found at legacy path ({version_str}): {legacy_path}")

    if legacy_version == LegacyVersion.V070:
        output.print_warning(
            "This chart was downloaded with a very old version of SBKube"
        )
    else:
        output.print_warning(
            "This chart was downloaded with an older version of SBKube"
        )

    # Get console for rich formatting
    console = output.get_console()
    console.print("[yellow]💡 Migration required (v0.8.0 path structure):[/yellow]")
    console.print(f"   1. Remove old charts: rm -rf {charts_dir}")
    console.print("   2. Re-download charts: sbkube prepare --force")
    console.print(
        "\n📚 See: docs/05-best-practices/directory-structure.md (v0.8.0 migration)"
    )


def resolve_remote_chart_path(
    app: "HelmApp",
    charts_dir: Path,
    output: "OutputManager | None" = None,
) -> ChartPathResult:
    """Resolve path for a remote Helm chart.

    Checks for:
    1. Modern path structure (v0.8.0+): charts/{repo}/{chart-name}-{version}/
    2. Legacy v0.7.1 path: charts/{chart-name}/
    3. Legacy v0.7.0 path: charts/{chart-name}/{chart-name}/

    Args:
        app: HelmApp configuration with chart reference
        charts_dir: Base charts directory (.sbkube/charts/)
        output: Optional OutputManager for printing migration hints

    Returns:
        ChartPathResult with resolution status and path

    """
    # Try modern path structure first
    source_path = app.get_chart_path(charts_dir)

    if source_path and source_path.exists():
        return ChartPathResult(
            chart_path=source_path,
            found=True,
        )

    # Check for legacy paths
    chart_name = app.get_chart_name()
    legacy_version, legacy_path = check_legacy_chart_paths(charts_dir, chart_name)

    if legacy_version != LegacyVersion.NONE and legacy_path:
        # Print migration hint if output manager provided
        if output:
            print_legacy_migration_hint(output, legacy_version, legacy_path, charts_dir)

        return ChartPathResult(
            chart_path=None,
            found=False,
            legacy_version=legacy_version,
            legacy_path=legacy_path,
            error_message=f"Chart found at legacy path ({legacy_version.value})",
        )

    # Not found anywhere
    error_msg = f"Remote chart not found: {source_path}"
    if output:
        output.print_error(error_msg)
        output.print_warning("Run 'sbkube prepare' first")

    return ChartPathResult(
        chart_path=None,
        found=False,
        error_message=error_msg,
    )


def resolve_local_chart_path(
    app: "HelmApp",
    app_config_dir: Path,
    output: "OutputManager | None" = None,
) -> ChartPathResult:
    """Resolve path for a local Helm chart.

    Handles three path formats:
    1. Relative path starting with "./": relative to app_config_dir
    2. Absolute path starting with "/": used as-is
    3. Simple name: treated as relative to app_config_dir

    Args:
        app: HelmApp configuration with chart reference
        app_config_dir: App configuration directory
        output: Optional OutputManager for printing errors

    Returns:
        ChartPathResult with resolution status and path

    """
    chart_ref = app.chart

    if chart_ref.startswith("./"):
        # Relative path: app_config_dir 기준
        source_path = app_config_dir / chart_ref[2:]  # Remove "./"
    elif chart_ref.startswith("/"):
        # Absolute path
        source_path = Path(chart_ref)
    else:
        # Simple name: treat as relative to app_config_dir
        source_path = app_config_dir / chart_ref

    if source_path.exists():
        return ChartPathResult(
            chart_path=source_path,
            found=True,
        )

    error_msg = f"Local chart not found: {source_path}"
    if output:
        output.print_error(error_msg)

    return ChartPathResult(
        chart_path=None,
        found=False,
        error_message=error_msg,
    )


def resolve_chart_path(
    app: "HelmApp",
    app_name: str,
    charts_dir: Path,
    build_dir: Path,
    app_config_dir: Path,
    output: "OutputManager | None" = None,
    check_build_first: bool = True,
) -> ChartPathResult:
    """Resolve chart path with build directory priority.

    Resolution order:
    1. Build directory (.sbkube/build/{app_name}/) - if check_build_first is True
    2. Remote chart path (if app.is_remote_chart())
    3. Local chart path

    Args:
        app: HelmApp configuration
        app_name: Name of the app (used for build directory lookup)
        charts_dir: Charts directory (.sbkube/charts/)
        build_dir: Build directory (.sbkube/build/)
        app_config_dir: App configuration directory
        output: Optional OutputManager for messages
        check_build_first: Whether to check build directory first (default: True)

    Returns:
        ChartPathResult with resolution status and path

    """
    # 1. Check build directory first (for deploy command)
    if check_build_first:
        build_path = build_dir / app_name
        if build_path.exists() and build_path.is_dir():
            return ChartPathResult(
                chart_path=build_path,
                found=True,
            )

    # 2. Resolve based on chart type
    if app.is_remote_chart():
        return resolve_remote_chart_path(app, charts_dir, output)
    else:
        return resolve_local_chart_path(app, app_config_dir, output)
