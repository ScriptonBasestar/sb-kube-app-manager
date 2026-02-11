import json
from pathlib import Path

import click
from jsonschema import ValidationError
from jsonschema import validate as jsonschema_validate
from pydantic import ValidationError as PydanticValidationError

from sbkube.models.config_model import SBKubeConfig
from sbkube.models.sources_model import SourceScheme
from sbkube.utils.deprecation import option_was_explicitly_set, warn_deprecated_option
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.logger import logger, setup_logging_from_context


def load_json_schema(path: Path) -> dict:
    """JSON 스키마 파일을 로드합니다."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"스키마 파일을 찾을 수 없습니다: {path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"스키마 파일 ({path})이 올바른 JSON 형식이 아닙니다: {e}")
        raise
    except Exception as e:
        logger.error(f"스키마 파일 ({path}) 로딩 중 예상치 못한 오류 발생: {e}")
        raise


class ValidateCommand:
    """Validate 명령 구현."""

    def __init__(
        self,
        target_file: str,
        schema_type: str | None,
        base_dir: str,
        custom_schema_path: str | None,
        skip_deps: bool = False,
        strict_deps: bool = False,
        skip_storage_check: bool = False,
        strict_storage_check: bool = False,
        kubeconfig: str | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.target_file = target_file
        self.schema_type = schema_type
        self.custom_schema_path = custom_schema_path
        self.skip_deps = skip_deps
        self.strict_deps = strict_deps
        self.skip_storage_check = skip_storage_check
        self.strict_storage_check = strict_storage_check
        self.kubeconfig = kubeconfig

    def validate_dependencies(self, config: SBKubeConfig) -> bool:
        """Validate app-group dependencies declared in config.deps.

        Args:
            config: Validated SBKubeConfig instance

        Returns:
            bool: True if all dependencies are deployed, False otherwise

        """
        if self.skip_deps:
            logger.warning("의존성 검증 건너뜀 (--skip-deps)")
            return True

        if not config.deps:
            logger.info("앱 그룹 의존성 없음 (config.deps) - 검증 건너뜀")
            return True

        logger.heading("앱 그룹 의존성 검증")

        from sbkube.utils.deployment_checker import DeploymentChecker

        # Get target file's parent directory as base
        target_path = Path(self.target_file)
        app_dir = target_path.parent.resolve()
        parent_dir = app_dir.parent

        logger.debug(f"Target file: {target_path}")
        logger.debug(f"App dir: {app_dir}")
        logger.debug(f"Base dir for deps: {parent_dir}")

        checker = DeploymentChecker(
            base_dir=parent_dir,
            cluster=None,  # Uses current kubectl context
            namespace=None,  # Auto-detect from deployment history
        )

        result = checker.check_dependencies(config.deps, namespace=None)

        if result["all_deployed"]:
            logger.success(f"✅ 모든 의존성 배포됨 ({len(config.deps)}개)")
            for dep, (deployed, msg) in result["details"].items():
                logger.info(f"  ✓ {dep}: {msg}")
            return True

        logger.error(f"❌ {len(result['missing'])}개 의존성이 배포되지 않음:")
        for dep in result["missing"]:
            _, msg = result["details"][dep]
            logger.error(f"  ✗ {dep}: {msg}")

        if self.strict_deps:
            logger.error("의존성 검증 실패 (--strict-deps 모드)")
            logger.warning("배포가 실패할 수 있습니다. 의존성을 먼저 배포하세요:")
            for dep in result["missing"]:
                logger.info(f"  sbkube deploy --app-dir {dep}")
            return False

        logger.warning("의존성 검증 실패 (논-블로킹) - 배포 시 실패할 수 있음")
        logger.info("배포 권장 순서:")
        for dep in result["missing"]:
            logger.info(f"  sbkube deploy --app-dir {dep}")

        return False

    def validate_storage(self, config: SBKubeConfig) -> bool:
        """Validate PV/PVC requirements for apps with no-provisioner StorageClass.

        Args:
            config: Validated SBKubeConfig instance

        Returns:
            bool: True if all required PVs exist, False otherwise

        """
        if self.skip_storage_check:
            logger.info("스토리지 검증 건너뜀 (--skip-storage-check)")
            return True

        logger.heading("스토리지 검증 (PV/PVC)")

        from sbkube.validators.storage_validators import StorageValidatorLegacy

        validator = StorageValidatorLegacy(kubeconfig=self.kubeconfig)
        result = validator.check_required_pvs(config)

        if result["all_exist"]:
            if result["existing"]:
                logger.success(
                    f"✅ 모든 필요한 PV 존재 확인 ({len(result['existing'])}개)"
                )
                for pv in result["existing"]:
                    logger.info(
                        f"  ✓ {pv['app']}: {pv['storage_class']} ({pv['size']})"
                    )
            else:
                logger.success("✅ 수동 PV가 필요한 앱이 없습니다")
            return True

        logger.error(f"❌ {len(result['missing'])}개의 PV가 없습니다:")
        for pv in result["missing"]:
            logger.error(f"  ✗ {pv['app']}: {pv['storage_class']} ({pv['size']})")

        logger.warning("\n💡 PV 생성 방법:")
        logger.info("  1. 수동 생성: kubectl apply -f pv.yaml")
        logger.info(
            "  2. Dynamic Provisioner 설치: local-path-provisioner, nfs-provisioner"
        )
        logger.info("  3. 검증 건너뛰기: sbkube validate --skip-storage-check")
        logger.info("\n📚 자세한 내용: docs/05-best-practices/storage-management.md")

        if self.strict_storage_check:
            logger.error("스토리지 검증 실패 (--strict-storage-check 모드)")
            logger.warning("배포가 실패할 수 있습니다. PV를 먼저 생성하세요")
            return False

        logger.warning(
            "스토리지 검증 실패 (논-블로킹) - 배포 시 PVC가 Pending될 수 있음"
        )
        return False

    def execute(self) -> None:
        """Validate 명령 실행."""
        logger.heading(f"Validate 시작 - 파일: {self.target_file}")
        target_path = Path(self.target_file)
        filename = target_path.name
        logger.info(f"'{filename}' 파일 유효성 검사 시작")
        base_path = self.base_dir
        # 파일 타입 결정
        if not self.schema_type:
            if filename.startswith("config."):
                file_type = "config"
            elif filename.startswith("sources."):
                file_type = "sources"
            else:
                logger.error(
                    f"파일 타입을 파일명({filename})으로 유추할 수 없습니다. --schema-type 옵션을 사용하세요.",
                )
                raise click.Abort
        else:
            file_type = self.schema_type

        # JSON 스키마 검증 (선택적)
        schema_path = None
        if self.custom_schema_path:
            schema_path = Path(self.custom_schema_path)
            logger.info(f"사용자 정의 스키마 사용: {schema_path}")
        else:
            default_schema_path = base_path / "schemas" / f"{file_type}.schema.json"
            if default_schema_path.exists():
                schema_path = default_schema_path
                logger.info(f"JSON 스키마 사용: {schema_path}")
            else:
                logger.warning(
                    "JSON 스키마 파일이 없습니다. Pydantic 모델 검증만 수행합니다."
                )
                logger.info("스키마 생성: sbkube init 또는 --schema-path 옵션 사용")
        # 설정 파일 로드
        try:
            logger.info(f"설정 파일 로드 중: {target_path}")
            data = load_config_file(str(target_path))
            logger.success("설정 파일 로드 성공")
        except Exception as e:
            logger.error(f"설정 파일 ({target_path}) 로딩 실패: {e}")
            raise click.Abort

        # JSON 스키마 검증 (있을 경우만)
        if schema_path:
            try:
                logger.info(f"JSON 스키마 로드 중: {schema_path}")
                schema_def = load_json_schema(schema_path)
                logger.success("JSON 스키마 로드 성공")
            except Exception:
                raise click.Abort

            try:
                logger.info("JSON 스키마 기반 유효성 검사 중...")
                jsonschema_validate(instance=data, schema=schema_def)
                logger.success("JSON 스키마 유효성 검사 통과")
            except ValidationError as e:
                logger.error(f"JSON 스키마 유효성 검사 실패: {e.message}")
                if e.path:
                    logger.error(f"Path: {'.'.join(str(p) for p in e.path)}")
                if e.instance:
                    logger.error(
                        f"Instance: {json.dumps(e.instance, indent=2, ensure_ascii=False)}",
                    )
                if e.schema_path:
                    logger.error(
                        f"Schema Path: {'.'.join(str(p) for p in e.schema_path)}"
                    )
                raise click.Abort
            except Exception as e:
                logger.error(f"JSON 스키마 검증 중 오류: {e}")
                raise click.Abort

        # 데이터 모델 검증 (Pydantic 모델 사용)
        if file_type == "config":
            try:
                logger.info("Pydantic 모델 검증 중 (SBKubeConfig)...")
                config = SBKubeConfig(**data)
                logger.success(
                    f"데이터 모델 유효성 검사 통과 (앱 {len(config.apps)}개)"
                )
            except PydanticValidationError as e:
                logger.error("Pydantic 모델 검증 실패:")
                for error in e.errors():
                    loc = " -> ".join(str(x) for x in error["loc"])
                    logger.error(f"  - {loc}: {error['msg']}")
                raise click.Abort

            # Validate app-group dependencies (deps field)
            deps_valid = self.validate_dependencies(config)
            if not deps_valid:
                logger.warning("의존성 검증 실패 (논-블로킹) - 배포 시 실패할 수 있음")

            # Validate storage (PV/PVC requirements)
            storage_valid = self.validate_storage(config)
            if not storage_valid:
                logger.warning(
                    "스토리지 검증 실패 (논-블로킹) - PVC가 Pending될 수 있음"
                )
        elif file_type == "sources":
            try:
                logger.info("Pydantic 모델 검증 중 (SourceScheme)...")
                _sources = SourceScheme(**data)
                logger.success("데이터 모델 유효성 검사 통과 (SourceScheme)")
            except PydanticValidationError as e:
                logger.error("Pydantic 모델 검증 실패:")
                for error in e.errors():
                    loc = " -> ".join(str(x) for x in error["loc"])
                    logger.error(f"  - {loc}: {error['msg']}")
                raise click.Abort
        logger.success(f"'{filename}' 파일 유효성 검사 완료")


@click.command(name="validate")
@click.argument(
    "target_file",
    type=click.Path(dir_okay=False, resolve_path=True),
    required=False,
    default=None,
)
@click.option(
    "--app-dir",
    "app_config_dir_name",
    default=None,
    help="[DEPRECATED: use positional TARGET] 앱 설정 디렉토리 (지정하지 않으면 모든 하위 디렉토리 자동 탐색)",
)
@click.option(
    "--config-file",
    "config_file_name",
    default="config.yaml",
    help="[DEPRECATED: use -f with sbkube.yaml] 설정 파일 이름 (app-dir 내부, 기본값: config.yaml)",
)
@click.option(
    "--source",
    "sources_file_name",
    default="sources.yaml",
    help="[DEPRECATED: use unified sbkube.yaml settings] 소스 설정 파일 (base-dir 기준)",
)
@click.option(
    "--schema-type",
    type=click.Choice(["config", "sources"], case_sensitive=False),
    help="검증할 파일의 종류 (config 또는 sources). 파일명으로 자동 유추 가능 시 생략 가능.",
)
@click.option(
    "--base-dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
    default=".",
    help="[DEPRECATED: use TARGET full path or -f] 프로젝트 루트 디렉토리 (스키마 파일 상대 경로 해석 기준)",
)
@click.option(
    "--schema-path",
    "custom_schema_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="사용자 정의 JSON 스키마 파일 경로 (지정 시 schema-type 무시)",
)
@click.option("-v", "--verbose", count=True, help="로깅 상세도 (-v: 정보, -vv: 상세)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력 (추가 기능용)")
@click.option(
    "--skip-deps",
    is_flag=True,
    help="의존성 검증 건너뛰기 (config.deps 필드 무시)",
)
@click.option(
    "--strict-deps",
    is_flag=True,
    help="의존성 검증 실패 시 오류 발생 (기본: 경고만 출력)",
)
@click.option(
    "--skip-storage-check",
    is_flag=True,
    help="스토리지(PV/PVC) 검증 건너뛰기",
)
@click.option(
    "--strict-storage-check",
    is_flag=True,
    help="스토리지 검증 실패 시 오류 발생 (기본: 경고만 출력)",
)
@click.option(
    "--kubeconfig",
    type=click.Path(exists=True),
    help="kubeconfig 파일 경로 (기본: $KUBECONFIG 또는 ~/.kube/config)",
)
@click.pass_context
def cmd(
    ctx,
    target_file: str | None,
    app_config_dir_name: str | None,
    config_file_name: str,
    sources_file_name: str,
    schema_type: str | None,
    base_dir: str,
    custom_schema_path: str | None,
    verbose: int,
    debug: bool,
    skip_deps: bool,
    strict_deps: bool,
    skip_storage_check: bool,
    strict_storage_check: bool,
    kubeconfig: str | None,
) -> None:
    """config.yaml/toml 또는 sources.yaml/toml 파일을 JSON 스키마 및 데이터 모델로 검증합니다.

    Examples:
        # Validate all app groups (auto-discovery)
        sbkube validate

        # Validate specific app group
        sbkube validate --app-dir redis

        # Skip dependency validation
        sbkube validate --skip-deps

        # Strict dependency validation (fail on missing deps)
        sbkube validate --strict-deps

        # Skip storage (PV/PVC) validation
        sbkube validate --skip-storage-check

        # Strict storage validation (fail on missing PVs)
        sbkube validate --strict-storage-check

        # Explicit file path (backward compatible)
        sbkube validate /path/to/config.yaml

        # Custom config file name
        sbkube validate --app-dir redis --config-file custom.yaml

        # With custom kubeconfig
        sbkube validate --kubeconfig ~/.kube/production-config

    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    if option_was_explicitly_set(ctx, "app_config_dir_name"):
        warn_deprecated_option("--app-dir", "positional TARGET argument")
    if option_was_explicitly_set(ctx, "base_dir"):
        warn_deprecated_option("--base-dir", "full path in TARGET or -f")
    if option_was_explicitly_set(ctx, "config_file_name"):
        warn_deprecated_option("--config-file", "-f with sbkube.yaml")
    if option_was_explicitly_set(ctx, "sources_file_name"):
        warn_deprecated_option("--source", "unified sbkube.yaml settings")

    # Validate conflicting options
    if skip_deps and strict_deps:
        logger.error("--skip-deps와 --strict-deps는 함께 사용할 수 없습니다")
        raise click.Abort

    if skip_storage_check and strict_storage_check:
        logger.error(
            "--skip-storage-check와 --strict-storage-check는 함께 사용할 수 없습니다"
        )
        raise click.Abort

    # Resolve base directory
    BASE_DIR = Path(base_dir).resolve()

    # Case 1: Explicit file path provided (backward compatible)
    if target_file:
        target_path = Path(target_file)
        logger.info(f"Using explicit file path: {target_path}")

        validate_cmd = ValidateCommand(
            target_file=str(target_path),
            schema_type=schema_type,
            base_dir=str(BASE_DIR),
            custom_schema_path=custom_schema_path,
            skip_deps=skip_deps,
            strict_deps=strict_deps,
            skip_storage_check=skip_storage_check,
            strict_storage_check=strict_storage_check,
            kubeconfig=kubeconfig,
        )
        validate_cmd.execute()
        return

    # Case 2 & 3: Auto-discovery or --app-dir specified
    from rich.console import Console

    from sbkube.utils.app_dir_resolver import resolve_app_dirs

    console = Console()
    console.print("[bold blue]✨ SBKube `validate` 시작 ✨[/bold blue]")

    # 앱 그룹 디렉토리 결정 (공통 유틸리티 사용)
    try:
        app_config_dirs = resolve_app_dirs(
            BASE_DIR, app_config_dir_name, config_file_name
        )
    except ValueError:
        raise click.Abort

    # 각 앱 그룹 검증
    overall_success = True
    failed_apps = []
    success_apps = []

    for APP_CONFIG_DIR in app_config_dirs:
        console.print(
            f"\n[bold cyan]━━━ Validating app group: {APP_CONFIG_DIR.name} ━━━[/bold cyan]"
        )

        config_file_path = APP_CONFIG_DIR / config_file_name

        # 설정 파일 존재 확인
        if not config_file_path.exists():
            console.print(f"[red]❌ Config file not found: {config_file_path}[/red]")
            failed_apps.append(APP_CONFIG_DIR.name)
            overall_success = False
            continue

        console.print(f"[cyan]📄 Validating config: {config_file_path}[/cyan]")

        # 검증 실행
        try:
            validate_cmd = ValidateCommand(
                target_file=str(config_file_path),
                schema_type=schema_type,
                base_dir=str(BASE_DIR),
                custom_schema_path=custom_schema_path,
                skip_deps=skip_deps,
                strict_deps=strict_deps,
                skip_storage_check=skip_storage_check,
                strict_storage_check=strict_storage_check,
                kubeconfig=kubeconfig,
            )
            validate_cmd.execute()
            console.print(
                f"[bold green]✅ App group '{APP_CONFIG_DIR.name}' validated successfully![/bold green]"
            )
            success_apps.append(APP_CONFIG_DIR.name)
        except click.Abort:
            console.print(
                f"[red]❌ App group '{APP_CONFIG_DIR.name}' validation failed[/red]"
            )
            failed_apps.append(APP_CONFIG_DIR.name)
            overall_success = False
        except Exception as e:
            console.print(
                f"[red]❌ App group '{APP_CONFIG_DIR.name}' validation failed: {e}[/red]"
            )
            failed_apps.append(APP_CONFIG_DIR.name)
            overall_success = False

    # 전체 결과 출력
    console.print("\n[bold]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold]")
    console.print("[bold cyan]📊 Validation Summary[/bold cyan]")
    console.print(f"  Total: {len(app_config_dirs)} app group(s)")
    console.print(f"  [green]✓ Success: {len(success_apps)}[/green]")
    console.print(f"  [red]✗ Failed: {len(failed_apps)}[/red]")

    if success_apps:
        console.print("\n[green]✅ Successfully validated:[/green]")
        for app in success_apps:
            console.print(f"  ✓ {app}")

    if failed_apps:
        console.print("\n[red]❌ Failed to validate:[/red]")
        for app in failed_apps:
            console.print(f"  ✗ {app}")

    if not overall_success:
        console.print("\n[bold red]❌ Some app groups failed validation[/bold red]")
        raise click.Abort
    console.print(
        "\n[bold green]🎉 All app groups validated successfully![/bold green]"
    )
