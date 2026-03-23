import click

import sbkube
from sbkube.utils.global_options import global_options


@click.command(name="version")
@global_options
def cmd() -> None:
    """현재 sbkube 버전을 출력합니다."""
    click.echo(f"sbkube version: {sbkube.__version__}")
