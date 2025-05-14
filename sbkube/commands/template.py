import os
import subprocess
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit

console = Console()

BASE_DIR = Path.cwd()
BUILD_DIR = BASE_DIR / "build"

@click.command(name="template")
@click.option("--apps", default="config", help="앱 구성 설정 파일 (확장자 생략 가능)")
@click.option("--output-dir", default=None, help="YAML 출력 경로 (지정 시 파일 저장)")
def cmd(apps, output_dir):
    """Helm chart를 YAML로 렌더링 (helm template)"""
    check_helm_installed_or_exit()
    apps_config = load_config_file(apps)

    for app in apps_config.get("apps", []):
        if app["type"] not in ("pull-helm", "pull-helm-oci", "install-helm"):
            continue

        name = app["name"]
        release = app.get("release", name)
        values_files = app["specs"].get("values", [])
        chart_dir = BUILD_DIR / name
        if not chart_dir.exists():
            console.print(f"[red]❌ chart 디렉토리 없음: {chart_dir}[/red]")
            continue

        cmd = ["helm", "template", release, str(chart_dir)]
        for vf in values_files:
            vf_path = Path(vf)
            if not vf_path.exists():
                vf_path = BUILD_DIR / name / vf  # 상대 경로 fallback
            if vf_path.exists():
                cmd += ["--values", str(vf_path)]
            else:
                console.print(f"[yellow]⚠️ values 파일 없음: {vf}[/yellow]")

        console.print(f"[cyan]🧾 helm template: {' '.join(cmd)}[/cyan]")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            console.print(f"[red]❌ helm template 실패: {result.stderr}[/red]")
            continue

        if output_dir:
            out_path = Path(output_dir) / f"{name}.yaml"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(result.stdout)
            console.print(f"[green]📄 저장됨: {out_path}[/green]")
        else:
            console.print(result.stdout)

    console.print("[bold green]✅ template 완료[/bold green]")
