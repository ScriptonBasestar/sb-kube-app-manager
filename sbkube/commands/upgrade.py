import subprocess
import json
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit

console = Console()

def get_installed_charts(namespace: str) -> dict:
    cmd = ["helm", "list", "-o", "json", "-n", namespace]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return {item["name"]: item for item in json.loads(result.stdout)}

@click.command(name="upgrade")
@click.option("--apps", default="config", help="앱 구성 설정 파일 (확장자 생략 가능)")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
@click.option("--namespace", default=None, help="기본 네임스페이스 (없으면 앱별로 따름)")
@click.option("--dry-run", is_flag=True, default=False, help="dry-run 모드로 실행")
def cmd(apps, base_dir, namespace, dry_run):
    """설치된 Helm 릴리스를 업그레이드"""
    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    BUILD_DIR = BASE_DIR / "build"
    VALUES_DIR = BASE_DIR / "values"

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
        if app.get("type") != "install-helm":
            continue

        name = app["name"]
        release = app.get("release", name)
        ns = namespace or app.get("namespace") or apps_config.get("namespace") or "default"

        chart_dir = BUILD_DIR / name
        if not chart_dir.exists():
            console.print(f"[red]❌ chart 디렉토리 없음: {chart_dir}[/red]")
            raise click.Abort()

        installed = release in get_installed_charts(ns)
        if not installed:
            console.print(f"[yellow]⚠️ 설치되지 않음: {release} → upgrade 스킵[/yellow]")
            continue

        helm_cmd = ["helm", "upgrade", release, str(chart_dir), "--namespace", ns]

        for vf in app["specs"].get("values", []):
            vf_path = Path(vf) if Path(vf).is_absolute() else VALUES_DIR / vf
            if vf_path.exists():
                helm_cmd += ["--values", str(vf_path)]
                console.print(f"[green]✅ values: {vf_path}[/green]")
            else:
                console.print(f"[yellow]⚠️ values 파일 없음: {vf_path}[/yellow]")

        if dry_run:
            helm_cmd.append("--dry-run=client")

        console.print(f"[cyan]⬆️ helm upgrade: {' '.join(helm_cmd)}[/cyan]")
        result = subprocess.run(helm_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            console.print("[red]❌ upgrade 실패:[/red]")
            console.print(result.stderr)
            console.print("[blue]STDOUT:[/blue]")
            console.print(result.stdout)
        else:
            console.print(f"[bold green]✅ {release} 업그레이드 완료 (namespace: {ns})[/bold green]")