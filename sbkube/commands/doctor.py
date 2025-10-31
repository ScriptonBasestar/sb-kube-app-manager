import asyncio
import sys

import click
from rich.console import Console

from sbkube.diagnostics.kubernetes_checks import (
    ConfigValidityCheck,
    HelmInstallationCheck,
    KubernetesConnectivityCheck,
    NetworkAccessCheck,
    PermissionsCheck,
    ResourceAvailabilityCheck,
)
from sbkube.utils.diagnostic_system import DiagnosticEngine
from sbkube.utils.logger import logger

console = Console()


@click.command(name="doctor")
@click.option("--detailed", is_flag=True, help="상세한 진단 결과 표시")
@click.option("--check", help="특정 검사만 실행 (예: k8s_connectivity)")
@click.option("--config-dir", default=".", help="설정 파일 디렉토리")
@click.pass_context
def cmd(ctx, detailed, check, config_dir):
    """SBKube 시스템 종합 진단

    Kubernetes 클러스터 연결, Helm 설치, 설정 파일 유효성 등을
    종합적으로 진단하고 문제점을 찾아 해결 방안을 제시합니다.

    \\b
    사용 예시:
        sbkube doctor                     # 기본 진단 실행
        sbkube doctor --detailed          # 상세 결과 표시
        sbkube doctor --check k8s_connectivity  # 특정 검사만 실행
    """

    try:
        # 진단 엔진 초기화
        engine = DiagnosticEngine(console)

        # 진단 체크 등록
        all_checks = [
            KubernetesConnectivityCheck(),
            HelmInstallationCheck(),
            ConfigValidityCheck(config_dir),
            NetworkAccessCheck(),
            PermissionsCheck(),
            ResourceAvailabilityCheck(),
        ]

        # 사용 가능한 체크 이름 매핑
        check_mapping = {c.name: c for c in all_checks}

        # 특정 체크만 실행하는 경우
        if check:
            if check not in check_mapping:
                console.print(f"❌ 알 수 없는 검사: {check}")
                console.print("사용 가능한 검사:")
                for c in all_checks:
                    console.print(f"  - {c.name}: {c.description}")
                sys.exit(1)

            checks = [check_mapping[check]]
        else:
            checks = all_checks

        # 선택된 체크들 등록
        for diagnostic_check in checks:
            engine.register_check(diagnostic_check)

        # 진단 실행
        results = asyncio.run(engine.run_all_checks())

        # 결과 표시
        engine.display_results(detailed=detailed)

        # 종료 코드 결정
        summary = engine.get_summary()
        if summary["error"] > 0:
            sys.exit(1)
        elif summary["warning"] > 0:
            sys.exit(2)
        else:
            sys.exit(0)

    except Exception as e:
        logger.error(f"❌ 진단 실행 실패: {e}")
        sys.exit(1)




# Public API for testing and extension
def get_available_checks():
    """사용 가능한 진단 체크 목록 반환 (Public API for testing/extension)

    Returns:
        list[DiagnosticCheck]: 모든 사용 가능한 진단 체크 인스턴스 목록

    Example:
        >>> checks = get_available_checks()
        >>> for check in checks:
        ...     print(f"{check.name}: {check.description}")
    """
    return [
        KubernetesConnectivityCheck(),
        HelmInstallationCheck(),
        ConfigValidityCheck(),
        NetworkAccessCheck(),
        PermissionsCheck(),
        ResourceAvailabilityCheck(),
    ]


def get_check_info(check_name: str):
    """특정 체크의 정보 반환 (Public API for testing/extension)

    Args:
        check_name: 체크 이름 (예: "k8s_connectivity", "helm_installation")

    Returns:
        dict | None: 체크 정보 딕셔너리 또는 None (체크를 찾지 못한 경우)

    Example:
        >>> info = get_check_info("k8s_connectivity")
        >>> print(info["description"])
        Kubernetes 클러스터 연결
    """
    checks = get_available_checks()
    for check in checks:
        if check.name == check_name:
            return {
                "name": check.name,
                "description": check.description,
                "class": check.__class__.__name__,
            }
    return None
