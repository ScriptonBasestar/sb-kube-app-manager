"""
Enhanced command base class with integrated validation and inheritance support.

This module provides an improved base class for all sbkube commands
with automatic configuration validation and inheritance capabilities.
"""

from pathlib import Path

import click

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_manager import ConfigManager
from sbkube.models.config_model import SBKubeConfig
from sbkube.models.sources_model import SourceScheme
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.hook_executor import HookExecutor
from sbkube.utils.logger import LogLevel, logger


class EnhancedBaseCommand:
    """Enhanced base class for all commands with validation support."""

    def __init__(
        self,
        base_dir: str = ".",
        app_config_dir: str = "config",
        cli_namespace: str | None = None,
        config_file_name: str | None = None,
        sources_file: str = "sources.yaml",
        validate_on_load: bool = True,
        use_inheritance: bool = True,
    ):
        """
        Initialize enhanced base command.

        Args:
            base_dir: Project root directory
            app_config_dir: App configuration directory name
            cli_namespace: CLI-specified namespace
            config_file_name: Configuration file name to use
            sources_file: Sources configuration file name
            validate_on_load: Whether to validate configurations on load
            use_inheritance: Whether to enable configuration inheritance
        """
        self.base_dir = Path(base_dir).resolve()
        self.app_config_dir = self.base_dir / app_config_dir
        self.cli_namespace = cli_namespace
        self.config_file_name = config_file_name
        self.sources_file = sources_file
        self.validate_on_load = validate_on_load
        self.use_inheritance = use_inheritance

        # Common directories
        self.build_dir = self.app_config_dir / "build"
        self.values_dir = self.app_config_dir / "values"
        self.charts_dir = self.base_dir / "charts"
        self.repos_dir = self.base_dir / "repos"
        self.schema_dir = self.base_dir / "schemas"

        # Configuration manager
        self.config_manager = ConfigManager(
            base_dir=self.base_dir,
            schema_dir=self.schema_dir if self.schema_dir.exists() else None,
        )

        # Configuration objects
        self.config_file_path: Path | None = None
        self.app_group: SBKubeConfig | None = None
        self.sources: SourceScheme | None = None
        self.app_info_list: list = []

        # Validation errors tracking
        self.validation_errors: list[str] = []

        # Hook executor (initialized after config load)
        self.hook_executor: HookExecutor | None = None

    def _init_hook_executor(self, dry_run: bool = False):
        """Initialize hook executor after configuration is loaded."""
        if not self.hook_executor:
            self.hook_executor = HookExecutor(
                base_dir=self.base_dir,
                working_dir=self.app_config_dir,
                dry_run=dry_run,
            )

    def execute_pre_hook(self):
        """Execute common preprocessing before each command."""
        try:
            # Load configurations with validation
            self.load_config()

            # Load sources if needed
            if self.needs_sources():
                self.load_sources()

            # Validate cross-references if both configs are loaded
            if self.app_group and self.sources:
                self.validate_references()

            logger.verbose("Enhanced preprocessing completed")

        except ConfigValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            if self.validation_errors:
                logger.error("Validation errors:")
                for error in self.validation_errors:
                    logger.error(f"  - {error}")
            raise click.Abort()

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise click.Abort()

    def needs_sources(self) -> bool:
        """
        Check if this command needs sources configuration.
        Override in subclasses as needed.
        """
        # By default, check if any apps need repository references
        if not self.app_info_list:
            return False

        source_types = {"helm", "git", "http"}
        return any(app.type in source_types for app in self.app_info_list)

    def find_config_file(self) -> Path:
        """Find configuration file (config.yaml, config.yml, config.toml)."""
        if self.config_file_name:
            # --config-file option specified
            config_path = self.app_config_dir / self.config_file_name
            if not config_path.exists() or not config_path.is_file():
                logger.error(f"Specified config file not found: {config_path}")
                raise click.Abort()
            return config_path
        else:
            # Auto-detect
            for ext in [".yaml", ".yml", ".toml"]:
                candidate = self.app_config_dir / f"config{ext}"
                if candidate.exists() and candidate.is_file():
                    return candidate

            logger.error(
                f"App config file not found: {self.app_config_dir}/config.[yaml|yml|toml]",
            )
            raise click.Abort()

    def load_config(self) -> SBKubeConfig:
        """Load and validate configuration file."""
        self.config_file_path = self.find_config_file()
        logger.info(f"Using config file: {self.config_file_path}")

        try:
            # Check for parent configuration in the file
            parent_config = None
            if self.use_inheritance:
                # Peek at the raw data to check for _parent field
                raw_data = load_config_file(str(self.config_file_path))
                parent_config = raw_data.get("_parent")

            # Load with config manager
            self.app_group = self.config_manager.load_app_config(
                app_dir=self.app_config_dir.relative_to(self.base_dir),
                config_file=self.config_file_path.name,
                inherit_from=parent_config,
                validate=self.validate_on_load,
            )

            # Parse apps list
            self.app_info_list = self.app_group.get_enabled_apps()

            return self.app_group

        except ConfigValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise ConfigValidationError(f"Failed to load config: {e}")

    def load_sources(self) -> SourceScheme:
        """Load and validate sources configuration."""
        try:
            # Determine environment from config or CLI
            environment = self.get_environment()

            self.sources = self.config_manager.load_sources(
                sources_file=self.sources_file,
                environment=environment,
                validate=self.validate_on_load,
            )

            logger.info(f"Loaded sources for cluster: {self.sources.cluster}")
            return self.sources

        except ConfigValidationError:
            raise  # Re-raise validation errors
        except Exception as e:
            raise ConfigValidationError(f"Failed to load sources: {e}")

    def get_environment(self) -> str | None:
        """
        Determine environment name from config or CLI.
        Override in subclasses to implement custom logic.
        """
        # Could be extended to support --profile CLI option
        return None

    def validate_references(self):
        """Validate references between app config and sources."""
        if not self.app_group or not self.sources:
            return

        errors = self.config_manager.validate_config_references(
            self.app_group,
            self.sources,
        )

        if errors:
            self.validation_errors.extend(errors)
            if self.validate_on_load:
                raise ConfigValidationError(
                    f"Found {len(errors)} reference validation errors",
                )

    def parse_apps(
        self,
        app_types: list[str] | None = None,
        app_name: str | None = None,
    ) -> list:
        """
        Parse and filter app information with validation.

        Args:
            app_types: List of app types to process (None for all types)
            app_name: Specific app name (None for all apps)

        Returns:
            Filtered list of apps
        """
        if not self.app_group:
            logger.error("Configuration not loaded")
            raise click.Abort()

        parsed_apps = []

        for app_info in self.app_info_list:
            try:
                # Validate specs for the app type
                if self.validate_on_load:
                    app_info.get_validated_specs()

                # Type filtering
                if app_types and app_info.type not in app_types:
                    if app_name and app_info.name == app_name:
                        logger.warning(
                            f"App '{app_info.name}' (type: {app_info.type}): "
                            f"Type not supported by this command",
                        )
                    continue

                # Name filtering
                if app_name and app_info.name != app_name:
                    continue

                parsed_apps.append(app_info)

            except ConfigValidationError as e:
                logger.error(f"Validation error for app '{app_info.name}': {e}")
                self.validation_errors.append(f"{app_info.name}: {e}")
                continue
            except Exception as e:
                logger.error(f"Error processing app '{app_info.name}': {e}")
                logger.debug(f"App config: {app_info.model_dump()}")
                continue

        # Check if specific app was not found
        if app_name and not parsed_apps:
            logger.error(f"Specified app '{app_name}' not found")
            raise click.Abort()

        # Raise validation errors if any
        if self.validation_errors and self.validate_on_load:
            raise ConfigValidationError(
                f"Found {len(self.validation_errors)} validation errors",
            )

        self.app_info_list = parsed_apps
        return parsed_apps

    def get_namespace(self, app_info) -> str | None:
        """
        Determine namespace for the app.
        Priority: CLI > App config > Global config
        """
        if self.cli_namespace:
            return self.cli_namespace

        if app_info.namespace and app_info.namespace not in [
            "!ignore",
            "!none",
            "!false",
            "",
        ]:
            return app_info.namespace

        if self.app_group and self.app_group.namespace:
            return self.app_group.namespace

        return None

    def ensure_directory(self, path: Path, description: str = "directory"):
        """Ensure directory exists, create if necessary."""
        try:
            path.mkdir(parents=True, exist_ok=True)
            logger.verbose(f"{description} ready: {path}")
        except OSError as e:
            logger.error(f"Failed to create {description}: {e}")
            raise click.Abort()

    def clean_directory(self, path: Path, description: str = "directory"):
        """Clean directory (remove and recreate)."""
        import shutil

        try:
            if path.exists():
                shutil.rmtree(path)
                logger.verbose(f"Removed existing {description}: {path}")
            path.mkdir(parents=True, exist_ok=True)
            logger.verbose(f"{description} ready: {path}")
        except OSError as e:
            logger.error(f"Failed to clean/create {description}: {e}")
            raise click.Abort()

    def create_app_spec(self, app_info):
        """Create spec object for app type with validation."""
        try:
            return app_info.get_validated_specs()
        except Exception as e:
            logger.error(f"Failed to create spec for app '{app_info.name}': {e}")
            raise

    def execute_command_with_logging(
        self,
        cmd: list,
        error_msg: str,
        success_msg: str = None,
        timeout: int = 300,
    ):
        """Execute command with logging (using common function)."""
        from sbkube.utils.common import execute_command_with_logging

        return execute_command_with_logging(
            cmd,
            error_msg,
            success_msg,
            self.base_dir,
            timeout,
        )

    def check_required_cli_tools(self):
        """Check required CLI tools for app list (using common function)."""
        from sbkube.utils.common import check_required_cli_tools

        return check_required_cli_tools(self.app_info_list)

    def process_apps_with_stats(self, process_func, operation_name: str = "processing"):
        """
        Process app list and output statistics.

        Args:
            process_func: Function to process each app (takes app_info, returns bool)
            operation_name: Operation name for logging
        """
        if not self.app_info_list:
            logger.warning(f"No apps to {operation_name} in config file")
            logger.heading(f"{operation_name} completed (no apps to process)")
            return

        total_apps = len(self.app_info_list)
        success_apps = 0
        failed_apps = []

        for app_info in self.app_info_list:
            try:
                if process_func(app_info):
                    success_apps += 1
                else:
                    failed_apps.append(app_info.name)
            except Exception as e:
                logger.error(
                    f"Unexpected error {operation_name} app '{app_info.name}': {e}",
                )
                failed_apps.append(app_info.name)
                if logger._level.value <= LogLevel.DEBUG.value:
                    import traceback

                    logger.debug(traceback.format_exc())

        # Output results
        if total_apps > 0:
            logger.success(
                f"{operation_name} summary: "
                f"{success_apps} of {total_apps} apps succeeded",
            )

            if failed_apps:
                logger.warning(f"Failed apps: {', '.join(failed_apps)}")

        logger.heading(f"{operation_name} completed")

    def export_validated_config(
        self,
        output_path: str | Path,
        format: str = "yaml",
    ):
        """
        Export validated configuration to file.

        Args:
            output_path: Output file path
            format: Output format (yaml or json)
        """
        if not self.app_group:
            logger.error("No configuration loaded to export")
            raise click.Abort()

        try:
            self.config_manager.export_merged_config(
                self.app_group,
                output_path,
                format,
            )
            logger.success(f"Exported validated config to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to export config: {e}")
            raise click.Abort()

    def execute_command_hook(
        self,
        hook_phase: str,  # "pre" or "post" or "on_failure"
        command_name: str,  # "prepare", "deploy" 등
        dry_run: bool = False,
    ) -> bool:
        """
        명령어 수준 전역 훅 실행.

        Args:
            hook_phase: "pre", "post", "on_failure"
            command_name: 명령어 이름
            dry_run: dry-run 모드

        Returns:
            성공 여부
        """
        if not self.app_group or not self.app_group.hooks:
            return True

        command_hooks = self.app_group.hooks.get(command_name)
        if not command_hooks:
            return True

        # Hook executor 초기화
        self._init_hook_executor(dry_run=dry_run)

        # CommandHooks 객체를 dict로 변환
        hook_config = command_hooks.model_dump()

        return self.hook_executor.execute_command_hooks(
            hook_config=hook_config,
            hook_phase=hook_phase,
            command_name=command_name,
        )

    def execute_app_hook(
        self,
        app_info,
        hook_type: str,  # "pre_deploy", "post_deploy" 등
        context: dict | None = None,
        dry_run: bool = False,
    ) -> bool:
        """
        앱별 훅 실행.

        Args:
            app_info: 앱 정보 객체 (AppConfig)
            hook_type: "pre_deploy", "post_deploy" 등
            context: 추가 컨텍스트 (namespace, release_name 등)
            dry_run: dry-run 모드

        Returns:
            성공 여부
        """
        if not hasattr(app_info, "hooks") or not app_info.hooks:
            return True

        # Hook executor 초기화
        self._init_hook_executor(dry_run=dry_run)

        # AppHooks 객체를 dict로 변환
        app_hooks = app_info.hooks.model_dump()

        # app_info에서 이름 추출 (dict인 경우 대비)
        app_name = getattr(app_info, "name", str(app_info))

        return self.hook_executor.execute_app_hook(
            app_name=app_name,
            app_hooks=app_hooks,
            hook_type=hook_type,
            context=context,
        )


# Backward compatibility alias
BaseCommand = EnhancedBaseCommand
