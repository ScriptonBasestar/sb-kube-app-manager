import click
import logging

from sbkube.commands import prepare, build, template, deploy, upgrade, delete, validate, version

print("✅ prepare.cmd =", hasattr(prepare, "cmd"))  # ← 이 줄 추가

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
main.add_command(validate.cmd)
main.add_command(version.cmd)

if __name__ == "__main__":
    main()
