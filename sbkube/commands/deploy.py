import click
from rich.console import Console

console = Console()

@click.command()
def cmd():
    """
    템플릿된 YAML 또는 Helm 차트를 k3s 클러스터에 설치합니다.
    """
    console.print("[bold green]배포 시작...[/bold green]")
    
    # TODO: kubectl apply -f 또는 helm install 수행

    console.print("[bold blue]배포 완료[/bold blue]")
