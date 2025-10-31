"""Test CLI help command output and categorization."""

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def cli_runner():
    """Provide a Click CLI test runner."""
    return CliRunner()


def test_help_command_categorization(cli_runner):
    """Test that commands are properly categorized in help output."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # Check all categories are present
    assert "🔄 핵심 워크플로우" in result.output
    assert "⚡ 통합 명령어" in result.output
    assert "📊 상태 관리" in result.output
    assert "🔧 업그레이드/삭제" in result.output
    assert "🛠️ 유틸리티" in result.output


def test_help_core_workflow_commands(cli_runner):
    """Test that core workflow commands are listed."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # Core workflow commands
    assert "prepare" in result.output
    assert "build" in result.output
    assert "template" in result.output
    assert "deploy" in result.output


def test_help_integrated_command(cli_runner):
    """Test that integrated command (apply) is listed."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "apply" in result.output


def test_help_state_management_commands(cli_runner):
    """Test that state management commands are listed."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # State management commands
    assert "status" in result.output
    assert "history" in result.output
    assert "rollback" in result.output


def test_help_lifecycle_commands(cli_runner):
    """Test that lifecycle commands (upgrade/delete) are listed."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # Lifecycle commands
    assert "upgrade" in result.output
    assert "delete" in result.output


def test_help_utility_commands(cli_runner):
    """Test that utility commands are listed."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # Utility commands
    assert "init" in result.output
    assert "validate" in result.output
    assert "doctor" in result.output
    assert "version" in result.output


def test_help_no_uncategorized_section(cli_runner):
    """Test that there are no uncategorized commands."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # No "기타" (uncategorized) section should exist
    assert "기타:" not in result.output


def test_help_command_completeness(cli_runner):
    """Test that all expected commands are present in help output."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # All 14 commands should be present
    expected_commands = [
        "prepare",
        "build",
        "template",
        "deploy",
        "apply",
        "status",
        "history",
        "rollback",
        "upgrade",
        "delete",
        "init",
        "validate",
        "doctor",
        "version",
    ]

    for cmd in expected_commands:
        assert cmd in result.output, f"Command '{cmd}' not found in help output"


def test_help_options_present(cli_runner):
    """Test that global options are present in help output."""
    result = cli_runner.invoke(main, ["--help"])

    assert result.exit_code == 0

    # Check global options
    assert "--kubeconfig" in result.output
    assert "--context" in result.output
    assert "--source" in result.output
    assert "--profile" in result.output
    assert "--namespace" in result.output
    assert "--verbose" in result.output
