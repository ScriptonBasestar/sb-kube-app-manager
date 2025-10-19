"""
E2E tests for complete workflow example.

This test uses the examples/complete-workflow/ directory to verify
the entire sbkube workflow from prepare through deploy.
"""

from pathlib import Path

import pytest

from tests.e2e.conftest import run_sbkube_command, verify_example_exists


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteWorkflow:
    """Test complete sbkube workflow with all phases."""

    def test_complete_workflow_prepare_phase(self, runner, examples_dir, tmp_path):
        """
        Test prepare phase of complete workflow.

        This test verifies that prepare correctly handles the configuration
        in examples/complete-workflow/config.yaml which includes various
        app types (pull-helm, pull-git, etc.).
        """
        # Verify example files exist
        example_dir = examples_dir / "complete-workflow"
        sources_file = example_dir / "sources.yaml"

        verify_example_exists(example_dir, required_files=["config.yaml", "sources.yaml"])

        # Get project root
        project_root = examples_dir.parent

        # Run prepare command
        result = run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources-file",
                str(sources_file.relative_to(project_root)),
            ],
            debug_info={
                "example_dir": example_dir,
                "sources_file": sources_file,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "prepare" in result.output.lower() or "준비" in result.output

    def test_complete_workflow_build_phase(self, runner, examples_dir, tmp_path):
        """
        Test build phase of complete workflow.

        This test runs prepare first, then builds the application.
        """
        # Verify example files exist
        example_dir = examples_dir / "complete-workflow"
        sources_file = example_dir / "sources.yaml"

        verify_example_exists(example_dir)

        # Get project root
        project_root = examples_dir.parent

        # Step 1: Prepare
        run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources-file",
                str(sources_file.relative_to(project_root)),
            ],
        )

        # Step 2: Build
        result = run_sbkube_command(
            runner,
            [
                "build",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
            ],
            debug_info={
                "example_dir": example_dir,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "build" in result.output.lower() or "빌드" in result.output

    def test_complete_workflow_deploy_phase_dry_run(self, runner, examples_dir, tmp_path):
        """
        Test deploy phase of complete workflow (dry-run).

        This test runs prepare and build first, then deploys with --dry-run.
        """
        # Verify example files exist
        example_dir = examples_dir / "complete-workflow"
        sources_file = example_dir / "sources.yaml"

        verify_example_exists(example_dir)

        # Get project root
        project_root = examples_dir.parent

        # Step 1: Prepare
        run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources-file",
                str(sources_file.relative_to(project_root)),
            ],
        )

        # Step 2: Build
        run_sbkube_command(
            runner,
            [
                "build",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
            ],
        )

        # Step 3: Deploy (dry-run)
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
