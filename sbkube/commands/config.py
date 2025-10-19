"""Kubernetes 설정 정보를 확인하는 명령어."""

import click

from sbkube.utils.kubeconfig_info import display_kubeconfig_info


@click.command(name="config")
@click.pass_context
def cmd(ctx: click.Context) -> None:
    """Kubernetes 설정 정보를 확인합니다.

    현재 활성 컨텍스트, 사용 가능한 컨텍스트 목록, 클러스터 정보 등을 표시합니다.
    """
    kubeconfig = ctx.obj.get("kubeconfig")
    context = ctx.obj.get("context")

    display_kubeconfig_info(kubeconfig_path=kubeconfig, context_name=context)
