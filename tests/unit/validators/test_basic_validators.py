"""Basic validators 테스트."""

import asyncio
from pathlib import Path

import pytest

from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.validation_system import ValidationContext, ValidationSeverity
from sbkube.validators.basic_validators import (
    BasicSystemValidator,
    ConfigSyntaxValidator,
    FileExistenceValidator,
)


@pytest.fixture
def mock_context(tmp_path: Path) -> ValidationContext:
    """Mock ValidationContext를 생성합니다."""
    # config 디렉토리 생성
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    # ValidationContext 생성
    context = ValidationContext(
        base_dir=str(tmp_path),
        config_dir="config",
        environment="test",
        metadata={"cluster": "test-cluster", "namespace": "test-namespace"},
    )
    return context


class TestFileExistenceValidator:
    """FileExistenceValidator 테스트."""

    def test_init(self) -> None:
        """FileExistenceValidator 초기화 테스트."""
        validator = FileExistenceValidator()
        assert validator.name == "file_existence"
        assert validator.description == "필수 설정 파일 존재성 확인"
        assert validator.category == "configuration"

    def test_validation_success_when_all_files_exist(
        self, mock_context: ValidationContext
    ) -> None:
        """모든 필수 파일이 존재할 때 성공 테스트."""
        validator = FileExistenceValidator()

        # 필수 파일 생성
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        (config_dir / "config.yaml").write_text("test: config")
        (config_dir / "sources.yaml").write_text("test: sources")

        # 검증 실행
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.severity == ValidationSeverity.INFO
        assert "모든 필수 설정 파일이 존재합니다" in result.message

    def test_validation_failure_when_files_missing(
        self, mock_context: ValidationContext
    ) -> None:
        """필수 파일이 없을 때 실패 테스트."""
        validator = FileExistenceValidator()

        # 필수 파일 생성하지 않음
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH
        assert "필수 설정 파일이 누락되었습니다" in result.message
        assert "config.yaml" in result.message or "sources.yaml" in result.message
        assert result.fix_command == "sbkube init"

    def test_validation_failure_when_one_file_missing(
        self, mock_context: ValidationContext
    ) -> None:
        """하나의 필수 파일만 없을 때 실패 테스트."""
        validator = FileExistenceValidator()

        # config.yaml만 생성
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        (config_dir / "config.yaml").write_text("test: config")

        # 검증 실행
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH
        assert "sources.yaml" in result.message


class TestConfigSyntaxValidator:
    """ConfigSyntaxValidator 테스트."""

    def test_init(self) -> None:
        """ConfigSyntaxValidator 초기화 테스트."""
        validator = ConfigSyntaxValidator()
        assert validator.name == "config_syntax"
        assert validator.description == "설정 파일 YAML 문법 확인"
        assert validator.category == "configuration"

    def test_validation_success_with_valid_yaml(
        self, mock_context: ValidationContext
    ) -> None:
        """유효한 YAML 파일들이 있을 때 성공 테스트."""
        validator = ConfigSyntaxValidator()

        # 유효한 YAML 파일 생성
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        (config_dir / "config.yaml").write_text("namespace: test\napps: {}")
        (config_dir / "sources.yaml").write_text("cluster: test")

        # 검증 실행
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.severity == ValidationSeverity.INFO
        assert "모든 설정 파일의 YAML 문법이 정상입니다" in result.message

    def test_validation_failure_with_invalid_yaml(
        self, mock_context: ValidationContext
    ) -> None:
        """잘못된 YAML 파일이 있을 때 실패 테스트."""
        validator = ConfigSyntaxValidator()

        # 잘못된 YAML 파일 생성
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        (config_dir / "config.yaml").write_text("invalid: yaml: syntax: :")
        (config_dir / "sources.yaml").write_text("cluster: test")

        # 검증 실행
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH
        assert "YAML 문법 오류가 발견되었습니다" in result.message

    def test_validation_warning_with_no_files(
        self, mock_context: ValidationContext
    ) -> None:
        """설정 파일이 하나도 없을 때 경고 테스트."""
        validator = ConfigSyntaxValidator()

        # 파일 생성하지 않음
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.WARNING
        assert result.severity == ValidationSeverity.MEDIUM
        assert "검증할 설정 파일이 없습니다" in result.message

    def test_validation_with_one_valid_file(
        self, mock_context: ValidationContext
    ) -> None:
        """하나의 유효한 파일만 있을 때 성공 테스트."""
        validator = ConfigSyntaxValidator()

        # config.yaml만 생성
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        (config_dir / "config.yaml").write_text("namespace: test")

        # 검증 실행
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.SUCCESS
        assert "config.yaml" in result.details


class TestBasicSystemValidator:
    """BasicSystemValidator 테스트."""

    def test_init(self) -> None:
        """BasicSystemValidator 초기화 테스트."""
        validator = BasicSystemValidator()
        assert validator.name == "basic_system"
        assert validator.description == "기본 시스템 요구사항 확인"
        assert validator.category == "environment"

    def test_validation_success_with_proper_permissions(
        self, mock_context: ValidationContext
    ) -> None:
        """적절한 권한이 있을 때 성공 테스트."""
        validator = BasicSystemValidator()

        # tmp_path는 기본적으로 쓰기 권한 있음
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.severity == ValidationSeverity.INFO
        assert "기본 시스템 요구사항을 충족합니다" in result.message

    def test_validation_success_creates_sbkube_dir(
        self, mock_context: ValidationContext
    ) -> None:
        """검증 중 .sbkube 디렉토리가 생성되는지 확인."""
        validator = BasicSystemValidator()

        sbkube_dir = Path(mock_context.base_dir) / ".sbkube"
        assert not sbkube_dir.exists()

        # 검증 실행
        result = asyncio.run(validator.run_validation(mock_context))

        # .sbkube 디렉토리가 생성되었는지 확인
        assert sbkube_dir.exists()
        assert result.level == DiagnosticLevel.SUCCESS

    def test_validation_cleans_up_test_file(
        self, mock_context: ValidationContext
    ) -> None:
        """검증 후 테스트 파일이 정리되는지 확인."""
        validator = BasicSystemValidator()

        test_file = Path(mock_context.base_dir) / ".sbkube_test_write"

        # 검증 실행
        asyncio.run(validator.run_validation(mock_context))

        # 테스트 파일이 삭제되었는지 확인
        assert not test_file.exists()


@pytest.mark.integration
class TestValidatorsIntegration:
    """Validators 통합 테스트."""

    def test_all_validators_run_successfully(
        self, mock_context: ValidationContext
    ) -> None:
        """모든 validators를 순차적으로 실행하는 통합 테스트."""
        # 필수 파일 생성
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        (config_dir / "config.yaml").write_text("namespace: test\napps: {}")
        (config_dir / "sources.yaml").write_text("cluster: test")

        # 모든 validators 생성
        validators = [
            FileExistenceValidator(),
            ConfigSyntaxValidator(),
            BasicSystemValidator(),
        ]

        # 모든 validators 실행
        results = []
        for validator in validators:
            result = asyncio.run(validator.run_validation(mock_context))
            results.append(result)

        # 모든 검증이 성공해야 함
        for result in results:
            assert result.level == DiagnosticLevel.SUCCESS

    def test_validators_fail_with_incomplete_setup(
        self, mock_context: ValidationContext
    ) -> None:
        """불완전한 설정으로 validators 실패 테스트."""
        # 파일을 생성하지 않음

        validators = [
            FileExistenceValidator(),
            ConfigSyntaxValidator(),
            BasicSystemValidator(),
        ]

        results = []
        for validator in validators:
            result = asyncio.run(validator.run_validation(mock_context))
            results.append(result)

        # FileExistenceValidator는 실패해야 함
        assert results[0].level == DiagnosticLevel.ERROR

        # ConfigSyntaxValidator는 경고를 반환해야 함
        assert results[1].level == DiagnosticLevel.WARNING

        # BasicSystemValidator는 성공해야 함 (권한은 정상)
        assert results[2].level == DiagnosticLevel.SUCCESS
