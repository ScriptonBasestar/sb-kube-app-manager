import json
import subprocess


def get_installed_charts(namespace: str) -> dict:
    cmd = ["helm", "list", "-o", "json", "-n", namespace]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return {item["name"]: item for item in json.loads(result.stdout)}
