"""E2E tests for prepare command examples.

These tests use the actual examples/prepare/ directory to verify
prepare command functionality with real configuration files.
"""

import pytest

from tests.e2e.conftest import run_sbkube_command, verify_example_exists


@pytest.mark.e2e
@pytest.mark.requires_helm
class TestPrepareExamples:
    """Test prepare command with various example configurations."""

    def test_prepare_pull_helm_oci(self, runner, examples_dir, tmp_path):
        """Test prepare with OCI Helm chart pulling.

        This test verifies that prepare correctly pulls Helm charts
        from OCI registries as specified in examples/prepare/helm-oci/config.yaml.
        """
        # Verify example files exist
        example_dir = examples_dir / "prepare" / "helm-oci"
        verify_example_exists(
            example_dir, required_files=["config.yaml", "sources.yaml"]
        )

        # Get project root
        project_root = examples_dir.parent
        sources_file = example_dir / "sources.yaml"

        # Run prepare command
        result = run_sbkube_command(
            runner,
            [
                "prepare",
                "--app-dir",
                str(example_dir.relative_to(project_root)),
                "--base-dir",
                str(project_root),
                "--source",
                str(sources_file.relative_to(project_root)),
            ],
            debug_info={
                "example_dir": example_dir,
                "project_root": project_root,
                "sources_file": sources_file,
            },
        )

        # Verify output
        assert "prepare" in result.output.lower() or "준비" in result.output

        # Verify charts were downloaded
        charts_dir = project_root / "charts"
        assert charts_dir.exists(), f"Charts directory not created: {charts_dir}"

        # Based on config.yaml, we expect n8n-chart and rsshub-chart
        # Note: The exact chart directory names might vary
        chart_files = list(charts_dir.rglob("Chart.yaml"))
        assert len(chart_files) > 0, f"No Chart.yaml files found in {charts_dir}"
