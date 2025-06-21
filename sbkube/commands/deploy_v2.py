"""
Enhanced deploy command with state tracking support.

This module provides an enhanced version of the deploy command that
integrates with the deployment state tracking system.
"""

import subprocess
import click
from pathlib import Path
from typing import Optional, Dict, Any
import yaml

from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.logger import logger, setup_logging_from_context, LogLevel
from sbkube.utils.cli_check import check_helm_installed, check_kubectl_installed, CliToolNotFoundError, CliToolExecutionError, print_kube_connection_help
from sbkube.utils.helm_util import get_installed_charts
from sbkube.utils.file_loader import load_config_file
from sbkube.models.config_model import (
    AppInfoScheme,
    AppInstallHelmSpec,
    AppInstallActionSpec,
    AppExecSpec,
)
from sbkube.state import DeploymentTracker
from sbkube.models.deployment_state import ResourceAction

class EnhancedDeployCommand(BaseCommand):
    """Enhanced deploy command with state tracking"""
    
    def __init__(self, base_dir: str, app_config_dir: str, cli_namespace: Optional[str],
                 dry_run: bool, target_app_name: Optional[str], config_file_name: Optional[str],
                 enable_tracking: bool = True):
        super().__init__(base_dir, app_config_dir, cli_namespace, config_file_name)
        self.dry_run = dry_run
        self.target_app_name = target_app_name
        self.enable_tracking = enable_tracking
        self.tracker = DeploymentTracker() if enable_tracking else None
        self.sources_data = None
        
    def execute(self):
        """Execute deploy command with state tracking"""
        self.execute_pre_hook()
        logger.heading(f"Deploy 시작 - app-dir: {self.app_config_dir.name}")
        
        # Load sources if available
        sources_path = self.base_dir / "sources.yaml"
        if sources_path.exists():
            self.sources_data = load_config_file(sources_path)
        
        # Get cluster info from sources
        cluster = self.sources_data.get("cluster", "default") if self.sources_data else "default"
        global_namespace = self.apps_config_dict.get("namespace", "default")
        
        # Start deployment tracking
        if self.tracker and not self.dry_run:
            with self.tracker.track_deployment(
                cluster=cluster,
                namespace=global_namespace,
                app_config_dir=str(self.app_config_dir),
                config_file_path=str(self.config_file_path),
                config_data=self.apps_config_dict,
                sources_data=self.sources_data,
                command="deploy",
                command_args={
                    "dry_run": self.dry_run,
                    "target_app": self.target_app_name,
                    "cli_namespace": self.cli_namespace
                },
                dry_run=self.dry_run
            ) as deployment_id:
                if deployment_id:
                    logger.info(f"Deployment tracking ID: {deployment_id}")
                self._execute_deployment()
        else:
            self._execute_deployment()
    
    def _execute_deployment(self):
        """Execute the actual deployment"""
        # 지원하는 앱 타입
        supported_types = ["install-helm", "install-yaml", "exec"]
        
        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        # 필요한 CLI 도구들 체크
        self.check_required_cli_tools()
            
        # 앱 처리
        self.process_apps_with_stats(self._deploy_app, "배포")
        
    def _deploy_app(self, app_info: AppInfoScheme) -> bool:
        """Deploy individual app with tracking"""
        app_type = app_info.type
        app_name = app_info.name
        current_ns = self.get_namespace(app_info)
        
        logger.progress(f"앱 '{app_name}' (타입: {app_type}, 네임스페이스: {current_ns or '기본값'}) 배포 시작")
        
        # Track app deployment
        if self.tracker and not self.dry_run:
            with self.tracker.track_app_deployment(
                app_name=app_name,
                app_type=app_type,
                app_namespace=current_ns,
                app_config=app_info.specs
            ):
                return self._deploy_app_internal(app_info, current_ns)
        else:
            return self._deploy_app_internal(app_info, current_ns)
    
    def _deploy_app_internal(self, app_info: AppInfoScheme, current_ns: Optional[str]) -> bool:
        """Internal app deployment logic"""
        try:
            # Spec 모델 생성
            spec_obj = self.create_app_spec(app_info)
            if not spec_obj:
                return False
                
            # 타입별 배포 처리
            if app_info.type == "install-helm":
                self._deploy_helm(app_info, spec_obj, current_ns)
            elif app_info.type == "install-yaml":
                self._deploy_yaml(app_info, spec_obj, current_ns)
            elif app_info.type == "exec":
                self._deploy_exec(app_info, spec_obj)
                
            return True
                
        except Exception as e:
            logger.error(f"앱 '{app_info.name}' 배포 중 예상치 못한 오류: {e}")
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False
            
    def _deploy_helm(self, app_info: AppInfoScheme, spec_obj: AppInstallHelmSpec, namespace: Optional[str]):
        """Deploy Helm chart with tracking"""
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
            
        # Values 파일 수집
        values_dict = self._collect_helm_values(spec_obj)
        
        # Helm 명령 구성
        helm_cmd = self._build_helm_command(release_name, chart_dir, namespace, spec_obj)
        
        # 실행
        self.execute_command_with_logging(
            helm_cmd,
            error_msg=f"앱 '{app_info.name}': Helm 설치 실패",
            success_msg=f"앱 '{app_info.name}': Helm으로 성공적으로 설치됨"
        )
        
        # Track Helm release
        if self.tracker and not self.dry_run:
            # Get chart info
            chart_yaml_path = chart_dir / "Chart.yaml"
            chart_version = None
            if chart_yaml_path.exists():
                with open(chart_yaml_path, 'r') as f:
                    chart_data = yaml.safe_load(f)
                    chart_version = chart_data.get("version")
            
            self.tracker.track_helm_release(
                release_name=release_name,
                namespace=namespace or "default",
                chart=str(chart_dir),
                chart_version=chart_version,
                values=values_dict
            )
            
    def _deploy_yaml(self, app_info: AppInfoScheme, spec_obj: AppInstallActionSpec, namespace: Optional[str]):
        """Deploy YAML manifests with tracking"""
        actions = spec_obj.actions
        if not actions:
            logger.warning(f"앱 '{app_info.name}': 실행할 액션이 없습니다.")
            return
            
        # 각 액션 처리
        for action in actions:
            self._deploy_yaml_action(app_info, action, namespace)
            
    def _deploy_yaml_action(self, app_info: AppInfoScheme, action, namespace: Optional[str]):
        """Deploy single YAML action with tracking"""
        action_type = action.type
        file_path = action.path
        resolved_path = self._resolve_yaml_path(app_info, file_path)
        
        if not resolved_path:
            logger.error(f"앱 '{app_info.name}': YAML 파일을 찾을 수 없습니다: {file_path}")
            return
            
        # Track resources before applying
        previous_states = {}
        if self.tracker and not self.dry_run and action_type in ["apply", "create"]:
            # Load YAML and track each resource
            with open(resolved_path, 'r') as f:
                documents = yaml.safe_load_all(f)
                for doc in documents:
                    if doc and isinstance(doc, dict):
                        # Get previous state if updating
                        previous_state = None
                        if action_type == "apply":
                            previous_state = self.tracker.get_resource_state(
                                api_version=doc.get("apiVersion", ""),
                                kind=doc.get("kind", ""),
                                name=doc.get("metadata", {}).get("name", ""),
                                namespace=doc.get("metadata", {}).get("namespace", namespace)
                            )
                        
                        # Determine action
                        resource_action = ResourceAction.CREATE if not previous_state else ResourceAction.UPDATE
                        
                        # Track resource
                        self.tracker.track_resource(
                            manifest=doc,
                            action=resource_action,
                            source_file=str(resolved_path),
                            previous_state=previous_state
                        )
        
        # kubectl 명령 구성
        kubectl_cmd = ["kubectl", action_type, "-f", str(resolved_path)]
        if namespace:
            kubectl_cmd.extend(["-n", namespace])
        if self.dry_run:
            kubectl_cmd.append("--dry-run=client")
            
        # 실행
        self.execute_command_with_logging(
            kubectl_cmd,
            error_msg=f"앱 '{app_info.name}': kubectl {action_type} 실패 (파일: {file_path})",
            success_msg=f"앱 '{app_info.name}': kubectl {action_type} 성공 (파일: {file_path})"
        )
        
    def _deploy_exec(self, app_info: AppInfoScheme, spec_obj: AppExecSpec):
        """Execute commands (no tracking for exec type)"""
        commands = spec_obj.commands
        if not commands:
            logger.warning(f"앱 '{app_info.name}': 실행할 명령이 없습니다.")
            return
            
        for cmd_str in commands:
            logger.info(f"앱 '{app_info.name}': 명령 실행 - {cmd_str}")
            
            try:
                # 쉘 명령으로 실행
                result = subprocess.run(
                    cmd_str,
                    shell=True,
                    cwd=self.base_dir,
                    capture_output=True,
                    text=True,
                    check=True
                )
                
                if result.stdout:
                    logger.verbose(f"명령 출력:\n{result.stdout}")
                    
                logger.success(f"앱 '{app_info.name}': 명령 실행 성공")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"앱 '{app_info.name}': 명령 실행 실패")
                if e.stderr:
                    logger.error(f"에러 출력:\n{e.stderr}")
                raise
    
    def _collect_helm_values(self, spec_obj: AppInstallHelmSpec) -> Dict[str, Any]:
        """Collect Helm values for tracking"""
        values_dict = {}
        
        for values_file in spec_obj.values:
            values_path = self.values_dir / values_file
            if values_path.exists():
                with open(values_path, 'r') as f:
                    file_values = yaml.safe_load(f)
                    if file_values:
                        values_dict.update(file_values)
        
        return values_dict
    
    def _is_helm_installed(self, release_name: str, namespace: Optional[str]) -> bool:
        """Helm 릴리스 설치 여부 확인"""
        try:
            installed_charts = get_installed_charts(namespace)
            return any(chart['name'] == release_name for chart in installed_charts)
        except Exception as e:
            logger.debug(f"Helm 릴리스 목록 조회 실패: {e}")
            return False
            
    def _build_helm_command(self, release_name: str, chart_dir: Path, 
                          namespace: Optional[str], spec_obj: AppInstallHelmSpec) -> list:
        """Helm install 명령 구성"""
        cmd = ["helm", "install", release_name, str(chart_dir)]
        
        if namespace:
            cmd.extend(["-n", namespace])
            
        # values 파일들 추가
        for values_file in spec_obj.values:
            values_path = self.values_dir / values_file
            if values_path.exists():
                cmd.extend(["-f", str(values_path)])
            else:
                logger.warning(f"Values 파일을 찾을 수 없습니다: {values_path}")
                
        if self.dry_run:
            cmd.append("--dry-run")
            
        return cmd
    
    def _resolve_yaml_path(self, app_info: AppInfoScheme, file_path: str) -> Optional[Path]:
        """YAML 파일 경로 해석"""
        # 절대 경로인 경우
        if Path(file_path).is_absolute():
            path = Path(file_path)
            if path.exists():
                return path
                
        # 빌드 디렉토리에서 찾기
        build_path = self.build_dir / app_info.name / file_path
        if build_path.exists():
            return build_path
            
        # 앱 설정 디렉토리에서 찾기
        config_path = self.app_config_dir / file_path
        if config_path.exists():
            return config_path
            
        # base_dir에서 찾기
        base_path = self.base_dir / file_path
        if base_path.exists():
            return base_path
            
        return None