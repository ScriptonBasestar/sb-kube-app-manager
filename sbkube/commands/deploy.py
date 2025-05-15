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

@click.command(name="deploy")
@click.option("--apps", default="config", help="앱 구성 설정 파일 (확장자 생략 가능)")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
@click.option("--namespace", default=None, help="설치할 기본 네임스페이스 (없으면 앱별로 따름)")
@click.option("--dry-run", is_flag=True, default=False, help="실제로 적용하지 않고 dry-run")
def cmd(apps, base_dir, namespace, dry_run):
    """Helm chart 및 YAML, exec 명령을 클러스터에 적용"""
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
        app_type = app.get("type")
        name = app.get("name")
        ns = namespace or app.get("namespace") or apps_config.get("namespace")

        if not ns:
            console.print(f"[red]❌ namespace가 지정되지 않았습니다. 앱: {name}[/red]")
            raise click.Abort()

        if app_type == "install-helm":
            release = app.get("release", name)
            values_files = app["specs"].get("values", [])
            chart_dir = BUILD_DIR / name

            if not chart_dir.exists():
                console.print(f"[red]❌ chart 디렉토리 없음: {chart_dir}[/red]")
                console.print(f"[bold yellow]⚠️ build 명령을 먼저 실행해야 합니다.[/bold yellow]")
                raise click.Abort()

            installed = release in get_installed_charts(ns)

            if installed:
                console.print(f"[yellow]⚠️ 이미 설치됨: {release} (namespace: {ns}) → 건너뜀[/yellow]")
                continue

            helm_cmd = ["helm", "install", release, str(chart_dir), "--create-namespace", "--namespace", ns]

            for vf in values_files:
                vf_path = Path(vf) if Path(vf).is_absolute() else VALUES_DIR / vf
                if vf_path.exists():
                    helm_cmd += ["--values", str(vf_path)]
                    console.print(f"[green]✅ values: {vf_path}[/green]")
                else:
                    console.print(f"[yellow]⚠️ values 파일 없음: {vf_path}[/yellow]")

            if dry_run:
                helm_cmd.append("--dry-run=client")

            console.print(f"[cyan]🚀 helm install: {' '.join(helm_cmd)}[/cyan]")
            result = subprocess.run(helm_cmd, capture_output=True, text=True)

            if result.returncode != 0:
                console.print("[red]❌ helm 작업 실패:[/red]")
                console.print(result.stderr)
                console.print("[blue]STDOUT:[/blue]")
                console.print(result.stdout)
            else:
                console.print(f"[bold green]✅ {release} 배포 완료 (namespace: {ns})[/bold green]")

        elif app_type == "install-yaml":
            yaml_files = app["specs"].get("files", [])
            for yfile in yaml_files:
                yaml_path = str(Path(yfile))
                cmd = ["kubectl", "apply", "-f", yaml_path, "-n", ns]
                if dry_run:
                    cmd.append("--dry-run=client")
                console.print(f"[cyan]📄 kubectl apply: {' '.join(cmd)}[/cyan]")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"[red]❌ YAML 적용 실패: {result.stderr}[/red]")
                else:
                    console.print(f"[green]✅ YAML 적용 완료: {yaml_path}[/green]")

        elif app_type == "exec":
            exec_cmds = app["specs"].get("commands", [])
            for raw in exec_cmds:
                cmd = raw.split(" ")
                console.print(f"[cyan]💻 exec: {' '.join(cmd)}[/cyan]")
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    console.print(f"[red]❌ 실행 실패: {result.stderr}[/red]")
                else:
                    console.print(f"[green]✅ 실행 완료[/green]")
