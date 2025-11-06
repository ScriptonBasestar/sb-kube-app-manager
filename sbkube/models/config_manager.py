"""Configuration manager with inheritance and validation support.

This module provides a centralized configuration management system
with support for inheritance, validation, and multi-environment configs.
"""

import json
from pathlib import Path
from typing import Any

import yaml

from sbkube.exceptions import FileOperationError
from sbkube.utils.logger import get_logger

from .base_model import ConfigLoader
from .config_model import SBKubeConfig
from .sources_model import SourceScheme

logger = get_logger()


class ConfigManager:
    """Centralized configuration manager for sbkube.

    Features:
    - Configuration inheritance
    - Multi-environment support
    - Validation and schema enforcement
    - Configuration merging
    - Default values management
    """

    def __init__(
        self,
        base_dir: str | Path,
        schema_dir: str | Path | None = None,
    ) -> None:
        """Initialize configuration manager.

        Args:
            base_dir: Base directory for configuration files
            schema_dir: Optional directory containing JSON schemas

        """
        self.base_dir = Path(base_dir)
        self.schema_dir = Path(schema_dir) if schema_dir else self.base_dir / "schemas"
        self.loader = ConfigLoader(self.base_dir, self.schema_dir)

        # Cache for loaded configurations
        self._sources_cache: dict[str, SourceScheme] = {}
        self._app_configs_cache: dict[str, SBKubeConfig] = {}
        self._defaults: dict[str, Any] = {}

    def load_sources(
        self,
        sources_file: str = "sources.yaml",
        environment: str | None = None,
        validate: bool = True,
    ) -> SourceScheme:
        """Load sources configuration with optional environment overlay.

        Args:
            sources_file: Base sources configuration file
            environment: Optional environment name for overlay
            validate: Whether to validate against schema

        Returns:
            Loaded and validated SourceScheme

        """
        cache_key = f"{sources_file}:{environment or 'default'}"

        if cache_key in self._sources_cache:
            return self._sources_cache[cache_key]

        # Load base sources
        sources = self.loader.load_config(
            sources_file,
            SourceScheme,
            validate_schema=validate,
        )

        # Apply environment overlay if specified
        if environment:
            env_file = self.base_dir / f"sources.{environment}.yaml"
            if env_file.exists():
                env_sources = self.loader.load_config(
                    env_file.name,
                    SourceScheme,
                    validate_schema=validate,
                )
                sources = sources.merge_with(env_sources)

        # Cache the result
        self._sources_cache[cache_key] = sources

        return sources

    def load_app_config(
        self,
        app_dir: str | Path,
        config_file: str = "config.yaml",
        inherit_from: str | None = None,
        validate: bool = True,
    ) -> SBKubeConfig:
        """Load application configuration with inheritance support.

        Args:
            app_dir: Application configuration directory
            config_file: Configuration file name
            inherit_from: Optional parent configuration to inherit from
            validate: Whether to validate against schema

        Returns:
            Loaded and validated SBKubeConfig

        """
        config_path = Path(app_dir) / config_file
        cache_key = f"{config_path}:{inherit_from or 'no-parent'}"

        if cache_key in self._app_configs_cache:
            return self._app_configs_cache[cache_key]

        # Load configuration with inheritance
        if inherit_from:
            config_data = self._load_with_inheritance(config_path, inherit_from)
            config = SBKubeConfig(**config_data)
        else:
            config = self.loader.load_config(
                config_path,
                SBKubeConfig,
                validate_schema=validate,
            )

        # Apply defaults if set
        if self._defaults:
            config = self._apply_defaults(config)

        # Cache the result
        self._app_configs_cache[cache_key] = config

        return config

    def _load_with_inheritance(
        self,
        config_path: Path,
        parent_path: str,
    ) -> dict[str, Any]:
        """Load configuration with inheritance from parent.

        Args:
            config_path: Path to child configuration
            parent_path: Path to parent configuration

        Returns:
            Merged configuration dictionary

        """
        # Load parent configuration
        parent_config = self.load_app_config(parent_path)
        parent_data = parent_config.model_dump()

        # Load child configuration
        child_path = self.base_dir / config_path
        if not child_path.exists():
            msg = f"Configuration file not found: {child_path}"
            raise FileOperationError(msg)

        with open(child_path) as f:
            child_data = yaml.safe_load(f) or {}

        # Merge configurations
        return self._deep_merge(parent_data, child_data)


    def _deep_merge(
        self,
        base: dict[str, Any],
        overlay: dict[str, Any],
    ) -> dict[str, Any]:
        """Deep merge two dictionaries.

        Args:
            base: Base dictionary
            overlay: Dictionary to overlay

        Returns:
            Merged dictionary

        """
        result = base.copy()

        for key, value in overlay.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = self._deep_merge(result[key], value)
                elif isinstance(result[key], list) and isinstance(value, list):
                    # For lists, we can either extend or replace
                    # Here we choose to replace (similar to Helm)
                    result[key] = value
                else:
                    result[key] = value
            else:
                result[key] = value

        return result

    def _apply_defaults(self, config: SBKubeConfig) -> SBKubeConfig:
        """Apply default values to configuration.

        Args:
            config: Configuration to apply defaults to

        Returns:
            Configuration with defaults applied

        """
        # Apply namespace default
        if "namespace" in self._defaults and not config.namespace:
            config.namespace = self._defaults["namespace"]

        # Apply app defaults
        for app in config.apps:
            if "app_defaults" in self._defaults:
                app_defaults = self._defaults["app_defaults"].get(app.type, {})
                if app_defaults:
                    # Merge defaults with app specs
                    app.specs = {**app_defaults, **app.specs}

        return config

    def set_defaults(self, defaults: dict[str, Any]) -> None:
        """Set default values for configurations.

        Args:
            defaults: Dictionary of default values

        """
        self._defaults = defaults

    def validate_config_references(
        self,
        app_config: SBKubeConfig,
        sources: SourceScheme,
    ) -> list[str]:
        """Validate that all references in app config exist in sources.

        Args:
            app_config: Application configuration
            sources: Sources configuration

        Returns:
            List of validation errors (empty if valid)

        """
        errors = []

        # Convert apps to dict format for validation
        app_dicts = [app.model_dump() for app in app_config.apps]

        # Use sources validation method
        ref_errors = sources.validate_repo_references(app_dicts)
        errors.extend(ref_errors)

        # Validate dependencies exist
        for dep in app_config.deps:
            dep_path = self.base_dir / dep / "config.yaml"
            if not dep_path.exists():
                errors.append(f"Dependency not found: {dep}")

        return errors

    def load_all_configs(
        self,
        app_dirs: list[str | Path],
        sources_file: str = "sources.yaml",
        environment: str | None = None,
        validate: bool = True,
    ) -> dict[str, SBKubeConfig]:
        """Load multiple application configurations.

        Args:
            app_dirs: List of application directories
            sources_file: Sources configuration file
            environment: Optional environment name
            validate: Whether to validate configurations

        Returns:
            Dictionary mapping app_dir to SBKubeConfig

        """
        configs = {}

        # Load sources first
        sources = self.load_sources(sources_file, environment, validate)

        # Load each app config
        for app_dir in app_dirs:
            try:
                config = self.load_app_config(app_dir, validate=validate)

                # Validate references if requested
                if validate:
                    errors = self.validate_config_references(config, sources)
                    if errors:
                        logger.warning(
                            f"Validation errors in {app_dir}:\n"
                            + "\n".join(f"  - {e}" for e in errors),
                        )

                configs[str(app_dir)] = config

            except Exception as e:
                logger.exception(f"Failed to load config from {app_dir}: {e}")
                if validate:
                    raise

        return configs

    def export_merged_config(
        self,
        app_config: SBKubeConfig,
        output_path: str | Path,
        format: str = "yaml",
    ) -> None:
        """Export merged configuration to file.

        Args:
            app_config: Application configuration to export
            output_path: Output file path
            format: Output format (yaml or json)

        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        data = app_config.model_dump(exclude_none=True)

        if format.lower() == "yaml":
            with open(output_path, "w") as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        elif format.lower() == "json":
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
        else:
            msg = f"Unsupported format: {format}"
            raise ValueError(msg)

        logger.info(f"Exported configuration to {output_path}")

    def clear_cache(self) -> None:
        """Clear all configuration caches."""
        self._sources_cache.clear()
        self._app_configs_cache.clear()
        self.loader.clear_cache()
