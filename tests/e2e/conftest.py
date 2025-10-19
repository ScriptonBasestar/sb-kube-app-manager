"""
E2E test fixtures and utilities.

This module provides fixtures and helper functions for E2E tests
that use actual examples/ directory files.
"""

from pathlib import Path
from typing import List, Optional

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def examples_dir() -> Path:
    """
    Return the examples directory path.

    Returns:
        Path: Path to examples/ directory
    """
    return Path("examples")


@pytest.fixture
def runner() -> CliRunner:
    """
    Provide a Click CLI test runner.

    Returns:
        CliRunner: Click test runner instance
    """
    return CliRunner()


def verify_example_exists(example_path: Path, required_files: Optional[List[str]] = None):
    """
    Verify that an example directory exists and contains required files.

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
            assert (
                alt_path.exists()
            ), f"Required file not found: {filename} (tried {file_path} and {alt_path})"


def run_sbkube_command(
    runner: CliRunner,
    command_args: List[str],
    expected_exit_code: int = 0,
    debug_info: Optional[dict] = None,
) -> "click.testing.Result":
    """
    Run sbkube command and verify exit code with detailed error reporting.

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
            f"\nsbkube command failed!",
            f"Command: sbkube {' '.join(command_args)}",
            f"Expected exit code: {expected_exit_code}",
            f"Actual exit code: {result.exit_code}",
            f"\n--- Output ---",
            result.output,
        ]

        if result.exception:
            error_msg.append(f"\n--- Exception ---")
            error_msg.append(str(result.exception))
            import traceback

            error_msg.append("\n--- Traceback ---")
            error_msg.append("".join(traceback.format_exception(type(result.exception), result.exception, result.exception.__traceback__)))

        if debug_info:
            error_msg.append(f"\n--- Debug Info ---")
            for key, value in debug_info.items():
                error_msg.append(f"{key}: {value}")

        raise AssertionError("\n".join(error_msg))

    return result


@pytest.fixture
def verify_charts_downloaded(tmp_path: Path):
    """
    Fixture that returns a function to verify charts were downloaded.

    Args:
        tmp_path: Temporary directory path

    Returns:
        Callable: Function that verifies chart existence
    """

    def _verify(chart_name: str, base_dir: Optional[Path] = None):
        """
        Verify that a Helm chart was downloaded.

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
    """
    Fixture that returns a function to verify build output.

    Args:
        tmp_path: Temporary directory path

    Returns:
        Callable: Function that verifies build output
    """

    def _verify(app_name: str, app_dir: Path):
        """
        Verify that build output exists.

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
    """
    Fixture that returns a function to list directory contents for debugging.

    Returns:
        Callable: Function that returns directory listing
    """

    def _list(directory: Path, pattern: str = "**/*") -> List[str]:
        """
        List all files in a directory matching pattern.

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
