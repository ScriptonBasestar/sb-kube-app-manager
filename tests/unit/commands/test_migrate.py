"""Unit tests for sbkube migrate command.

Tests verify:
- CLI help and options
- Dry-run mode (no helm upgrade executed)
- No-conflict scenario
- Release filtering
"""

from unittest.mock import patch

from click.testing import CliRunner

from sbkube.commands.migrate import cmd


class TestMigrateCLI:
    """Test migrate command CLI interface."""

    def test_help_output(self) -> None:
        """Test --help shows correct command info."""
        runner = CliRunner()
        result = runner.invoke(cmd, ["--help"], catch_exceptions=False)
        assert result.exit_code == 0
        assert "SSA" in result.output
        assert "--dry-run" in result.output
        assert "--all" in result.output
        assert "--app" in result.output
        assert "--yes" in result.output
        assert "--deep" in result.output

    @patch("sbkube.commands.migrate.run_command")
    def test_dry_run_no_helm_upgrade(self, mock_run_command) -> None:
        """Test --dry-run does not execute helm upgrade."""
        # helm version
        mock_run_command.side_effect = [
            (0, "v4.1.1", ""),  # helm version
            (0, "[]", ""),  # helm list (empty)
        ]

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--dry-run", "--all"],
            obj={"kubeconfig": None, "context": None},
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        # Verify no helm upgrade was called
        for call_args in mock_run_command.call_args_list:
            cmd_list = call_args[0][0]
            assert "upgrade" not in cmd_list

    @patch("sbkube.commands.migrate.run_command")
    def test_no_releases(self, mock_run_command) -> None:
        """Test graceful handling when no releases exist."""
        mock_run_command.side_effect = [
            (0, "v4.1.1", ""),  # helm version
            (0, "[]", ""),  # helm list (empty)
        ]

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--all", "--dry-run"],
            obj={"kubeconfig": None, "context": None},
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "없습니다" in result.output

    @patch("sbkube.commands.migrate.run_command")
    def test_no_conflicts_found(self, mock_run_command) -> None:
        """Test when releases exist but no conflicts detected."""
        releases = [
            {"name": "traefik", "namespace": "kube-system", "status": "deployed"},
        ]
        import json

        mock_run_command.side_effect = [
            (0, "v4.1.1", ""),  # helm version
            (0, json.dumps(releases), ""),  # helm list
            (0, json.dumps([{"revision": 1, "status": "deployed", "description": "Install complete"}]), ""),  # helm history
        ]

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--all", "--dry-run"],
            obj={"kubeconfig": None, "context": None},
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "정상" in result.output

    @patch("sbkube.commands.migrate.run_command")
    def test_app_filter(self, mock_run_command) -> None:
        """Test --app filters to specific release."""
        releases = [
            {"name": "traefik", "namespace": "kube-system", "status": "deployed"},
            {"name": "coredns", "namespace": "kube-system", "status": "deployed"},
        ]
        import json

        mock_run_command.side_effect = [
            (0, "v4.1.1", ""),
            (0, json.dumps(releases), ""),
            (0, json.dumps([{"revision": 1, "status": "deployed", "description": "OK"}]), ""),
        ]

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--app", "traefik", "--dry-run"],
            obj={"kubeconfig": None, "context": None},
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "1개 release" in result.output  # Only traefik

    @patch("sbkube.commands.migrate.run_command")
    def test_app_not_found(self, mock_run_command) -> None:
        """Test --app with nonexistent release."""
        releases = [
            {"name": "traefik", "namespace": "kube-system", "status": "deployed"},
        ]
        import json

        mock_run_command.side_effect = [
            (0, "v4.1.1", ""),
            (0, json.dumps(releases), ""),
        ]

        runner = CliRunner()
        result = runner.invoke(
            cmd,
            ["--app", "nonexistent", "--dry-run"],
            obj={"kubeconfig": None, "context": None},
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "찾을 수 없습니다" in result.output
