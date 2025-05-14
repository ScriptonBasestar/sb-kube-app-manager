import os
import subprocess
import shutil
import json
import click
import yaml
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit

console = Console()

BASE_DIR = os.getcwd()
CHARTS_DIR = os.path.join(BASE_DIR, "charts")
REPOS_DIR = os.path.join(BASE_DIR, "repos")


@click.command(name="prepare")  # ⬅️ 명시적으로 커맨드 이름 지정
@click.option("--apps", default="config.yaml", help="앱 설정 파일")
@click.option("--sources", default="sources.yaml", help="소스 설정 파일")
def cmd(apps, sources):
    """Helm, Git, HTTP 소스 다운로드 및 준비"""
    check_helm_installed_or_exit()
    console.print(f"[green]prepare 실행됨! apps: {apps}, sources: {sources}[/green]")

    apps_config = load_config_file(apps)
    sources_config = load_config_file(sources)

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

    # 현재 helm repo 목록 가져오기
    result = subprocess.run(["helm", "repo", "list", "-o", "json"], capture_output=True, check=True, text=True)
    local_helm_repos = {entry["name"]: entry["url"] for entry in json.loads(result.stdout)}

    # 필요한 helm repo 추가
    for repo_name in pull_helm_repo_names:
        if repo_name in helm_repos:
            repo_url = helm_repos[repo_name]
            if repo_name not in local_helm_repos:
                console.print(f"[yellow]➕ helm repo add: {repo_name}[/yellow]")
                subprocess.run(["helm", "repo", "add", repo_name, repo_url], check=True)
            subprocess.run(["helm", "repo", "update", repo_name], check=True)
        else:
            console.print(f"[red]❌ {repo_name} is not found in sources.yaml[/red]")

    # git repos 처리
    os.makedirs(REPOS_DIR, exist_ok=True)
    for repo_name in pull_git_repo_names:
        if repo_name in git_repos:
            repo = git_repos[repo_name]
            repo_path = os.path.join(REPOS_DIR, repo_name)
            if os.path.exists(repo_path):
                subprocess.run(["git", "-C", repo_path, "reset", "--hard", "HEAD"], check=True)
                subprocess.run(["git", "-C", repo_path, "clean", "-dfx"], check=True)
                if repo.get("branch"):
                    subprocess.run(["git", "-C", repo_path, "checkout", repo["branch"]], check=True)
                subprocess.run(["git", "-C", repo_path, "pull"], check=True)
            else:
                subprocess.run(["git", "clone", repo["url"], repo_path], check=True)
        else:
            console.print(f"[red]❌ {repo_name} not in git_repos[/red]")

    # helm chart pull
    os.makedirs(CHARTS_DIR, exist_ok=True)
    for app in app_list:
        if app["type"] == "pull-helm":
            repo = app["specs"]["repo"]
            chart = app["specs"]["chart"]
            chart_ver = app["specs"].get("chart_version")
            chart_dest = os.path.join(CHARTS_DIR, repo)
            shutil.rmtree(os.path.join(chart_dest, chart), ignore_errors=True)

            cmd = ["helm", "pull", f"{repo}/{chart}", "-d", chart_dest, "--untar"]
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

            chart_dest = os.path.join(CHARTS_DIR, repo)
            shutil.rmtree(chart_dest, ignore_errors=True)
            cmd = ["helm", "pull", repo_url, "-d", chart_dest, "--untar"]
            if chart_ver:
                cmd += ["--version", chart_ver]
            console.print(f"[cyan]📥 helm OCI pull: {cmd}[/cyan]")
            subprocess.run(cmd, check=True)

    console.print(f"[bold green]✅ prepare 완료[/bold green]")
