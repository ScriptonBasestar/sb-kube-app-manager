"""Configuration Loader with Backward Compatibility for SBKube v0.10.0+.

This module provides a unified configuration loading interface that supports
both the new sbkube.yaml format and legacy configuration files.

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

import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sbkube.exceptions import ConfigFileNotFoundError, ConfigValidationError
from sbkube.models.config_model import SBKubeConfig
from sbkube.models.sources_model import SourceScheme
from sbkube.models.unified_config_model import UnifiedConfig
from sbkube.models.workspace_model import WorkspaceConfig
from sbkube.utils.file_loader import (
    ConfigType,
    DetectedConfig,
    detect_config_file,
    emit_deprecation_warning,
)
from sbkube.utils.logger import logger


@dataclass
class LoadedConfiguration:
    """Result of configuration loading."""

    config_type: ConfigType
    unified_config: UnifiedConfig | None
    workspace_config: WorkspaceConfig | None
    sources_config: SourceScheme | None
    app_config: SBKubeConfig | None
    base_dir: Path
    config_file: Path | None

    def get_effective_settings(self) -> dict[str, Any]:
        """Get effective settings from the loaded configuration."""
        if self.unified_config:
            return self.unified_config.settings.model_dump()
        if self.sources_config:
            return {
                "kubeconfig": self.sources_config.kubeconfig,
                "kubeconfig_context": self.sources_config.kubeconfig_context,
                "namespace": self.app_config.namespace if self.app_config else "default",
                "helm_repos": {
                    k: v.model_dump() for k, v in self.sources_config.helm_repos.items()
                },
            }
        return {}


class ConfigLoader:
    """Configuration loader with backward compatibility.

    Supports:
    - UnifiedConfig (sbkube.yaml) - v0.10.0+
    - WorkspaceConfig (workspace.yaml) - v0.9.x
    - SourceScheme + SBKubeConfig (sources.yaml + config.yaml) - Legacy

    """

    def __init__(
        self,
        base_dir: Path | str | None = None,
        config_file: Path | str | None = None,
        app_config_dir: str | None = None,
        sources_file: str = "sources.yaml",
        config_file_name: str = "config.yaml",
        emit_warnings: bool = True,
    ) -> None:
        """Initialize configuration loader.

        Args:
            base_dir: Base directory for configuration files
            config_file: Explicit configuration file path
            app_config_dir: App configuration directory (for legacy format)
            sources_file: Sources file name (for legacy format)
            config_file_name: Config file name (for legacy format)
            emit_warnings: Whether to emit deprecation warnings

        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.config_file = Path(config_file) if config_file else None
        self.app_config_dir = app_config_dir
        self.sources_file = sources_file
        self.config_file_name = config_file_name
        self.emit_warnings = emit_warnings

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

            if self.emit_warnings and self._detected.is_deprecated():
                emit_deprecation_warning(self._detected)

        return self._detected

    def load(self) -> LoadedConfiguration:
        """Load configuration based on detected type.

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
            # Try legacy format explicitly
            legacy_result = self._try_load_legacy()
            if legacy_result:
                self._loaded = legacy_result
                return self._loaded

            msg = f"No configuration file found in {self.base_dir}"
            raise ConfigFileNotFoundError(
                str(self.base_dir),
                ["sbkube.yaml", "workspace.yaml", "sources.yaml"],
            )

        if detected.config_type == ConfigType.UNIFIED:
            self._loaded = self._load_unified(detected)
        elif detected.config_type == ConfigType.WORKSPACE:
            self._loaded = self._load_workspace(detected)
        else:  # LEGACY
            self._loaded = self._load_legacy(detected)

        return self._loaded

    def _load_unified(self, detected: DetectedConfig) -> LoadedConfiguration:
        """Load unified configuration (sbkube.yaml)."""
        if not detected.primary_file:
            msg = "No unified config file detected"
            raise ConfigValidationError(msg)

        config = UnifiedConfig.from_yaml(detected.primary_file)
        logger.info(f"Loaded unified config: {detected.primary_file}")

        return LoadedConfiguration(
            config_type=ConfigType.UNIFIED,
            unified_config=config,
            workspace_config=None,
            sources_config=None,
            app_config=None,
            base_dir=detected.base_dir,
            config_file=detected.primary_file,
        )

    def _load_workspace(self, detected: DetectedConfig) -> LoadedConfiguration:
        """Load workspace configuration (workspace.yaml)."""
        if not detected.primary_file:
            msg = "No workspace config file detected"
            raise ConfigValidationError(msg)

        config = WorkspaceConfig.from_yaml(detected.primary_file)
        logger.info(f"Loaded workspace config: {detected.primary_file}")

        return LoadedConfiguration(
            config_type=ConfigType.WORKSPACE,
            unified_config=None,
            workspace_config=config,
            sources_config=None,
            app_config=None,
            base_dir=detected.base_dir,
            config_file=detected.primary_file,
        )

    def _load_legacy(self, detected: DetectedConfig) -> LoadedConfiguration:
        """Load legacy configuration (sources.yaml + config.yaml)."""
        sources_config = None
        app_config = None

        # Load sources.yaml
        if detected.primary_file and "sources" in detected.primary_file.name:
            sources_config = SourceScheme.from_yaml(detected.primary_file)
            logger.info(f"Loaded sources config: {detected.primary_file}")

        # Load config.yaml from app_config_dir if specified
        if self.app_config_dir:
            config_path = self.base_dir / self.app_config_dir / self.config_file_name
            if config_path.exists():
                app_config = SBKubeConfig.from_yaml(config_path)
                logger.info(f"Loaded app config: {config_path}")

        return LoadedConfiguration(
            config_type=ConfigType.LEGACY,
            unified_config=None,
            workspace_config=None,
            sources_config=sources_config,
            app_config=app_config,
            base_dir=detected.base_dir,
            config_file=detected.primary_file,
        )

    def _try_load_legacy(self) -> LoadedConfiguration | None:
        """Try to load legacy configuration explicitly."""
        sources_path = self.base_dir / self.sources_file

        if not sources_path.exists():
            return None

        try:
            sources_config = SourceScheme.from_yaml(sources_path)

            if self.emit_warnings:
                warnings.warn(
                    "sources.yaml + config.yaml format is deprecated. "
                    "Migrate to sbkube.yaml for v1.0 compatibility.",
                    DeprecationWarning,
                    stacklevel=3,
                )

            app_config = None
            if self.app_config_dir:
                config_path = self.base_dir / self.app_config_dir / self.config_file_name
                if config_path.exists():
                    app_config = SBKubeConfig.from_yaml(config_path)

            return LoadedConfiguration(
                config_type=ConfigType.LEGACY,
                unified_config=None,
                workspace_config=None,
                sources_config=sources_config,
                app_config=app_config,
                base_dir=self.base_dir,
                config_file=sources_path,
            )

        except Exception:
            return None

    def to_unified_config(self) -> UnifiedConfig:
        """Convert loaded configuration to UnifiedConfig.

        This is useful for commands that want to work with a unified
        interface regardless of the original config format.

        Returns:
            UnifiedConfig instance

        """
        loaded = self.load()

        if loaded.unified_config:
            return loaded.unified_config

        # Convert from legacy/workspace
        return UnifiedConfig.from_legacy_files(
            sources_path=loaded.config_file
            if loaded.sources_config
            else None,
            config_path=self.base_dir / self.app_config_dir / self.config_file_name
            if self.app_config_dir
            else None,
            workspace_path=loaded.config_file
            if loaded.workspace_config
            else None,
        )


def load_configuration(
    base_dir: Path | str | None = None,
    config_file: Path | str | None = None,
    app_config_dir: str | None = None,
    emit_warnings: bool = True,
) -> tuple[LoadedConfiguration, ConfigType]:
    """Convenience function to load configuration.

    Args:
        base_dir: Base directory for configuration
        config_file: Explicit configuration file
        app_config_dir: App configuration directory
        emit_warnings: Whether to emit deprecation warnings

    Returns:
        Tuple of (LoadedConfiguration, ConfigType)

    """
    loader = ConfigLoader(
        base_dir=base_dir,
        config_file=config_file,
        app_config_dir=app_config_dir,
        emit_warnings=emit_warnings,
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
        ConfigType.WORKSPACE: "Workspace (workspace.yaml) [deprecated]",
        ConfigType.LEGACY: "Legacy (sources.yaml + config.yaml) [deprecated]",
        ConfigType.UNKNOWN: "Unknown",
    }
    return display_map.get(config_type, str(config_type))
