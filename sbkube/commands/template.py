import click
from rich.console import Console

console = Console()

@click.command()
def cmd():
    """
    최종적으로 배포할 YAML을 템플릿으로 출력합니다.
    예: helm template 명령을 호출하여 yaml 생성
    """
    console.print("[bold green]템플릿 생성 시작...[/bold green]")
    
    # TODO: helm template 수행 후 생성된 YAML을 출력하거나 파일로 저장

    console.print("[bold blue]템플릿 생성 완료[/bold blue]")
