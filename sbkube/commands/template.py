import subprocess
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit

console = Console()

@click.command(name="template")
@click.option("--app-dir", default="config", help="앱 구성 디렉토리 (내부 config.yaml|yml|toml) 자동 탐색")
@click.option("--output-dir", default="rendered", help="YAML 출력 디렉토리 (기본: rendered/)")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
def cmd(app_dir, output_dir, base_dir):
    """Helm chart를 YAML로 렌더링 (helm template)"""
    check_helm_installed_or_exit()

    BASE_DIR = Path(base_dir).resolve()
    APP_DIR = BASE_DIR / app_dir
    BUILD_DIR = APP_DIR / "build"
    VALUES_DIR = APP_DIR / "values"
    OUTPUT_DIR = Path(output_dir).resolve() if Path(output_dir).is_absolute() else APP_DIR / output_dir

    if not BASE_DIR.exists():
        console.print(f"[red]❌ base-dir 디렉토리가 존재하지 않습니다: {BASE_DIR}[/red]")
        raise click.Abort()

    config_path = None
    for ext in [".yaml", ".yml", ".toml"]:
        candidate = (APP_DIR / f"config{ext}").resolve()
        if candidate.exists():
            config_path = candidate
            break

    if not config_path or not config_path.exists():
        console.print(f"[red]❌ config 설정 파일이 존재하지 않습니다: {APP_DIR}/config.[yaml|yml|toml][/red]")
        raise click.Abort()

    apps_config = load_config_file(str(config_path))

    total = 0
    success = 0

    for app in apps_config.get("apps", []):
        if app["type"] != "install-helm":
            continue

        total += 1
        name = app["name"]
        release = app.get("release", name)
        chart_rel = app.get("path", name)
        chart_dir = BUILD_DIR / chart_rel

        if not chart_dir.exists():
            console.print(f"[red]❌ chart 디렉토리 없음: {chart_dir}[/red]")
            continue

        helm_cmd = ["helm", "template", release, str(chart_dir)]

        values_files = app["specs"].get("values", [])
        for vf in values_files:
            vf_path = Path(vf) if Path(vf).is_absolute() else VALUES_DIR / vf
            if vf_path.exists():
                console.print(f"[green]✅ values 파일 사용: {vf_path}[/green]")
                helm_cmd += ["--values", str(vf_path)]
            else:
                console.print(f"[red]❌ values 파일 없음: {vf} (경로: {vf_path})[/red]")

        console.print(f"[cyan]🧾 helm template: {' '.join(helm_cmd)}[/cyan]")
        result = subprocess.run(helm_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            console.print(f"[red]❌ helm template 실패: {result.stderr}[/red]")
            continue

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / f"{name}.yaml"
        out_path.write_text(result.stdout)
        console.print(f"[green]📄 저장됨: {out_path}[/green]")
        success += 1

    console.print(f"[bold green]✅ template 완료: {success}/{total} 개 완료[/bold green]")
