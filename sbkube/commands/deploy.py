import subprocess
import click
from pathlib import Path
from typing import Optional

from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.logger import logger, setup_logging_from_context, LogLevel
from sbkube.utils.cli_check import check_helm_installed, check_kubectl_installed, CliToolNotFoundError, CliToolExecutionError, print_kube_connection_help
from sbkube.utils.helm_util import get_installed_charts
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppInstallActionSpec,
    AppExecSpec,
)

class DeployCommand(BaseCommand):
    """Deploy 명령 구현"""
    
    def __init__(self, base_dir: str, app_config_dir: str, cli_namespace: Optional[str],
                 dry_run: bool, target_app_name: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.dry_run = dry_run
        self.target_app_name = target_app_name
        
    def execute(self):
        """deploy 명령 실행"""
        self.execute_pre_hook()
        logger.heading(f"Deploy 시작 - app-dir: {self.app_config_dir.name}")
        
        # 지원하는 앱 타입
        supported_types = ["install-helm", "install-yaml", "exec"]
        
        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        # 필요한 CLI 도구들 체크 (공통 함수 사용)
        self.check_required_cli_tools()
            
        # 앱 처리 (공통 로직 사용)
        self.process_apps_with_stats(self._deploy_app, "배포")
        
    def _deploy_app(self, app_info: AppInfoScheme) -> bool:
        """개별 앱 배포"""
        app_type = app_info.type
        app_name = app_info.name
        current_ns = self.get_namespace(app_info)
        
        logger.progress(f"앱 '{app_name}' (타입: {app_type}, 네임스페이스: {current_ns or '기본값'}) 배포 시작")
        
        try:
            # Spec 모델 생성 (공통 함수 사용)
            spec_obj = self.create_app_spec(app_info)
            if not spec_obj:
                return False
                
            # 타입별 배포 처리
            if app_type == "install-helm":
                self._deploy_helm(app_info, spec_obj, current_ns)
            elif app_type == "install-yaml":
                self._deploy_yaml(app_info, spec_obj, current_ns)
            elif app_type == "exec":
                self._deploy_exec(app_info, spec_obj)
                
            return True
                
        except Exception as e:
            logger.error(f"앱 '{app_name}' 배포 중 예상치 못한 오류: {e}")
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False
            

        
    def _deploy_helm(self, app_info: AppInfoScheme, spec_obj: AppInstallHelmSpec, namespace: Optional[str]):
        """Helm 차트 배포"""
        release_name = app_info.release_name or app_info.name
        
        # 차트 경로 결정
        chart_path_in_build = app_info.specs.get("path") if isinstance(app_info.specs, dict) else getattr(app_info.specs, "path", None)
        chart_path_in_build = chart_path_in_build or app_info.name
        chart_dir = self.build_dir / chart_path_in_build
        
        # 차트 디렉토리 확인
        if not chart_dir.exists():
            logger.error(f"앱 '{app_info.name}': Helm 차트 디렉토리가 빌드 위치에 존재하지 않습니다: {chart_dir}")
            logger.warning("'sbkube build' 명령을 먼저 실행했는지 확인하세요.")
            return
            
        # 이미 설치 확인
        if self._is_helm_installed(release_name, namespace):
            logger.warning(f"앱 '{app_info.name}': Helm 릴리스 '{release_name}'(ns: {namespace or 'default'})가 이미 설치되어 있습니다. 건너뜁니다.")
            return
            
        # Helm 명령 구성
        helm_cmd = self._build_helm_command(release_name, chart_dir, namespace, spec_obj)
        
        # 실행
        self.execute_command_with_logging(helm_cmd, f"앱 '{app_info.name}': Helm 작업 실패 (릴리스: {release_name})")
        
        ns_msg = f" (네임스페이스: {namespace})" if namespace else ""
        logger.success(f"앱 '{app_info.name}': Helm 릴리스 '{release_name}' 배포 완료{ns_msg}")
        
    def _deploy_yaml(self, app_info: AppInfoScheme, spec_obj: AppInstallActionSpec, namespace: Optional[str]):
        """YAML 매니페스트 배포"""
        for action_spec in spec_obj.actions:
            action_type = action_spec.type
            action_path = action_spec.path
            
            # YAML 파일 경로 결정
            target_path = self._resolve_yaml_path(action_path)
            if not target_path:
                logger.error(f"앱 '{app_info.name}': YAML 파일 경로를 확인할 수 없습니다: '{action_path}'")
                continue
                
            # kubectl 명령 구성
            kubectl_cmd = self._build_kubectl_command(action_type, target_path, namespace)
            if not kubectl_cmd:
                logger.error(f"앱 '{app_info.name}': 지원하지 않는 YAML 액션 타입 '{action_type}' 입니다. (지원: apply, create, delete)")
                continue
                
            # 실행
            self.execute_command_with_logging(kubectl_cmd, f"앱 '{app_info.name}': YAML 작업 ('{action_type}' on '{target_path}') 실패")
            logger.success(f"앱 '{app_info.name}': YAML 작업 ('{action_type}' on '{target_path}') 완료")
            
    def _deploy_exec(self, app_info: AppInfoScheme, spec_obj: AppExecSpec):
        """실행 명령 처리"""
        for raw_cmd in spec_obj.commands:
            cmd_parts = raw_cmd.split(" ")
            logger.command(raw_cmd)
            
            result = subprocess.run(cmd_parts, capture_output=True, text=True, check=False, cwd=self.base_dir)
            
            if result.returncode != 0:
                logger.error(f"앱 '{app_info.name}': 명령어 실행 실패 ('{raw_cmd}')")
                if result.stdout:
                    logger.verbose(f"STDOUT: {result.stdout.strip()}")
                if result.stderr:
                    logger.error(f"STDERR: {result.stderr.strip()}")
            else:
                if result.stdout:
                    logger.verbose(f"STDOUT: {result.stdout.strip()}")
                logger.success(f"앱 '{app_info.name}': 명령어 실행 완료 ('{raw_cmd}')")
                
    def _is_helm_installed(self, release_name: str, namespace: Optional[str]) -> bool:
        """Helm 릴리스 설치 여부 확인"""
        if not namespace:
            return False
            
        try:
            installed_charts = get_installed_charts(namespace)
            return release_name in installed_charts
        except subprocess.CalledProcessError as e:
            logger.warning(f"Helm list 실패 (namespace: {namespace}): {e.stderr or e.stdout}")
            return False
            
    def _build_helm_command(self, release_name: str, chart_dir: Path, namespace: Optional[str], 
                           spec_obj: AppInstallHelmSpec) -> list:
        """Helm 설치 명령 구성"""
        cmd = ["helm", "install", release_name, str(chart_dir)]
        
        if namespace:
            cmd.extend(["--namespace", namespace, "--create-namespace"])
        else:
            cmd.append("--create-namespace")
            
        # Values 파일 추가
        for vf_rel_path in spec_obj.values:
            vf_path = Path(vf_rel_path) if Path(vf_rel_path).is_absolute() else self.values_dir / vf_rel_path
            if vf_path.exists():
                cmd.extend(["--values", str(vf_path)])
                logger.verbose(f"values 파일 사용: {vf_path}")
            else:
                logger.warning(f"values 파일 없음 (건너뜀): {vf_path}")
                
        if self.dry_run:
            cmd.append("--dry-run")
            
        return cmd
        
    def _build_kubectl_command(self, action_type: str, target_path: str, namespace: Optional[str]) -> Optional[list]:
        """kubectl 명령 구성"""
        if action_type not in ["apply", "create", "delete"]:
            return None
            
        cmd = ["kubectl", action_type, "-f", target_path]
        
        if namespace:
            cmd.extend(["-n", namespace])
            
        if self.dry_run:
            cmd.append("--dry-run=client")
            
        return cmd
        
    def _resolve_yaml_path(self, path_str: str) -> Optional[str]:
        """YAML 파일 경로 해석"""
        # URL인 경우
        if path_str.startswith("http://") or path_str.startswith("https://"):
            logger.verbose(f"URL에서 YAML 처리 시도: {path_str}")
            return path_str
            
        # 절대 경로인 경우
        path_obj = Path(path_str)
        if path_obj.is_absolute():
            return str(path_obj) if path_obj.exists() else None
            
        # 상대 경로인 경우 - 여러 위치 시도
        candidates = [
            self.app_config_dir / path_str,
            self.base_dir / path_str
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return str(candidate.resolve())
                
        return None
        



@click.command(name="deploy")
@common_click_options
@click.option("--namespace", "cli_namespace", default=None, help="설치할 기본 네임스페이스")
@click.option("--dry-run", is_flag=True, default=False, help="실제로 적용하지 않고 dry-run")
@click.pass_context
def cmd(ctx, app_config_dir_name, base_dir, config_file_name, app_name, verbose, debug, cli_namespace, dry_run):
    """Helm chart 및 YAML, exec 명령을 클러스터에 적용"""
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)
    
    logger.heading(f"Deploy 시작 - app-dir: {app_config_dir_name}")
    
    deploy_cmd = DeployCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        cli_namespace=cli_namespace,
        dry_run=dry_run,
        target_app_name=app_name,
        config_file_name=config_file_name
    )
    
    deploy_cmd.execute()
