import os
import yaml
import toml
from pathlib import Path
from sbkube.utils.logger import logger

def load_config_file(basename: str | Path):
    """
    basename: 확장자 없는 파일명 (예: 'config' 또는 Path('config'))
    확장자가 없으면 .yaml → .yml → .toml 순서로 탐색
    """
    basename_str = str(basename)

    candidates = [
        f"{basename_str}.yaml" if not basename_str.endswith(".yaml") else basename_str,
        f"{basename_str}.yml" if not basename_str.endswith(".yml") else basename_str,
        f"{basename_str}.toml" if not basename_str.endswith(".toml") else basename_str,
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

    logger.error(f"설정 파일을 찾을 수 없습니다: {basename_str}.yaml|.yml|.toml")
    raise FileNotFoundError(f"Missing config file for base name: {basename_str}")
