import json
from pathlib import Path

import click
from jsonschema import ValidationError
from jsonschema import validate as jsonschema_validate
from pydantic import ValidationError as PydanticValidationError

from sbkube.models.config_model import SBKubeConfig
from sbkube.models.sources_model import SourceScheme
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.logger import logger, setup_logging_from_context


def load_json_schema(path: Path):
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


class ValidateCommand(BaseCommand):
    """Validate 명령 구현"""

    def __init__(
        self,
        target_file: str,
        schema_type: str | None,
        base_dir: str,
        custom_schema_path: str | None,
    ):
        super().__init__(base_dir, ".", None, None)
        self.target_file = target_file
        self.schema_type = schema_type
        self.custom_schema_path = custom_schema_path

    def execute(self):
        """validate 명령 실행"""
        self.execute_pre_hook()

        logger.heading(f"Validate 시작 - 파일: {self.target_file}")
        target_path = Path(self.target_file)
        filename = target_path.name
        logger.info(f"'{filename}' 파일 유효성 검사 시작")
        base_path = Path(self.base_dir)
        # 스키마 경로 결정
        if self.custom_schema_path:
            schema_path = Path(self.custom_schema_path)
            logger.info(f"사용자 정의 스키마 사용: {schema_path}")
        else:
            schema_type = self.schema_type
            if not schema_type:
                if filename.startswith("config."):
                    schema_type = "config"
                elif filename.startswith("sources."):
                    schema_type = "sources"
                else:
                    logger.error(
                        f"스키마 타입을 파일명({filename})으로 유추할 수 없습니다. --schema-type 옵션을 사용하세요.",
                    )
                    raise click.Abort()
            schema_path = base_path / "schemas" / f"{schema_type}.schema.json"
            logger.info(f"자동 결정된 스키마 사용 ({schema_type}): {schema_path}")
        if not schema_path.exists():
            logger.error(f"JSON 스키마 파일을 찾을 수 없습니다: {schema_path}")
            logger.error(
                "`sbkube init`을 실행하여 기본 스키마 파일을 생성하거나, 올바른 --base-dir 또는 --schema-path를 지정하세요.",
            )
            raise click.Abort()
        # 설정 파일 로드
        try:
            logger.info(f"설정 파일 로드 중: {target_path}")
            data = load_config_file(str(target_path))
            logger.success("설정 파일 로드 성공")
        except Exception as e:
            logger.error(f"설정 파일 ({target_path}) 로딩 실패: {e}")
            raise click.Abort()
        # JSON 스키마 로드
        try:
            logger.info(f"JSON 스키마 로드 중: {schema_path}")
            schema_def = load_json_schema(schema_path)
            logger.success("JSON 스키마 로드 성공")
        except Exception:
            raise click.Abort()
        # JSON 스키마 검사
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
                logger.error(f"Schema Path: {'.'.join(str(p) for p in e.schema_path)}")
            raise click.Abort()
        except Exception as e:
            logger.error(f"JSON 스키마 검증 중 오류: {e}")
            raise click.Abort()
        # 데이터 모델 검증 (Pydantic 모델 사용)
        if schema_path.name == "config.schema.json":
            try:
                logger.info("Pydantic 모델 검증 중 (SBKubeConfig)...")
                config = SBKubeConfig(**data)
                logger.success(f"데이터 모델 유효성 검사 통과 (앱 {len(config.apps)}개)")
            except PydanticValidationError as e:
                logger.error("Pydantic 모델 검증 실패:")
                for error in e.errors():
                    loc = " -> ".join(str(x) for x in error["loc"])
                    logger.error(f"  - {loc}: {error['msg']}")
                raise click.Abort()
        elif schema_path.name == "sources.schema.json":
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
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
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
    target_file: str,
    schema_type: str | None,
    base_dir: str,
    custom_schema_path: str | None,
    verbose: bool,
    debug: bool,
):
    """
    config.yaml/toml 또는 sources.yaml/toml 파일을 JSON 스키마 및 데이터 모델로 검증합니다.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging_from_context(ctx)
    validate_cmd = ValidateCommand(
        target_file=target_file,
        schema_type=schema_type,
        base_dir=base_dir,
        custom_schema_path=custom_schema_path,
    )
    validate_cmd.execute()
