import subprocess
import json
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit
from sbkube.utils.helm_util import get_installed_charts

console = Console()

@click.command(name="deploy")
@click.option("--app-dir", default="config", help="앱 구성 디렉토리 (내부 config.yaml|yml|toml) 자동 탐색")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
@click.option("--namespace", default=None, help="설치할 기본 네임스페이스 (없으면 앱별로 따름)")
@click.option("--dry-run", is_flag=True, default=False, help="실제로 적용하지 않고 dry-run")
def cmd(app_dir, base_dir, namespace, dry_run):
    """Helm chart 및 YAML, exec 명령을 클러스터에 적용"""
    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    app_path = Path(app_dir)
    BUILD_DIR = BASE_DIR / app_path / "build"
    VALUES_DIR = BASE_DIR / app_path / "values"

    config_path = None
    for ext in [".yaml", ".yml", ".toml"]:
        candidate = (BASE_DIR / app_path / f"config{ext}").resolve()
        if candidate.exists():
            config_path = candidate
            break

    if not config_path or not config_path.exists():
        console.print(f"[red]❌ 앱 설정 파일이 존재하지 않습니다: {BASE_DIR / app_path}/config.[yaml|yml|toml][/red]")
        raise click.Abort()

    apps_config = load_config_file(str(config_path))

    for app in apps_config.get("apps", []):
        app_type = app.get("type")
        name = app.get("name")
        # apps의 namespace 필드가 있으면 우선 사용, 없으면 config의 namespace 사용
        if "namespace" in app:
            ns = namespace if namespace is not None else app.get("namespace")
        else:
            ns = apps_config.get("namespace")
        ns_ignore = (ns == "!ignore" or ns == "!none" or ns == "!false" or ns == "")
        if ns_ignore:
            ns = None

        if app_type == "install-helm":
            release = app.get("release", name)
            values_files = app["specs"].get("values", [])
            chart_rel = app.get("path", name)
            chart_dir = BUILD_DIR / chart_rel

            if not chart_dir.exists():
                console.print(f"[red]❌ chart 디렉토리 없음: {chart_dir}[/red]")
                console.print(f"[bold yellow]⚠️ build 명령을 먼저 실행해야 합니다.[/bold yellow]")
                raise click.Abort()

            installed = release in get_installed_charts(ns) if ns else False

            if installed:
                console.print(f"[yellow]⚠️ 이미 설치됨: {release} (namespace: {ns}) → 건너뜀[/yellow]")
                continue

            helm_cmd = ["helm", "install", release, str(chart_dir), "--create-namespace"]
            if ns:
                helm_cmd += ["--namespace", ns]

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
                ns_msg = f" (namespace: {ns})" if ns else ""
                console.print(f"[bold green]✅ {release} 배포 완료{ns_msg}[/bold green]")

        elif app_type == "install-yaml":
            yaml_files = app["specs"].get("files", [])
            for yfile in yaml_files:
                yfile_path = Path(yfile)
                yaml_path = yfile_path if yfile_path.is_absolute() else BASE_DIR / app_path / yfile_path
                cmd = ["kubectl", "apply", "-f", str(yaml_path)]
                if ns:
                    cmd += ["-n", ns]
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
