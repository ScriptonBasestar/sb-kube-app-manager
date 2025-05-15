import subprocess
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit
from sbkube.utils.helm_util import get_installed_charts

console = Console()

@click.command(name="delete")
@click.option("--app-dir", default="config", help="앱 구성 디렉토리 (내부 config.yaml|yml|toml) 자동 탐색")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
@click.option("--namespace", default=None, help="삭제할 기본 네임스페이스 (없으면 앱별로 따름)")
def cmd(app_dir, base_dir, namespace):
    """설치된 Helm 릴리스를 삭제"""
    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    app_path = Path(app_dir)
    config_dir = BASE_DIR / app_path

    if not config_dir.is_dir():
        console.print(f"[red]❌ 앱 디렉토리가 존재하지 않습니다: {config_dir}[/red]")
        raise click.Abort()

    try:
        apps_config = load_config_file(str(config_dir / "config"))
    except FileNotFoundError:
        console.print(f"[red]❌ 앱 설정 파일이 존재하지 않습니다: {config_dir}/config.[yaml|yml|toml][/red]")
        raise click.Abort()

    total = 0
    deleted = 0

    for app in apps_config.get("apps", []):
        if app.get("type") != "install-helm":
            continue

        total += 1
        name = app["name"]
        release = app.get("release", name)
        ns = namespace or app.get("namespace") or apps_config.get("namespace") or "default"

        installed = release in get_installed_charts(ns)
        if not installed:
            console.print(f"[yellow]⚠️ 설치되지 않음: {release} → 삭제 생략[/yellow]")
            continue

        helm_cmd = ["helm", "uninstall", release, "--namespace", ns]
        console.print(f"[cyan]🗑️ helm uninstall: {' '.join(helm_cmd)}[/cyan]")
        result = subprocess.run(helm_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            console.print("[red]❌ 삭제 실패:[/red]")
            console.print(result.stderr)
            console.print("[blue]STDOUT:[/blue]")
            console.print(result.stdout)
        else:
            deleted += 1
            console.print(f"[bold green]✅ {release} 삭제 완료 (namespace: {ns})[/bold green]")

    console.print(f"[bold green]✅ 삭제 요약: {deleted}/{total} 개 완료[/bold green]")