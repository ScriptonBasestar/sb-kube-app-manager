import click
from rich.console import Console

console = Console()

@click.command()
def cmd():
    """Helm, Git, YAML 소스 다운로드"""
    console.print("[bold green]다운로드 시작...[/bold green]")
    # 여기에서 로컬 config.yaml을 읽고 소스 내려받는 로직 수행
    # 예: GitPython, subprocess로 helm pull, yaml 다운로드 등
    ...
    console.print("[bold blue]다운로드 완료[/bold blue]")
