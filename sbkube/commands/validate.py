import json
from pathlib import Path

import click
from jsonschema import ValidationError
from jsonschema import validate as jsonschema_validate
from pydantic import ValidationError as PydanticValidationError

from sbkube.models.config_model import SBKubeConfig
from sbkube.models.sources_model import SourceScheme
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
    """Validate 명령 구현"""

    def __init__(
        self,
        target_file: str,
        schema_type: str | None,
        base_dir: str,
        custom_schema_path: str | None,
    ):
        self.base_dir = Path(base_dir)
        self.target_file = target_file
        self.schema_type = schema_type
        self.custom_schema_path = custom_schema_path

    def validate_dependencies(self, config: SBKubeConfig) -> bool:
        """
        Validate app-group dependencies declared in config.deps.

        Args:
            config: Validated SBKubeConfig instance

        Returns:
            bool: True if all dependencies are deployed, False otherwise
        """
        if not config.deps:
            logger.info("앱 그룹 의존성 없음 (config.deps) - 검증 건너뜀")
            return True

        logger.heading("앱 그룹 의존성 검증")

        from sbkube.utils.deployment_checker import DeploymentChecker

        # Get target file's parent directory as base
        target_path = Path(self.target_file)
        app_dir = target_path.parent
        parent_dir = app_dir.parent if app_dir.name != "." else Path.cwd()

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
        else:
            logger.error(f"❌ {len(result['missing'])}개 의존성이 배포되지 않음:")
            for dep in result["missing"]:
                _, msg = result["details"][dep]
                logger.error(f"  ✗ {dep}: {msg}")

            logger.warning("배포가 실패할 수 있습니다. 의존성을 먼저 배포하세요:")
            for dep in result["missing"]:
                logger.info(f"  sbkube deploy --app-dir {dep}")

            return False

    def execute(self):
        """validate 명령 실행"""
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
                raise click.Abort()
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
            raise click.Abort()

        # JSON 스키마 검증 (있을 경우만)
        if schema_path:
            try:
                logger.info(f"JSON 스키마 로드 중: {schema_path}")
                schema_def = load_json_schema(schema_path)
                logger.success("JSON 스키마 로드 성공")
            except Exception:
                raise click.Abort()

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
                raise click.Abort()
            except Exception as e:
                logger.error(f"JSON 스키마 검증 중 오류: {e}")
                raise click.Abort()

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
                raise click.Abort()

            # Validate app-group dependencies (deps field)
            deps_valid = self.validate_dependencies(config)
            if not deps_valid:
                logger.warning(
                    "의존성 검증 실패 (논-블로킹) - 배포 시 실패할 수 있음"
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
                raise click.Abort()
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
    help="앱 설정 디렉토리 (config.yaml 자동 검색)",
)
@click.option(
    "--config-file",
    "config_file_name",
    default="config.yaml",
    help="설정 파일 이름 (app-dir 내부, 기본값: config.yaml)",
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
    help="프로젝트 루트 디렉토리 (스키마 파일 상대 경로 해석 기준)",
)
@click.option(
    "--schema-path",
    "custom_schema_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="사용자 정의 JSON 스키마 파일 경로 (지정 시 schema-type 무시)",
)
@click.option("-v", "--verbose", is_flag=True, help="상세 로그 출력 (추가 기능용)")
@click.option("--debug", is_flag=True, help="디버그 로그 출력 (추가 기능용)")
@click.pass_context
def cmd(
    ctx,
    target_file: str | None,
    app_config_dir_name: str | None,
    config_file_name: str,
    schema_type: str | None,
    base_dir: str,
    custom_schema_path: str | None,
    verbose: bool,
    debug: bool,
):
    """
    config.yaml/toml 또는 sources.yaml/toml 파일을 JSON 스키마 및 데이터 모델로 검증합니다.

    Examples:

        # Explicit file path (backward compatible)
        sbkube validate /path/to/config.yaml

        # Using --app-dir
        sbkube validate --app-dir redis

        # Custom config file name
        sbkube validate --app-dir redis --config-file custom.yaml

        # Current directory (default)
        sbkube validate
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)

    # Resolve base directory
    BASE_DIR = Path(base_dir).resolve()

    # Resolve target file path
    if target_file:
        # Case 1: Explicit file path provided (backward compatible)
        target_path = Path(target_file)
        logger.info(f"Using explicit file path: {target_path}")

    elif app_config_dir_name:
        # Case 2: --app-dir specified
        app_dir = BASE_DIR / app_config_dir_name

        # Validate app directory exists
        if not app_dir.exists() or not app_dir.is_dir():
            logger.error(f"App directory not found: {app_dir}")
            logger.info("💡 Check directory path or use explicit file path")
            raise click.Abort()

        # Construct config file path
        target_path = app_dir / config_file_name
        logger.info(f"Using app directory: {app_dir}")
        logger.info(f"Config file: {config_file_name}")

        # Validate config file exists
        if not target_path.exists():
            logger.error(f"Config file not found: {target_path}")
            logger.info("💡 Use --config-file to specify different name")
            raise click.Abort()

    else:
        # Case 3: Current directory fallback
        target_path = BASE_DIR / config_file_name
        logger.info(f"Using current directory: {BASE_DIR}")

        # Validate file exists
        if not target_path.exists():
            logger.error(f"Config file not found: {target_path}")
            logger.info("💡 Solutions:")
            logger.info("   1. Provide explicit path: sbkube validate path/to/config.yaml")
            logger.info("   2. Use --app-dir: sbkube validate --app-dir <directory>")
            logger.info("   3. Ensure config.yaml exists in current directory")
            raise click.Abort()

    # Execute validation (existing logic)
    validate_cmd = ValidateCommand(
        target_file=str(target_path),
        schema_type=schema_type,
        base_dir=str(BASE_DIR),
        custom_schema_path=custom_schema_path,
    )
    validate_cmd.execute()
