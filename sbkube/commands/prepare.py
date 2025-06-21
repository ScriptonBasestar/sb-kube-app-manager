import json
import subprocess
import shutil
from pathlib import Path
import click
from shutil import which
from typing import Optional

# config_model 임포트
from sbkube.models.config_model import (
    AppInfoScheme,
    AppPullHelmSpec,
    AppPullHelmOciSpec,
    AppPullGitSpec,
    # TODO: 다른 App Spec 모델들도 필요에 따라 임포트
)
from sbkube.utils.common import common_click_options
from sbkube.utils.file_loader import load_config_file
# sbkube.utils.cli_check 임포트는 check_helm_installed_or_exit 만 사용
from sbkube.utils.cli_check import check_helm_installed, CliToolNotFoundError, CliToolExecutionError
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.logger import logger, setup_logging_from_context, LogLevel
from sbkube.utils.cmd_executor import run_helm_cmd_with_retry, run_git_cmd_with_retry
from sbkube.exceptions import HelmError, GitRepositoryError

def check_command_available(command):
    if which(command) is None:
        logger.warning(f"'{command}' 명령을 찾을 수 없습니다. PATH에 등록되어 있는지 확인하세요.")
        return False
    try:
        result = subprocess.run([command, "--help"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            return False
        return True
    except Exception:
        return False

class PrepareCommand(BaseCommand):
    """Prepare 명령 구현"""
    
    def __init__(self, base_dir: str, app_config_dir: str, sources_file: str, 
                 target_app_name: Optional[str], config_file_name: Optional[str]):
        super().__init__(base_dir, app_config_dir, None, config_file_name)
        self.sources_file = sources_file
        self.target_app_name = target_app_name
        
    def execute(self):
        """prepare 명령 실행"""
        self.execute_pre_hook()
        logger.heading("Prepare 시작")
        
        # 지원하는 앱 타입
        supported_types = ["pull-helm", "pull-helm-oci", "pull-git"]
        
        # 앱 파싱
        self.parse_apps(app_types=supported_types, app_name=self.target_app_name)
        
        # 필요한 CLI 도구들 체크 (공통 함수 사용)
        if self.app_info_list:
            self.check_required_cli_tools()
        
        # 앱 처리 (공통 로직 사용)
        self.process_apps_with_stats(self._prepare_app, "준비")
        
    def _prepare_app(self, app_info: AppInfoScheme) -> bool:
        """개별 앱 준비"""
        app_name = app_info.name
        app_type = app_info.type
        
        logger.progress(f"앱 '{app_name}' (타입: {app_type}) 준비 시작...")
        
        try:
            # Spec 모델 생성 (공통 함수 사용)
            spec_obj = self.create_app_spec(app_info)
            if not spec_obj:
                return False
                
            # 타입별 준비 처리
            if app_type in ["pull-helm", "pull-helm-oci"]:
                self._prepare_helm(app_info, spec_obj)
            elif app_type == "pull-git":
                self._prepare_git(app_info, spec_obj)
                
            logger.success(f"앱 '{app_name}' 준비 완료")
            return True
            
        except Exception as e:
            logger.error(f"앱 '{app_name}' 준비 중 예상치 못한 오류: {e}")
            if logger._level.value <= LogLevel.DEBUG.value:
                import traceback
                logger.debug(traceback.format_exc())
            return False

    def _prepare_helm(self, app_info: AppInfoScheme, spec_obj):
        """Helm 차트 준비"""
        logger.info(f"Helm 차트 준비: {app_info.name}")
        
        if isinstance(spec_obj, AppPullHelmSpec):
            # 일반 Helm 저장소에서 차트 pull
            repo_name = spec_obj.repo
            chart_name = spec_obj.chart
            version = spec_obj.version
            dest_dir = spec_obj.dest or chart_name
            
            # charts 디렉토리 생성
            charts_dir = self.base_dir / "charts"
            charts_dir.mkdir(exist_ok=True)
            
            dest_path = charts_dir / dest_dir
            
            # sources.yaml에서 repo URL 찾기
            sources_path = self.base_dir / self.sources_file
            if sources_path.exists():
                sources_data = load_config_file(sources_path)
                helm_repos = sources_data.get('helm_repos', {})
                
                if repo_name in helm_repos:
                    repo_url = helm_repos[repo_name]
                    
                    # helm repo add (with retry)
                    try:
                        if not run_helm_cmd_with_retry(['helm', 'repo', 'add', repo_name, repo_url]):
                            # Check if repo already exists
                            result = subprocess.run(['helm', 'repo', 'list'], 
                                                   capture_output=True, text=True)
                            if repo_name not in result.stdout:
                                logger.warning(f"Helm 저장소 '{repo_name}' 추가 실패")
                            else:
                                logger.info(f"Helm 저장소 '{repo_name}' 이미 존재함")
                        else:
                            logger.info(f"Helm 저장소 '{repo_name}' 추가됨")
                    except Exception as e:
                        logger.warning(f"Helm 저장소 추가 중 오류: {e}")
                    
                    # helm repo update (with retry)
                    try:
                        if run_helm_cmd_with_retry(['helm', 'repo', 'update']):
                            logger.info("Helm 저장소 업데이트 완료")
                        else:
                            logger.warning("Helm 저장소 업데이트 실패")
                    except Exception as e:
                        logger.warning(f"Helm 저장소 업데이트 중 오류: {e}")
                    
                    # helm pull (with retry)
                    pull_cmd = ['helm', 'pull', f"{repo_name}/{chart_name}"]
                    if version:
                        pull_cmd.extend(['--version', version])
                    pull_cmd.extend(['--untar', '--untardir', str(charts_dir)])
                    if dest_dir != chart_name:
                        pull_cmd.extend(['--destination', str(dest_path)])
                    
                    try:
                        if run_helm_cmd_with_retry(pull_cmd):
                            logger.success(f"Helm 차트 '{chart_name}' 다운로드 완료: {dest_path}")
                        else:
                            logger.error(f"Helm 차트 '{chart_name}' 다운로드 실패")
                            raise HelmError(f"Failed to download Helm chart '{chart_name}'")
                    except Exception as e:
                        logger.error(f"Helm 차트 다운로드 중 오류: {e}")
                        return False
                else:
                    logger.error(f"sources.yaml에서 저장소 '{repo_name}'을 찾을 수 없습니다.")
                    return False
            else:
                logger.error(f"sources 파일을 찾을 수 없습니다: {sources_path}")
                return False
                
        elif isinstance(spec_obj, AppPullHelmOciSpec):
            # OCI 저장소에서 차트 pull
            oci_url = spec_obj.oci_url
            version = spec_obj.version
            dest_dir = spec_obj.dest
            
            charts_dir = self.base_dir / "charts"
            charts_dir.mkdir(exist_ok=True)
            
            pull_cmd = ['helm', 'pull', oci_url]
            if version:
                pull_cmd.extend(['--version', version])
            pull_cmd.extend(['--untar', '--untardir', str(charts_dir)])
            
            try:
                if run_helm_cmd_with_retry(pull_cmd):
                    logger.success(f"OCI Helm 차트 다운로드 완료: {oci_url}")
                else:
                    logger.error(f"OCI Helm 차트 다운로드 실패: {oci_url}")
                    raise HelmError(f"Failed to download OCI Helm chart from '{oci_url}'")
            except Exception as e:
                logger.error(f"OCI Helm 차트 다운로드 중 오류: {e}")
                return False
        
        return True
    
    def _prepare_git(self, app_info: AppInfoScheme, spec_obj):
        """Git 저장소 준비"""
        logger.info(f"Git 저장소 준비: {app_info.name}")
        
        if isinstance(spec_obj, AppPullGitSpec):
            repo_name = spec_obj.repo
            paths = spec_obj.paths or []
            
            # sources.yaml에서 git repo 정보 찾기
            sources_path = self.base_dir / self.sources_file
            if sources_path.exists():
                sources_data = load_config_file(sources_path)
                git_repos = sources_data.get('git_repos', {})
                
                if repo_name in git_repos:
                    repo_info = git_repos[repo_name]
                    repo_url = repo_info.get('url')
                    branch = repo_info.get('branch', 'main')
                    
                    # repos 디렉토리 생성
                    repos_dir = self.base_dir / "repos"
                    repos_dir.mkdir(exist_ok=True)
                    
                    repo_dir = repos_dir / repo_name
                    
                    # git clone 또는 pull (with retry)
                    if repo_dir.exists():
                        # 기존 저장소 업데이트
                        try:
                            if run_git_cmd_with_retry(['git', 'pull'], cwd=repo_dir):
                                logger.info(f"Git 저장소 '{repo_name}' 업데이트 완료")
                            else:
                                logger.warning(f"Git 저장소 '{repo_name}' 업데이트 실패")
                        except Exception as e:
                            logger.warning(f"Git 저장소 업데이트 중 오류: {e}")
                    else:
                        # 새로 clone
                        clone_cmd = ['git', 'clone', repo_url, str(repo_dir)]
                        if branch != 'main':
                            clone_cmd.extend(['-b', branch])
                        
                        try:
                            if run_git_cmd_with_retry(clone_cmd):
                                logger.success(f"Git 저장소 '{repo_name}' 클론 완료: {repo_dir}")
                            else:
                                logger.error(f"Git 저장소 '{repo_name}' 클론 실패")
                                raise GitRepositoryError(repo_url, "clone", f"Failed to clone repository '{repo_name}'")
                        except Exception as e:
                            logger.error(f"Git 저장소 클론 중 오류: {e}")
                            return False
                    
                    # 지정된 경로들 복사
                    for path_spec in paths:
                        src_path = repo_dir / path_spec.get('src', '.')
                        dest_path = self.app_config_dir / path_spec.get('dest', '.')
                        
                        if src_path.exists():
                            dest_path.parent.mkdir(parents=True, exist_ok=True)
                            if src_path.is_dir():
                                shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
                            else:
                                shutil.copy2(src_path, dest_path)
                            logger.info(f"복사 완료: {src_path} -> {dest_path}")
                        else:
                            logger.warning(f"소스 경로를 찾을 수 없습니다: {src_path}")
                else:
                    logger.error(f"sources.yaml에서 Git 저장소 '{repo_name}'을 찾을 수 없습니다.")
                    return False
            else:
                logger.error(f"sources 파일을 찾을 수 없습니다: {sources_path}")
                return False
        
        return True

    def _check_required_tools(self):
        """준비할 앱들에 필요한 CLI 도구들 체크"""
        needs_helm = any(app.type in ["pull-helm", "pull-helm-oci"] for app in self.app_info_list)
        needs_git = any(app.type == "pull-git" for app in self.app_info_list)
        
        if needs_helm:
            try:
                check_helm_installed()
            except (CliToolNotFoundError, CliToolExecutionError):
                raise click.Abort()
                
        if needs_git:
            if not check_command_available("git"):
                logger.error("git 명령이 필요하지만 사용할 수 없습니다.")
                raise click.Abort()

@click.command(name="prepare")
@common_click_options
@click.option("--sources", "sources_file", default="sources.yaml", help="소스 설정 파일")
@click.option("--sources-file", "sources_override", default=None, help="소스 설정 파일 경로(테스트 호환)")
@click.pass_context
def cmd(ctx, app_config_dir_name, base_dir, config_file_name, app_name, verbose, debug, sources_file, sources_override):
    ctx.ensure_object(dict)
    ctx.obj['verbose'] = verbose
    ctx.obj['debug'] = debug
    setup_logging_from_context(ctx)
    
    cmd = PrepareCommand(
        base_dir=base_dir,
        app_config_dir=app_config_dir_name,
        sources_file=sources_file,
        target_app_name=app_name,
        config_file_name=config_file_name
    )
    cmd.execute()
