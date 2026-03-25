"""Helm 3→4 SSA(Server-Side Apply) 필드 관리자 마이그레이션.

Helm 4는 SSA가 기본값이므로, Helm 3에서 관리하던 리소스의
field manager 소유권을 Helm으로 이전해야 합니다.
이 명령은 충돌이 발생할 수 있는 release를 감지하고,
--force-adopt 플래그로 소유권을 마이그레이션합니다.
"""

import json
import re

import click
from rich.console import Console
from rich.table import Table

from sbkube.utils.common import run_command
from sbkube.utils.global_options import global_options
from sbkube.utils.logger import logger

# Use logger's console so it respects --format (quiet in non-human modes)
console = logger.console


def _list_helm_releases(
    kubeconfig: str | None = None,
    context: str | None = None,
    namespace: str | None = None,
) -> list[dict]:
    """전체 Helm release 목록 조회.

    Args:
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름
        namespace: 특정 namespace로 필터링 (None이면 전체)

    Returns:
        Helm release 딕셔너리 목록

    """
    cmd = ["helm", "list", "--output", "json"]
    if namespace:
        cmd.extend(["--namespace", namespace])
    else:
        cmd.append("-A")
    if kubeconfig:
        cmd.extend(["--kubeconfig", kubeconfig])
    if context:
        cmd.extend(["--kube-context", context])

    return_code, stdout, stderr = run_command(cmd, timeout=15)
    if return_code != 0:
        logger.warning(f"Helm release 목록 조회 실패: {stderr}")
        return []

    try:
        return json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        logger.warning("Helm 출력 JSON 파싱 실패")
        return []


def _check_release_conflict(
    name: str,
    namespace: str,
    kubeconfig: str | None = None,
    context: str | None = None,
) -> dict | None:
    """release의 최근 배포 히스토리에서 SSA 충돌 여부 확인.

    Args:
        name: Helm release 이름
        namespace: release namespace
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름

    Returns:
        충돌 정보 dict 또는 None (충돌 없음)

    """
    cmd = ["helm", "history", name, "-n", namespace, "--output", "json", "--max", "5"]
    if kubeconfig:
        cmd.extend(["--kubeconfig", kubeconfig])
    if context:
        cmd.extend(["--kube-context", context])

    return_code, stdout, stderr = run_command(cmd, timeout=10)
    if return_code != 0:
        return None

    try:
        history = json.loads(stdout) if stdout.strip() else []
    except json.JSONDecodeError:
        return None

    if not history:
        return None

    # 히스토리에서 conflict 관련 실패 검색
    for entry in reversed(history):
        desc = entry.get("description", "").lower()
        status = entry.get("status", "").lower()
        if "conflict" in desc:
            # field manager 이름 추출 시도
            manager_match = re.search(r'"([^"]*client-side[^"]*)"', entry.get("description", ""))
            manager = manager_match.group(1) if manager_match else None
            return {
                "release": name,
                "namespace": namespace,
                "status": status,
                "description": entry.get("description", ""),
                "conflicting_manager": manager,
                "revision": entry.get("revision", ""),
            }

    return None


def _check_release_managed_fields(
    name: str,
    namespace: str,
    kubeconfig: str | None = None,
    context: str | None = None,
) -> list[dict]:
    """release의 리소스에서 non-helm field manager를 가진 항목 검색.

    Args:
        name: Helm release 이름
        namespace: release namespace
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름

    Returns:
        충돌 가능한 리소스 정보 목록

    """
    # helm get manifest로 리소스 목록 추출
    cmd = ["helm", "get", "manifest", name, "-n", namespace]
    if kubeconfig:
        cmd.extend(["--kubeconfig", kubeconfig])
    if context:
        cmd.extend(["--kube-context", context])

    return_code, stdout, stderr = run_command(cmd, timeout=15)
    if return_code != 0:
        return []

    # YAML 문서에서 kind/name 추출
    resources = []
    for doc in stdout.split("---"):
        kind_match = re.search(r"^kind:\s*(\S+)", doc, re.MULTILINE)
        name_match = re.search(r"^\s+name:\s*(\S+)", doc, re.MULTILINE)
        if kind_match and name_match:
            resources.append({
                "kind": kind_match.group(1),
                "name": name_match.group(1),
            })

    conflicts = []
    for resource in resources:
        kind = resource["kind"]
        res_name = resource["name"]

        # kubectl get으로 managedFields 확인
        kubectl_cmd = [
            "kubectl", "get", f"{kind}/{res_name}", "-n", namespace,
            "-o", "jsonpath={.metadata.managedFields[*].manager}",
        ]
        if kubeconfig:
            kubectl_cmd.extend(["--kubeconfig", kubeconfig])
        if context:
            kubectl_cmd.extend(["--context", context])

        rc, out, _ = run_command(kubectl_cmd, timeout=5)
        if rc != 0 or not out.strip():
            continue

        managers = out.strip().split()
        non_helm_managers = [
            m for m in managers
            if m not in ("helm", "helm-mapkubeapis", "Go-http-client")
            and not m.startswith("helm")
        ]
        if non_helm_managers:
            conflicts.append({
                "kind": kind,
                "name": res_name,
                "namespace": namespace,
                "managers": non_helm_managers,
            })

    return conflicts


def _display_conflict_summary(
    release_conflicts: dict[str, list[dict]],
    history_conflicts: dict[str, dict],
) -> None:
    """충돌 요약 테이블 출력.

    Args:
        release_conflicts: {release_key: [resource_conflicts]}
        history_conflicts: {release_key: history_conflict_info}

    """
    if not release_conflicts and not history_conflicts:
        console.print("\n[green]✅ SSA 필드 관리자 충돌이 없습니다.[/green]")
        return

    # 히스토리 기반 충돌 (실패한 배포)
    if history_conflicts:
        table = Table(title="🔴 배포 실패 이력 (SSA 충돌)")
        table.add_column("Release", style="red")
        table.add_column("Namespace")
        table.add_column("Status")
        table.add_column("충돌 관리자")

        for key, info in history_conflicts.items():
            table.add_row(
                info["release"],
                info["namespace"],
                info["status"],
                info.get("conflicting_manager") or "unknown",
            )
        console.print(table)

    # 리소스 기반 충돌 (managedFields 검사)
    if release_conflicts:
        table = Table(title="⚠️  Non-Helm Field Manager 감지")
        table.add_column("Release", style="yellow")
        table.add_column("Resource")
        table.add_column("Field Managers", style="red")

        for release_key, resources in release_conflicts.items():
            for res in resources:
                table.add_row(
                    release_key,
                    f"{res['kind']}/{res['name']}",
                    ", ".join(res["managers"]),
                )
        console.print(table)


def _migrate_release(
    name: str,
    namespace: str,
    kubeconfig: str | None = None,
    context: str | None = None,
) -> bool:
    """release의 field manager를 Helm으로 마이그레이션.

    helm upgrade --force-adopt을 사용하여 소유권을 이전합니다.

    Args:
        name: Helm release 이름
        namespace: release namespace
        kubeconfig: kubeconfig 파일 경로
        context: kubectl context 이름

    Returns:
        마이그레이션 성공 여부

    """
    # 현재 release의 chart 정보 추출
    metadata_cmd = ["helm", "get", "metadata", name, "-n", namespace, "--output", "json"]
    if kubeconfig:
        metadata_cmd.extend(["--kubeconfig", kubeconfig])
    if context:
        metadata_cmd.extend(["--kube-context", context])

    rc, stdout, _ = run_command(metadata_cmd, timeout=10)
    if rc != 0:
        # metadata 명령이 없는 경우 status로 대체
        status_cmd = ["helm", "status", name, "-n", namespace, "--output", "json"]
        if kubeconfig:
            status_cmd.extend(["--kubeconfig", kubeconfig])
        if context:
            status_cmd.extend(["--kube-context", context])
        rc, stdout, _ = run_command(status_cmd, timeout=10)
        if rc != 0:
            logger.error(f"Release '{name}' 정보 조회 실패")
            return False

    try:
        info = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        logger.error(f"Release '{name}' 정보 파싱 실패")
        return False

    chart = info.get("chart", "")
    if not chart:
        logger.error(f"Release '{name}'의 chart 정보를 찾을 수 없습니다")
        return False

    # helm upgrade --force-adopt 실행
    upgrade_cmd = [
        "helm", "upgrade", name, chart,
        "-n", namespace,
        "--force-adopt",
        "--reuse-values",
    ]
    if kubeconfig:
        upgrade_cmd.extend(["--kubeconfig", kubeconfig])
    if context:
        upgrade_cmd.extend(["--kube-context", context])

    console.print(f"  🔄 Migrating {namespace}/{name}...")
    rc, stdout, stderr = run_command(upgrade_cmd, timeout=300)

    if rc != 0:
        console.print(f"  [red]❌ 마이그레이션 실패: {name}[/red]")
        logger.error(stderr)
        return False

    console.print(f"  [green]✅ 마이그레이션 완료: {name}[/green]")
    return True


@click.command(name="migrate")
@click.argument("target", required=False)
@click.option(
    "--all",
    "migrate_all",
    is_flag=True,
    help="전체 Helm release 마이그레이션",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="변경 없이 충돌 확인만 수행",
)
@click.option(
    "--app",
    "target_app",
    help="특정 앱만 마이그레이션",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="확인 프롬프트 건너뛰기",
)
@click.option(
    "--deep",
    is_flag=True,
    help="리소스별 managedFields 상세 검사 (느림)",
)
@global_options
@click.pass_context
def cmd(
    ctx: click.Context,
    target: str | None,
    migrate_all: bool,
    dry_run: bool,
    target_app: str | None,
    yes: bool,
    deep: bool,
) -> None:
    r"""Helm 3→4 SSA 필드 관리자 마이그레이션.

    Helm 4의 Server-Side Apply(SSA) 기본값 변경으로 인한
    필드 관리자 충돌을 감지하고 해결합니다.

    \b
    Examples:
      sbkube migrate --dry-run --all       # 전체 release 충돌 확인
      sbkube migrate --all                 # 전체 release 마이그레이션
      sbkube migrate --app traefik         # 특정 앱만 마이그레이션
      sbkube migrate --deep --all          # 상세 managedFields 검사
    """
    kubeconfig = ctx.obj.get("kubeconfig")
    kube_context = ctx.obj.get("context")

    console.print("\n[bold]🔍 Helm SSA 마이그레이션 검사[/bold]\n")

    # 1. Helm 버전 확인
    rc, version_out, _ = run_command(["helm", "version", "--short"], timeout=5)
    if rc == 0:
        version = version_out.strip()
        console.print(f"  Helm 버전: {version}")
        if "v4." not in version:
            console.print(
                "[yellow]⚠️  Helm v4가 아닙니다. "
                "SSA 마이그레이션은 Helm 4 환경에서만 필요합니다.[/yellow]"
            )
            if not yes:
                if not click.confirm("계속 진행하시겠습니까?", default=False):
                    return

    # 2. Release 목록 조회
    releases = _list_helm_releases(kubeconfig, kube_context)
    if not releases:
        console.print("[yellow]Helm release가 없습니다.[/yellow]")
        return

    # 필터링
    if target_app:
        releases = [r for r in releases if r.get("name") == target_app]
        if not releases:
            console.print(f"[red]Release '{target_app}'을 찾을 수 없습니다.[/red]")
            return

    console.print(f"  검사 대상: {len(releases)}개 release\n")

    # 3. 충돌 검사
    history_conflicts: dict[str, dict] = {}
    resource_conflicts: dict[str, list[dict]] = {}

    with console.status("충돌 검사 중..."):
        for release in releases:
            name = release.get("name", "")
            namespace = release.get("namespace", "")
            release_key = f"{namespace}/{name}"

            # 히스토리 기반 충돌 검사 (빠름)
            conflict = _check_release_conflict(name, namespace, kubeconfig, kube_context)
            if conflict:
                history_conflicts[release_key] = conflict

            # managedFields 상세 검사 (--deep 옵션)
            if deep:
                conflicts = _check_release_managed_fields(
                    name, namespace, kubeconfig, kube_context
                )
                if conflicts:
                    resource_conflicts[release_key] = conflicts

    # 4. 결과 출력
    _display_conflict_summary(resource_conflicts, history_conflicts)

    total_conflicts = len(history_conflicts) + len(resource_conflicts)
    if total_conflicts == 0:
        console.print("\n[green]모든 release가 정상입니다.[/green]")
        return

    if dry_run:
        console.print(f"\n[cyan]📋 {total_conflicts}개 release에서 충돌 감지 (dry-run)[/cyan]")
        console.print("[dim]실제 마이그레이션: --dry-run 제거 후 재실행[/dim]")
        return

    # 5. 마이그레이션 실행
    targets = set(history_conflicts.keys()) | set(resource_conflicts.keys())

    if not yes:
        console.print(f"\n⚠️  {len(targets)}개 release를 마이그레이션합니다.")
        for t in sorted(targets):
            console.print(f"  • {t}")
        if not click.confirm("\n진행하시겠습니까?", default=False):
            return

    console.print(f"\n[bold]🚀 마이그레이션 시작 ({len(targets)}개 release)[/bold]\n")

    success = 0
    failed = 0
    for release_key in sorted(targets):
        parts = release_key.split("/", 1)
        namespace, name = parts[0], parts[1]
        if _migrate_release(name, namespace, kubeconfig, kube_context):
            success += 1
        else:
            failed += 1

    # 6. 결과 요약
    console.print(f"\n{'─' * 40}")
    console.print(f"[bold]마이그레이션 완료[/bold]")
    console.print(f"  ✅ 성공: {success}")
    if failed:
        console.print(f"  ❌ 실패: {failed}")
    console.print(f"{'─' * 40}")
