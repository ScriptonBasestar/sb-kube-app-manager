import click
from sbkube.commands import prepare, build, template, deploy, upgrade, delete

@click.group()
def main():
    """sbkube: k3s용 Helm/YAML/Git 배포 도구"""
    pass

main.add_command(prepare.cmd)
main.add_command(build.cmd)
main.add_command(template.cmd)
main.add_command(deploy.cmd)
main.add_command(upgrade.cmd)
main.add_command(delete.cmd)

if __name__ == "__main__":
    main()
