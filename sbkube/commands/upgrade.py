import click
from rich.console import Console

console = Console()

@click.command()
def cmd():
    """
    기존에 설치된 리소스를 Helm upgrade 또는 kubectl apply로 갱신합니다.
    """
    console.print("[bold green]업그레이드 시작...[/bold green]")
    
    # TODO: helm upgrade 또는 kubectl apply 수행 (차이 구분)

    console.print("[bold blue]업그레이드 완료[/bold blue]")
