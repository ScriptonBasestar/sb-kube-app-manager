"""
Base model with configuration inheritance support.

This module provides base classes for configuration models with
built-in support for inheritance, validation, and error handling.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Type, TypeVar, Union

import yaml
from pydantic import BaseModel, ConfigDict, model_validator
from pydantic_core import ValidationError

from sbkube.exceptions import ConfigValidationError
from sbkube.utils.logger import get_logger

from .validators import ValidatorMixin

logger = get_logger()

T = TypeVar("T", bound="ConfigBaseModel")


class ConfigBaseModel(BaseModel, ValidatorMixin):
    """
    Base model for all configuration models with enhanced validation.

    Features:
    - Automatic validation on instantiation
    - Inheritance support
    - Enhanced error messages
    - Built-in validators from ValidatorMixin
    """

    model_config = ConfigDict(
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=True,
        extra="forbid",  # Prevent unknown fields
    )

    def __init__(self, **data):
        """Initialize with enhanced error handling."""
        try:
            super().__init__(**data)
        except ValidationError as e:
            # Format validation errors for better readability
            errors = []
            for error in e.errors():
                field_path = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"  - {field_path}: {msg}")

            raise ConfigValidationError(
                "Configuration validation failed:\n" + "\n".join(errors)
            )

    @classmethod
    def from_dict(
        cls: Type[T], data: Dict[str, Any], context: Optional[Dict[str, Any]] = None
    ) -> T:
        """
        Create instance from dictionary with optional context.

        Args:
            data: Configuration data dictionary
            context: Optional context for validation (e.g., parent config)

        Returns:
            Validated model instance
        """
        if context:
            # Store context for validators that need it
            data["_context"] = context

        instance = cls(**data)

        # Remove context from model data after validation
        if hasattr(instance, "_context"):
            delattr(instance, "_context")

        return instance

    def merge_with(
        self: T, other: Optional[Union[Dict[str, Any], T]], deep: bool = True
    ) -> T:
        """
        Merge this configuration with another, creating a new instance.

        Args:
            other: Configuration to merge with (dict or model instance)
            deep: Whether to perform deep merge for nested structures

        Returns:
            New instance with merged configuration
        """
        if other is None:
            return self.model_copy()

        if isinstance(other, BaseModel):
            other_dict = other.model_dump()
        else:
            other_dict = other

        self_dict = self.model_dump()

        if deep:
            merged = self._deep_merge(self_dict, other_dict)
        else:
            merged = {**self_dict, **other_dict}

        return self.__class__(**merged)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform deep merge of two dictionaries.

        Args:
            base: Base dictionary
            override: Dictionary with values to override

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigBaseModel._deep_merge(result[key], value)
            elif (
                key in result
                and isinstance(result[key], list)
                and isinstance(value, list)
            ):
                # For lists, we can either extend or replace
                # Here we choose to replace to match Helm's behavior
                result[key] = value
            else:
                result[key] = value

        return result

    def validate_against_schema(self, schema_path: Path) -> None:
        """
        Validate this model against a JSON schema.

        Args:
            schema_path: Path to JSON schema file

        Raises:
            ConfigValidationError: If validation fails
        """
        try:
            import jsonschema

            with open(schema_path, "r") as f:
                schema = yaml.safe_load(f)

            data = self.model_dump()
            jsonschema.validate(instance=data, schema=schema)

        except jsonschema.ValidationError as e:
            raise ConfigValidationError(
                f"Schema validation failed: {e.message}\n"
                f"Failed at path: {'.'.join(str(x) for x in e.path)}"
            )
        except Exception as e:
            raise ConfigValidationError(f"Schema validation error: {str(e)}")

    def to_yaml(self, path: Optional[Path] = None) -> str:
        """
        Convert model to YAML string or save to file.

        Args:
            path: Optional path to save YAML file

        Returns:
            YAML string representation
        """
        data = self.model_dump(exclude_none=True)
        yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)

        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(yaml_str)

        return yaml_str

    @classmethod
    def from_yaml(cls: Type[T], path: Union[str, Path]) -> T:
        """
        Load model from YAML file.

        Args:
            path: Path to YAML file

        Returns:
            Model instance
        """
        path = Path(path)
        if not path.exists():
            raise ConfigValidationError(f"Configuration file not found: {path}")

        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f)

            if data is None:
                data = {}

            return cls(**data)

        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Invalid YAML in {path}: {str(e)}")


class InheritableConfigModel(ConfigBaseModel):
    """
    Base model with built-in inheritance support.

    Supports:
    - Inheriting from parent configurations
    - Merging with defaults
    - Override specific fields
    """

    _parent: Optional[str] = None  # Path to parent config
    _defaults: Optional[Dict[str, Any]] = None  # Default values

    @model_validator(mode="before")
    @classmethod
    def apply_inheritance(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Apply inheritance from parent configuration."""
        parent_path = values.pop("_parent", None)
        defaults = values.pop("_defaults", None)

        # Start with defaults if provided
        if defaults:
            result = defaults.copy()
            result.update(values)
            values = result

        # Apply parent configuration if specified
        if parent_path:
            try:
                parent = cls.from_yaml(parent_path)
                parent_dict = parent.model_dump()

                # Deep merge parent with current values
                values = cls._deep_merge(parent_dict, values)

            except Exception as e:
                logger.warning(f"Failed to load parent config from {parent_path}: {e}")

        return values


class ConfigLoader:
    """
    Utility class for loading configurations with inheritance and validation.
    """

    def __init__(self, base_dir: Path, schema_dir: Optional[Path] = None):
        """
        Initialize configuration loader.

        Args:
            base_dir: Base directory for configuration files
            schema_dir: Optional directory containing JSON schemas
        """
        self.base_dir = Path(base_dir)
        self.schema_dir = Path(schema_dir) if schema_dir else None
        self._cache: Dict[str, Any] = {}

    def load_config(
        self,
        config_path: Union[str, Path],
        model_class: Type[T],
        validate_schema: bool = True,
        use_cache: bool = True,
    ) -> T:
        """
        Load and validate configuration file.

        Args:
            config_path: Path to configuration file
            model_class: Pydantic model class to use
            validate_schema: Whether to validate against JSON schema
            use_cache: Whether to use cached configurations

        Returns:
            Validated configuration instance
        """
        config_path = self.base_dir / config_path
        cache_key = f"{model_class.__name__}:{config_path}"

        # Check cache
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Load configuration
        config = model_class.from_yaml(config_path)

        # Validate against schema if requested
        if validate_schema and self.schema_dir:
            schema_name = f"{model_class.__name__.lower()}.schema.json"
            schema_path = self.schema_dir / schema_name

            if schema_path.exists():
                config.validate_against_schema(schema_path)

        # Cache the result
        if use_cache:
            self._cache[cache_key] = config

        return config

    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()
