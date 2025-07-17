import click
import sys
import asyncio
from typing import List

from rich.console import Console
from sbkube.utils.diagnostic_system import DiagnosticEngine
from sbkube.diagnostics.kubernetes_checks import (
    KubernetesConnectivityCheck,
    HelmInstallationCheck, 
    ConfigValidityCheck,
    NetworkAccessCheck,
    PermissionsCheck,
    ResourceAvailabilityCheck
)
from sbkube.utils.logger import logger

console = Console()


@click.command(name="doctor")
@click.option("--detailed", is_flag=True, help="상세한 진단 결과 표시")
@click.option("--fix", is_flag=True, help="자동 수정 가능한 문제들을 수정")
@click.option("--check", help="특정 검사만 실행 (예: k8s_connectivity)")
@click.option("--config-dir", default="config", help="설정 파일 디렉토리")
@click.pass_context
def cmd(ctx, detailed, fix, check, config_dir):
    """SBKube 시스템 종합 진단
    
    Kubernetes 클러스터 연결, Helm 설치, 설정 파일 유효성 등을
    종합적으로 진단하고 문제점을 찾아 해결 방안을 제시합니다.
    
    \\b
    사용 예시:
        sbkube doctor                     # 기본 진단 실행
        sbkube doctor --detailed          # 상세 결과 표시
        sbkube doctor --fix               # 자동 수정 실행
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
            ResourceAvailabilityCheck()
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
        
        # 자동 수정 실행
        if fix:
            _run_auto_fixes(engine, results)
        
        # 종료 코드 결정
        summary = engine.get_summary()
        if summary['error'] > 0:
            sys.exit(1)
        elif summary['warning'] > 0:
            sys.exit(2)
        else:
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ 진단 실행 실패: {e}")
        sys.exit(1)


def _run_auto_fixes(engine: DiagnosticEngine, results: List) -> None:
    """자동 수정 실행"""
    fixable_results = engine.get_fixable_results()
    
    if not fixable_results:
        console.print("🤷 자동 수정 가능한 문제가 없습니다.")
        return
    
    console.print(f"\n🔧 {len(fixable_results)}개 문제의 자동 수정을 시작합니다...")
    
    success_count = 0
    
    for result in fixable_results:
        if not click.confirm(f"'{result.message}' 문제를 수정하시겠습니까?"):
            continue
        
        console.print(f"🔄 수정 중: {result.fix_description}")
        
        try:
            import subprocess
            import shlex
            
            # 명령어를 안전하게 파싱
            fix_command = shlex.split(result.fix_command)
            
            fix_result = subprocess.run(
                fix_command,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if fix_result.returncode == 0:
                console.print(f"✅ 수정 완료: {result.message}")
                success_count += 1
            else:
                console.print(f"❌ 수정 실패: {fix_result.stderr}")
                console.print(f"💡 수동 실행: {result.fix_command}")
                
        except subprocess.TimeoutExpired:
            console.print(f"⏰ 수정 시간 초과: {result.message}")
            console.print(f"💡 수동 실행: {result.fix_command}")
        except Exception as e:
            console.print(f"❌ 수정 중 오류 발생: {e}")
            console.print(f"💡 수동 실행: {result.fix_command}")
    
    console.print(f"\n📊 자동 수정 완료: {success_count}/{len(fixable_results)}개 성공")
    
    if success_count < len(fixable_results):
        console.print("💡 일부 문제는 수동으로 해결해야 합니다.")
        console.print("   sbkube doctor --detailed 로 상세 정보를 확인하세요.")


# 사용 가능한 체크 목록 함수
def get_available_checks():
    """사용 가능한 진단 체크 목록 반환"""
    return [
        KubernetesConnectivityCheck(),
        HelmInstallationCheck(),
        ConfigValidityCheck(),
        NetworkAccessCheck(),
        PermissionsCheck(),
        ResourceAvailabilityCheck()
    ]


# 진단 체크 정보 함수
def get_check_info(check_name: str):
    """특정 체크의 정보 반환"""
    checks = get_available_checks()
    for check in checks:
        if check.name == check_name:
            return {
                'name': check.name,
                'description': check.description,
                'class': check.__class__.__name__
            }
    return None