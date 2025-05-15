import json
import yaml
import click
import subprocess
import shutil
from pathlib import Path
from jsonschema import validate as jsonschema_validate, ValidationError
from shutil import which
from rich.console import Console

console = Console()

def check_command_available(command):
    if which(command) is None:
        console.print(f"[yellow]⚠️ '{command}' 명령을 찾을 수 없습니다. PATH에 등록되어 있는지 확인하세요.[/yellow]")
        return
    try:
        result = subprocess.run([command, "version"], capture_output=True, text=True)
        if result.returncode != 0:
            console.print(f"[yellow]⚠️ '{command}' 실행 실패: {result.stderr.strip()}[/yellow]")
    except Exception as e:
        console.print(f"[yellow]⚠️ '{command}' 실행 오류: {e}[/yellow]")

# CLI 진입 시 사전 확인
check_command_available("helm")
check_command_available("kubectl")

@click.command(name="prepare")
@click.option("--app-dir", default=".", help="앱 설정 디렉토리 (config.yaml을 내부에서 탐색)")
@click.option("--sources", default="sources.yaml", help="소스 설정 파일")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리")
def cmd(app_dir, sources, base_dir):
    from sbkube.utils.file_loader import load_config_file
    from sbkube.utils.cli_check import check_helm_installed_or_exit

    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    CHARTS_DIR = BASE_DIR / "charts"
    REPOS_DIR = BASE_DIR / "repos"

    console.print(f"[green]prepare 실행됨! app-dir: {app_dir}, sources: {sources}[/green]")

    app_path = Path(app_dir)
    config_path = None
    for ext in [".yaml", ".yml", ".toml"]:
        candidate = (BASE_DIR / app_path / f"config{ext}").resolve()
        if candidate.exists():
            config_path = candidate
            break

    if not config_path or not config_path.exists():
        console.print(f"[red]❌ 앱 설정 파일이 존재하지 않습니다: {BASE_DIR / app_path}/config.[yaml|yml|toml][/red]")
        raise click.Abort()

    sources_path = (BASE_DIR / sources).resolve()
    if not sources_path.exists():
        console.print(f"[red]❌ 소스 설정 파일이 존재하지 않습니다: {sources_path}[/red]")
        raise click.Abort()

    apps_config = load_config_file(str(config_path))
    sources_config = load_config_file(str(sources_path))

    helm_repos = sources_config.get("helm_repos", {})
    oci_repos = sources_config.get("oci_repos", {})
    git_repos = sources_config.get("git_repos", {})

    app_list = apps_config.get("apps", [])
    total = 0
    success = 0

    pull_helm_repo_names = set()
    pull_git_repo_names = set()

    for app in app_list:
        if app["type"] in ("pull-helm", "pull-helm-oci"):
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
            try:
                if repo_path.exists():
                    subprocess.run(["git", "-C", str(repo_path), "reset", "--hard", "HEAD"], check=True)
                    subprocess.run(["git", "-C", str(repo_path), "clean", "-dfx"], check=True)
                    if repo.get("branch"):
                        subprocess.run(["git", "-C", str(repo_path), "checkout", repo["branch"]], check=True)
                    subprocess.run(["git", "-C", str(repo_path), "pull"], check=True)
                else:
                    subprocess.run(["git", "clone", repo["url"], str(repo_path)], check=True)
                success += 1
            except subprocess.CalledProcessError:
                console.print(f"[red]❌ Git 작업 실패: {repo_name}[/red]")
            total += 1
        else:
            console.print(f"[red]❌ {repo_name} not in git_repos[/red]")

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    for app in app_list:
        if app["type"] in ("pull-helm", "pull-helm-oci"):
            total += 1
            try:
                repo = app["specs"]["repo"]
                chart = app["specs"]["chart"]
                chart_ver = app["specs"].get("chart_version")
                chart_dest = CHARTS_DIR / repo
                shutil.rmtree(chart_dest / chart, ignore_errors=True)

                if app["type"] == "pull-helm":
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
                else:
                    repo_url = oci_repos.get(repo, {}).get(chart)
                    if not repo_url:
                        console.print(f"[red]❌ OCI chart not found: {repo}/{chart}[/red]")
                        continue
                    cmd = ["helm", "pull", repo_url, "-d", str(chart_dest), "--untar"]
                    if chart_ver:
                        cmd += ["--version", chart_ver]
                console.print(f"[cyan]📥 helm pull: {cmd}[/cyan]")
                subprocess.run(cmd, check=True)
                success += 1
            except subprocess.CalledProcessError:
                console.print(f"[red]❌ Helm pull 실패: {app.get('name', chart)}[/red]")

    console.print(f"[bold green]✅ prepare 완료: {success}/{total} 개 완료[/bold green]")
