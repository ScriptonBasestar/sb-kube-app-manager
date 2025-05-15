import subprocess
import click
from pathlib import Path
from rich.console import Console

from sbkube.utils.file_loader import load_config_file
from sbkube.utils.cli_check import check_helm_installed_or_exit

console = Console()

@click.command(name="template")
@click.option("--apps", default="config", help="앱 구성 설정 파일 (확장자 생략 가능)")
@click.option("--output-dir", default="rendered", help="YAML 출력 디렉토리 (기본: rendered/)")
@click.option("--base-dir", default=".", help="프로젝트 루트 디렉토리 (기본: 현재 경로)")
def cmd(apps, output_dir, base_dir):
    """Helm chart를 YAML로 렌더링 (helm template)"""
    check_helm_installed_or_exit()

    # 🔹 BASE 경로 확인
    BASE_DIR = Path(base_dir).resolve()
    if not BASE_DIR.exists():
        console.print(f"[red]❌ base-dir 디렉토리가 존재하지 않습니다: {BASE_DIR}[/red]")
        raise click.Abort()

    # 🔹 앱 설정 파일 확장자 확인 및 경로 구성
    apps_base = BASE_DIR / apps
    if apps_base.suffix:  # .yaml 등 확장자 포함된 경우
        apps_path = apps_base
        if not apps_path.exists():
            console.print(f"[red]❌ 지정된 앱 구성 파일이 존재하지 않습니다: {apps_path}[/red]")
            raise click.Abort()
    else:
        for ext in [".yaml", ".yml", ".toml"]:
            candidate = apps_base.with_suffix(ext)
            if candidate.exists():
                apps_path = candidate
                break
        else:
            console.print(f"[red]❌ config 파일이 존재하지 않습니다: {apps_base}.[yaml|yml|toml][/red]")
            raise click.Abort()

    # 🔹 경로 설정
    BUILD_DIR = BASE_DIR / "build"
    VALUES_DIR = BASE_DIR / "values"
    OUTPUT_DIR = Path(output_dir).resolve() if Path(output_dir).is_absolute() else BASE_DIR / output_dir

    # 🔹 앱 구성 로드
    apps_config = load_config_file(str(apps_path))

    for app in apps_config.get("apps", []):
        if app["type"] not in ("install-helm"):
            continue

        name = app["name"]
        release = app.get("release", name)
        chart_dir = BUILD_DIR / name

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

    console.print("[bold green]✅ template 완료[/bold green]")
