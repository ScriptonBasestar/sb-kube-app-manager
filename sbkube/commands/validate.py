import json
import click
from pathlib import Path
from jsonschema import validate as jsonschema_validate, ValidationError
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppInstallActionSpec,
    AppInstallKubectlSpec,
    AppInstallShellSpec,
    AppPullHelmSpec,
    # AppPullHelmOciSpec, # TODO: OCI Spec 모델 구현 시 추가
    AppPullGitSpec,
    AppCopySpec,
    AppExecSpec,
    AppRenderSpec,
)
from sbkube.models import get_spec_model

console = Console()

def load_json_schema(path: Path):
    """JSON 스키마 파일을 로드합니다."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        console.print(f"[red]❌ 스키마 파일을 찾을 수 없습니다: {path}[/red]")
        raise
    except json.JSONDecodeError as e:
        console.print(f"[red]❌ 스키마 파일 ({path})이 올바른 JSON 형식이 아닙니다: {e}[/red]")
        raise
    except Exception as e:
        console.print(f"[red]❌ 스키마 파일 ({path}) 로딩 중 예상치 못한 오류 발생: {e}[/red]")
        raise

@click.command(name="validate")
@click.argument("target_file", type=click.Path(exists=True, dir_okay=False, resolve_path=True))
@click.option("--schema-type", type=click.Choice(["config", "sources"], case_sensitive=False),
              help="검증할 파일의 종류 (config 또는 sources). 파일명으로 자동 유추 가능 시 생략 가능.")
@click.option("--base-dir", type=click.Path(exists=True, file_okay=False, dir_okay=True, resolve_path=True),
              default=".", help="프로젝트 루트 디렉토리 (스키마 파일 상대 경로 해석 기준)")
@click.option("--schema-path", "custom_schema_path", type=click.Path(exists=True, dir_okay=False, resolve_path=True),
              help="사용자 정의 JSON 스키마 파일 경로 (지정 시 schema-type 무시)")
def cmd(target_file: str, schema_type: str | None, base_dir: str, custom_schema_path: str | None):
    """
    config.yaml/toml 또는 sources.yaml/toml 파일을 JSON 스키마 및 데이터 모델로 검증합니다.
    """
    target_file_path = Path(target_file)
    target_filename = target_file_path.name
    console.print(f"[bold blue]✨ '{target_filename}' 파일 유효성 검사 시작 ✨[/bold blue]")

    base_path = Path(base_dir)

    schema_json_path = None
    if custom_schema_path:
        schema_json_path = Path(custom_schema_path)
        console.print(f"[cyan]ℹ️ 사용자 정의 스키마 사용: {schema_json_path}[/cyan]")
    else:
        determined_type = schema_type
        if not determined_type:
            if target_filename.startswith("config."):
                determined_type = "config"
            elif target_filename.startswith("sources."):
                determined_type = "sources"
            else:
                console.print(f"[red]❌ 스키마 타입을 파일명({target_filename})으로 유추할 수 없습니다. --schema-type 옵션을 사용하세요.[/red]")
                raise click.Abort()

        schema_file_name = f"{determined_type}.schema.json"
        schema_json_path = base_path / "schemas" / schema_file_name
        console.print(f"[cyan]ℹ️ 자동 결정된 스키마 사용 ({determined_type} 타입): {schema_json_path}[/cyan]")

    if not schema_json_path.exists():
        console.print(f"[red]❌ JSON 스키마 파일을 찾을 수 없습니다: {schema_json_path}[/red]")
        console.print(f"    [yellow]L `sbkube init`을 실행하여 기본 스키마 파일을 생성하거나, 올바른 --base-dir 또는 --schema-path를 지정하세요.[/yellow]")
        raise click.Abort()

    try:
        console.print(f"[cyan]🔄 설정 파일 로드 중: {target_file_path}[/cyan]")
        config_data_dict = load_config_file(str(target_file_path))
        console.print("[green]✅ 설정 파일 로드 성공.[/green]")
    except Exception as e:
        console.print(f"[red]❌ 설정 파일 ({target_file_path}) 로딩 실패:[/red]")
        console.print(f"    [red]L 원인: {e}[/red]")
        raise click.Abort()

    try:
        console.print(f"[cyan]🔄 JSON 스키마 로드 중: {schema_json_path}[/cyan]")
        schema_definition = load_json_schema(schema_json_path)
        console.print("[green]✅ JSON 스키마 로드 성공.[/green]")
    except Exception:
        raise click.Abort()

    try:
        console.print(f"[cyan]🔄 JSON 스키마 기반 유효성 검사 중...[/cyan]")
        jsonschema_validate(instance=config_data_dict, schema=schema_definition)
        console.print("[green]✅ JSON 스키마 유효성 검사 통과![/green]")
    except ValidationError as e:
        console.print(f"[red]❌ JSON 스키마 유효성 검사 실패:[/red]")
        console.print(f"    [red]Message: {e.message}[/red]")
        if e.path:
            console.print(f"    [red]Path: {'.'.join(str(p) for p in e.path)}[/red]")
        if e.instance:
            console.print(f"    [red]Instance: {json.dumps(e.instance, indent=2, ensure_ascii=False)}[/red]")
        if e.schema_path:
             console.print(f"    [red]Schema Path: {'.'.join(str(p) for p in e.schema_path)}[/red]")
        console.print(f"    [yellow]L 스키마 정의 ({schema_json_path}) 또는 설정 파일 ({target_file_path})을 확인하세요.[/yellow]")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red]❌ JSON 스키마 검증 중 예상치 못한 오류: {e}[/red]")
        raise click.Abort()

    if schema_json_path.name == "config.schema.json":
        console.print(f"[cyan]🔄 데이터 모델 기반 유효성 검사 중 ('apps' 목록)...[/cyan]")
        apps_list = config_data_dict.get("apps", [])
        if not isinstance(apps_list, list):
            console.print(f"[red]❌ 데이터 모델 검증 실패: 'apps' 필드는 리스트여야 합니다. 현재 타입: {type(apps_list)}[/red]")
            raise click.Abort()

        if not apps_list:
            console.print("[yellow]⚠️ 'apps' 목록이 비어있습니다. 모델 검증을 건너뜁니다.[/yellow]")
        else:
            validation_errors_found = False
            for i, app_dict in enumerate(apps_list):
                app_name_for_error = app_dict.get('name', f"인덱스 {i}의 앱")
                try:
                    app_info = AppInfoScheme(**app_dict)
                    if app_info.specs:
                        SpecModel = get_spec_model(app_info.type)
                        if SpecModel:
                            SpecModel(**app_info.specs)
                except Exception as e:
                    console.print(f"[red]❌ 앱 '{app_name_for_error}' (타입: {app_dict.get('type', '알 수 없음')}) 데이터 모델 검증 실패:[/red]")
                    console.print(f"    [red]L 오류: {e}[/red]")
                    console.print(f"    [red]L 해당 앱 데이터: {json.dumps(app_dict, indent=2, ensure_ascii=False)}[/red]")
                    validation_errors_found = True
            
            if validation_errors_found:
                console.print("[red]❌ 데이터 모델 유효성 검사에서 하나 이상의 오류가 발견되었습니다.[/red]")
                raise click.Abort()
            else:
                console.print("[green]✅ 데이터 모델 유효성 검사 통과! ('apps' 목록)[/green]")
    else:
        console.print(f"[cyan]ℹ️ '{target_filename}' 파일은 'apps' 목록에 대한 데이터 모델 검증 대상이 아닙니다. (config 스키마 아님)[/cyan]")

    console.print(f"[bold green]🎉 '{target_filename}' 파일 유효성 검사 성공적으로 완료! 🎉[/bold green]")
