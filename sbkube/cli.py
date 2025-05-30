import click
import logging

from sbkube.commands import prepare, build, template, deploy, upgrade, delete, validate, version

from sbkube.utils.cli_check import print_kube_connection_help
from sbkube.utils.cli_check import print_helm_connection_help


print("✅ prepare.cmd =", hasattr(prepare, "cmd"))  # ← 이 줄 추가

class SbkubeGroup(click.Group):
    def invoke(self, ctx):
        import subprocess
        import shutil
        from pathlib import Path
        kubeconfig = str(Path.home() / ".kube" / "config")
        # 1. kubectl이 설치되어 있는지 확인
        if shutil.which("kubectl") is not None:
            # 2. context가 1개 이상 있는지 확인
            try:
                result = subprocess.run([
                    "kubectl", "config", "get-contexts", "-o", "name"
                ], capture_output=True, text=True, timeout=2)
                contexts = result.stdout.strip().splitlines()
            except Exception:
                contexts = []
            if contexts:
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
        # helm 체크 추가
        if shutil.which("helm") is not None:
            # helm repo가 1개 이상 있는지 확인
            try:
                repo_result = subprocess.run([
                    "helm", "repo", "list", "-o", "json"
                ], capture_output=True, text=True, timeout=2)
                import json as _json
                repos = _json.loads(repo_result.stdout) if repo_result.returncode == 0 else []
            except Exception:
                repos = []
            if repos:
                # helm version이 동작하는지 확인
                try:
                    version_result = subprocess.run([
                        "helm", "version"
                    ], capture_output=True, text=True, timeout=2)
                    if version_result.returncode != 0:
                        print_helm_connection_help()
                except Exception:
                    print_helm_connection_help()
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
