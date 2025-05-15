import subprocess
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file

console = Console()

@click.command(name="delete")
@click.option("--apps", default="config", help="앱 구성 설정 파일 (확장자 생략 가능)")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
@click.option("--namespace", default=None, help="삭제할 기본 네임스페이스 (없으면 앱별로 따름)")
def cmd(apps, base_dir, namespace):
    """설치된 Helm 릴리스를 삭제"""
    BASE_DIR = Path(base_dir).resolve()

    apps_base = BASE_DIR / apps
    if apps_base.suffix:
        apps_path = apps_base
    else:
        for ext in [".yaml", ".yml", ".toml"]:
            candidate = apps_base.with_suffix(ext)
            if candidate.exists():
                apps_path = candidate
                break
        else:
            console.print(f"[red]❌ 앱 설정 파일이 존재하지 않습니다: {apps_base}.[yaml|yml|toml][/red]")
            raise click.Abort()
    apps_path = apps_path.resolve()

    apps_config = load_config_file(str(apps_path))

    for app in apps_config.get("apps", []):
        if app["type"] not in ("pull-helm", "pull-helm-oci", "install-helm"):
            continue

        name = app["name"]
        release = app.get("release", name)
        ns = namespace or app.get("namespace") or "default"

        helm_cmd = ["helm", "uninstall", release, "--namespace", ns]
        console.print(f"[cyan]🗑️ helm uninstall: {' '.join(helm_cmd)}[/cyan]")
        result = subprocess.run(helm_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            console.print(f"[red]❌ 삭제 실패: {result.stderr}[/red]")
        else:
            console.print(f"[bold green]✅ {release} 삭제 완료 (namespace: {ns})[/bold green]")
