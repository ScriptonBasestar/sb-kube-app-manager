import os
import warnings
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import toml
import yaml

from sbkube.exceptions import ConfigFileNotFoundError, FileOperationError
from sbkube.utils.logger import logger


# ============================================================================
# Configuration File Detection (v0.10.0+)
# ============================================================================


class ConfigType(Enum):
    """Type of configuration detected."""

    UNIFIED = "unified"  # sbkube.yaml (v0.10.0+)
    WORKSPACE = "workspace"  # workspace.yaml (v0.9.x)
    LEGACY = "legacy"  # sources.yaml + config.yaml (v0.8.x and earlier)
    UNKNOWN = "unknown"  # No configuration found


@dataclass
class DetectedConfig:
    """Result of configuration file detection."""

    config_type: ConfigType
    primary_file: Path | None
    secondary_files: list[Path]
    base_dir: Path
    deprecation_warning: str | None = None

    def is_deprecated(self) -> bool:
        """Check if detected config format is deprecated."""
        return self.config_type in (ConfigType.WORKSPACE, ConfigType.LEGACY)


# File detection priority order
CONFIG_FILE_PRIORITY = [
    ("sbkube.yaml", ConfigType.UNIFIED),
    ("sbkube.yml", ConfigType.UNIFIED),
    ("workspace.yaml", ConfigType.WORKSPACE),
    ("workspace.yml", ConfigType.WORKSPACE),
]

LEGACY_FILES = [
    "sources.yaml",
    "sources.yml",
    "config.yaml",
    "config.yml",
]


def detect_config_file(
    search_dir: Path | str | None = None,
    explicit_file: Path | str | None = None,
) -> DetectedConfig:
    """Detect configuration file with priority ordering.

    Priority order:
    1. Explicit file (if provided)
    2. sbkube.yaml/yml (unified format)
    3. workspace.yaml/yml (multi-phase)
    4. sources.yaml/yml + config.yaml/yml (legacy)

    Args:
        search_dir: Directory to search in (default: current directory)
        explicit_file: Explicitly specified config file (overrides detection)

    Returns:
        DetectedConfig with file information and type

    """
    base_dir = Path(search_dir) if search_dir else Path.cwd()

    # If explicit file provided, use it
    if explicit_file:
        explicit_path = Path(explicit_file)
        if not explicit_path.is_absolute():
            explicit_path = base_dir / explicit_path

        if explicit_path.exists():
            config_type = _determine_config_type(explicit_path)
            warning = None
            if config_type == ConfigType.WORKSPACE:
                warning = (
                    "workspace.yaml format is deprecated. "
                    "Migrate to sbkube.yaml for v1.0 compatibility."
                )
            elif config_type == ConfigType.LEGACY:
                warning = (
                    "sources.yaml + config.yaml format is deprecated. "
                    "Migrate to sbkube.yaml for v1.0 compatibility."
                )

            return DetectedConfig(
                config_type=config_type,
                primary_file=explicit_path,
                secondary_files=[],
                base_dir=explicit_path.parent,
                deprecation_warning=warning,
            )

    # Search for config files in priority order
    for filename, config_type in CONFIG_FILE_PRIORITY:
        config_path = base_dir / filename
        if config_path.exists():
            warning = None
            if config_type == ConfigType.WORKSPACE:
                warning = (
                    "workspace.yaml format is deprecated. "
                    "Migrate to sbkube.yaml for v1.0 compatibility."
                )

            return DetectedConfig(
                config_type=config_type,
                primary_file=config_path,
                secondary_files=[],
                base_dir=base_dir,
                deprecation_warning=warning,
            )

    # Check for legacy files
    legacy_files = []
    for filename in LEGACY_FILES:
        file_path = base_dir / filename
        if file_path.exists():
            legacy_files.append(file_path)

    if legacy_files:
        # Find primary (sources.yaml preferred)
        primary = None
        for f in legacy_files:
            if "sources" in f.name:
                primary = f
                break
        if not primary:
            primary = legacy_files[0]

        secondary = [f for f in legacy_files if f != primary]

        return DetectedConfig(
            config_type=ConfigType.LEGACY,
            primary_file=primary,
            secondary_files=secondary,
            base_dir=base_dir,
            deprecation_warning=(
                "sources.yaml + config.yaml format is deprecated. "
                "Migrate to sbkube.yaml for v1.0 compatibility."
            ),
        )

    # No config found
    return DetectedConfig(
        config_type=ConfigType.UNKNOWN,
        primary_file=None,
        secondary_files=[],
        base_dir=base_dir,
    )


def _determine_config_type(file_path: Path) -> ConfigType:
    """Determine config type from file name and content.

    Args:
        file_path: Path to config file

    Returns:
        ConfigType enum value

    """
    name = file_path.name.lower()

    if name.startswith("sbkube"):
        return ConfigType.UNIFIED
    if name.startswith("workspace"):
        return ConfigType.WORKSPACE
    if name.startswith("sources") or name.startswith("config"):
        return ConfigType.LEGACY

    # Check content for apiVersion
    try:
        with open(file_path, encoding="utf-8") as f:
            content = yaml.safe_load(f)
            if content and isinstance(content, dict):
                api_version = content.get("apiVersion", "")
                if api_version.startswith("sbkube/"):
                    return ConfigType.UNIFIED
                if "phases" in content and "metadata" in content:
                    return ConfigType.WORKSPACE
    except Exception:
        pass

    return ConfigType.UNKNOWN


def emit_deprecation_warning(detected: DetectedConfig) -> None:
    """Emit deprecation warning if applicable.

    Args:
        detected: Detected configuration result

    """
    if detected.deprecation_warning:
        warnings.warn(detected.deprecation_warning, DeprecationWarning, stacklevel=2)
        logger.warning(f"⚠️  {detected.deprecation_warning}")


def resolve_path(base: Path, relative: str) -> Path:
    """Resolve a relative path against a base path.

    Args:
        base: Base path to resolve against
        relative: Relative path string

    Returns:
        Path: Resolved absolute or relative path

    """
    p = Path(relative)
    return p if p.is_absolute() else base / p


def load_config_file(basename: str | Path) -> dict[str, Any]:
    """Load configuration file with multiple format support.

    Args:
        basename: Base filename without extension (e.g., 'config' or Path('config'))
                 Searches for .yaml → .yml → .toml in that order

    Returns:
        Dict[str, Any]: Loaded configuration data

    Raises:
        ConfigFileNotFoundError: When no configuration file is found
        FileOperationError: When file cannot be read or parsed

    """
    basename_str = str(basename)

    candidates = [
        f"{basename_str}.yaml" if not basename_str.endswith(".yaml") else basename_str,
        f"{basename_str}.yml" if not basename_str.endswith(".yml") else basename_str,
        f"{basename_str}.toml" if not basename_str.endswith(".toml") else basename_str,
    ]

    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for candidate in candidates:
        path = os.path.abspath(candidate)
        if path not in seen:
            seen.add(path)
            unique_candidates.append(candidate)

    # Try to load each candidate file
    for candidate in unique_candidates:
        if os.path.exists(candidate):
            try:
                return _load_file_by_extension(candidate)
            except Exception as e:
                logger.error(f"Failed to parse config file '{candidate}': {e}")
                raise FileOperationError(candidate, "parse", str(e))

    logger.error(f"설정 파일을 찾을 수 없습니다: {basename_str}.yaml|.yml|.toml")
    raise ConfigFileNotFoundError(basename_str, unique_candidates)


def _load_file_by_extension(file_path: str) -> dict[str, Any]:
    """Load file content based on extension.

    Args:
        file_path: Path to the file to load

    Returns:
        Dict[str, Any]: Parsed file content

    Raises:
        FileOperationError: When file cannot be read or parsed

    """
    ext = os.path.splitext(file_path)[1].lower()

    try:
        with open(file_path, encoding="utf-8") as f:
            if ext in [".yaml", ".yml"]:
                content = yaml.safe_load(f)
                return content if content is not None else {}
            if ext == ".toml":
                return toml.load(f)
            raise FileOperationError(
                file_path,
                "parse",
                f"Unsupported file extension: {ext}",
            )
    except OSError as e:
        raise FileOperationError(file_path, "read", str(e))
    except yaml.YAMLError as e:
        raise FileOperationError(file_path, "parse", f"YAML parsing error: {e}")
    except toml.TomlDecodeError as e:
        raise FileOperationError(file_path, "parse", f"TOML parsing error: {e}")


def load_file_safely(file_path: str | Path) -> dict[str, Any]:
    """Load file safely without raising exceptions.

    Args:
        file_path: Path to the file to load

    Returns:
        Dict[str, Any]: Loaded configuration data or empty dict on failure

    """
    try:
        return _load_file_by_extension(str(file_path))
    except (FileOperationError, ConfigFileNotFoundError):
        logger.warning(
            f"Failed to load file '{file_path}', returning empty configuration",
        )
        return {}
