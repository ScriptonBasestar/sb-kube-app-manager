"""Tests for error suggestions module."""

from sbkube.utils.error_suggestions import (
    ERROR_GUIDE,
    format_suggestions,
    get_error_suggestions,
    get_quick_fix_command,
    is_auto_recoverable,
)


def test_error_guide_contains_all_expected_errors():
    """ERROR_GUIDE should contain all documented error types."""
    expected_errors = [
        "ConfigFileNotFoundError",
        "KubernetesConnectionError",
        "HelmNotFoundError",
        "HelmChartNotFoundError",
        "GitRepositoryError",
        "NamespaceNotFoundError",
        "ValidationError",
        "DeploymentFailedError",
        "PermissionDeniedError",
        "ResourceQuotaExceededError",
    ]

    for error_type in expected_errors:
        assert error_type in ERROR_GUIDE, f"{error_type} not found in ERROR_GUIDE"


def test_get_error_suggestions_returns_valid_guide():
    """get_error_suggestions should return valid guide for known errors."""
    guide = get_error_suggestions("ConfigFileNotFoundError")

    assert guide is not None
    assert "title" in guide
    assert "suggestions" in guide
    assert "commands" in guide
    assert "doc_link" in guide
    assert "quick_fix" in guide
    assert "auto_recoverable" in guide


def test_get_error_suggestions_returns_none_for_unknown():
    """get_error_suggestions should return None for unknown errors."""
    guide = get_error_suggestions("UnknownError")
    assert guide is None


def test_format_suggestions_returns_formatted_string():
    """format_suggestions should return formatted string with all sections."""
    result = format_suggestions("ConfigFileNotFoundError")

    assert "💡" in result  # Title icon
    assert "설정 파일을 찾을 수 없습니다" in result  # Title
    assert "📋 해결 방법:" in result  # Suggestions section
    assert "sbkube init" in result  # Quick fix
    assert "🔧 유용한 명령어:" in result  # Commands section
    assert "📖 자세한 내용:" in result  # Doc link section
    assert "⚡ 빠른 해결:" in result  # Quick fix section


def test_format_suggestions_returns_empty_for_unknown():
    """format_suggestions should return empty string for unknown errors."""
    result = format_suggestions("UnknownError")
    assert result == ""


def test_get_quick_fix_command_returns_command():
    """get_quick_fix_command should return quick fix command for recoverable errors."""
    command = get_quick_fix_command("ConfigFileNotFoundError")
    assert command == "sbkube init"


def test_get_quick_fix_command_returns_none_for_non_recoverable():
    """get_quick_fix_command should return None for non-recoverable errors."""
    command = get_quick_fix_command("HelmNotFoundError")
    assert command is None


def test_get_quick_fix_command_returns_none_for_unknown():
    """get_quick_fix_command should return None for unknown errors."""
    command = get_quick_fix_command("UnknownError")
    assert command is None


def test_is_auto_recoverable_true_for_recoverable():
    """is_auto_recoverable should return True for auto-recoverable errors."""
    assert is_auto_recoverable("ConfigFileNotFoundError") is True
    assert is_auto_recoverable("KubernetesConnectionError") is True
    assert is_auto_recoverable("HelmChartNotFoundError") is True


def test_is_auto_recoverable_false_for_non_recoverable():
    """is_auto_recoverable should return False for non-recoverable errors."""
    assert is_auto_recoverable("HelmNotFoundError") is False
    assert is_auto_recoverable("PermissionDeniedError") is False


def test_is_auto_recoverable_false_for_unknown():
    """is_auto_recoverable should return False for unknown errors."""
    assert is_auto_recoverable("UnknownError") is False


def test_all_guides_have_required_fields():
    """All error guides should have required fields."""
    required_fields = [
        "title",
        "suggestions",
        "commands",
        "doc_link",
        "quick_fix",
        "auto_recoverable",
    ]

    for error_type, guide in ERROR_GUIDE.items():
        for field in required_fields:
            assert field in guide, f"{error_type} missing required field: {field}"

        # Validate field types
        assert isinstance(guide["title"], str), f"{error_type}.title must be string"
        assert isinstance(guide["suggestions"], list), (
            f"{error_type}.suggestions must be list"
        )
        assert isinstance(guide["commands"], dict), (
            f"{error_type}.commands must be dict"
        )
        assert isinstance(guide["doc_link"], str), (
            f"{error_type}.doc_link must be string"
        )
        assert guide["quick_fix"] is None or isinstance(guide["quick_fix"], str), (
            f"{error_type}.quick_fix must be string or None"
        )
        assert isinstance(guide["auto_recoverable"], bool), (
            f"{error_type}.auto_recoverable must be bool"
        )


def test_suggestions_are_actionable():
    """All suggestions should be actionable (contain → or specific instructions)."""
    for error_type, guide in ERROR_GUIDE.items():
        for suggestion in guide["suggestions"]:
            # Suggestions should either contain → or be imperative (명령문)
            assert "→" in suggestion or any(
                keyword in suggestion
                for keyword in ["확인", "실행", "추가", "업데이트", "문의"]
            ), f"{error_type} has non-actionable suggestion: {suggestion}"


def test_commands_have_descriptions():
    """All commands should have descriptions."""
    for error_type, guide in ERROR_GUIDE.items():
        for cmd, desc in guide["commands"].items():
            assert isinstance(cmd, str) and len(cmd) > 0, (
                f"{error_type} has invalid command key"
            )
            assert isinstance(desc, str) and len(desc) > 0, (
                f"{error_type} has empty command description"
            )


def test_doc_links_are_valid_paths():
    """All doc links should be valid relative paths."""
    for error_type, guide in ERROR_GUIDE.items():
        doc_link = guide["doc_link"]
        assert doc_link.startswith("docs/"), (
            f"{error_type}.doc_link should start with 'docs/'"
        )
        assert doc_link.endswith(".md") or "#" in doc_link, (
            f"{error_type}.doc_link should be .md file or anchor"
        )
