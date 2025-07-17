import sys

import click

from sbkube.commands import build, deploy, prepare, template
from sbkube.exceptions import SbkubeError
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.common import common_click_options
from sbkube.utils.execution_tracker import ExecutionTracker
from sbkube.utils.logger import logger
from sbkube.utils.profile_manager import ProfileManager


class RunExecutionError(SbkubeError):
    """Run 명령어 실행 중 발생하는 오류"""

    def __init__(self, step: str, message: str, suggestions: list[str] = None):
        self.step = step
        self.suggestions = suggestions or []
        super().__init__(f"{step} 단계 실패: {message}")


class RunCommand(BaseCommand):
    """전체 워크플로우를 통합 실행하는 명령어"""

    def __init__(
        self,
        base_dir: str,
        app_config_dir: str,
        target_app_name: str | None = None,
        config_file_name: str | None = None,
        from_step: str | None = None,
        to_step: str | None = None,
        only_step: str | None = None,
        dry_run: bool = False,
        profile: str | None = None,
        continue_from: str | None = None,
        retry_failed: bool = False,
        resume: bool = False,
        show_progress: bool = True,
    ):
        super().__init__(
            base_dir,
            app_config_dir,
            target_app_name,
            config_file_name,
            show_progress=show_progress,
            profile=profile,
        )
        self.from_step = from_step
        self.to_step = to_step
        self.only_step = only_step
        self.dry_run = dry_run
        self.continue_from = continue_from
        self.retry_failed = retry_failed
        self.resume = resume
        self.tracker = ExecutionTracker(base_dir, profile)

    def execute(self):
        """실행 상태 추적이 통합된 실행"""
        # 프로파일 로딩
        if self.profile:
            self._load_profile()

        # 설정 로드
        config = self._load_config()

        if self.dry_run:
            steps = self._determine_steps()
            self._show_execution_plan(steps)
            return

        # 실행 상태 초기화
        force_new = not (self.resume or self.retry_failed or self.continue_from)
        execution_state = self.tracker.start_execution(config, force_new)

        # 시작 지점 결정
        start_step = self._determine_start_step(execution_state)

        # 실행할 단계 결정
        steps = self._determine_steps_with_tracking(start_step)

        logger.info(f"📋 실행할 단계: {' → '.join(steps)}")

        # 사전 작업 실행
        self.execute_pre_hook()

        # 단계 의존성 검증
        self._validate_step_dependencies(steps)

        # 진행률 추적 설정
        self.setup_progress_tracking(steps)

        try:
            # 진행률 표시 시작
            self.start_progress_display()

            for step in steps:
                # 진행률 추적과 실행 상태 추적을 모두 사용
                if self.progress_manager:
                    with self.progress_manager.track_step(step) as progress_tracker:
                        with self.tracker.track_step(step):
                            self._execute_step_with_progress(
                                step, config, progress_tracker
                            )
                else:
                    with self.tracker.track_step(step):
                        self._execute_step(step)

            self.tracker.complete_execution()
            logger.success("🎉 모든 단계가 성공적으로 완료되었습니다!")

        except Exception as e:
            logger.error(f"실행 실패: {e}")
            self._show_restart_options()
            raise

        finally:
            # 진행률 표시 종료
            self.stop_progress_display()

    def _execute_step(self, step_name: str):
        """개별 단계 실행 (오류 처리 강화)"""
        try:
            if step_name == "prepare":
                cmd = prepare.PrepareCommand(
                    self.base_dir,
                    self.app_config_dir,
                    self.target_app_name,
                    self.config_file_name,
                )
            elif step_name == "build":
                cmd = build.BuildCommand(
                    self.base_dir,
                    self.app_config_dir,
                    self.target_app_name,
                    self.config_file_name,
                )
            elif step_name == "template":
                cmd = template.TemplateCommand(
                    self.base_dir,
                    self.app_config_dir,
                    self.target_app_name,
                    self.config_file_name,
                )
            elif step_name == "deploy":
                cmd = deploy.DeployCommand(
                    self.base_dir,
                    self.app_config_dir,
                    self.target_app_name,
                    self.config_file_name,
                )
            else:
                raise ValueError(f"Unknown step: {step_name}")

            cmd.execute()

        except Exception as e:
            # 단계별 세부 오류 정보 추가
            detailed_error = self._enhance_error_message(step_name, e)
            raise type(e)(detailed_error) from e

    def _execute_step_with_progress(self, step: str, config: dict, tracker):
        """진행률 추적과 함께 단계 실행"""

        if step == "prepare":
            self._execute_prepare_with_progress(config, tracker)
        elif step == "build":
            self._execute_build_with_progress(config, tracker)
        elif step == "template":
            self._execute_template_with_progress(config, tracker)
        elif step == "deploy":
            self._execute_deploy_with_progress(config, tracker)

    def _execute_prepare_with_progress(self, config: dict, tracker):
        """준비 단계 (진행률 포함)"""
        tracker.update(10, "설정 파일 검증 중...")
        time.sleep(0.2)  # 시각적 효과

        tracker.update(30, "의존성 확인 중...")
        # 실제 prepare 명령 실행
        cmd = prepare.PrepareCommand(
            self.base_dir,
            self.app_config_dir,
            self.target_app_name,
            self.config_file_name,
        )
        cmd.execute()

        tracker.update(100, "준비 완료")

    def _execute_build_with_progress(self, config: dict, tracker):
        """빌드 단계 (진행률 포함)"""
        tracker.update(10, "빌드 환경 준비 중...")
        time.sleep(0.2)

        tracker.update(30, "앱 빌드 시작...")
        # 실제 build 명령 실행
        cmd = build.BuildCommand(
            self.base_dir,
            self.app_config_dir,
            self.target_app_name,
            self.config_file_name,
        )
        cmd.execute()

        tracker.update(100, "빌드 완료")

    def _execute_template_with_progress(self, config: dict, tracker):
        """템플릿 단계 (진행률 포함)"""
        tracker.update(20, "템플릿 엔진 초기화...")
        time.sleep(0.2)

        tracker.update(50, "템플릿 렌더링 중...")
        # 실제 template 명령 실행
        cmd = template.TemplateCommand(
            self.base_dir,
            self.app_config_dir,
            self.target_app_name,
            self.config_file_name,
        )
        cmd.execute()

        tracker.update(100, "템플릿 처리 완료")

    def _execute_deploy_with_progress(self, config: dict, tracker):
        """배포 단계 (진행률 포함)"""
        tracker.update(10, "배포 환경 확인...")
        time.sleep(0.2)

        tracker.update(30, "리소스 배포 중...")
        # 실제 deploy 명령 실행
        cmd = deploy.DeployCommand(
            self.base_dir,
            self.app_config_dir,
            self.target_app_name,
            self.config_file_name,
        )
        cmd.execute()

        tracker.update(100, "배포 완료")

    def _determine_steps(self) -> list[str]:
        """실행할 단계들을 결정"""
        all_steps = ["prepare", "build", "template", "deploy"]

        # --only 옵션이 있으면 해당 단계만 실행
        if self.only_step:
            if self.only_step not in all_steps:
                raise ValueError(f"Invalid step: {self.only_step}")
            return [self.only_step]

        # 시작/종료 단계 결정
        start_index = 0
        end_index = len(all_steps)

        if self.from_step:
            if self.from_step not in all_steps:
                raise ValueError(f"Invalid from-step: {self.from_step}")
            start_index = all_steps.index(self.from_step)

        if self.to_step:
            if self.to_step not in all_steps:
                raise ValueError(f"Invalid to-step: {self.to_step}")
            end_index = all_steps.index(self.to_step) + 1

        if start_index >= end_index:
            raise ValueError("from-step must come before to-step")

        return all_steps[start_index:end_index]

    def _determine_steps_with_tracking(self, start_step: str | None) -> list[str]:
        """상태 추적을 고려한 단계 결정"""
        steps = ["prepare", "build", "template", "deploy"]

        if self.only_step:
            return [self.only_step]

        if start_step:
            # 시작 지점부터 실행
            start_index = steps.index(start_step) if start_step in steps else 0
            steps = steps[start_index:]

        # from_step, to_step 적용
        if self.from_step:
            from_index = steps.index(self.from_step) if self.from_step in steps else 0
            steps = steps[from_index:]

        if self.to_step:
            to_index = (
                steps.index(self.to_step) + 1 if self.to_step in steps else len(steps)
            )
            steps = steps[:to_index]

        return steps

    def _determine_start_step(self, execution_state) -> str | None:
        """시작 단계 결정"""
        if self.continue_from:
            return self.continue_from

        if self.retry_failed:
            restart_point = self.tracker.get_restart_point()
            if restart_point:
                logger.info(f"🔄 실패한 단계부터 재시작: {restart_point}")
                return restart_point

        if self.resume:
            if self.tracker.can_resume():
                restart_point = self.tracker.get_restart_point()
                if restart_point:
                    logger.info(f"🔄 중단된 지점부터 재시작: {restart_point}")
                    return restart_point
            else:
                logger.info("재시작할 수 있는 실행이 없습니다. 새로 시작합니다.")

        return None

    def _load_config(self) -> dict:
        """설정 로드"""
        # 기본 설정 로드 로직 구현
        config = {"namespace": "default", "apps": []}

        # 프로파일이 있는 경우 프로파일 설정 로드
        if self.profile:
            try:
                profile_manager = ProfileManager(self.base_dir, self.app_config_dir)
                profile_config = profile_manager.load_profile(self.profile)
                config.update(profile_config)
            except Exception as e:
                logger.warning(f"프로파일 로딩 실패: {e}")

        return config

    def _show_restart_options(self):
        """재시작 옵션 안내"""
        if self.tracker.can_resume():
            restart_point = self.tracker.get_restart_point()
            logger.info("\n💡 재시작 옵션:")
            logger.info("   sbkube run --retry-failed  # 실패한 단계부터 재시작")
            logger.info(
                f"   sbkube run --continue-from {restart_point}  # {restart_point} 단계부터 재시작"
            )
            logger.info("   sbkube run --resume  # 자동으로 재시작 지점 탐지")

    def _validate_step_dependencies(self, steps: list[str]):
        """단계별 의존성 확인"""
        dependencies = {
            "build": ["prepare"],
            "template": ["prepare", "build"],
            "deploy": ["prepare", "build", "template"],
        }

        for step in steps:
            if step in dependencies:
                missing_deps = []
                for dep in dependencies[step]:
                    if dep not in steps and not self._is_step_completed(dep):
                        missing_deps.append(dep)

                if missing_deps:
                    logger.warning(
                        f"⚠️  {step} 단계 실행 전에 다음 단계가 필요합니다: {', '.join(missing_deps)}"
                    )

    def _is_step_completed(self, step: str) -> bool:
        """단계 완료 여부 확인 (추후 상태 관리 시스템과 연동)"""
        # 현재는 기본적으로 False 반환
        # Phase 2에서 상태 추적 시스템과 연동
        return False

    def _handle_step_failure(
        self, step: str, error: Exception, current_step: int, total_steps: int
    ):
        """단계별 실패 처리"""
        logger.error(f"❌ {step.title()} 단계 실패 ({current_step}/{total_steps})")
        logger.error(f"오류 내용: {error}")

        # 진행 상황 표시
        progress = "█" * (current_step - 1) + "❌" + "░" * (total_steps - current_step)
        logger.info(f"진행 상황: {progress} {current_step - 1}/{total_steps} 완료")

        # 실패한 단계 정보 저장 (Phase 2에서 재시작 기능과 연동)
        self._save_failure_state(step, error)

    def _enhance_error_message(self, step: str, error: Exception) -> str:
        """단계별 오류 메시지 강화"""
        base_message = str(error)

        # 단계별 컨텍스트 정보 추가
        if step == "prepare":
            return f"소스 준비 중 오류 발생: {base_message}"
        elif step == "build":
            return f"앱 빌드 중 오류 발생: {base_message}"
        elif step == "template":
            return f"템플릿 렌더링 중 오류 발생: {base_message}"
        elif step == "deploy":
            return f"배포 중 오류 발생: {base_message}"
        else:
            return base_message

    def _get_failure_suggestions(self, step: str, error: Exception) -> list[str]:
        """단계별 실패 시 해결 방법 제안"""
        suggestions = []
        error_msg = str(error).lower()

        if step == "prepare":
            suggestions.extend(
                [
                    "sources.yaml 파일에서 저장소 설정을 확인하세요",
                    "네트워크 연결 상태를 확인하세요",
                ]
            )
            if "not found" in error_msg:
                suggestions.append("저장소 URL이 올바른지 확인하세요")
            if "permission" in error_msg:
                suggestions.append("저장소 접근 권한을 확인하세요")

        elif step == "build":
            suggestions.extend(
                [
                    "config.yaml 파일의 앱 설정을 확인하세요",
                    "필요한 소스 파일들이 존재하는지 확인하세요",
                ]
            )
            if "file not found" in error_msg:
                suggestions.append("prepare 단계가 정상적으로 완료되었는지 확인하세요")

        elif step == "template":
            suggestions.extend(
                [
                    "Helm 차트 문법을 확인하세요",
                    "values 파일의 형식을 확인하세요",
                ]
            )
            if "yaml" in error_msg:
                suggestions.append("YAML 파일 문법 오류를 확인하세요")

        elif step == "deploy":
            suggestions.extend(
                [
                    "Kubernetes 클러스터 연결을 확인하세요",
                    "네임스페이스가 존재하는지 확인하세요",
                    "권한 설정을 확인하세요",
                ]
            )
            if "namespace" in error_msg:
                suggestions.append(
                    "kubectl create namespace <namespace-name>으로 네임스페이스를 생성하세요"
                )
            if "permission" in error_msg:
                suggestions.append("kubectl 권한 설정을 확인하세요")

        # 공통 제안사항
        suggestions.extend(
            [
                f"sbkube run --from-step {step}로 해당 단계부터 재시작하세요",
                "sbkube validate로 설정 파일을 검증하세요",
                "-v 옵션으로 상세 로그를 확인하세요",
            ]
        )

        return suggestions

    def _save_failure_state(self, step: str, error: Exception):
        """실패 상태 저장 (Phase 2 재시작 기능과 연동)"""
        # 현재는 로그로만 기록, Phase 2에서 파일 저장으로 확장
        logger.debug(f"실패 상태 기록: {step} - {error}")

    def _load_profile(self):
        """프로파일 기반 설정 로드"""
        try:
            profile_manager = ProfileManager(self.base_dir, self.app_config_dir)

            if self.profile not in profile_manager.available_profiles:
                available = ", ".join(profile_manager.available_profiles)
                raise ValueError(
                    f"프로파일 '{self.profile}'을 찾을 수 없습니다. 사용 가능한 프로파일: {available}"
                )

            logger.info(f"🔄 프로파일 '{self.profile}' 로딩 중...")

            # 프로파일 검증
            validation = profile_manager.validate_profile(self.profile)
            if not validation["valid"]:
                error_msg = ", ".join(validation["errors"])
                raise ValueError(f"프로파일 '{self.profile}' 검증 실패: {error_msg}")

            if validation["warnings"]:
                for warning in validation["warnings"]:
                    logger.warning(f"⚠️  프로파일 경고: {warning}")

            # 프로파일 로드 및 적용
            profile_config = profile_manager.load_profile(self.profile)

            # 기본 설정 파일 경로 업데이트 (프로파일 설정으로 오버라이드)
            if not self.config_file_name:
                self.config_file_name = f"config-{self.profile}.yaml"

            logger.success(f"✅ 프로파일 '{self.profile}' 로딩 완료")
            logger.info(
                f"   네임스페이스: {profile_config.get('namespace', 'default')}"
            )
            logger.info(f"   앱 개수: {len(profile_config.get('apps', []))}")

        except Exception as e:
            logger.error(f"❌ 프로파일 로딩 실패: {e}")
            raise RunExecutionError(
                "profile",
                str(e),
                [
                    f"프로파일 설정 파일 'config-{self.profile}.yaml'이 존재하는지 확인하세요",
                    "sbkube validate로 설정 파일을 검증하세요",
                    "사용 가능한 프로파일을 확인하려면 'ls config/config-*.yaml' 명령어를 실행하세요",
                ],
            )

    def _show_execution_plan(self, steps: list[str]):
        """실행 계획 표시 (dry-run 모드)"""
        from rich.console import Console
        from rich.table import Table

        console = Console()
        table = Table(title="🔍 실행 계획 (Dry Run)")
        table.add_column("순서", style="cyan", width=6)
        table.add_column("단계", style="magenta", width=12)
        table.add_column("설명", style="white")
        table.add_column("예상 시간", style="green", width=10)

        step_descriptions = {
            "prepare": "외부 소스 다운로드 (Helm 차트, Git 리포지토리 등)",
            "build": "앱 빌드 및 로컬 파일 복사",
            "template": "Helm 차트 템플릿 렌더링",
            "deploy": "Kubernetes 클러스터에 배포",
        }

        estimated_times = {
            "prepare": "1-3분",
            "build": "1-2분",
            "template": "30초",
            "deploy": "2-5분",
        }

        for i, step in enumerate(steps, 1):
            table.add_row(
                str(i),
                step.title(),
                step_descriptions.get(step, ""),
                estimated_times.get(step, "?"),
            )

        console.print(table)
        console.print("\n💡 실제 실행: [bold cyan]sbkube run[/bold cyan]")
        console.print(
            f"💡 특정 단계부터: [bold cyan]sbkube run --from-step {steps[0]}[/bold cyan]"
        )


@click.command(name="run")
@common_click_options
@click.option(
    "--from-step",
    type=click.Choice(["prepare", "build", "template", "deploy"]),
    help="시작할 단계 지정",
)
@click.option(
    "--to-step",
    type=click.Choice(["prepare", "build", "template", "deploy"]),
    help="종료할 단계 지정",
)
@click.option(
    "--only",
    type=click.Choice(["prepare", "build", "template", "deploy"]),
    help="특정 단계만 실행",
)
@click.option("--dry-run", is_flag=True, help="실제 실행 없이 계획만 표시")
@click.option(
    "--profile", help="사용할 환경 프로파일 (예: development, staging, production)"
)
@click.option(
    "--continue-from",
    type=click.Choice(["prepare", "build", "template", "deploy"]),
    help="지정한 단계부터 재시작",
)
@click.option("--retry-failed", is_flag=True, help="실패한 단계부터 자동 재시작")
@click.option("--resume", is_flag=True, help="중단된 지점부터 자동 재시작")
@click.option("--no-progress", is_flag=True, help="진행률 표시 비활성화")
@click.pass_context
def cmd(
    ctx,
    app_dir,
    base_dir,
    config_file,
    app,
    verbose,
    debug,
    from_step,
    to_step,
    only,
    dry_run,
    profile,
    continue_from,
    retry_failed,
    resume,
    no_progress,
):
    """전체 워크플로우를 통합 실행합니다.

    prepare → build → template → deploy 단계를 순차적으로 실행하며,
    각 단계별 진행 상황을 실시간으로 표시합니다.

    \b
    기본 사용법:
        sbkube run                                  # 전체 워크플로우 실행
        sbkube run --app web-frontend               # 특정 앱만 실행
        sbkube run --dry-run                        # 실행 계획만 표시

    \b
    단계별 실행 제어:
        sbkube run --from-step template             # template부터 실행
        sbkube run --to-step build                  # build까지만 실행
        sbkube run --only template                  # template만 실행
        sbkube run --from-step build --to-step template  # build와 template만

    \b
    환경 설정:
        sbkube run --profile production            # 프로덕션 환경 프로파일
        sbkube run --profile development           # 개발 환경 프로파일
        sbkube run --app-dir production             # 다른 설정 디렉토리
        sbkube run --config-file prod-config.yaml  # 다른 설정 파일

    \b
    문제 해결:
        sbkube run --from-step <단계>               # 실패한 단계부터 재시작
        sbkube validate                             # 설정 파일 검증
        sbkube run -v                               # 상세 로그 출력
    """
    # 옵션 충돌 검사
    if only and (from_step or to_step):
        logger.error("--only 옵션은 --from-step, --to-step과 함께 사용할 수 없습니다.")
        sys.exit(1)

    command = RunCommand(
        base_dir=base_dir,
        app_config_dir=app_dir,
        target_app_name=app,
        config_file_name=config_file,
        from_step=from_step,
        to_step=to_step,
        only_step=only,
        dry_run=dry_run,
        profile=profile,
        continue_from=continue_from,
        retry_failed=retry_failed,
        resume=resume,
        show_progress=not no_progress,
    )

    try:
        command.execute()
        logger.success("🎉 모든 단계가 성공적으로 완료되었습니다!")

    except RunExecutionError as e:
        logger.error(f"\n{e}")

        if e.suggestions:
            logger.info("\n💡 다음 해결 방법을 시도해보세요:")
            for i, suggestion in enumerate(e.suggestions, 1):
                logger.info(f"   {i}. {suggestion}")

        logger.info(f"\n🔄 재시작 방법: sbkube run --from-step {e.step}")
        sys.exit(1)

    except ValueError as e:
        logger.error(f"❌ 옵션 오류: {e}")
        logger.info("💡 sbkube run --help로 사용법을 확인하세요")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\n⏹️  사용자에 의해 중단되었습니다")
        sys.exit(130)

    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류가 발생했습니다: {e}")
        logger.info("💡 다음 방법을 시도해보세요:")
        logger.info("   1. -v 옵션으로 상세 로그를 확인하세요")
        logger.info("   2. GitHub Issues에 버그를 신고하세요")
        logger.info("   3. sbkube validate로 설정을 검증하세요")
        sys.exit(1)
