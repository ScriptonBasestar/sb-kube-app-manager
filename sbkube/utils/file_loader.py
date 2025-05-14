import os
import yaml
import toml
from rich.console import Console

console = Console()


def load_config_file(basename: str):
    """
    basename: 확장자 없는 파일명 (예: 'config')
    확장자가 없으면 .yaml → .yml → .toml 순서로 탐색
    """
    candidates = [
        f"{basename}.yaml" if not basename.endswith(".yaml") else basename,
        f"{basename}.yml" if not basename.endswith(".yml") else basename,
        f"{basename}.toml" if not basename.endswith(".toml") else basename,
    ]

    seen = set()
    for candidate in candidates:
        path = os.path.abspath(candidate)
        if path in seen:
            continue
        seen.add(path)

        if os.path.exists(path):
            ext = os.path.splitext(candidate)[1]
            with open(path, "r", encoding="utf-8") as f:
                if ext in [".yaml", ".yml"]:
                    return yaml.safe_load(f)
                elif ext == ".toml":
                    return toml.load(f)
    console.print(f"[red]❌ 설정 파일을 찾을 수 없습니다: {basename}.yaml|.yml|.toml[/red]")
    raise FileNotFoundError(f"Missing config file for base name: {basename}")
