"""Tests for migrate command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from sbkube.commands.migrate import (
    _clean_app_dict,
    _clean_nested_dict,
    _clean_settings_dict,
    cmd,
)


@pytest.fixture
def runner() -> CliRunner:
    """Click test runner."""
    return CliRunner()


class TestMigrateCommand:
    """migrate 명령어 테스트."""

    def test_help(self, runner: CliRunner) -> None:
        """--help 테스트."""
        result = runner.invoke(cmd, ["--help"])

        assert result.exit_code == 0
        assert "Migrate legacy configuration" in result.output
        assert "--dry-run" in result.output
        assert "--source-dir" in result.output

    def test_no_config_found(self, runner: CliRunner, tmp_path: Path) -> None:
        """설정 파일이 없을 때 테스트."""
        result = runner.invoke(cmd, ["-s", str(tmp_path)])

        assert result.exit_code != 0
        assert "No legacy configuration" in result.output or "Aborted" in result.output

    def test_already_unified(self, runner: CliRunner, tmp_path: Path) -> None:
        """이미 unified 형식일 때 테스트."""
        sbkube_yaml = tmp_path / "sbkube.yaml"
        sbkube_yaml.write_text("""
apiVersion: sbkube/v1
settings:
  namespace: test
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
""")

        result = runner.invoke(cmd, ["-s", str(tmp_path)])

        assert result.exit_code == 0
        assert "Already using unified config" in result.output

    def test_migrate_legacy_dry_run(self, runner: CliRunner, tmp_path: Path) -> None:
        """Legacy 형식 dry-run 마이그레이션 테스트."""
        sources_yaml = tmp_path / "sources.yaml"
        sources_yaml.write_text("""
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
""")

        config_yaml = tmp_path / "config.yaml"
        config_yaml.write_text("""
namespace: test-ns
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
    version: "15.0.0"
""")

        result = runner.invoke(cmd, ["-s", str(tmp_path), "--dry-run"])

        assert result.exit_code == 0
        assert "Migration Preview" in result.output
        assert "apiVersion: sbkube/v1" in result.output
        assert "nginx:" in result.output
        assert "Would write to" in result.output

    def test_migrate_workspace_dry_run(self, runner: CliRunner, tmp_path: Path) -> None:
        """Workspace 형식 dry-run 마이그레이션 테스트."""
        workspace_yaml = tmp_path / "workspace.yaml"
        workspace_yaml.write_text("""
version: "1.0"
metadata:
  name: test-workspace
  environment: dev
global:
  timeout: 600
phases:
  p1-infra:
    description: Infrastructure
    source: p1/sources.yaml
    app_groups:
      - infra-apps
""")

        result = runner.invoke(cmd, ["-s", str(tmp_path), "--dry-run"])

        assert result.exit_code == 0
        assert "Migration Preview" in result.output
        assert "apiVersion: sbkube/v1" in result.output
        assert "test-workspace" in result.output
        assert "p1-infra:" in result.output

    def test_migrate_output_file(self, runner: CliRunner, tmp_path: Path) -> None:
        """실제 파일 출력 테스트."""
        sources_yaml = tmp_path / "sources.yaml"
        sources_yaml.write_text("""
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
""")

        config_yaml = tmp_path / "config.yaml"
        config_yaml.write_text("""
namespace: test-ns
apps:
  nginx:
    type: helm
    chart: bitnami/nginx
""")

        output_path = tmp_path / "output" / "sbkube.yaml"
        result = runner.invoke(cmd, ["-s", str(tmp_path), "-o", str(output_path)])

        # Debug output
        if result.exit_code != 0:
            print(f"DEBUG: {result.output}")

        assert result.exit_code == 0
        assert "Migration complete" in result.output
        assert output_path.exists()

        content = output_path.read_text()
        assert "apiVersion: sbkube/v1" in content
        assert "nginx:" in content

    def test_migrate_no_overwrite(self, runner: CliRunner, tmp_path: Path) -> None:
        """기존 파일 덮어쓰기 방지 테스트."""
        # Create source directory with legacy config
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        sources_yaml = source_dir / "sources.yaml"
        sources_yaml.write_text("kubeconfig: ~/.kube/config\nkubeconfig_context: test")

        # Create existing output file
        output_path = tmp_path / "output.yaml"
        output_path.write_text("existing content")

        result = runner.invoke(cmd, ["-s", str(source_dir), "-o", str(output_path)])

        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_migrate_force_overwrite(self, runner: CliRunner, tmp_path: Path) -> None:
        """--force 덮어쓰기 테스트."""
        # Create source directory with legacy config
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        sources_yaml = source_dir / "sources.yaml"
        sources_yaml.write_text("kubeconfig: ~/.kube/config\nkubeconfig_context: test")

        # Create existing output file
        output_path = tmp_path / "output.yaml"
        output_path.write_text("existing content")

        result = runner.invoke(cmd, ["-s", str(source_dir), "-o", str(output_path), "--force"])

        assert result.exit_code == 0
        assert "Migration complete" in result.output

        content = output_path.read_text()
        assert "apiVersion: sbkube/v1" in content


class TestCleanSettingsDict:
    """_clean_settings_dict 테스트."""

    def test_removes_none_values(self) -> None:
        """None 값 제거 테스트."""
        settings = {"kubeconfig": None, "namespace": "test"}
        result = _clean_settings_dict(settings)

        assert "kubeconfig" not in result
        assert result["namespace"] == "test"

    def test_removes_default_values(self) -> None:
        """기본값 제거 테스트."""
        settings = {
            "namespace": "default",  # Default
            "timeout": 300,  # Not default
        }
        result = _clean_settings_dict(settings)

        assert "namespace" not in result
        assert result["timeout"] == 300

    def test_removes_empty_collections(self) -> None:
        """빈 컬렉션 제거 테스트."""
        settings = {
            "helm_repos": {},
            "incompatible_charts": [],
            "namespace": "test",
        }
        result = _clean_settings_dict(settings)

        assert "helm_repos" not in result
        assert "incompatible_charts" not in result
        assert result["namespace"] == "test"


class TestCleanAppDict:
    """_clean_app_dict 테스트."""

    def test_removes_enabled_true(self) -> None:
        """enabled=True 제거 테스트."""
        app = {"type": "helm", "chart": "test", "enabled": True}
        result = _clean_app_dict(app)

        assert "enabled" not in result
        assert result["chart"] == "test"

    def test_keeps_enabled_false(self) -> None:
        """enabled=False 유지 테스트."""
        app = {"type": "helm", "chart": "test", "enabled": False}
        result = _clean_app_dict(app)

        assert result["enabled"] is False

    def test_removes_helm_defaults(self) -> None:
        """Helm 기본값 제거 테스트."""
        app = {
            "type": "helm",
            "chart": "test",
            "create_namespace": False,  # Default
            "wait": True,  # Default
            "atomic": False,  # Default
        }
        result = _clean_app_dict(app)

        assert "create_namespace" not in result
        assert "wait" not in result
        assert "atomic" not in result


class TestCleanNestedDict:
    """_clean_nested_dict 테스트."""

    def test_removes_none_values(self) -> None:
        """None 값 제거 테스트."""
        d = {"url": "https://example.com", "username": None}
        result = _clean_nested_dict(d)

        assert result == {"url": "https://example.com"}

    def test_removes_empty_nested(self) -> None:
        """빈 중첩 딕셔너리 제거 테스트."""
        d = {"valid": "value", "empty": {}}
        result = _clean_nested_dict(d)

        assert "empty" not in result
        assert result["valid"] == "value"

    def test_recursive_cleaning(self) -> None:
        """재귀적 정리 테스트."""
        d = {
            "level1": {
                "level2": {
                    "value": "test",
                    "none_value": None,
                }
            }
        }
        result = _clean_nested_dict(d)

        assert result == {"level1": {"level2": {"value": "test"}}}
