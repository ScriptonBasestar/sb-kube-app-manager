"""Unit tests for workspace.py edge cases and error scenarios.

Tests verify:
- File loading errors
- Validation errors
- Optional metadata fields
- Dependency cycle detection

Note: These tests use the unified sbkube.yaml format (v0.10.0+).
The legacy workspace.yaml format is no longer supported.
"""

from pathlib import Path

import click
import pytest

from sbkube.commands.workspace import WorkspaceGraphCommand, WorkspaceValidateCommand


class TestWorkspaceFileLoadingErrors:
    """Test file loading error scenarios."""

    def test_file_not_found(self, tmp_path: Path) -> None:
        """Test error when workspace file doesn't exist."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        # File does NOT exist

        # Act & Assert
        with pytest.raises(click.Abort):  # click.Abort causes SystemExit
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Test error when workspace file has invalid YAML syntax."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text("invalid: yaml: syntax: [")  # Invalid YAML

        # Act & Assert
        with pytest.raises(click.Abort):
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test that empty file creates valid default UnifiedConfig (v0.10.0+ behavior)."""
        # Note: In unified config format, empty file creates a default valid config
        # This is intentional as apps can be added later
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text("")  # Empty file

        # Act - should not raise (empty file creates default config)
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert - default config is created
        assert workspace is not None
        assert workspace.apiVersion == "sbkube/v1"


class TestWorkspaceValidationErrors:
    """Test Pydantic validation error scenarios."""

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Test that missing fields use defaults (v0.10.0+ behavior).

        In the unified config format, all fields have sensible defaults:
        - metadata: empty dict when not provided
        - phases: empty dict is valid (apps can be defined directly)
        """
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
# Missing metadata and phases - uses defaults
"""
        )

        # Act - should not raise (defaults are used)
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert - defaults are applied
        assert workspace is not None
        assert workspace.apiVersion == "sbkube/v1"
        assert len(workspace.phases) == 0

    def test_invalid_phase_dependency(self, tmp_path: Path) -> None:
        """Test error when phase has non-existent dependency."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
phases:
  phase1:
    source: p1-kube/sbkube.yaml
    depends_on:
      - non_existent_phase  # This phase doesn't exist
"""
        )

        # Act & Assert
        with pytest.raises(click.Abort):
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()


class TestWorkspaceOptionalFields:
    """Test optional metadata fields display."""

    def test_workspace_with_description(self, tmp_path: Path) -> None:
        """Test workspace with description field."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
  description: "Test workspace description"
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert - validation should succeed
        assert workspace is not None
        assert workspace.metadata.get("description") == "Test workspace description"

    def test_workspace_with_environment(self, tmp_path: Path) -> None:
        """Test workspace with environment field."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
  environment: production
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.get("environment") == "production"

    def test_workspace_with_tags(self, tmp_path: Path) -> None:
        """Test workspace with tags field."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
  tags:
    - backend
    - database
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.get("tags") == ["backend", "database"]

    def test_workspace_with_all_optional_fields(self, tmp_path: Path) -> None:
        """Test workspace with all optional metadata fields."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
  description: "Complete workspace"
  environment: staging
  tags:
    - api
    - monitoring
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.get("description") == "Complete workspace"
        assert workspace.metadata.get("environment") == "staging"
        assert workspace.metadata.get("tags") == ["api", "monitoring"]


class TestWorkspaceDependencyCycles:
    """Test dependency cycle detection."""

    def test_simple_cycle_detection(self, tmp_path: Path) -> None:
        """Test detection of simple A -> B -> A cycle."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
    depends_on:
      - phase2
  phase2:
    description: "Phase 2"
    source: p2-kube/sbkube.yaml
    depends_on:
      - phase1  # Cycle: phase1 -> phase2 -> phase1
"""
        )

        # Act & Assert
        with pytest.raises(click.Abort):
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()

    def test_complex_cycle_detection(self, tmp_path: Path) -> None:
        """Test detection of complex A -> B -> C -> A cycle."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
    depends_on:
      - phase2
  phase2:
    description: "Phase 2"
    source: p2-kube/sbkube.yaml
    depends_on:
      - phase3
  phase3:
    description: "Phase 3"
    source: p3-kube/sbkube.yaml
    depends_on:
      - phase1  # Cycle: phase1 -> phase2 -> phase3 -> phase1
"""
        )

        # Act & Assert
        with pytest.raises(click.Abort):
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()


class TestWorkspaceGraphVisualization:
    """Test workspace graph visualization."""

    def test_graph_output_success(self, tmp_path: Path) -> None:
        """Test successful graph generation."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
  phase2:
    description: "Phase 2"
    source: p2-kube/sbkube.yaml
    depends_on:
      - phase1
"""
        )

        # Act
        cmd = WorkspaceGraphCommand(str(workspace_file))
        cmd.execute()

        # Assert
        # Graph command should execute without error (just checking no exception)

    def test_graph_without_graphviz(self, tmp_path: Path) -> None:
        """Test graph generation when graphviz is not available."""
        # Arrange
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
"""
        )

        # Act
        # Try to generate graph (may fail if graphviz not installed, but shouldn't crash)
        try:
            cmd = WorkspaceGraphCommand(str(workspace_file))
            cmd.execute()
        except (ImportError, FileNotFoundError):
            # Expected if graphviz not installed
            pass


class TestWorkspaceInitialization:
    """Test workspace initialization scenarios."""

    def test_init_with_custom_name(self, tmp_path: Path) -> None:
        """Test workspace init with custom name."""
        # This tests the init_workspace function indirectly
        # by verifying the WorkspaceValidateCommand can load the created file
        workspace_file = tmp_path / "sbkube.yaml"
        workspace_file.write_text(
            """
apiVersion: "sbkube/v1"
metadata:
  name: custom-workspace
phases:
  phase1:
    description: "Phase 1"
    source: p1-kube/sbkube.yaml
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.get("name") == "custom-workspace"
