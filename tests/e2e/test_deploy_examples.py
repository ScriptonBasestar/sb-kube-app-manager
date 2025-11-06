"""E2E tests for deploy command examples.

These tests use the actual examples/deploy/ directory to verify
deploy command functionality with real configuration files.

Note: These tests require kubectl with cluster access (even with --dry-run).
"""

import pytest

from tests.e2e.conftest import run_sbkube_command, verify_example_exists


@pytest.mark.e2e
@pytest.mark.requires_k8s
class TestDeployExamples:
    """Test deploy command with various example configurations."""

    def test_deploy_install_yaml_dry_run(self, runner, examples_dir, tmp_path):
        """Test deploy with YAML manifest installation (dry-run).

        This test verifies that deploy correctly handles YAML manifests
        as specified in examples/deploy/yaml/config.yaml.
        """
        # Verify example files exist
        example_dir = examples_dir / "deploy" / "yaml-example"
        verify_example_exists(example_dir)

        # Get project root
        project_root = examples_dir.parent

        # Run deploy command with --dry-run
        result = run_sbkube_command(
            runner,
            [
                "deploy",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--dry-run",
            ],
            debug_info={
                "example_dir": example_dir,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "deploy" in result.output.lower() or "배포" in result.output

    def test_deploy_install_action_dry_run(self, runner, examples_dir, tmp_path):
        """Test deploy with custom action installation (dry-run).

        This test verifies that deploy correctly handles custom actions
        as specified in examples/deploy/install-action/config.yaml.
        """
        # Verify example files exist
        example_dir = examples_dir / "deploy" / "action-example"
        verify_example_exists(example_dir)

        # Get project root
        project_root = examples_dir.parent

        # Run deploy command with --dry-run
        result = run_sbkube_command(
            runner,
            [
                "deploy",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--dry-run",
            ],
            debug_info={
                "example_dir": example_dir,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "deploy" in result.output.lower() or "배포" in result.output

    def test_deploy_exec_dry_run(self, runner, examples_dir, tmp_path):
        """Test deploy with exec command (dry-run).

        This test verifies that deploy correctly handles exec commands
        as specified in examples/deploy/exec/config.yaml.
        """
        # Verify example files exist
        example_dir = examples_dir / "deploy" / "exec"
        verify_example_exists(example_dir)

        # Get project root
        project_root = examples_dir.parent

        # Run deploy command with --dry-run
        result = run_sbkube_command(
            runner,
            [
                "deploy",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--dry-run",
            ],
            debug_info={
                "example_dir": example_dir,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "deploy" in result.output.lower() or "배포" in result.output
