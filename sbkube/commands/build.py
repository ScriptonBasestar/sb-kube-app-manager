import os
import shutil
import click
import yaml
from pathlib import Path
from rich.console import Console

console = Console()

BASE_DIR = Path.cwd()
CHARTS_DIR = BASE_DIR / "charts"
REPOS_DIR = BASE_DIR / "repos"
BUILD_DIR = BASE_DIR / "build"
OVERRIDES_DIR = BASE_DIR / "overrides"

@click.command()
@click.option("--apps", default="config.yaml", help="앱 구성 설정 파일")
def cmd(apps):
    """다운로드된 Helm/Git Chart를 기반으로 빌드 디렉토리 생성"""
    console.print(f"[bold green]🏗️ build 시작: {apps}[/bold green]")

    with open(apps, "r") as f:
        apps_config = yaml.safe_load(f)

    BUILD_DIR.mkdir(exist_ok=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    BUILD_DIR.mkdir()

    for app in apps_config.get("apps", []):
        app_type = app["type"]
        app_name = app["name"]
        specs = app.get("specs", {})

        if app_type == "pull-helm" or app_type == "pull-helm-oci":
            repo = specs["repo"]
            chart = specs["chart"]
            dest = specs.get("dest", app_name)

            src_chart_path = CHARTS_DIR / repo / chart
            dst_path = BUILD_DIR / dest

            if not src_chart_path.exists():
                console.print(f"[red]❌ {src_chart_path} 없음[/red]")
                continue

            shutil.copytree(src_chart_path, dst_path)
            console.print(f"[cyan]📁 Helm chart 복사: {src_chart_path} → {dst_path}[/cyan]")

            # overrides 처리
            for override in specs.get("overrides", []):
                override_src = OVERRIDES_DIR / dest / override
                override_dst = dst_path / override
                if override_src.exists():
                    override_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(override_src, override_dst)
                    console.print(f"[yellow]🔁 override: {override_src} → {override_dst}[/yellow]")

            # removes 처리
            for remove in specs.get("removes", []):
                target = dst_path / remove
                if target.exists():
                    if target.is_file():
                        target.unlink()
                        console.print(f"[red]🗑️ remove: {target}[/red]")

        elif app_type == "pull-git":
            repo = specs["repo"]
            paths = specs.get("paths", [])
            dst_path = BUILD_DIR / app_name
            dst_path.mkdir(parents=True, exist_ok=True)

            for c in paths:
                src = REPOS_DIR / repo / c["src"]
                dst = dst_path / c["dest"]
                shutil.copytree(src, dst)
                console.print(f"[magenta]📂 Git path 복사: {src} → {dst}[/magenta]")

        elif app_type == "copy-app":
            paths = specs.get("paths", [])
            dst_path = BUILD_DIR / app_name
            dst_path.mkdir(parents=True, exist_ok=True)

            for c in paths:
                src = Path(c["src"]).resolve()
                dst = dst_path / c["dest"]
                shutil.copytree(src, dst)
                console.print(f"[blue]📂 copy-app: {src} → {dst}[/blue]")

        else:
            console.print(f"[gray]➖ 처리 대상 아님: {app_type} ({app_name})[/gray]")

    console.print(f"[bold green]✅ build 완료: {BUILD_DIR}[/bold green]")
