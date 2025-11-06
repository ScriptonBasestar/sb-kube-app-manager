"""
Tests for output formatter utility.
"""

import json
import os

import pytest

from sbkube.utils.output_formatter import (
    OutputFormat,
    OutputFormatter,
    get_output_format_from_context,
)


class TestOutputFormat:
    """Test OutputFormat enum."""

    def test_enum_values(self):
        """Test that all expected format values exist."""
        assert OutputFormat.HUMAN == "human"
        assert OutputFormat.LLM == "llm"
        assert OutputFormat.JSON == "json"
        assert OutputFormat.YAML == "yaml"


class TestOutputFormatter:
    """Test OutputFormatter class."""

    def test_init_with_string(self):
        """Test initialization with string format."""
        formatter = OutputFormatter("llm")
        assert formatter.format == OutputFormat.LLM

    def test_init_with_enum(self):
        """Test initialization with enum format."""
        formatter = OutputFormatter(OutputFormat.JSON)
        assert formatter.format == OutputFormat.JSON

    def test_from_env_or_cli_with_cli_option(self):
        """Test format selection with CLI option (highest priority)."""
        formatter = OutputFormatter.from_env_or_cli(cli_format="json")
        assert formatter.format == OutputFormat.JSON

    def test_from_env_or_cli_with_env_var(self, monkeypatch):
        """Test format selection with environment variable."""
        monkeypatch.setenv("SBKUBE_OUTPUT_FORMAT", "llm")
        formatter = OutputFormatter.from_env_or_cli()
        assert formatter.format == OutputFormat.LLM

    def test_from_env_or_cli_cli_overrides_env(self, monkeypatch):
        """Test that CLI option overrides environment variable."""
        monkeypatch.setenv("SBKUBE_OUTPUT_FORMAT", "json")
        formatter = OutputFormatter.from_env_or_cli(cli_format="yaml")
        assert formatter.format == OutputFormat.YAML

    def test_from_env_or_cli_default(self):
        """Test default format when no options provided."""
        # Ensure env var is not set
        if "SBKUBE_OUTPUT_FORMAT" in os.environ:
            del os.environ["SBKUBE_OUTPUT_FORMAT"]
        formatter = OutputFormatter.from_env_or_cli()
        assert formatter.format == OutputFormat.HUMAN

    def test_from_env_or_cli_invalid_format(self):
        """Test fallback to human format for invalid format string."""
        formatter = OutputFormatter.from_env_or_cli(cli_format="invalid")
        assert formatter.format == OutputFormat.HUMAN


class TestFormatDeploymentResult:
    """Test deployment result formatting."""

    @pytest.fixture
    def sample_data(self):
        """Sample deployment data."""
        return {
            "status": "success",
            "summary": {
                "charts_deployed": 3,
                "duration_seconds": 12.5,
                "timestamp": "2025-01-03T12:34:56Z",
            },
            "deployments": [
                {
                    "name": "nginx-app",
                    "namespace": "default",
                    "status": "running",
                    "version": "1.25.0",
                },
                {
                    "name": "postgres-db",
                    "namespace": "database",
                    "status": "running",
                    "version": "15.0",
                },
                {
                    "name": "redis-cache",
                    "namespace": "cache",
                    "status": "running",
                    "version": "7.2",
                },
            ],
            "next_steps": [
                "kubectl get pods -n default",
                "kubectl get pods -n database",
            ],
            "errors": [],
        }

    def test_format_llm(self, sample_data):
        """Test LLM format output."""
        formatter = OutputFormatter(OutputFormat.LLM)
        result = formatter.format_deployment_result(
            status=sample_data["status"],
            summary=sample_data["summary"],
            deployments=sample_data["deployments"],
            next_steps=sample_data["next_steps"],
            errors=sample_data["errors"],
        )

        assert isinstance(result, str)
        assert "STATUS: success ✅" in result
        assert "DEPLOYED: 3 charts in 12.5s" in result
        assert "APPLICATIONS:" in result
        assert "nginx-app (default): running v1.25.0" in result
        assert "postgres-db (database): running v15.0" in result
        assert "NEXT STEPS:" in result
        assert "kubectl get pods -n default" in result
        assert "ERRORS: none" in result

    def test_format_llm_with_errors(self, sample_data):
        """Test LLM format output with errors."""
        formatter = OutputFormatter(OutputFormat.LLM)
        sample_data["status"] = "failed"
        sample_data["errors"] = [
            "Database connection failed",
            "Timeout waiting for pod",
        ]

        result = formatter.format_deployment_result(
            status=sample_data["status"],
            summary=sample_data["summary"],
            deployments=sample_data["deployments"],
            next_steps=sample_data["next_steps"],
            errors=sample_data["errors"],
        )

        assert "STATUS: failed ❌" in result
        assert "ERRORS:" in result
        assert "- Database connection failed" in result
        assert "- Timeout waiting for pod" in result

    def test_format_json(self, sample_data):
        """Test JSON format output."""
        formatter = OutputFormatter(OutputFormat.JSON)
        result = formatter.format_deployment_result(
            status=sample_data["status"],
            summary=sample_data["summary"],
            deployments=sample_data["deployments"],
            next_steps=sample_data["next_steps"],
            errors=sample_data["errors"],
        )

        # Parse JSON to verify structure
        parsed = json.loads(result)
        assert parsed["status"] == "success"
        assert parsed["summary"]["charts_deployed"] == 3
        assert len(parsed["deployments"]) == 3
        assert parsed["deployments"][0]["name"] == "nginx-app"
        assert len(parsed["next_steps"]) == 2
        assert parsed["errors"] == []

    def test_format_yaml(self, sample_data):
        """Test YAML format output."""
        formatter = OutputFormatter(OutputFormat.YAML)
        result = formatter.format_deployment_result(
            status=sample_data["status"],
            summary=sample_data["summary"],
            deployments=sample_data["deployments"],
            next_steps=sample_data["next_steps"],
            errors=sample_data["errors"],
        )

        # Basic YAML structure check
        assert isinstance(result, str)
        assert "status:" in result or "status: success" in result
        assert "deployments:" in result
        assert "nginx-app" in result


class TestGetOutputFormatFromContext:
    """Test get_output_format_from_context helper."""

    def test_from_context_params(self):
        """Test extracting format from Click context params."""

        class MockContext:
            params = {"format": "llm"}

        result = get_output_format_from_context(MockContext())
        assert result == OutputFormat.LLM

    def test_from_context_no_params(self):
        """Test default format when context has no params."""

        class MockContext:
            pass

        result = get_output_format_from_context(MockContext())
        assert result == OutputFormat.HUMAN

    def test_from_env_variable(self, monkeypatch):
        """Test extracting format from environment variable."""
        monkeypatch.setenv("SBKUBE_OUTPUT_FORMAT", "json")

        class MockContext:
            params = {}

        result = get_output_format_from_context(MockContext())
        assert result == OutputFormat.JSON


class TestPrintOutput:
    """Test print_output method."""

    def test_print_string_output(self, capsys):
        """Test printing string output."""
        formatter = OutputFormatter(OutputFormat.LLM)
        formatter.print_output("STATUS: success ✅")

        captured = capsys.readouterr()
        assert "STATUS: success ✅" in captured.out

    def test_print_dict_output_json(self, capsys):
        """Test printing dict as JSON."""
        formatter = OutputFormatter(OutputFormat.JSON)
        data = {"status": "success", "count": 3}
        formatter.print_output(data)

        captured = capsys.readouterr()
        assert '"status": "success"' in captured.out
        assert '"count": 3' in captured.out
