"""E2E test fixtures and utilities.

This module provides fixtures and helper functions for E2E tests
that use actual examples/ directory files.
"""

import shutil
import subprocess
from pathlib import Path

import click
import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def examples_dir() -> Path:
    """Return the examples directory path.

    Returns:
        Path: Path to examples/ directory

    """
    return Path("examples")


@pytest.fixture
def runner() -> CliRunner:
    """Provide a Click CLI test runner.

    Returns:
        CliRunner: Click test runner instance

    """
    return CliRunner()


def verify_example_exists(example_path: Path, required_files: list[str] | None = None):
    """Verify that an example directory exists and contains required files.

    Args:
        example_path: Path to the example directory
        required_files: List of required file names (default: ["config.yaml"])

    Raises:
        AssertionError: If directory or required files don't exist

    """
    if required_files is None:
        required_files = ["config.yaml"]

    assert example_path.exists(), f"Example directory not found: {example_path}"
    assert example_path.is_dir(), f"Example path is not a directory: {example_path}"

    for filename in required_files:
        file_path = example_path / filename
        # Support both .yaml and .yml extensions
        if not file_path.exists():
            alt_path = example_path / filename.replace(".yaml", ".yml")
            assert alt_path.exists(), (
                f"Required file not found: {filename} (tried {file_path} and {alt_path})"
            )


def run_sbkube_command(
    runner: CliRunner,
    command_args: list[str],
    expected_exit_code: int = 0,
    debug_info: dict | None = None,
) -> "click.testing.Result":
    """Run sbkube command and verify exit code with detailed error reporting.

    Args:
        runner: Click test runner
        command_args: List of command arguments
        expected_exit_code: Expected exit code (default: 0)
        debug_info: Optional debug information to include in error messages

    Returns:
        Result: Click test result object

    Raises:
        AssertionError: If exit code doesn't match expected value

    """
    result = runner.invoke(main, command_args)

    if result.exit_code != expected_exit_code:
        error_msg = [
            "\nsbkube command failed!",
            f"Command: sbkube {' '.join(command_args)}",
            f"Expected exit code: {expected_exit_code}",
            f"Actual exit code: {result.exit_code}",
            "\n--- Output ---",
            result.output,
        ]

        if result.exception:
            error_msg.append("\n--- Exception ---")
            error_msg.append(str(result.exception))
            import traceback

            error_msg.append("\n--- Traceback ---")
            error_msg.append(
                "".join(
                    traceback.format_exception(
                        type(result.exception),
                        result.exception,
                        result.exception.__traceback__,
                    )
                )
            )

        if debug_info:
            error_msg.append("\n--- Debug Info ---")
            for key, value in debug_info.items():
                error_msg.append(f"{key}: {value}")

        raise AssertionError("\n".join(error_msg))

    return result


@pytest.fixture
def verify_charts_downloaded(tmp_path: Path):
    """Fixture that returns a function to verify charts were downloaded.

    Args:
        tmp_path: Temporary directory path

    Returns:
        Callable: Function that verifies chart existence

    """

    def _verify(chart_name: str, base_dir: Path | None = None):
        """Verify that a Helm chart was downloaded.

        Args:
            chart_name: Name of the chart
            base_dir: Base directory (default: tmp_path)

        Raises:
            AssertionError: If chart directory doesn't exist

        """
        if base_dir is None:
            base_dir = tmp_path

        charts_dir = base_dir / "charts"
        chart_dir = charts_dir / chart_name

        assert charts_dir.exists(), f"Charts directory not found: {charts_dir}"
        assert chart_dir.exists(), f"Chart directory not found: {chart_dir}"
        assert chart_dir.is_dir(), f"Chart path is not a directory: {chart_dir}"

        # Verify Chart.yaml exists
        chart_yaml = chart_dir / "Chart.yaml"
        assert chart_yaml.exists(), f"Chart.yaml not found in {chart_dir}"

    return _verify


@pytest.fixture
def verify_build_output(tmp_path: Path):
    """Fixture that returns a function to verify build output.

    Args:
        tmp_path: Temporary directory path

    Returns:
        Callable: Function that verifies build output

    """

    def _verify(app_name: str, app_dir: Path):
        """Verify that build output exists.

        Args:
            app_name: Name of the application
            app_dir: Application directory path

        Raises:
            AssertionError: If build output doesn't exist

        """
        build_dir = app_dir / "build" / app_name
        assert build_dir.exists(), f"Build directory not found: {build_dir}"
        assert build_dir.is_dir(), f"Build path is not a directory: {build_dir}"

    return _verify


@pytest.fixture
def list_directory_contents():
    """Fixture that returns a function to list directory contents for debugging.

    Returns:
        Callable: Function that returns directory listing

    """

    def _list(directory: Path, pattern: str = "**/*") -> list[str]:
        """List all files in a directory matching pattern.

        Args:
            directory: Directory to list
            pattern: Glob pattern (default: "**/*")

        Returns:
            List[str]: List of file paths relative to directory

        """
        if not directory.exists():
            return [f"Directory does not exist: {directory}"]

        files = []
        for item in sorted(directory.glob(pattern)):
            relative_path = item.relative_to(directory)
            if item.is_dir():
                files.append(f"{relative_path}/")
            else:
                files.append(str(relative_path))

        return files

    return _list


# ============================================================================
# Environment Check Fixtures (for E2E test stability)
# ============================================================================


@pytest.fixture(scope="session")
def helm_available() -> bool:
    """Check if helm is available in PATH.

    Returns:
        bool: True if helm is available, False otherwise

    """
    return shutil.which("helm") is not None


@pytest.fixture(scope="session")
def kubectl_available() -> bool:
    """Check if kubectl is available in PATH.

    Returns:
        bool: True if kubectl is available, False otherwise

    """
    return shutil.which("kubectl") is not None


@pytest.fixture(scope="session")
def helm_version(helm_available) -> str | None:
    """Get helm version if available.

    Args:
        helm_available: Helm availability fixture

    Returns:
        str | None: Helm version string or None if not available

    """
    if not helm_available:
        return None
    try:
        result = subprocess.run(
            ["helm", "version", "--short"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return None


@pytest.fixture(autouse=True, scope="function")
def skip_if_helm_unavailable(request, helm_available):
    """Auto-skip tests marked with requires_helm if helm is not available.

    This fixture runs automatically for all E2E tests and checks if the test
    requires helm. If helm is not available, the test is skipped with a clear message.

    Args:
        request: pytest request object
        helm_available: Helm availability fixture

    """
    if request.node.get_closest_marker("requires_helm"):
        if not helm_available:
            pytest.skip(
                "Helm is not installed or not in PATH. Install helm to run this test."
            )


def is_k8s_cluster_reachable():
    """Check if a Kubernetes cluster is reachable."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture(autouse=True, scope="function")
def skip_if_k8s_unavailable(request, kubectl_available):
    """Auto-skip tests marked with requires_k8s if kubectl is not available or cluster is unreachable.

    This fixture runs automatically for all E2E tests and checks if the test
    requires kubectl and a reachable cluster. If either is not available, the test is skipped.

    Args:
        request: pytest request object
        kubectl_available: kubectl availability fixture

    """
    if request.node.get_closest_marker("requires_k8s"):
        if not kubectl_available:
            pytest.skip(
                "kubectl is not installed or not in PATH. Install kubectl to run this test."
            )
        if not is_k8s_cluster_reachable():
            pytest.skip(
                "Kubernetes cluster is not reachable. Ensure a cluster is running and kubeconfig is valid."
            )
