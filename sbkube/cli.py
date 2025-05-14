import click
from sbkube.commands import prepare, build, template, deploy, upgrade, delete

@click.group()
def main():
    """sbkube: YAML/Helm/Git 기반의 k3s 배포 도구"""
    pass

main.add_command(prepare.cmd)
main.add_command(build.cmd)
main.add_command(template.cmd)
main.add_command(deploy.cmd)
main.add_command(upgrade.cmd)
main.add_command(delete.cmd)
