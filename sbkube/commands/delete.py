import click
from rich.console import Console

console = Console()

@click.command()
def cmd():
    """
    설치된 리소스를 삭제합니다.
    예: helm uninstall 또는 kubectl delete -f
    """
    console.print("[bold green]삭제 시작...[/bold green]")
    
    # TODO: helm uninstall 또는 kubectl delete 로직 구현

    console.print("[bold red]삭제 완료[/bold red]")
