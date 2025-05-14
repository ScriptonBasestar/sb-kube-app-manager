import shutil
import subprocess
import sys
from rich.console import Console

console = Console()

def check_helm_installed_or_exit():
    helm_path = shutil.which("helm")
    if not helm_path:
        console.print("[red]❌ helm 명령이 시스템에 설치되어 있지 않습니다.[/red]")
        sys.exit(1)

    try:
        result = subprocess.run(["helm", "version"], capture_output=True, text=True, check=True)
        console.print(f"[green]✅ helm 확인됨:[/green] {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ helm 실행 실패:[/red] {e}")
        sys.exit(1)
    except PermissionError:
        console.print(f"[red]❌ helm 바이너리에 실행 권한이 없습니다: {helm_path}[/red]")
        sys.exit(1)
