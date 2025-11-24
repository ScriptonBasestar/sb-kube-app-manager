"""Unit tests for prepare.py - HTTP and Git app preparation.

Tests verify:
- HTTP file download
- Git repository clone
- Dry-run mode
- Error scenarios
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from sbkube.commands.prepare import prepare_git_app, prepare_http_app
from sbkube.models.config_model import GitApp, HttpApp
from sbkube.utils.output_manager import OutputManager


class TestPrepareHttpAppBasic:
    """Test basic HTTP app preparation scenarios."""

    @patch("sbkube.commands.prepare.run_command")
    def test_download_http_file_success(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test successful HTTP file download."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/manifest.yaml",
            dest="manifest.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Mock curl success
        mock_run_command.return_value = (0, "", "")

        # Act
        result = prepare_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify curl command was called
        mock_run_command.assert_called_once()
        call_args = mock_run_command.call_args[0][0]
        assert "curl" in call_args
        assert "-L" in call_args
        assert "https://example.com/manifest.yaml" in call_args

    def test_skip_existing_file(self, tmp_path: Path) -> None:
        """Test skipping download when file already exists."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        dest_file = app_config_dir / "existing.yaml"
        dest_file.write_text("existing content")

        app = HttpApp(
            type="http",
            url="https://example.com/manifest.yaml",
            dest="existing.yaml",  # Already exists
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        output.print_warning.assert_called_once()
        assert "already exists" in str(output.print_warning.call_args)

    @patch("sbkube.commands.prepare.run_command")
    def test_download_with_headers(self, mock_run_command, tmp_path: Path) -> None:
        """Test HTTP download with custom headers."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://api.example.com/file",
            dest="file.yaml",
            headers={
                "Authorization": "Bearer token123",
                "Accept": "application/yaml",
            },
        )

        output = MagicMock(spec=OutputManager)
        mock_run_command.return_value = (0, "", "")

        # Act
        result = prepare_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        call_args = mock_run_command.call_args[0][0]
        # Headers should be passed with -H flags
        assert "-H" in call_args

    def test_http_app_dry_run(self, tmp_path: Path) -> None:
        """Test HTTP app in dry-run mode."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/manifest.yaml",
            dest="manifest.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=True,  # DRY-RUN
        )

        # Assert
        assert result is True
        # Should print DRY-RUN message
        output.print.assert_called()
        call_str = str(output.print.call_args)
        assert "DRY-RUN" in call_str or "Would download" in call_str


class TestPrepareHttpAppErrors:
    """Test HTTP app error scenarios."""

    @patch("sbkube.commands.prepare.run_command")
    def test_curl_download_failure(self, mock_run_command, tmp_path: Path) -> None:
        """Test handling of curl download failure."""
        # Arrange
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)

        app = HttpApp(
            type="http",
            url="https://example.com/nonexistent.yaml",
            dest="file.yaml",
        )

        output = MagicMock(spec=OutputManager)

        # Mock curl failure
        mock_run_command.return_value = (22, "", "Error: 404 Not Found")

        # Act
        result = prepare_http_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            app_config_dir=app_config_dir,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        # Failed download should not leave partial file
        dest_path = app_config_dir / "file.yaml"
        assert not dest_path.exists()


class TestPrepareGitAppBasic:
    """Test basic Git app preparation scenarios."""

    @patch("sbkube.commands.prepare.run_command")
    def test_clone_git_repo_success(self, mock_run_command, tmp_path: Path) -> None:
        """Test successful Git repository clone."""
        # Arrange
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
git_repos:
  my-infra: https://github.com/example/infra.git
"""
        )

        app = GitApp(
            type="git",
            repo="my-infra",
            ref="main",
            path="k8s/manifests",
        )

        output = MagicMock(spec=OutputManager)

        # Mock git clone success
        mock_run_command.return_value = (0, "Cloning into...", "")

        # Act
        result = prepare_git_app(
            app_name="infra",
            app=app,
            base_dir=tmp_path,
            repos_dir=repos_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is True
        # Verify git clone was called
        mock_run_command.assert_called()
        call_args = mock_run_command.call_args[0][0]
        assert "git" in call_args
        assert "clone" in call_args

    @patch("sbkube.commands.prepare.run_command")
    def test_skip_existing_repo(self, mock_run_command, tmp_path: Path) -> None:
        """Test skipping clone when repo already exists."""
        # Arrange
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(exist_ok=True)

        # Create existing repo directory
        existing_repo = repos_dir / "my-infra"
        existing_repo.mkdir(exist_ok=True)
        (existing_repo / ".git").mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("git_repos:\n  my-infra: https://github.com/example/infra.git")

        app = GitApp(
            type="git",
            repo="my-infra",
            ref="main",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_git_app(
            app_name="infra",
            app=app,
            base_dir=tmp_path,
            repos_dir=repos_dir,
            sources_file=sources_file,
            output=output,
            force=False,  # Don't force re-clone
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should not call git clone
        mock_run_command.assert_not_called()

    @patch("sbkube.commands.prepare.run_command")
    def test_force_reclone_existing_repo(
        self, mock_run_command, tmp_path: Path
    ) -> None:
        """Test force flag re-clones existing repo."""
        # Arrange
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(exist_ok=True)

        existing_repo = repos_dir / "my-infra"
        existing_repo.mkdir(exist_ok=True)
        (existing_repo / ".git").mkdir(exist_ok=True)
        (existing_repo / "old-file.txt").write_text("old")

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("git_repos:\n  my-infra: https://github.com/example/infra.git")

        app = GitApp(
            type="git",
            repo="my-infra",
            ref="main",
        )

        output = MagicMock(spec=OutputManager)
        mock_run_command.return_value = (0, "Cloning...", "")

        # Act
        result = prepare_git_app(
            app_name="infra",
            app=app,
            base_dir=tmp_path,
            repos_dir=repos_dir,
            sources_file=sources_file,
            output=output,
            force=True,  # Force re-clone
            dry_run=False,
        )

        # Assert
        assert result is True
        # Should remove and re-clone
        mock_run_command.assert_called()

    def test_git_app_dry_run(self, tmp_path: Path) -> None:
        """Test Git app in dry-run mode."""
        # Arrange
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("git_repos:\n  my-infra: https://github.com/example/infra.git")

        app = GitApp(
            type="git",
            repo="my-infra",
            ref="main",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_git_app(
            app_name="infra",
            app=app,
            base_dir=tmp_path,
            repos_dir=repos_dir,
            sources_file=sources_file,
            output=output,
            dry_run=True,  # DRY-RUN
        )

        # Assert
        assert result is True
        # Should print DRY-RUN message
        output.print.assert_called()


class TestPrepareGitAppErrors:
    """Test Git app error scenarios."""

    def test_repo_not_in_sources(self, tmp_path: Path) -> None:
        """Test error when Git repo not defined in sources.yaml."""
        # Arrange
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            """
git_repos:
  other-repo: https://github.com/example/other.git
"""
        )

        app = GitApp(
            type="git",
            repo="my-infra",  # Not in sources
            ref="main",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_git_app(
            app_name="infra",
            app=app,
            base_dir=tmp_path,
            repos_dir=repos_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
        assert "not found" in str(output.print_error.call_args).lower()

    @patch("sbkube.commands.prepare.run_command")
    def test_git_clone_failure(self, mock_run_command, tmp_path: Path) -> None:
        """Test handling of git clone failure."""
        # Arrange
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("git_repos:\n  my-infra: https://github.com/example/nonexistent.git")

        app = GitApp(
            type="git",
            repo="my-infra",
            ref="main",
        )

        output = MagicMock(spec=OutputManager)

        # Mock git clone failure
        mock_run_command.return_value = (128, "", "fatal: repository not found")

        # Act
        result = prepare_git_app(
            app_name="infra",
            app=app,
            base_dir=tmp_path,
            repos_dir=repos_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()

    def test_sources_file_not_found(self, tmp_path: Path) -> None:
        """Test error when sources.yaml doesn't exist."""
        # Arrange
        repos_dir = tmp_path / "repos"
        repos_dir.mkdir(exist_ok=True)

        sources_file = tmp_path / "nonexistent.yaml"  # Doesn't exist

        app = GitApp(
            type="git",
            repo="my-infra",
            ref="main",
        )

        output = MagicMock(spec=OutputManager)

        # Act
        result = prepare_git_app(
            app_name="infra",
            app=app,
            base_dir=tmp_path,
            repos_dir=repos_dir,
            sources_file=sources_file,
            output=output,
            dry_run=False,
        )

        # Assert
        assert result is False
        output.print_error.assert_called()
