import click
import sys
import yaml
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from sbkube.utils.profile_loader import ProfileLoader
from sbkube.utils.logger import logger

console = Console()


@click.group(name="profiles")
def profiles_group():
    """프로파일 관리 명령어"""
    pass


@profiles_group.command("list")
@click.option("--detailed", is_flag=True, help="상세 정보 표시")
@click.pass_context
def list_profiles(ctx, detailed):
    """사용 가능한 프로파일 목록 조회"""
    try:
        loader = ProfileLoader()
        profiles = loader.list_available_profiles()
        
        if not profiles:
            console.print("⚠️  사용 가능한 프로파일이 없습니다.")
            console.print("💡 'sbkube init' 명령어로 프로젝트를 초기화하세요.")
            return
        
        if detailed:
            _show_detailed_profiles(profiles)
        else:
            _show_simple_profiles(profiles)
            
    except Exception as e:
        logger.error(f"❌ 프로파일 목록 조회 실패: {e}")
        sys.exit(1)


@profiles_group.command("validate")
@click.argument("profile_name", required=False)
@click.option("--all", is_flag=True, help="모든 프로파일 검증")
@click.pass_context
def validate_profile(ctx, profile_name, all):
    """프로파일 설정 검증"""
    try:
        loader = ProfileLoader()
        
        if all:
            _validate_all_profiles(loader)
        elif profile_name:
            _validate_single_profile(loader, profile_name)
        else:
            # 기본 프로파일 검증
            _validate_single_profile(loader, None)
            
    except Exception as e:
        logger.error(f"❌ 프로파일 검증 실패: {e}")
        sys.exit(1)


@profiles_group.command("show")
@click.argument("profile_name")
@click.option("--merged", is_flag=True, help="병합된 최종 설정 표시")
@click.pass_context
def show_profile(ctx, profile_name, merged):
    """프로파일 설정 내용 표시"""
    try:
        loader = ProfileLoader()
        
        if merged:
            config = loader.load_with_overrides(profile_name)
            console.print(f"\n🔧 프로파일 '{profile_name}' 병합된 설정:")
        else:
            config = loader.profile_manager.load_profile(profile_name)
            console.print(f"\n📋 프로파일 '{profile_name}' 원본 설정:")
        
        yaml_output = yaml.dump(config, default_flow_style=False, allow_unicode=True)
        console.print(Panel(yaml_output, expand=False))
        
    except Exception as e:
        logger.error(f"❌ 프로파일 조회 실패: {e}")
        sys.exit(1)


def _show_simple_profiles(profiles: List[Dict[str, Any]]):
    """간단한 프로파일 목록 표시"""
    table = Table(title="🏷️  사용 가능한 프로파일")
    table.add_column("이름", style="cyan")
    table.add_column("네임스페이스", style="green")
    table.add_column("앱 수", justify="center")
    table.add_column("상태", justify="center")
    
    for profile in profiles:
        status = "✅" if profile["valid"] else "❌"
        table.add_row(
            profile["name"],
            profile["namespace"],
            str(profile["apps_count"]),
            status
        )
    
    console.print(table)


def _show_detailed_profiles(profiles: List[Dict[str, Any]]):
    """상세한 프로파일 정보 표시"""
    for i, profile in enumerate(profiles):
        if i > 0:
            console.print()
        
        status_color = "green" if profile["valid"] else "red"
        status_text = "유효" if profile["valid"] else "오류"
        
        panel_content = f"""[bold]네임스페이스:[/bold] {profile['namespace']}
[bold]앱 개수:[/bold] {profile['apps_count']}
[bold]상태:[/bold] [{status_color}]{status_text}[/{status_color}]
[bold]오류:[/bold] {profile['errors']}개
[bold]경고:[/bold] {profile['warnings']}개"""
        
        if 'error_message' in profile:
            panel_content += f"\n[bold red]오류 메시지:[/bold red] {profile['error_message']}"
        
        console.print(Panel(
            panel_content,
            title=f"📋 {profile['name']}",
            expand=False
        ))


def _validate_single_profile(loader: ProfileLoader, profile_name: str):
    """단일 프로파일 검증"""
    validation = loader.profile_manager.validate_profile(profile_name or "default")
    
    profile_display = profile_name or "기본 설정"
    console.print(f"\n🔍 프로파일 '{profile_display}' 검증 결과:")
    
    if validation["valid"]:
        console.print("✅ 프로파일이 유효합니다!")
    else:
        console.print("❌ 프로파일에 오류가 있습니다:")
        for error in validation["errors"]:
            console.print(f"   • {error}")
    
    if validation["warnings"]:
        console.print("\n⚠️  경고사항:")
        for warning in validation["warnings"]:
            console.print(f"   • {warning}")


def _validate_all_profiles(loader: ProfileLoader):
    """모든 프로파일 검증"""
    profiles = loader.list_available_profiles()
    
    if not profiles:
        console.print("⚠️  검증할 프로파일이 없습니다.")
        return
    
    console.print(f"\n🔍 {len(profiles)}개 프로파일 검증 중...\n")
    
    valid_count = 0
    for profile in profiles:
        status = "✅" if profile["valid"] else "❌"
        console.print(f"{status} {profile['name']}: ", end="")
        
        if profile["valid"]:
            console.print("[green]유효[/green]")
            valid_count += 1
        else:
            console.print(f"[red]{profile['errors']}개 오류[/red]")
    
    console.print(f"\n📊 검증 완료: {valid_count}/{len(profiles)}개 프로파일이 유효합니다.")


# CLI에 등록할 명령어
cmd = profiles_group