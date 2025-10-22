"""
SBKube v0.2.x → v0.3.0 설정 파일 마이그레이션 도구.

자동으로 기존 설정 파일을 새 형식으로 변환합니다:
- apps: list → dict
- pull-helm + install-helm → helm (통합)
- specs 제거 (평탄화)
"""

from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console
from rich.syntax import Syntax

console = Console()


def migrate_app_type(old_type: str) -> str:
    """
    v0.2.x 타입을 v0.3.0 타입으로 변환.

    Args:
        old_type: 기존 타입 (pull-helm, install-helm, install-yaml 등)

    Returns:
        새 타입 (helm, yaml, action 등)
    """
    type_mapping = {
        "pull-helm": "helm",  # pull만 하는 경우는 드물지만 helm으로 변환
        "pull-helm-oci": "helm",
        "install-helm": "helm",
        "install-yaml": "yaml",
        "install-kubectl": "yaml",
        "install-action": "action",
        "install-kustomize": "kustomize",
        "pull-git": "git",
        "exec": "exec",
        "copy-app": None,  # 제거 (더 이상 사용 안 함)
        "copy-repo": None,
        "copy-chart": None,
        "copy-root": None,
        "render": None,  # 제거 (template 명령어에서 처리)
    }
    return type_mapping.get(old_type, old_type)


def migrate_config_v2_to_v3(old_config: dict[str, Any]) -> dict[str, Any]:
    """
    v0.2.x 설정을 v0.3.0 형식으로 변환.

    변환 규칙:
    1. apps: list → dict (name → key)
    2. pull-helm + install-helm → helm (통합)
    3. specs → 평탄화
    4. 불필요한 필드 제거

    Args:
        old_config: v0.2.x 설정 딕셔너리

    Returns:
        v0.3.0 설정 딕셔너리
    """
    new_config: dict[str, Any] = {}

    # namespace 복사
    new_config["namespace"] = old_config.get("namespace", "default")

    # global labels/annotations 복사 (있으면)
    if "global_labels" in old_config:
        new_config["global_labels"] = old_config["global_labels"]
    if "global_annotations" in old_config:
        new_config["global_annotations"] = old_config["global_annotations"]

    # apps 변환: list → dict
    old_apps = old_config.get("apps", [])
    new_apps: dict[str, Any] = {}

    # pull-helm과 install-helm 쌍을 찾아 통합
    helm_pulls: dict[str, dict[str, Any]] = {}  # dest → pull app
    helm_installs: dict[str, dict[str, Any]] = {}  # path → install app

    for app in old_apps:
        app_name = app.get("name")
        app_type = app.get("type")
        enabled = app.get("enabled", True)
        specs = app.get("specs", {})

        if not enabled:
            # disabled 앱도 유지 (enabled: false로)
            new_type = migrate_app_type(app_type)
            if new_type is None:
                console.print(f"[yellow]⚠️  Skipping unsupported app type '{app_type}': {app_name}[/yellow]")
                continue

            new_apps[app_name] = {
                "type": new_type,
                "enabled": False,
            }
            continue

        # pull-helm 계열
        if app_type in ["pull-helm", "pull-helm-oci"]:
            dest = specs.get("dest", app_name)
            helm_pulls[dest] = {
                "name": app_name,
                "type": app_type,
                "specs": specs,
            }
            continue

        # install-helm
        if app_type == "install-helm":
            path = specs.get("path", app_name)
            helm_installs[path] = {
                "name": app_name,
                "type": app_type,
                "specs": specs,
                "namespace": app.get("namespace"),
                "release_name": app.get("release_name"),
            }
            continue

        # 기타 타입 변환
        new_type = migrate_app_type(app_type)
        if new_type is None:
            console.print(f"[yellow]⚠️  Skipping unsupported app type '{app_type}': {app_name}[/yellow]")
            continue

        new_app: dict[str, Any] = {"type": new_type}

        # specs 평탄화
        if app_type == "install-yaml" or app_type == "install-kubectl":
            # install-yaml: paths → files
            new_app["files"] = specs.get("paths", [])
        elif app_type == "install-action":
            new_app["actions"] = specs.get("actions", [])
        elif app_type == "install-kustomize":
            new_app["path"] = specs.get("kustomize_path", "")
        elif app_type == "pull-git":
            new_app["repo"] = specs.get("repo", "")
            if "paths" in specs:
                # paths는 v0.3.0에서 지원 안 함 (향후 확장 가능)
                new_app["path"] = specs["paths"][0].get("dest") if specs["paths"] else None
            if "ref" in specs:
                new_app["ref"] = specs["ref"]
        elif app_type == "exec":
            new_app["commands"] = specs.get("commands", [])

        # 네임스페이스 (있으면)
        if "namespace" in app:
            new_app["namespace"] = app["namespace"]

        # release_name (있으면)
        if "release_name" in app:
            new_app["release_name"] = app["release_name"]

        new_apps[app_name] = new_app

    # pull-helm + install-helm 통합
    for path, install_app in helm_installs.items():
        pull_app = helm_pulls.get(path)

        if pull_app:
            # 통합: pull + install → helm
            pull_specs = pull_app["specs"]
            install_specs = install_app["specs"]

            chart = f"{pull_specs.get('repo', 'unknown')}/{pull_specs.get('chart', 'unknown')}"
            new_app = {
                "type": "helm",
                "chart": chart,
            }

            if "chart_version" in pull_specs:
                new_app["version"] = pull_specs["chart_version"]

            if "values" in install_specs:
                new_app["values"] = install_specs["values"]

            # overrides (v0.2.x 기능 보존)
            if "overrides" in install_specs:
                new_app["overrides"] = install_specs["overrides"]

            # removes (v0.2.x 기능 보존)
            if "removes" in install_specs:
                new_app["removes"] = install_specs["removes"]

            # labels (v0.2.x 기능 보존)
            if "labels" in install_app:
                new_app["labels"] = install_app["labels"]
            elif "labels" in install_specs:
                new_app["labels"] = install_specs["labels"]

            # annotations (v0.2.x 기능 보존)
            if "annotations" in install_app:
                new_app["annotations"] = install_app["annotations"]
            elif "annotations" in install_specs:
                new_app["annotations"] = install_specs["annotations"]

            if install_app.get("namespace"):
                new_app["namespace"] = install_app["namespace"]

            if install_app.get("release_name"):
                new_app["release_name"] = install_app["release_name"]

            # install app 이름 사용
            app_name = install_app["name"]
            new_apps[app_name] = new_app

            console.print(f"[cyan]  Merged: {pull_app['name']} + {install_app['name']} → {app_name} (helm)[/cyan]")
        else:
            # install만 있는 경우 (pull 없이)
            console.print(
                f"[yellow]⚠️  No matching pull-helm for install-helm '{install_app['name']}' (path={path})[/yellow]"
            )
            # 기본값으로 변환
            new_app = {
                "type": "helm",
                "chart": f"unknown/{path}",  # chart 정보 없음
            }

            if "values" in install_app["specs"]:
                new_app["values"] = install_app["specs"]["values"]

            if install_app.get("namespace"):
                new_app["namespace"] = install_app["namespace"]

            if install_app.get("release_name"):
                new_app["release_name"] = install_app["release_name"]

            app_name = install_app["name"]
            new_apps[app_name] = new_app

    # pull만 있고 install 없는 경우 (드물지만 처리)
    for dest, pull_app in helm_pulls.items():
        if dest not in helm_installs:
            console.print(f"[yellow]⚠️  pull-helm without install-helm: {pull_app['name']} (dest={dest})[/yellow]")
            # helm으로 변환 (values 없음)
            pull_specs = pull_app["specs"]
            chart = f"{pull_specs.get('repo', 'unknown')}/{pull_specs.get('chart', 'unknown')}"
            new_app = {
                "type": "helm",
                "chart": chart,
            }

            if "chart_version" in pull_specs:
                new_app["version"] = pull_specs["chart_version"]

            app_name = pull_app["name"]
            new_apps[app_name] = new_app

    new_config["apps"] = new_apps

    return new_config


@click.command(name="migrate")
@click.argument(
    "config_file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="출력 파일 경로 (지정하지 않으면 미리보기만)",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="출력 파일이 이미 존재해도 덮어쓰기",
)
def cmd(config_file: str, output: str | None, force: bool):
    """
    SBKube v0.2.x 설정 파일을 v0.3.0 형식으로 마이그레이션.

    Examples:
        # 미리보기
        sbkube migrate config.yaml

        # 새 파일로 저장
        sbkube migrate config.yaml -o config-v3.yaml

        # 기존 파일 덮어쓰기
        sbkube migrate config.yaml -o config.yaml --force
    """
    console.print("[bold blue]🔄 SBKube v0.2.x → v0.3.0 Migration[/bold blue]")

    config_path = Path(config_file)

    # 기존 설정 파일 로드
    console.print(f"[cyan]📄 Loading: {config_path}[/cyan]")
    with open(config_path, "r") as f:
        old_config = yaml.safe_load(f)

    # 변환
    console.print("[cyan]🔄 Converting...[/cyan]")
    new_config = migrate_config_v2_to_v3(old_config)

    # YAML 문자열 생성
    new_yaml = yaml.dump(new_config, default_flow_style=False, allow_unicode=True, sort_keys=False)

    # 출력 또는 미리보기
    if output:
        output_path = Path(output)

        if output_path.exists() and not force:
            console.print(f"[red]❌ Output file already exists: {output_path}[/red]")
            console.print("[yellow]💡 Use --force to overwrite[/yellow]")
            raise click.Abort()

        console.print(f"[cyan]💾 Saving to: {output_path}[/cyan]")
        with open(output_path, "w") as f:
            f.write(new_yaml)

        console.print(f"[green]✅ Migration completed: {output_path}[/green]")
    else:
        # 미리보기
        console.print("\n[bold cyan]📋 Preview (v0.3.0 format):[/bold cyan]")
        syntax = Syntax(new_yaml, "yaml", theme="monokai", line_numbers=True)
        console.print(syntax)

        console.print("\n[yellow]💡 Use -o <output_file> to save the migrated config[/yellow]")
