"""
공통 패턴 테스트

리팩토링된 코드의 일관성과 공통 기능을 테스트합니다.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.models.config_model import AppInfoScheme
from sbkube.utils.base_command import BaseCommand
from sbkube.utils.cli_check import CliToolExecutionError, CliToolNotFoundError
from sbkube.utils.logger import LogLevel, SbkubeLogger, logger


class TestLogger:
    """로거 시스템 테스트"""

    def test_log_levels(self):
        """로그 레벨 테스트"""
        test_logger = SbkubeLogger()

        # 각 레벨 테스트
        assert test_logger._level == LogLevel.INFO

        test_logger.set_level(LogLevel.DEBUG)
        assert test_logger._level == LogLevel.DEBUG

        test_logger.set_level(LogLevel.VERBOSE)
        assert test_logger._level == LogLevel.VERBOSE

    def test_log_level_filtering(self):
        """로그 레벨 필터링 테스트"""
        test_logger = SbkubeLogger()
        test_logger.set_level(LogLevel.WARNING)

        # WARNING 레벨에서는 DEBUG, VERBOSE, INFO가 출력되지 않아야 함
        assert test_logger._level > LogLevel.DEBUG
        assert test_logger._level > LogLevel.VERBOSE
        assert test_logger._level > LogLevel.INFO


class TestBaseCommand:
    """BaseCommand 클래스 테스트"""

    def test_initialization(self, tmp_path):
        """초기화 테스트"""
        base_cmd = BaseCommand(
            base_dir=str(tmp_path), app_config_dir="config", cli_namespace="test-ns"
        )

        assert base_cmd.base_dir == tmp_path
        assert base_cmd.app_config_dir == tmp_path / "config"
        assert base_cmd.cli_namespace == "test-ns"
        assert base_cmd.build_dir == tmp_path / "config" / "build"

    def test_find_config_file(self):
        """설정 파일 찾기 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            app_config_dir = base_dir / "config"
            app_config_dir.mkdir(exist_ok=True)

            # config.yaml 파일 생성
            config_file = app_config_dir / "config.yaml"
            config_file.write_text("apps: []")

            cmd = BaseCommand(str(base_dir), "config")
            found_file = cmd.find_config_file()

            assert found_file.name == config_file.name
            assert found_file.exists()

    def test_find_config_file_priority(self):
        """설정 파일 우선순위 테스트 (yaml > yml > toml)"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            app_config_dir = base_dir / "config"
            app_config_dir.mkdir(exist_ok=True)

            # 여러 설정 파일 생성
            (app_config_dir / "config.yml").write_text("apps: []")
            (app_config_dir / "config.yaml").write_text("apps: []")

            cmd = BaseCommand(str(base_dir), "config")
            found_file = cmd.find_config_file()

            # .yaml이 우선순위가 높음
            assert found_file.name == "config.yaml"

    def test_namespace_priority(self, tmp_path):
        """네임스페이스 우선순위 테스트"""
        base_cmd = BaseCommand(
            base_dir=str(tmp_path), app_config_dir="config", cli_namespace="cli-ns"
        )

        # CLI 네임스페이스가 최우선
        app_info = AppInfoScheme(
            name="test-app", type="install-helm", namespace="app-ns", specs={}
        )

        assert base_cmd.get_namespace(app_info) == "cli-ns"

        # CLI 없으면 앱 네임스페이스
        base_cmd.cli_namespace = None
        assert base_cmd.get_namespace(app_info) == "app-ns"

        # 특수값은 무시
        app_info.namespace = "!ignore"
        assert base_cmd.get_namespace(app_info) is None

    def test_parse_apps_filtering(self, tmp_path):
        """앱 필터링 테스트"""
        base_cmd = BaseCommand(str(tmp_path), "config")
        base_cmd.apps_config_dict = {
            "apps": [
                {"name": "helm-app", "type": "install-helm", "specs": {"values": []}},
                {"name": "yaml-app", "type": "install-yaml", "specs": {"actions": []}},
                {"name": "exec-app", "type": "exec", "specs": {"commands": []}},
            ]
        }

        # 특정 타입만 필터링
        apps = base_cmd.parse_apps(app_types=["install-helm"])
        assert len(apps) == 1
        assert apps[0].name == "helm-app"

        # 특정 앱 이름 필터링
        apps = base_cmd.parse_apps(app_name="yaml-app")
        assert len(apps) == 1
        assert apps[0].name == "yaml-app"

        # 타입과 이름 조합
        apps = base_cmd.parse_apps(app_types=["exec"], app_name="exec-app")
        assert len(apps) == 1
        assert apps[0].type == "exec"


class TestCommandConsistency:
    """명령어 간 일관성 테스트"""

    def test_common_options(self):
        """공통 옵션 확인"""
        from sbkube.commands import build, deploy

        # 모든 명령어가 verbose와 debug 옵션을 가져야 함
        deploy_params = [p.name for p in deploy.cmd.params]
        build_params = [p.name for p in build.cmd.params]

        assert "verbose" in deploy_params
        assert "debug" in deploy_params
        assert "verbose" in build_params
        assert "debug" in build_params

    def test_error_handling_patterns(self):
        """에러 처리 패턴 일관성 테스트"""
        with tempfile.TemporaryDirectory() as temp_dir:
            base_dir = Path(temp_dir)
            app_config_dir = base_dir / "config"
            app_config_dir.mkdir()

            # 잘못된 설정 파일 생성
            config_file = app_config_dir / "config.yaml"
            config_file.write_text("invalid: yaml: content:")

            cmd = BaseCommand(str(base_dir), "config")

            # 설정 파일 로드 시 예외 발생 확인
            with pytest.raises(Exception):
                cmd.load_config()


class TestPathResolution:
    """경로 해석 테스트"""

    def test_absolute_vs_relative_paths(self, tmp_path):
        """절대 경로 vs 상대 경로 처리"""
        base_cmd = BaseCommand(str(tmp_path), "config")

        # 디렉토리 생성
        base_cmd.ensure_directory(base_cmd.build_dir, "빌드 디렉토리")
        assert base_cmd.build_dir.exists()

        # 디렉토리 정리
        test_file = base_cmd.build_dir / "test.txt"
        test_file.write_text("test")

        base_cmd.clean_directory(base_cmd.build_dir, "빌드 디렉토리")
        assert base_cmd.build_dir.exists()
        assert not test_file.exists()  # 내용은 삭제됨


class TestCliToolMocking:
    """CLI 도구 모킹 패턴 테스트"""

    def test_helm_check_mocking(self):
        """helm 체크 모킹 테스트"""
        from sbkube.utils.cli_check import check_helm_installed

        # helm이 없는 경우
        with patch("sbkube.utils.cli_check.shutil.which", return_value=None):
            with pytest.raises(CliToolNotFoundError):
                check_helm_installed()

        # helm이 있지만 실행 실패하는 경우
        with (
            patch("sbkube.utils.cli_check.shutil.which", return_value="/usr/bin/helm"),
            patch("sbkube.utils.cli_check.subprocess.run") as mock_run,
        ):
            from subprocess import CalledProcessError

            mock_run.side_effect = CalledProcessError(1, ["helm", "version"])
            with pytest.raises(CliToolExecutionError):
                check_helm_installed()

        # helm이 정상 동작하는 경우
        with (
            patch("sbkube.utils.cli_check.shutil.which", return_value="/usr/bin/helm"),
            patch("sbkube.utils.cli_check.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.stdout = 'version.BuildInfo{Version:"v3.18.0"}'
            mock_run.return_value = mock_result

            # 예외가 발생하지 않아야 함
            check_helm_installed()

    def test_kubectl_check_mocking(self):
        """kubectl 체크 모킹 테스트"""
        from sbkube.utils.cli_check import check_kubectl_installed

        # kubectl이 없는 경우
        with patch("sbkube.utils.cli_check.shutil.which", return_value=None):
            with pytest.raises(CliToolNotFoundError):
                check_kubectl_installed()

        # kubectl이 정상 동작하는 경우
        with (
            patch(
                "sbkube.utils.cli_check.shutil.which", return_value="/usr/bin/kubectl"
            ),
            patch("sbkube.utils.cli_check.subprocess.run") as mock_run,
        ):
            mock_result = MagicMock()
            mock_result.stdout = "Client Version: v1.28.0"
            mock_run.return_value = mock_result

            # 예외가 발생하지 않아야 함
            check_kubectl_installed()


class TestExampleIntegration:
    """Examples 디렉토리와의 통합 테스트"""

    def test_example_config_loading(self):
        """examples 디렉토리의 설정 파일 로딩 테스트"""
        examples_dir = Path(__file__).parent.parent / "examples"

        # k3scode 예제가 있는지 확인
        k3scode_dir = examples_dir / "k3scode"
        if not k3scode_dir.exists():
            pytest.skip("k3scode 예제 디렉토리가 없습니다")

        config_files = list(k3scode_dir.glob("config*.y*ml"))
        if not config_files:
            pytest.skip("k3scode 예제에 설정 파일이 없습니다")

        # 첫 번째 설정 파일로 테스트
        config_file = config_files[0]

        cmd = BaseCommand(str(k3scode_dir), ".", None, config_file.name)

        # 설정 파일 로드가 성공해야 함
        config_data = cmd.load_config()
        assert isinstance(config_data, dict)
        assert "apps" in config_data or len(config_data) > 0


class TestLoggerIntegration:
    """Logger 통합 테스트"""

    def test_logger_levels(self):
        """로거 레벨 테스트"""
        # 다양한 로그 레벨 테스트
        logger.debug("Debug message")
        logger.verbose("Verbose message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.success("Success message")
        logger.progress("Progress message")
        logger.command("command --test")
        logger.heading("Test Heading")

        # 예외가 발생하지 않으면 성공
        assert True


# 테스트용 헬퍼 함수들
def create_mock_config(apps_data):
    """테스트용 설정 데이터 생성"""
    return {"apps": apps_data, "namespace": "test-namespace"}


def create_mock_app(name, app_type, specs=None):
    """테스트용 앱 데이터 생성"""
    return {"name": name, "type": app_type, "specs": specs or {}}


def mock_helm_success():
    """helm 명령 성공 모킹"""
    return (
        patch("sbkube.utils.cli_check.shutil.which", return_value="/usr/bin/helm"),
        patch("sbkube.utils.cli_check.subprocess.run"),
    )


def mock_kubectl_success():
    """kubectl 명령 성공 모킹"""
    return (
        patch("sbkube.utils.cli_check.shutil.which", return_value="/usr/bin/kubectl"),
        patch("sbkube.utils.cli_check.subprocess.run"),
    )


def mock_subprocess_success(stdout="", stderr="", returncode=0):
    """subprocess 성공 모킹"""
    mock_result = MagicMock()
    mock_result.stdout = stdout
    mock_result.stderr = stderr
    mock_result.returncode = returncode
    return mock_result
