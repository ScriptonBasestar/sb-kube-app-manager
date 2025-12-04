"""Tests for workspace_resolver module."""

import pytest
from pathlib import Path

from sbkube.utils.workspace_resolver import (
    SbkubeDirectories,
    find_sources_file_upward,
    resolve_sbkube_directories,
    resolve_sources_and_work_dirs,
)


class TestSbkubeDirectories:
    """Test SbkubeDirectories dataclass."""

    def test_temp_dir_property(self, tmp_path: Path) -> None:
        """Test temp_dir property returns correct path."""
        dirs = SbkubeDirectories(
            base_dir=tmp_path,
            sources_file=None,
            sources_base_dir=tmp_path,
            sbkube_work_dir=tmp_path / ".sbkube",
            charts_dir=tmp_path / ".sbkube" / "charts",
            repos_dir=tmp_path / ".sbkube" / "repos",
            build_dir=tmp_path / ".sbkube" / "build",
            rendered_dir=tmp_path / ".sbkube" / "rendered",
        )
        assert dirs.temp_dir == tmp_path / ".sbkube" / "temp"

    def test_ensure_directories_creates_all(self, tmp_path: Path) -> None:
        """Test ensure_directories creates all required directories."""
        dirs = SbkubeDirectories(
            base_dir=tmp_path,
            sources_file=None,
            sources_base_dir=tmp_path,
            sbkube_work_dir=tmp_path / ".sbkube",
            charts_dir=tmp_path / ".sbkube" / "charts",
            repos_dir=tmp_path / ".sbkube" / "repos",
            build_dir=tmp_path / ".sbkube" / "build",
            rendered_dir=tmp_path / ".sbkube" / "rendered",
        )

        # Directories don't exist yet
        assert not dirs.sbkube_work_dir.exists()

        # Create them
        dirs.ensure_directories()

        # All should exist now
        assert dirs.sbkube_work_dir.exists()
        assert dirs.charts_dir.exists()
        assert dirs.repos_dir.exists()
        assert dirs.build_dir.exists()
        assert dirs.rendered_dir.exists()

    def test_ensure_temp_dir(self, tmp_path: Path) -> None:
        """Test ensure_temp_dir creates and returns temp directory."""
        dirs = SbkubeDirectories(
            base_dir=tmp_path,
            sources_file=None,
            sources_base_dir=tmp_path,
            sbkube_work_dir=tmp_path / ".sbkube",
            charts_dir=tmp_path / ".sbkube" / "charts",
            repos_dir=tmp_path / ".sbkube" / "repos",
            build_dir=tmp_path / ".sbkube" / "build",
            rendered_dir=tmp_path / ".sbkube" / "rendered",
        )

        temp_dir = dirs.ensure_temp_dir()
        assert temp_dir.exists()
        assert temp_dir == tmp_path / ".sbkube" / "temp"


class TestFindSourcesFileUpward:
    """Test find_sources_file_upward function."""

    def test_finds_in_current_dir(self, tmp_path: Path) -> None:
        """Test finding sources.yaml in current directory."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm: []")

        result = find_sources_file_upward(tmp_path)
        assert result == sources_file

    def test_finds_in_parent_dir(self, tmp_path: Path) -> None:
        """Test finding sources.yaml in parent directory."""
        # Create nested structure
        app_dir = tmp_path / "apps" / "redis"
        app_dir.mkdir(parents=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm: []")

        result = find_sources_file_upward(app_dir)
        assert result == sources_file

    def test_finds_in_grandparent_dir(self, tmp_path: Path) -> None:
        """Test finding sources.yaml in grandparent directory."""
        # Create deeply nested structure
        app_dir = tmp_path / "project" / "apps" / "redis"
        app_dir.mkdir(parents=True)

        sources_file = tmp_path / "project" / "sources.yaml"
        sources_file.write_text("helm: []")

        result = find_sources_file_upward(app_dir)
        assert result == sources_file

    def test_returns_none_when_not_found(self, tmp_path: Path) -> None:
        """Test returns None when sources.yaml doesn't exist."""
        app_dir = tmp_path / "apps" / "redis"
        app_dir.mkdir(parents=True)

        result = find_sources_file_upward(app_dir)
        assert result is None

    def test_custom_file_name(self, tmp_path: Path) -> None:
        """Test finding with custom file name."""
        sources_file = tmp_path / "custom-sources.yaml"
        sources_file.write_text("helm: []")

        result = find_sources_file_upward(tmp_path, sources_file_name="custom-sources.yaml")
        assert result == sources_file

    def test_stop_at_directory(self, tmp_path: Path) -> None:
        """Test stop_at parameter prevents searching beyond specified directory."""
        # Create structure:
        # tmp_path/
        #   sources.yaml  <- Should NOT be found
        #   project/
        #     apps/
        #       redis/  <- Start here
        project_dir = tmp_path / "project"
        app_dir = project_dir / "apps" / "redis"
        app_dir.mkdir(parents=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm: []")

        # Should not find sources.yaml because we stop at project_dir
        result = find_sources_file_upward(app_dir, stop_at=project_dir)
        assert result is None


class TestResolveSbkubeDirectories:
    """Test resolve_sbkube_directories function."""

    def test_with_sources_in_base_dir(self, tmp_path: Path) -> None:
        """Test resolution when sources.yaml is in base_dir."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm: []")

        app_dir = tmp_path / "apps" / "redis"
        app_dir.mkdir(parents=True)

        dirs = resolve_sbkube_directories(tmp_path, [app_dir])

        assert dirs.sources_file == sources_file
        assert dirs.sources_base_dir == tmp_path
        assert dirs.sbkube_work_dir == tmp_path / ".sbkube"
        assert dirs.charts_dir == tmp_path / ".sbkube" / "charts"
        assert dirs.build_dir == tmp_path / ".sbkube" / "build"
        assert dirs.repos_dir == tmp_path / ".sbkube" / "repos"
        assert dirs.rendered_dir == tmp_path / ".sbkube" / "rendered"

    def test_with_sources_in_app_parent(self, tmp_path: Path) -> None:
        """Test resolution when sources.yaml is in app's parent directory."""
        # Create structure:
        # tmp_path/
        #   project/
        #     sources.yaml  <- sources here
        #     redis/
        #       config.yaml
        project_dir = tmp_path / "project"
        app_dir = project_dir / "redis"
        app_dir.mkdir(parents=True)

        sources_file = project_dir / "sources.yaml"
        sources_file.write_text("helm: []")

        dirs = resolve_sbkube_directories(tmp_path, [app_dir])

        assert dirs.sources_file == sources_file
        assert dirs.sources_base_dir == project_dir
        assert dirs.sbkube_work_dir == project_dir / ".sbkube"

    def test_without_sources_file(self, tmp_path: Path) -> None:
        """Test resolution when no sources.yaml exists."""
        app_dir = tmp_path / "apps" / "redis"
        app_dir.mkdir(parents=True)

        dirs = resolve_sbkube_directories(tmp_path, [app_dir])

        assert dirs.sources_file is None
        assert dirs.sources_base_dir == tmp_path
        assert dirs.sbkube_work_dir == tmp_path / ".sbkube"

    def test_without_app_config_dirs(self, tmp_path: Path) -> None:
        """Test resolution without app_config_dirs."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm: []")

        dirs = resolve_sbkube_directories(tmp_path)

        assert dirs.sources_file == sources_file
        assert dirs.sources_base_dir == tmp_path

    def test_with_empty_app_config_dirs(self, tmp_path: Path) -> None:
        """Test resolution with empty app_config_dirs list."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm: []")

        dirs = resolve_sbkube_directories(tmp_path, [])

        assert dirs.sources_file == sources_file

    def test_base_dir_is_resolved(self, tmp_path: Path) -> None:
        """Test that base_dir is always resolved to absolute path."""
        # Use relative path
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            dirs = resolve_sbkube_directories(Path("."))
            assert dirs.base_dir.is_absolute()
        finally:
            os.chdir(original_cwd)


class TestResolveSourcesAndWorkDirs:
    """Test legacy compatibility function."""

    def test_returns_tuple(self, tmp_path: Path) -> None:
        """Test returns correct tuple format."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("helm: []")

        app_dir = tmp_path / "apps" / "redis"
        app_dir.mkdir(parents=True)

        result = resolve_sources_and_work_dirs(tmp_path, [app_dir])

        assert isinstance(result, tuple)
        assert len(result) == 5

        sources_path, sbkube_dir, charts_dir, build_dir, repos_dir = result

        assert sources_path == sources_file
        assert sbkube_dir == tmp_path / ".sbkube"
        assert charts_dir == tmp_path / ".sbkube" / "charts"
        assert build_dir == tmp_path / ".sbkube" / "build"
        assert repos_dir == tmp_path / ".sbkube" / "repos"

    def test_returns_none_sources_when_not_found(self, tmp_path: Path) -> None:
        """Test returns None for sources when not found."""
        app_dir = tmp_path / "apps" / "redis"
        app_dir.mkdir(parents=True)

        result = resolve_sources_and_work_dirs(tmp_path, [app_dir])
        sources_path, _, _, _, _ = result

        assert sources_path is None
