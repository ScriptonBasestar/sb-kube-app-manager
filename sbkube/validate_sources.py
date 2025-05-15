import yaml
import jsonschema
from pathlib import Path

from sbkube.source_model import SourceScheme

def validate_sources_yaml():
    yaml_path = Path(__file__).parent / "sources.yaml"
    schema_path = Path(__file__).parent / "../schemas/sources.schema.json"

    data = yaml.safe_load(open(yaml_path))
    schema = yaml.safe_load(open(schema_path))

    jsonschema.validate(instance=data, schema=schema)
    print("✅ sources.yaml 유효성 검사 통과")

if __name__ == '__main__':
    validate_sources_yaml()
