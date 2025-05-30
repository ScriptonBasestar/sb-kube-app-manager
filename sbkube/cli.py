import click
import logging

from sbkube.commands import prepare, build, template, deploy, upgrade, delete, validate, version

from sbkube.utils.cli_check import print_kube_connection_help


print("✅ prepare.cmd =", hasattr(prepare, "cmd"))  # ← 이 줄 추가

class SbkubeGroup(click.Group):
    def invoke(self, ctx):
        import subprocess
        import shutil
        from pathlib import Path
        kubeconfig = str(Path.home() / ".kube" / "config")
        # 1. kubectl이 설치되어 있는지 확인
        if shutil.which("kubectl") is None:
            # kubectl이 아예 없으면 안내 메시지 출력하지 않음
            return super().invoke(ctx)
        # 2. context가 1개 이상 있는지 확인
        try:
            result = subprocess.run([
                "kubectl", "config", "get-contexts", "-o", "name"
            ], capture_output=True, text=True, timeout=2)
            contexts = result.stdout.strip().splitlines()
        except Exception:
            contexts = []
        if not contexts:
            # context가 없으면 안내 메시지 출력하지 않음
            return super().invoke(ctx)
        # 3. 연결이 안 되어 있을 때만 안내
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode != 0 or "Kubernetes control plane" not in result.stdout:
                print_kube_connection_help()
        except Exception:
            print_kube_connection_help()
        return super().invoke(ctx)

@click.group(cls=SbkubeGroup)
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
