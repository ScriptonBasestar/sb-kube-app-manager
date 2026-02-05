"""Configuration Loader for SBKube v0.11.0+.

This module provides a unified configuration loading interface for sbkube.yaml format.

Usage:
    from sbkube.utils.config_loader import ConfigLoader, load_configuration

    # Auto-detect configuration
    config, config_type = load_configuration(base_dir=Path("."))

    # Explicit file
    config, config_type = load_configuration(config_file=Path("sbkube.yaml"))

    # Using ConfigLoader class
    loader = ConfigLoader(base_dir=Path("."))
    config = loader.load()
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sbkube.exceptions import ConfigFileNotFoundError, ConfigValidationError
from sbkube.models.unified_config_model import UnifiedConfig
from sbkube.utils.file_loader import (
    ConfigType,
    DetectedConfig,
    detect_config_file,
)
from sbkube.utils.logger import logger


@dataclass
class LoadedConfiguration:
    """Result of configuration loading."""

    config_type: ConfigType
    unified_config: UnifiedConfig
    base_dir: Path
    config_file: Path | None

    def get_effective_settings(self) -> dict[str, Any]:
        """Get effective settings from the loaded configuration."""
        return self.unified_config.settings.model_dump()


class ConfigLoader:
    """Configuration loader for sbkube.yaml.

    Supports only UnifiedConfig (sbkube.yaml) format.

    """

    def __init__(
        self,
        base_dir: Path | str | None = None,
        config_file: Path | str | None = None,
    ) -> None:
        """Initialize configuration loader.

        Args:
            base_dir: Base directory for configuration files
            config_file: Explicit configuration file path

        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.config_file = Path(config_file) if config_file else None

        self._detected: DetectedConfig | None = None
        self._loaded: LoadedConfiguration | None = None

    def detect(self) -> DetectedConfig:
        """Detect configuration file type.

        Returns:
            DetectedConfig with file information

        """
        if self._detected is None:
            self._detected = detect_config_file(
                search_dir=self.base_dir,
                explicit_file=self.config_file,
            )

        return self._detected

    def load(self) -> LoadedConfiguration:
        """Load configuration.

        Returns:
            LoadedConfiguration with parsed configuration

        Raises:
            ConfigFileNotFoundError: If no configuration found
            ConfigValidationError: If configuration is invalid

        """
        if self._loaded is not None:
            return self._loaded

        detected = self.detect()

        if detected.config_type == ConfigType.UNKNOWN:
            msg = f"No sbkube.yaml found in {self.base_dir}"
            raise ConfigFileNotFoundError(
                str(self.base_dir),
                ["sbkube.yaml", "sbkube.yml"],
            )

        self._loaded = self._load_unified(detected)
        return self._loaded

    def _load_unified(self, detected: DetectedConfig) -> LoadedConfiguration:
        """Load unified configuration (sbkube.yaml)."""
        if not detected.primary_file:
            msg = "No config file detected"
            raise ConfigValidationError(msg)

        config = UnifiedConfig.from_yaml(detected.primary_file)
        logger.info(f"Loaded config: {detected.primary_file}")

        return LoadedConfiguration(
            config_type=ConfigType.UNIFIED,
            unified_config=config,
            base_dir=detected.base_dir,
            config_file=detected.primary_file,
        )

    def to_unified_config(self) -> UnifiedConfig:
        """Get UnifiedConfig from loaded configuration.

        Returns:
            UnifiedConfig instance

        """
        return self.load().unified_config


def load_configuration(
    base_dir: Path | str | None = None,
    config_file: Path | str | None = None,
) -> tuple[LoadedConfiguration, ConfigType]:
    """Convenience function to load configuration.

    Args:
        base_dir: Base directory for configuration
        config_file: Explicit configuration file

    Returns:
        Tuple of (LoadedConfiguration, ConfigType)

    """
    loader = ConfigLoader(
        base_dir=base_dir,
        config_file=config_file,
    )

    loaded = loader.load()
    return loaded, loaded.config_type


def get_config_type_display(config_type: ConfigType) -> str:
    """Get display string for config type.

    Args:
        config_type: Configuration type

    Returns:
        Human-readable string

    """
    display_map = {
        ConfigType.UNIFIED: "Unified (sbkube.yaml)",
        ConfigType.UNKNOWN: "Unknown",
    }
    return display_map.get(config_type, str(config_type))
