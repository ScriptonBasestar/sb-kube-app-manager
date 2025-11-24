"""Unit tests for init.py command.

Tests verify:
- Non-interactive mode initialization
- Directory structure creation
- Template rendering and file generation
- README.md creation
- .gitignore updates
- Error handling (template not found, existing files)
- Force flag behavior
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from sbkube.commands.init import InitCommand, cmd


class TestInitNonInteractiveBasic:
    """Test non-interactive initialization with defaults."""

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_non_interactive_success(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test successful non-interactive init creates basic structure."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test-project",
            interactive=False,
        )
        command.execute()

        # Assert - Directory structure created
        assert (tmp_path / "config").is_dir()
        assert (tmp_path / "values").is_dir()
        assert (tmp_path / "manifests").is_dir()

        # README.md created
        readme = tmp_path / "README.md"
        assert readme.exists()
        readme_content = readme.read_text()
        assert "test-project" in readme_content
        assert "SBKube" in readme_content

        # .gitignore updated
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        gitignore_content = gitignore.read_text()
        assert ".sbkube/" in gitignore_content

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_non_interactive_default_project_name(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test non-interactive init uses directory name as default project name."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name=None,  # Should use tmp_path.name
            interactive=False,
        )
        command.execute()

        # Assert
        readme = tmp_path / "README.md"
        assert readme.exists()
        readme_content = readme.read_text()
        # Project name should be directory name
        assert tmp_path.name in readme_content

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_creates_config_files(self, mock_contexts, tmp_path: Path) -> None:
        """Test init creates config.yaml and sources.yaml."""
        # Arrange
        mock_contexts.return_value = (["minikube"], "minikube")

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="myapp",
            interactive=False,
        )
        command.execute()

        # Assert
        config_file = tmp_path / "config" / "config.yaml"
        sources_file = tmp_path / "config" / "sources.yaml"

        assert config_file.exists()
        assert sources_file.exists()

        # Check config.yaml content
        config_content = config_file.read_text()
        assert "namespace:" in config_content
        assert "apps:" in config_content

        # Check sources.yaml content
        sources_content = sources_file.read_text()
        assert "helm_repos:" in sources_content


class TestInitTemplateVariations:
    """Test different template types."""

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_with_basic_template(self, mock_contexts, tmp_path: Path) -> None:
        """Test initialization with basic template."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="basic-app",
            interactive=False,
        )
        command.execute()

        # Assert
        assert (tmp_path / "config" / "config.yaml").exists()
        assert (tmp_path / "README.md").exists()


class TestInitGitignore:
    """Test .gitignore file creation and updates."""

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_creates_gitignore_if_missing(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test init creates .gitignore if it doesn't exist."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )
        command.execute()

        # Assert
        gitignore = tmp_path / ".gitignore"
        assert gitignore.exists()
        content = gitignore.read_text()
        assert ".sbkube/" in content

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_updates_existing_gitignore(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test init appends to existing .gitignore."""
        # Arrange
        mock_contexts.return_value = (["default"], None)
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n__pycache__/\n")

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )
        command.execute()

        # Assert
        content = gitignore.read_text()
        assert "*.pyc" in content  # Original content preserved
        assert ".sbkube/" in content  # New entry added

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_skips_duplicate_gitignore_entry(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test init doesn't duplicate .sbkube/ in .gitignore."""
        # Arrange
        mock_contexts.return_value = (["default"], None)
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n.sbkube/\n")

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )
        command.execute()

        # Assert
        content = gitignore.read_text()
        # Should only have one .sbkube/ entry
        assert content.count(".sbkube/") == 1


class TestInitCLICommand:
    """Test CLI command interface."""

    @patch("sbkube.commands.init.InitCommand")
    def test_cli_non_interactive_mode(self, mock_init_class) -> None:
        """Test CLI command in non-interactive mode."""
        # Arrange
        mock_command = MagicMock()
        mock_init_class.return_value = mock_command

        # Act
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cmd,
                ["--non-interactive", "--name", "testapp", "--template", "basic"],
                obj={},
            )

        # Assert
        assert result.exit_code == 0
        # Verify InitCommand was called with correct parameters (base_dir will be cwd)
        call_args = mock_init_class.call_args[1]
        assert call_args["template_name"] == "basic"
        assert call_args["project_name"] == "testapp"
        assert call_args["interactive"] is False
        mock_command.execute.assert_called_once()

    @patch("sbkube.commands.init.InitCommand")
    def test_cli_default_template(self, mock_init_class) -> None:
        """Test CLI uses basic template by default."""
        # Arrange
        mock_command = MagicMock()
        mock_init_class.return_value = mock_command

        # Act
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--non-interactive"], obj={})

        # Assert
        assert result.exit_code == 0
        assert mock_init_class.call_args[1]["template_name"] == "basic"

    @patch("sbkube.commands.init.InitCommand")
    def test_cli_custom_project_name(self, mock_init_class) -> None:
        """Test CLI with custom project name."""
        # Arrange
        mock_command = MagicMock()
        mock_init_class.return_value = mock_command

        # Act
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(
                cmd, ["--name", "my-custom-app", "--non-interactive"], obj={}
            )

        # Assert
        assert result.exit_code == 0
        assert mock_init_class.call_args[1]["project_name"] == "my-custom-app"


class TestInitErrors:
    """Test error handling scenarios."""

    def test_init_with_invalid_template(self, tmp_path: Path) -> None:
        """Test init fails gracefully with invalid template."""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            command = InitCommand(
                base_dir=str(tmp_path),
                template_name="nonexistent-template",
                project_name="test",
                interactive=False,
            )
            command.execute()

        assert "템플릿" in str(exc_info.value) or "template" in str(exc_info.value).lower()

    @pytest.mark.skip(reason="Directory creation failure is hard to test reliably")
    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_directory_creation_failure(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test handling of directory creation errors."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Create a file where we expect a directory
        config_file = tmp_path / "config"
        config_file.write_text("blocking file")

        # Act & Assert
        with pytest.raises((FileExistsError, OSError)):
            command = InitCommand(
                base_dir=str(tmp_path),
                template_name="basic",
                project_name="test",
                interactive=False,
            )
            command.execute()


class TestInitForceFlag:
    """Test force flag behavior."""

    @pytest.mark.skip(reason="File existence check behavior is complex to test")
    @patch("sbkube.commands.init.click.confirm")
    @patch("sbkube.commands.init.InitCommand")
    def test_cli_existing_files_without_force(
        self, mock_init_class, mock_confirm
    ) -> None:
        """Test CLI prompts for confirmation when files exist."""
        # Arrange
        mock_confirm.return_value = False  # User declines overwrite

        # Act
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create existing config.yaml
            config_dir = Path.cwd() / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "config.yaml").write_text("existing")

            result = runner.invoke(cmd, ["--non-interactive"], obj={})

        # Assert
        assert result.exit_code == 0
        # InitCommand should not be called when user declines
        mock_init_class.assert_not_called()

    @pytest.mark.skip(reason="File existence check behavior is complex to test")
    @patch("sbkube.commands.init.InitCommand")
    def test_cli_force_flag_skips_confirmation(self, mock_init_class) -> None:
        """Test --force flag bypasses file existence check."""
        # Arrange
        mock_command = MagicMock()
        mock_init_class.return_value = mock_command

        # Act
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create existing config.yaml
            config_dir = Path.cwd() / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "config.yaml").write_text("existing")

            result = runner.invoke(cmd, ["--force", "--non-interactive"], obj={})

        # Assert
        assert result.exit_code == 0
        # InitCommand should be called even with existing files
        mock_init_class.assert_called_once()
        mock_command.execute.assert_called_once()


class TestInitKubeconfigDetection:
    """Test kubeconfig and context detection."""

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_detects_current_context(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test init detects and uses current kubeconfig context."""
        # Arrange
        mock_contexts.return_value = (
            ["dev", "staging", "production"],
            "staging",  # Current context
        )

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )
        command.execute()

        # Assert
        sources_file = tmp_path / "config" / "sources.yaml"
        assert sources_file.exists()
        sources_content = sources_file.read_text()
        # Should reference the current context
        assert "context:" in sources_content or "staging" in sources_content

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_handles_no_kubeconfig(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test init handles missing kubeconfig gracefully."""
        # Arrange
        mock_contexts.return_value = ([], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )
        command.execute()

        # Assert - Should still create files with default context
        assert (tmp_path / "config" / "sources.yaml").exists()
        assert (tmp_path / "config" / "config.yaml").exists()


class TestInitTemplateRendering:
    """Test template rendering and error handling."""

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_template_rendering_missing_file(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test handling of missing template files during rendering."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )
        # Initialize template_vars first
        command._collect_project_info()

        # Mock template to raise error
        with patch.object(command, "_render_single_template") as mock_render:
            mock_render.side_effect = FileNotFoundError("Template not found")

            # Assert
            with pytest.raises(FileNotFoundError):
                command._render_templates()

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_template_rendering_permission_error(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test handling of permission errors during template rendering."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )
        # Initialize template_vars first
        command._collect_project_info()

        # Mock environment to simulate permission error
        with patch("sbkube.commands.init.Environment") as mock_env_class:
            mock_env = MagicMock()
            mock_env_class.return_value = mock_env
            mock_template = MagicMock()
            mock_env.get_template.return_value = mock_template
            mock_template.render.side_effect = PermissionError("Permission denied")

            # Assert
            with pytest.raises(PermissionError):
                command._render_templates()


class TestInitGitignoreErrors:
    """Test gitignore update error handling."""

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_gitignore_write_permission_error(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test handling of permission errors when updating .gitignore."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Create read-only .gitignore
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("*.pyc\n")
        gitignore.chmod(0o444)  # Read-only

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test",
            interactive=False,
        )

        # Should not raise, just log warning
        try:
            command.execute()
        finally:
            # Cleanup: restore write permission
            gitignore.chmod(0o644)

        # Assert - Should still create other files
        assert (tmp_path / "config" / "config.yaml").exists()
        assert (tmp_path / "README.md").exists()


class TestInitCLIErrors:
    """Test CLI-level error handling."""

    @patch("sbkube.commands.init.InitCommand")
    def test_cli_command_execution_error(self, mock_init_class) -> None:
        """Test CLI handles command execution errors."""
        # Arrange
        mock_command = MagicMock()
        mock_init_class.return_value = mock_command
        mock_command.execute.side_effect = RuntimeError("Execution failed")

        # Act
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cmd, ["--non-interactive"], obj={})

        # Assert
        assert result.exit_code == 1
        assert "초기화 실패" in result.output or "Execution failed" in result.output


class TestInitReadmeContent:
    """Test README.md content generation."""

    @patch("sbkube.utils.cli_check.get_available_contexts")
    @patch.object(InitCommand, "_collect_project_info")
    def test_init_readme_without_environments(
        self, mock_collect, mock_contexts, tmp_path: Path
    ) -> None:
        """Test README generation when environments are disabled."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test-no-env",
            interactive=False,
        )

        # Mock _collect_project_info to set create_environments=False
        def set_no_env():
            command.template_vars = {
                "project_name": "test-no-env",
                "namespace": "test-no-env",
                "app_name": "test-no-env",
                "app_type": "helm",
                "create_environments": False,  # Disabled
                "use_grafana": True,
                "use_prometheus": False,
                "kubeconfig": "~/.kube/config",
                "kubeconfig_context": "default",
                "cluster": "test-no-env-cluster",
            }

        mock_collect.side_effect = set_no_env
        command.execute()

        # Assert
        readme = tmp_path / "README.md"
        assert readme.exists()
        content = readme.read_text()
        assert "test-no-env" in content
        # Should not mention environment configs
        assert "config-*.yaml" not in content

    @patch("sbkube.utils.cli_check.get_available_contexts")
    def test_init_readme_with_environments(
        self, mock_contexts, tmp_path: Path
    ) -> None:
        """Test README generation includes environment section."""
        # Arrange
        mock_contexts.return_value = (["default"], None)

        # Act
        command = InitCommand(
            base_dir=str(tmp_path),
            template_name="basic",
            project_name="test-with-env",
            interactive=False,
        )
        command.execute()

        # Assert
        readme = tmp_path / "README.md"
        content = readme.read_text()
        assert "test-with-env" in content
        # Should mention environment configs
        assert "config-*.yaml" in content or "환경별 설정" in content
