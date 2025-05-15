import subprocess
import shutil
import json
import click
import yaml
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit

console = Console()

@click.command(name="prepare")
@click.option("--apps", default="config.yaml", help="앱 설정 파일")
@click.option("--sources", default="sources.yaml", help="소스 설정 파일")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리")
def cmd(apps, sources, base_dir):
    """Helm, Git, HTTP 소스 다운로드 및 준비"""
    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    CHARTS_DIR = BASE_DIR / "charts"
    REPOS_DIR = BASE_DIR / "repos"

    console.print(f"[green]prepare 실행됨! apps: {apps}, sources: {sources}[/green]")

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
    sources_base = BASE_DIR / sources
    if sources_base.suffix:
        sources_path = sources_base
    else:
        for ext in [".yaml", ".yml", ".toml"]:
            candidate = sources_base.with_suffix(ext)
            if candidate.exists():
                sources_path = candidate
                break
        else:
            console.print(f"[red]❌ 소스 설정 파일이 존재하지 않습니다: {sources_base}.[yaml|yml|toml][/red]")
            raise click.Abort()
    sources_path = sources_path.resolve()

    if not apps_path.exists():
        console.print(f"[red]❌ 앱 설정 파일이 존재하지 않습니다: {apps_path}[/red]")
        raise click.Abort()
    if not sources_path.exists():
        console.print(f"[red]❌ 소스 설정 파일이 존재하지 않습니다: {sources_path}[/red]")
        raise click.Abort()

    apps_config = load_config_file(str(apps_path))
    sources_config = load_config_file(str(sources_path))

    helm_repos = sources_config.get("helm_repos", {})
    oci_repos = sources_config.get("oci_repos", {})
    git_repos = sources_config.get("git_repos", {})

    app_list = apps_config.get("apps", [])

    pull_helm_repo_names = set()
    pull_git_repo_names = set()

    for app in app_list:
        if app["type"] == "pull-helm":
            pull_helm_repo_names.add(app["specs"]["repo"])
        elif app["type"] == "pull-git":
            pull_git_repo_names.add(app["specs"]["repo"])

    result = subprocess.run(["helm", "repo", "list", "-o", "json"], capture_output=True, check=True, text=True)
    local_helm_repos = {entry["name"]: entry["url"] for entry in json.loads(result.stdout)}

    for repo_name in pull_helm_repo_names:
        if repo_name in helm_repos:
            repo_url = helm_repos[repo_name]
            if repo_name not in local_helm_repos:
                console.print(f"[yellow]➕ helm repo add: {repo_name}[/yellow]")
                subprocess.run(["helm", "repo", "add", repo_name, repo_url], check=True)
            subprocess.run(["helm", "repo", "update", repo_name], check=True)
        else:
            console.print(f"[red]❌ {repo_name} is not found in sources.yaml[/red]")

    REPOS_DIR.mkdir(parents=True, exist_ok=True)
    for repo_name in pull_git_repo_names:
        if repo_name in git_repos:
            repo = git_repos[repo_name]
            repo_path = REPOS_DIR / repo_name
            if repo_path.exists():
                subprocess.run(["git", "-C", str(repo_path), "reset", "--hard", "HEAD"], check=True)
                subprocess.run(["git", "-C", str(repo_path), "clean", "-dfx"], check=True)
                if repo.get("branch"):
                    subprocess.run(["git", "-C", str(repo_path), "checkout", repo["branch"]], check=True)
                subprocess.run(["git", "-C", str(repo_path), "pull"], check=True)
            else:
                subprocess.run(["git", "clone", repo["url"], str(repo_path)], check=True)
        else:
            console.print(f"[red]❌ {repo_name} not in git_repos[/red]")

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    for app in app_list:
        if app["type"] == "pull-helm":
            repo = app["specs"]["repo"]
            chart = app["specs"]["chart"]
            chart_ver = app["specs"].get("chart_version")
            chart_dest = CHARTS_DIR / repo
            shutil.rmtree(chart_dest / chart, ignore_errors=True)

            if repo not in local_helm_repos:
                if repo in helm_repos:
                    repo_url = helm_repos[repo]
                    console.print(f"[yellow]➕ helm repo (late) add: {repo}[/yellow]")
                    subprocess.run(["helm", "repo", "add", repo, repo_url], check=True)
                    subprocess.run(["helm", "repo", "update", repo], check=True)
                else:
                    console.print(f"[red]❌ helm repo '{repo}'를 sources.yaml에서 찾을 수 없습니다.[/red]")
                    continue

            cmd = ["helm", "pull", f"{repo}/{chart}", "-d", str(chart_dest), "--untar"]
            if chart_ver:
                cmd += ["--version", chart_ver]
            console.print(f"[cyan]📥 helm pull: {cmd}[/cyan]")
            subprocess.run(cmd, check=True)

        elif app["type"] == "pull-helm-oci":
            repo = app["specs"]["repo"]
            chart = app["specs"]["chart"]
            chart_ver = app["specs"].get("chart_version")
            repo_url = oci_repos.get(repo, {}).get(chart)
            if not repo_url:
                console.print(f"[red]❌ OCI chart not found: {repo}/{chart}[/red]")
                continue

            chart_dest = CHARTS_DIR / repo
            shutil.rmtree(chart_dest, ignore_errors=True)
            cmd = ["helm", "pull", repo_url, "-d", str(chart_dest), "--untar"]
            if chart_ver:
                cmd += ["--version", chart_ver]
            console.print(f"[cyan]📥 helm OCI pull: {cmd}[/cyan]")
            subprocess.run(cmd, check=True)

    console.print(f"[bold green]✅ prepare 완료[/bold green]")
