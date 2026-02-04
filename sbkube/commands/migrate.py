"""Configuration migration command.

This command migrates legacy configuration files (sources.yaml + config.yaml,
workspace.yaml) to the new unified sbkube.yaml format.

Version: v1.0.0+
"""

from pathlib import Path
from typing import Any

import click
import yaml

from sbkube.models.unified_config_model import UnifiedConfig
from sbkube.utils.file_loader import ConfigType, detect_config_file
from sbkube.utils.logger import logger


@click.command(name="migrate")
@click.option(
    "--source-dir",
    "-s",
    default=".",
    type=click.Path(exists=True),
    help="Directory containing legacy configuration files",
)
@click.option(
    "--output",
    "-o",
    default="sbkube.yaml",
    type=click.Path(),
    help="Output file path (default: sbkube.yaml)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview the migration without writing files",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Overwrite existing output file",
)
@click.option(
    "--validate",
    is_flag=True,
    default=True,
    help="Validate the generated configuration (default: True)",
)
@click.pass_context
def cmd(
    ctx,
    source_dir: str,
    output: str,
    dry_run: bool,
    force: bool,
    validate: bool,
) -> None:
    r"""Migrate legacy configuration to unified sbkube.yaml format.

    This command converts legacy configuration files to the new unified format:
    - sources.yaml + config.yaml -> sbkube.yaml
    - workspace.yaml -> sbkube.yaml

    \b
    Examples:
        # Preview migration (dry-run)
        sbkube migrate --dry-run

        # Migrate current directory
        sbkube migrate

        # Migrate from specific directory
        sbkube migrate -s ./legacy-config -o ./new-config/sbkube.yaml

        # Force overwrite existing file
        sbkube migrate -o sbkube.yaml --force
    """
    try:
        source_path = Path(source_dir).resolve()
        output_path = Path(output).resolve()

        # Detect existing configuration
        detected = detect_config_file(source_path)

        if detected.config_type == ConfigType.UNIFIED:
            logger.info("Already using unified config format (sbkube.yaml)")
            logger.info("No migration needed.")
            return

        if detected.config_type == ConfigType.UNKNOWN:
            logger.error("No legacy configuration files found in the specified directory")
            logger.info("Expected: sources.yaml, config.yaml, or workspace.yaml")
            raise click.Abort()

        # Display detected configuration
        logger.heading("Configuration Migration")
        logger.info(f"Source directory: {source_path}")
        logger.info(f"Detected format: {detected.config_type.value}")

        if detected.primary_file:
            logger.info(f"Primary file: {detected.primary_file}")
        if detected.secondary_files:
            for f in detected.secondary_files:
                logger.info(f"Secondary file: {f}")

        # Determine source files
        sources_path = None
        config_path = None
        workspace_path = None

        if detected.config_type == ConfigType.WORKSPACE:
            workspace_path = detected.primary_file
        elif detected.config_type == ConfigType.LEGACY:
            # Try to find sources.yaml and config.yaml
            sources_path = source_path / "sources.yaml"
            if not sources_path.exists():
                sources_path = detected.primary_file

            # Look for config.yaml in common locations
            config_candidates = [
                source_path / "config.yaml",
                source_path / "config" / "config.yaml",
            ]
            for candidate in config_candidates:
                if candidate.exists():
                    config_path = candidate
                    break

        # Perform migration
        logger.info("\nConverting to unified format...")

        unified_config = UnifiedConfig.from_legacy_files(
            sources_path=sources_path,
            config_path=config_path,
            workspace_path=workspace_path,
        )

        # Validate if requested
        if validate:
            logger.info("Validating converted configuration...")
            # Validation is done by Pydantic during model creation
            logger.success("Configuration is valid")

        # Generate YAML output
        config_dict = _config_to_yaml_dict(unified_config)
        yaml_output = yaml.dump(
            config_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        if dry_run:
            logger.heading("Migration Preview (dry-run)")
            click.echo("\n" + "=" * 60)
            click.echo(yaml_output)
            click.echo("=" * 60)
            logger.info(f"\nWould write to: {output_path}")
        else:
            # Check if output file exists
            if output_path.exists() and not force:
                logger.error(f"Output file already exists: {output_path}")
                logger.info("Use --force to overwrite")
                raise click.Abort()

            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write output file
            output_path.write_text(yaml_output, encoding="utf-8")
            logger.success(f"Migration complete: {output_path}")

            # Provide next steps
            logger.info("\nNext steps:")
            logger.info(f"  1. Review the generated {output_path.name}")
            logger.info("  2. Test with: sbkube validate -f sbkube.yaml")
            logger.info("  3. Run with: sbkube apply -f sbkube.yaml --dry-run")

            if detected.config_type == ConfigType.LEGACY:
                logger.warning("\nThe legacy files can be removed after verification:")
                if sources_path:
                    logger.warning(f"  - {sources_path}")
                if config_path:
                    logger.warning(f"  - {config_path}")
            elif detected.config_type == ConfigType.WORKSPACE:
                logger.warning(f"\nThe workspace file can be removed after verification:")
                logger.warning(f"  - {workspace_path}")

    except click.Abort:
        raise
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise click.Abort()


def _config_to_yaml_dict(config: UnifiedConfig) -> dict[str, Any]:
    """Convert UnifiedConfig to a YAML-friendly dictionary.

    Args:
        config: UnifiedConfig instance

    Returns:
        Dictionary suitable for YAML serialization

    """
    result: dict[str, Any] = {
        "apiVersion": config.apiVersion,
    }

    # Metadata
    if config.metadata:
        result["metadata"] = config.metadata

    # Settings - only include non-default values
    settings_dict = _clean_settings_dict(config.settings.model_dump())
    if settings_dict:
        result["settings"] = settings_dict

    # Apps
    if config.apps:
        result["apps"] = {}
        for app_name, app_config in config.apps.items():
            result["apps"][app_name] = _clean_app_dict(app_config.model_dump())

    # Phases
    if config.phases:
        result["phases"] = {}
        for phase_name, phase_ref in config.phases.items():
            phase_dict: dict[str, Any] = {}
            if phase_ref.description:
                phase_dict["description"] = phase_ref.description
            if phase_ref.source:
                phase_dict["source"] = phase_ref.source
            if phase_ref.depends_on:
                phase_dict["depends_on"] = phase_ref.depends_on
            if phase_ref.apps:
                phase_dict["apps"] = {}
                for app_name, app_config in phase_ref.apps.items():
                    phase_dict["apps"][app_name] = _clean_app_dict(app_config.model_dump())
            if phase_ref.settings:
                phase_dict["settings"] = _clean_settings_dict(
                    phase_ref.settings.model_dump()
                )
            result["phases"][phase_name] = phase_dict

    return result


def _clean_settings_dict(settings: dict[str, Any]) -> dict[str, Any]:
    """Remove default/None values from settings dictionary.

    Args:
        settings: Raw settings dictionary

    Returns:
        Cleaned dictionary with only meaningful values

    """
    # Default values to exclude
    defaults = {
        "kubeconfig": None,
        "kubeconfig_context": None,
        "cluster": None,
        "namespace": "default",
        "timeout": 600,
        "on_failure": "stop",
        "rollback_scope": "app",
        "execution_order": "apps_first",
        "parallel": False,
        "parallel_apps": False,
        "max_workers": 4,
        "helm_label_injection": True,
        "cluster_values_file": None,
        "http_proxy": None,
        "https_proxy": None,
        "no_proxy": None,
        "cleanup_metadata": True,
    }

    result = {}
    for key, value in settings.items():
        if value is None:
            continue
        if key in defaults and value == defaults[key]:
            continue
        # Handle empty collections
        if isinstance(value, (dict, list)) and not value:
            continue
        # Recursively clean nested dicts
        if isinstance(value, dict):
            cleaned = _clean_nested_dict(value)
            if cleaned:
                result[key] = cleaned
        else:
            result[key] = value

    return result


def _clean_nested_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively clean nested dictionaries.

    Args:
        d: Dictionary to clean

    Returns:
        Cleaned dictionary

    """
    result = {}
    for key, value in d.items():
        if value is None:
            continue
        if isinstance(value, (dict, list)) and not value:
            continue
        if isinstance(value, dict):
            cleaned = _clean_nested_dict(value)
            if cleaned:
                result[key] = cleaned
        else:
            result[key] = value
    return result


def _clean_app_dict(app: dict[str, Any]) -> dict[str, Any]:
    """Remove default/None values from app dictionary.

    Args:
        app: Raw app dictionary

    Returns:
        Cleaned dictionary with only meaningful values

    """
    # Default values for helm apps
    helm_defaults = {
        "create_namespace": False,
        "wait": True,
        "timeout": "5m",
        "atomic": False,
        "helm_label_injection": True,
        "force_label_injection": False,
    }

    result = {}
    for key, value in app.items():
        if value is None:
            continue
        if key == "enabled" and value is True:
            continue  # Default is enabled
        if key in helm_defaults and value == helm_defaults[key]:
            continue
        if isinstance(value, (dict, list)) and not value:
            continue
        if isinstance(value, dict):
            cleaned = _clean_nested_dict(value)
            if cleaned:
                result[key] = cleaned
        else:
            result[key] = value

    return result
