"""
E2E tests for k3scode example workflows.

These tests use the actual examples/k3scode/ directory to verify
complete sbkube workflows with real configuration files.
"""


import pytest

from tests.e2e.conftest import run_sbkube_command, verify_example_exists


@pytest.mark.e2e
@pytest.mark.requires_helm
class TestK3scodeAIWorkflow:
    """Test k3scode AI application workflow."""

    def test_ai_prepare(self, runner, examples_dir, tmp_path, list_directory_contents):
        """
        Test k3scode AI prepare phase.

        This test verifies that the prepare command correctly downloads
        Helm charts and Git repositories specified in examples/k3scode/ai/config.yaml.
        """
        # Verify example files exist
        ai_dir = examples_dir / "k3scode" / "ai"
        sources_file = examples_dir / "k3scode" / "sources.yaml"

        verify_example_exists(ai_dir)
        assert sources_file.exists(), f"sources.yaml not found: {sources_file}"

        # Get project root (examples/ parent directory)
        project_root = examples_dir.parent

        # Run prepare command
        # Note: --app-dir is relative to --base-dir
        result = run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(ai_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources",
                str(sources_file.relative_to(project_root)),
                "--force",
            ],
            debug_info={
                "ai_dir": ai_dir,
                "sources_file": sources_file,
                "project_root": project_root,
                "relative_ai_dir": str(ai_dir.relative_to(project_root)),
            },
        )

        # Verify output
        assert "prepare" in result.output.lower() or "준비" in result.output

        # Verify charts/repos were downloaded
        # They are created in project_root, not tmp_path
        charts_dir = project_root / "charts"
        repos_dir = project_root / "repos"

        # At least one of charts or repos should exist based on config.yaml
        assert (
            charts_dir.exists() or repos_dir.exists()
        ), f"Neither charts nor repos directory created in {project_root}\nContents: {list_directory_contents(project_root)}"

    def test_ai_build(self, runner, examples_dir, tmp_path, list_directory_contents):
        """
        Test k3scode AI build phase.

        This test runs prepare first (to get dependencies), then builds
        the application using examples/k3scode/ai configuration.
        """
        # Verify example files exist
        ai_dir = examples_dir / "k3scode" / "ai"
        sources_file = examples_dir / "k3scode" / "sources.yaml"

        verify_example_exists(ai_dir)

        # Get project root
        project_root = examples_dir.parent

        # Step 1: Prepare (to get dependencies)
        run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(ai_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources",
                str(sources_file.relative_to(project_root)),
                "--force",
            ],
        )

        # Step 2: Build
        result = run_sbkube_command(
            runner,
            [
                "build",
                "--app-dir",
                str(ai_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
            ],
            debug_info={
                "ai_dir": ai_dir,
                "project_root": project_root,
                "base_dir_contents_before_build": list_directory_contents(project_root),
            },
        )

        # Verify output
        assert "build" in result.output.lower() or "빌드" in result.output


@pytest.mark.e2e
@pytest.mark.requires_helm
class TestK3scodeDevOpsWorkflow:
    """Test k3scode DevOps application workflow."""

    def test_devops_prepare(self, runner, examples_dir, tmp_path, list_directory_contents):
        """
        Test k3scode DevOps prepare phase.

        This test verifies that the prepare command correctly handles
        the DevOps configuration in examples/k3scode/devops/.
        """
        # Verify example files exist
        devops_dir = examples_dir / "k3scode" / "devops"
        sources_file = examples_dir / "k3scode" / "sources.yaml"

        verify_example_exists(devops_dir)
        assert sources_file.exists(), f"sources.yaml not found: {sources_file}"

        # Get project root
        project_root = examples_dir.parent

        # Run prepare command
        result = run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(devops_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources",
                str(sources_file.relative_to(project_root)),
                "--force",
            ],
            debug_info={
                "devops_dir": devops_dir,
                "sources_file": sources_file,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "prepare" in result.output.lower() or "준비" in result.output

    def test_devops_build(self, runner, examples_dir, tmp_path, list_directory_contents):
        """
        Test k3scode DevOps build phase.

        This test runs prepare first, then builds the DevOps application.
        """
        # Verify example files exist
        devops_dir = examples_dir / "k3scode" / "devops"
        sources_file = examples_dir / "k3scode" / "sources.yaml"

        verify_example_exists(devops_dir)

        # Get project root
        project_root = examples_dir.parent

        # Step 1: Prepare
        run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(devops_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources",
                str(sources_file.relative_to(project_root)),
                "--force",
            ],
        )

        # Step 2: Build
        result = run_sbkube_command(
            runner,
            [
                "build",
                "--app-dir",
                str(devops_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
            ],
            debug_info={
                "devops_dir": devops_dir,
                "project_root": project_root,
            },
        )

        # Verify output
        assert "build" in result.output.lower() or "빌드" in result.output


@pytest.mark.e2e
@pytest.mark.requires_helm
class TestK3scodeMemoryWorkflow:
    """Test k3scode Memory application workflow."""

    def test_memory_prepare(self, runner, examples_dir, tmp_path):
        """
        Test k3scode Memory prepare phase.

        This test verifies prepare for the memory configuration.
        """
        # Verify example files exist
        memory_dir = examples_dir / "k3scode" / "memory"
        sources_file = examples_dir / "k3scode" / "sources.yaml"

        config_file = memory_dir / "config.yaml"
        assert config_file.exists(), f"config.yaml not found: {config_file}"
        assert sources_file.exists(), f"sources.yaml not found: {sources_file}"

        # Get project root
        project_root = examples_dir.parent

        # Run prepare command
        result = run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(memory_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources",
                str(sources_file.relative_to(project_root)),
                "--force",
            ],
        )

        # Verify output
        assert "prepare" in result.output.lower() or "준비" in result.output


@pytest.mark.e2e
@pytest.mark.requires_helm
class TestK3scodeRDBWorkflow:
    """Test k3scode RDB application workflow."""

    def test_rdb_prepare(self, runner, examples_dir, tmp_path):
        """
        Test k3scode RDB prepare phase.

        This test verifies prepare for the RDB configuration.
        """
        # Verify example files exist
        rdb_dir = examples_dir / "k3scode" / "rdb"
        sources_file = examples_dir / "k3scode" / "sources.yaml"

        verify_example_exists(rdb_dir)
        assert sources_file.exists(), f"sources.yaml not found: {sources_file}"

        # Get project root
        project_root = examples_dir.parent

        # Run prepare command
        result = run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(rdb_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--sources",
                str(sources_file.relative_to(project_root)),
                "--force",
            ],
        )

        # Verify output
        assert "prepare" in result.output.lower() or "준비" in result.output
