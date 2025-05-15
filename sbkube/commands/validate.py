import json
import yaml
import click
from pathlib import Path
from jsonschema import validate as jsonschema_validate, ValidationError


def load_yaml(file_path: Path):
    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_schema(schema_path: Path):
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


@click.command(name="validate")
@click.argument("target", type=str)
@click.option("--type", "type_", type=click.Choice(["schema", "sources"], case_sensitive=False), help="Force schema type (schema or sources)")
@click.option("--base-dir", type=click.Path(exists=True), default=".", help="Base directory for resolving paths")
@click.option("--schema", type=click.Path(exists=True), help="Override schema path")
def cmd(target, type_, base_dir, schema):
    """
    Validate a sources.yaml or config.yaml against JSON Schema.
    """
    base_path = Path(base_dir).expanduser().resolve()
    yaml_path = (base_path / target).expanduser().resolve()

    if not yaml_path.exists():
        click.echo(f"❌ YAML 파일을 찾을 수 없습니다: {yaml_path}")
        raise click.Abort()

    if schema:
        schema_path = Path(schema).expanduser().resolve()
    elif type_ == "sources" or yaml_path.name == "sources.yaml":
        schema_path = base_path / "schemas" / "sources.schema.json"
    elif type_ == "schema" or yaml_path.name == "config.yaml":
        schema_path = base_path / "schemas" / "config.schema.json"
    else:
        click.echo("❌ 자동으로 schema를 유추할 수 없습니다. --type 또는 --schema 옵션을 사용하세요.")
        raise click.Abort()

    if not schema_path.exists():
        click.echo(f"❌ 스키마 파일을 찾을 수 없습니다: {schema_path}")
        raise click.Abort()

    try:
        data = load_yaml(yaml_path)
    except Exception as e:
        click.echo(f"❌ YAML 로딩 실패: {yaml_path}\n    원인: {e}")
        raise click.Abort()

    try:
        schema_data = load_schema(schema_path)
    except Exception as e:
        click.echo(f"❌ 스키마 로딩 실패: {schema_path}\n    원인: {e}")
        raise click.Abort()

    try:
        jsonschema_validate(instance=data, schema=schema_data)
        click.echo(f"✅ Validation passed: {yaml_path.name}")
    except ValidationError as e:
        click.echo(f"❌ Validation failed: {e.message}")
        click.echo(f"🔍 위치: {' -> '.join(str(p) for p in e.path)}")
        raise click.Abort()