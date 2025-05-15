import yaml
import jsonschema
from pathlib import Path

def validate_config_yaml(group_name: str):
    config_path = Path(__file__).parent / group_name / "config.yaml"
    schema_path = Path(__file__).parent / "../schemas/config.schema.json"

    config = yaml.safe_load(open(config_path))
    schema = yaml.safe_load(open(schema_path))

    jsonschema.validate(instance=config, schema=schema)
    print("✅ config.yaml is valid")

# 실행 예시
validate_config_yaml("a000_infra")
