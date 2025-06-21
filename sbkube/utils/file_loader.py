import os
import yaml
import toml
from pathlib import Path
from typing import Any, Dict, Union
from sbkube.utils.logger import logger
from sbkube.exceptions import ConfigFileNotFoundError, FileOperationError


def resolve_path(base: Path, relative: str) -> Path:
    """
    Resolve a relative path against a base path.
    
    Args:
        base: Base path to resolve against
        relative: Relative path string
        
    Returns:
        Path: Resolved absolute or relative path
    """
    p = Path(relative)
    return p if p.is_absolute() else base / p


def load_config_file(basename: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration file with multiple format support.
    
    Args:
        basename: Base filename without extension (e.g., 'config' or Path('config'))
                 Searches for .yaml → .yml → .toml in that order
                 
    Returns:
        Dict[str, Any]: Loaded configuration data
        
    Raises:
        ConfigFileNotFoundError: When no configuration file is found
        FileOperationError: When file cannot be read or parsed
    """
    basename_str = str(basename)

    candidates = [
        f"{basename_str}.yaml" if not basename_str.endswith(".yaml") else basename_str,
        f"{basename_str}.yml" if not basename_str.endswith(".yml") else basename_str,
        f"{basename_str}.toml" if not basename_str.endswith(".toml") else basename_str,
    ]

    # Remove duplicates while preserving order
    seen = set()
    unique_candidates = []
    for candidate in candidates:
        path = os.path.abspath(candidate)
        if path not in seen:
            seen.add(path)
            unique_candidates.append(candidate)

    # Try to load each candidate file
    for candidate in unique_candidates:
        if os.path.exists(candidate):
            try:
                return _load_file_by_extension(candidate)
            except Exception as e:
                logger.error(f"Failed to parse config file '{candidate}': {e}")
                raise FileOperationError(candidate, "parse", str(e))

    logger.error(f"설정 파일을 찾을 수 없습니다: {basename_str}.yaml|.yml|.toml")
    raise ConfigFileNotFoundError(basename_str, unique_candidates)


def _load_file_by_extension(file_path: str) -> Dict[str, Any]:
    """
    Load file content based on extension.
    
    Args:
        file_path: Path to the file to load
        
    Returns:
        Dict[str, Any]: Parsed file content
        
    Raises:
        FileOperationError: When file cannot be read or parsed
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if ext in [".yaml", ".yml"]:
                content = yaml.safe_load(f)
                return content if content is not None else {}
            elif ext == ".toml":
                return toml.load(f)
            else:
                raise FileOperationError(
                    file_path, 
                    "parse", 
                    f"Unsupported file extension: {ext}"
                )
    except (OSError, IOError) as e:
        raise FileOperationError(file_path, "read", str(e))
    except yaml.YAMLError as e:
        raise FileOperationError(file_path, "parse", f"YAML parsing error: {e}")
    except toml.TomlDecodeError as e:
        raise FileOperationError(file_path, "parse", f"TOML parsing error: {e}")


def load_file_safely(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load file safely without raising exceptions.
    
    Args:
        file_path: Path to the file to load
        
    Returns:
        Dict[str, Any]: Loaded configuration data or empty dict on failure
    """
    try:
        return _load_file_by_extension(str(file_path))
    except (FileOperationError, ConfigFileNotFoundError):
        logger.warning(f"Failed to load file '{file_path}', returning empty configuration")
        return {}
