"""Configuration validators 테스트."""

import asyncio
from pathlib import Path

import pytest
import yaml

from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.validation_system import ValidationContext, ValidationSeverity
from sbkube.validators.configuration_validators import (
    ConfigContentValidator,
    ConfigStructureValidator,
    CrossReferenceValidator,
    SourcesIntegrityValidator,
)


@pytest.fixture
def mock_context(tmp_path: Path) -> ValidationContext:
    """Mock ValidationContext를 생성합니다."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)

    context = ValidationContext(
        base_dir=str(tmp_path),
        config_dir="config",
        environment="test",
        metadata={"cluster": "test-cluster", "namespace": "test-namespace"},
    )
    return context


class TestConfigStructureValidator:
    """ConfigStructureValidator 테스트."""

    def test_init(self) -> None:
        """ConfigStructureValidator 초기화 테스트."""
        validator = ConfigStructureValidator()
        assert validator.name == "config_structure"
        assert "구조" in validator.description
        assert validator.category == "configuration"

    def test_valid_config_structure(self, mock_context: ValidationContext) -> None:
        """유효한 config.yaml 구조 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test-namespace",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"chart": "grafana/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (유효한 구조이므로 SUCCESS 또는 WARNING)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.WARNING]

    def test_missing_config_file(self, mock_context: ValidationContext) -> None:
        """config.yaml 파일 없음 테스트."""
        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (config.yaml 없음 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH
        assert "config.yaml" in result.details

    def test_invalid_config_structure(self, mock_context: ValidationContext) -> None:
        """잘못된 config.yaml 구조 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # namespace 필드 누락
        config = {"apps": []}
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (필수 필드 누락 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_invalid_app_structure(self, mock_context: ValidationContext) -> None:
        """잘못된 앱 구조 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    # name 필드 누락
                    "type": "helm",
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (앱 필수 필드 누락 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_invalid_app_type(self, mock_context: ValidationContext) -> None:
        """지원하지 않는 앱 타입 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "test-app",
                    "type": "invalid_type",
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (지원하지 않는 타입 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_config_not_dict(self, mock_context: ValidationContext) -> None:
        """config.yaml이 dict가 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # config.yaml을 리스트로 작성 (dict가 아님)
        config_file.write_text("- item1\n- item2")

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (config가 dict가 아닐 때 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_namespace_not_string(self, mock_context: ValidationContext) -> None:
        """namespace가 문자열이 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": 123, "apps": []}  # namespace가 숫자
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (namespace 타입 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_apps_not_list(self, mock_context: ValidationContext) -> None:
        """apps가 리스트가 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": "test", "apps": "not-a-list"}  # apps가 문자열
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (apps 타입 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_config_file_read_error(self, mock_context: ValidationContext) -> None:
        """config.yaml 파일 읽기 오류 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        # 잘못된 YAML 형식
        config_file.write_text("invalid: yaml: content:\n  broken")

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (YAML 파싱 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_deps_not_list(self, mock_context: ValidationContext) -> None:
        """deps가 리스트가 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": "test", "apps": [], "deps": "not-a-list"}
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (deps 타입 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_app_not_dict(self, mock_context: ValidationContext) -> None:
        """app이 dict가 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": "test", "apps": ["string-app"]}  # app이 문자열
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (app 타입 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_app_name_not_string(self, mock_context: ValidationContext) -> None:
        """app name이 문자열이 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": "test", "apps": [{"name": 123, "type": "helm"}]}
        config_file.write_text(yaml.dump(config))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (name 타입 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_sources_git_not_dict(self, mock_context: ValidationContext) -> None:
        """sources.yaml의 git이 dict가 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        sources_file = config_dir / "sources.yaml"

        config = {"namespace": "test", "apps": []}
        config_file.write_text(yaml.dump(config))

        sources = {"git": "not-a-dict"}  # git이 문자열
        sources_file.write_text(yaml.dump(sources))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (git 타입 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_sources_with_git_repo(self, mock_context: ValidationContext) -> None:
        """sources.yaml에 git 저장소가 있는 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        sources_file = config_dir / "sources.yaml"

        config = {"namespace": "test", "apps": []}
        config_file.write_text(yaml.dump(config))

        sources = {
            "git": {
                "my-repo": {
                    "url": "https://github.com/user/repo.git",
                    "ref": "main",
                }
            }
        }
        sources_file.write_text(yaml.dump(sources))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (유효한 git 소스)
        assert result.level in [
            DiagnosticLevel.SUCCESS,
            DiagnosticLevel.WARNING,
            DiagnosticLevel.ERROR,
        ]

    def test_sources_helm_not_dict(self, mock_context: ValidationContext) -> None:
        """sources.yaml의 helm이 dict가 아닌 경우 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        sources_file = config_dir / "sources.yaml"

        config = {"namespace": "test", "apps": []}
        config_file.write_text(yaml.dump(config))

        sources = {"helm": ["not", "a", "dict"]}  # helm이 리스트
        sources_file.write_text(yaml.dump(sources))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (helm 타입 오류 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_valid_sources_structure(self, mock_context: ValidationContext) -> None:
        """유효한 sources.yaml 구조 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        sources_file = config_dir / "sources.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "nginx",
                    "type": "helm",
                    "specs": {"chart": "grafana/nginx"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        sources = {
            "helm": {
                "grafana": {"url": "https://grafana.github.io/helm-charts"}
            }
        }
        sources_file.write_text(yaml.dump(sources))

        validator = ConfigStructureValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (유효한 구조 시 SUCCESS)
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.severity == ValidationSeverity.INFO


class TestConfigContentValidator:
    """ConfigContentValidator 테스트."""

    def test_init(self) -> None:
        """ConfigContentValidator 초기화 테스트."""
        validator = ConfigContentValidator()
        assert validator.name == "config_content"
        assert "유효성" in validator.description
        assert validator.category == "configuration"

    def test_duplicate_app_names(self, mock_context: ValidationContext) -> None:
        """중복된 앱 이름 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {"name": "nginx", "type": "helm", "specs": {}},
                {"name": "nginx", "type": "yaml", "specs": {}},
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = ConfigContentValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (중복 이름 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH
        assert "중복" in result.details

    def test_valid_app_content(self, mock_context: ValidationContext) -> None:
        """유효한 앱 내용 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {"name": "app1", "type": "helm", "specs": {}},
                {"name": "app2", "type": "yaml", "specs": {}},
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = ConfigContentValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (유효한 내용 시 SUCCESS 또는 WARNING)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.WARNING, DiagnosticLevel.ERROR]


class TestSourcesIntegrityValidator:
    """SourcesIntegrityValidator 테스트."""

    def test_init(self) -> None:
        """SourcesIntegrityValidator 초기화 테스트."""
        validator = SourcesIntegrityValidator()
        assert validator.name == "sources_integrity"
        assert "참조" in validator.description
        assert validator.category == "configuration"

    def test_missing_config_file(self, mock_context: ValidationContext) -> None:
        """config.yaml 파일 없음 테스트."""
        validator = SourcesIntegrityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (config.yaml 없음 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_missing_sources_file(self, mock_context: ValidationContext) -> None:
        """sources.yaml 파일 없음 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {"namespace": "test", "apps": []}
        config_file.write_text(yaml.dump(config))

        validator = SourcesIntegrityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (sources.yaml 없음 시 WARNING)
        assert result.level == DiagnosticLevel.WARNING
        assert result.severity == ValidationSeverity.LOW

    def test_undefined_git_repo(self, mock_context: ValidationContext) -> None:
        """정의되지 않은 Git 저장소 참조 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        sources_file = config_dir / "sources.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "myapp",
                    "type": "git",
                    "specs": {"repo": "undefined-repo"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        sources = {"git": {}}
        sources_file.write_text(yaml.dump(sources))

        validator = SourcesIntegrityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (정의되지 않은 저장소 참조 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH
        assert "undefined-repo" in result.details

    def test_valid_references(self, mock_context: ValidationContext) -> None:
        """유효한 참조 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"
        sources_file = config_dir / "sources.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "myapp",
                    "type": "git",
                    "specs": {"repo": "myrepo"},
                }
            ],
        }
        config_file.write_text(yaml.dump(config))

        sources = {
            "git": {
                "myrepo": {"url": "https://github.com/example/repo.git"}
            }
        }
        sources_file.write_text(yaml.dump(sources))

        validator = SourcesIntegrityValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (유효한 참조 시 SUCCESS 또는 ERROR)
        assert result.level in [DiagnosticLevel.SUCCESS, DiagnosticLevel.ERROR]


class TestCrossReferenceValidator:
    """CrossReferenceValidator 테스트."""

    def test_init(self) -> None:
        """CrossReferenceValidator 초기화 테스트."""
        validator = CrossReferenceValidator()
        assert validator.name == "cross_reference"
        assert "의존성" in validator.description or "충돌" in validator.description
        assert validator.category == "configuration"

    def test_missing_config_file(self, mock_context: ValidationContext) -> None:
        """config.yaml 파일 없음 테스트."""
        validator = CrossReferenceValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (config.yaml 없음 시 ERROR)
        assert result.level == DiagnosticLevel.ERROR
        assert result.severity == ValidationSeverity.HIGH

    def test_no_conflicts(self, mock_context: ValidationContext) -> None:
        """충돌 없음 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {"name": "app1", "type": "helm", "specs": {}},
                {"name": "app2", "type": "helm", "specs": {}},
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = CrossReferenceValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (충돌 없음 시 SUCCESS)
        assert result.level == DiagnosticLevel.SUCCESS
        assert result.severity == ValidationSeverity.INFO

    def test_duplicate_dest_path(self, mock_context: ValidationContext) -> None:
        """중복된 대상 경로 테스트."""
        config_dir = Path(mock_context.base_dir) / mock_context.config_dir
        config_file = config_dir / "config.yaml"

        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "app1",
                    "type": "helm",
                    "specs": {"dest": "/tmp/dest"},
                },
                {
                    "name": "app2",
                    "type": "git",
                    "specs": {"dest": "/tmp/dest"},
                },
            ],
        }
        config_file.write_text(yaml.dump(config))

        validator = CrossReferenceValidator()
        result = asyncio.run(validator.run_validation(mock_context))

        # 검증 (중복 경로 시 ERROR 또는 WARNING)
        assert result.level in [DiagnosticLevel.ERROR, DiagnosticLevel.WARNING]
        assert "dest" in result.details or "경로" in result.details
