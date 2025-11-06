import click

import sbkube


@click.command(name="version")
def cmd() -> None:
    """현재 sbkube 버전을 출력합니다."""
    click.echo(f"sbkube version: {sbkube.__version__}")
