"""Tests for security helpers."""

from sbkube.utils.security import is_exec_allowed


def test_is_exec_allowed_defaults_to_true(monkeypatch) -> None:
    """Exec should be allowed when env var is unset."""
    monkeypatch.delenv("SBKUBE_ALLOW_EXEC", raising=False)
    assert is_exec_allowed() is True


def test_is_exec_allowed_false_values(monkeypatch) -> None:
    """Exec should be disabled for explicit false values."""
    for value in ["0", "false", "no", "off", " FALSE "]:
        monkeypatch.setenv("SBKUBE_ALLOW_EXEC", value)
        assert is_exec_allowed() is False


def test_is_exec_allowed_true_values(monkeypatch) -> None:
    """Exec should be enabled for explicit true values."""
    for value in ["1", "true", "yes", "on", " TRUE "]:
        monkeypatch.setenv("SBKUBE_ALLOW_EXEC", value)
        assert is_exec_allowed() is True


def test_is_exec_allowed_unknown_values(monkeypatch) -> None:
    """Unknown values should default to allow."""
    monkeypatch.setenv("SBKUBE_ALLOW_EXEC", "maybe")
    assert is_exec_allowed() is True
