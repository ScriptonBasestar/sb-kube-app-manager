import subprocess
import json
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit


def get_installed_charts(namespace: str) -> dict:
    cmd = ["helm", "list", "-o", "json", "-n", namespace]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return {item["name"]: item for item in json.loads(result.stdout)}
