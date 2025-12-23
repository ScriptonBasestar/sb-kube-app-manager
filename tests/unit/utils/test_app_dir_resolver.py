"""Tests for app_dir_resolver module."""

from pathlib import Path

import pytest

from sbkube.utils.app_dir_resolver import resolve_app_dirs


class TestResolveAppDirs:
    """Test resolve_app_dirs function."""

    def test_raises_when_app_dir_missing(self, tmp_path: Path) -> None:
        """Raise ValueError when --app-dir does not exist."""
        with pytest.raises(ValueError, match="App directory not found"):
            resolve_app_dirs(tmp_path, "missing-app", "config.yaml")

    def test_raises_when_app_dir_is_file(self, tmp_path: Path) -> None:
        """Raise ValueError when --app-dir points to a file."""
        app_file = tmp_path / "app-file"
        app_file.write_text("not a directory")

        with pytest.raises(ValueError, match="Not a directory"):
            resolve_app_dirs(tmp_path, "app-file", "config.yaml")

    def test_returns_explicit_app_dir_when_exists(self, tmp_path: Path) -> None:
        """Return the explicit app dir when it exists."""
        app_dir = tmp_path / "app1"
        app_dir.mkdir()

        result = resolve_app_dirs(tmp_path, "app1", "config.yaml")

        assert result == [app_dir]
