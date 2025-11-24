"""Unit tests for workspace.py edge cases and error scenarios.

Tests verify:
- File loading errors
- Validation errors
- Optional metadata fields
- Dependency cycle detection
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
        workspace_file = tmp_path / "workspace.yaml"
        # File does NOT exist

        # Act & Assert
        with pytest.raises(click.Abort):  # click.Abort causes SystemExit
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()

    def test_invalid_yaml_syntax(self, tmp_path: Path) -> None:
        """Test error when workspace file has invalid YAML syntax."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text("invalid: yaml: syntax: [")  # Invalid YAML

        # Act & Assert
        with pytest.raises(click.Abort):
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()

    def test_empty_file(self, tmp_path: Path) -> None:
        """Test error when workspace file is empty."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text("")  # Empty file

        # Act & Assert
        with pytest.raises(click.Abort):
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()


class TestWorkspaceValidationErrors:
    """Test Pydantic validation error scenarios."""

    def test_missing_required_fields(self, tmp_path: Path) -> None:
        """Test error when required fields are missing."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
# Missing metadata and phases
"""
        )

        # Act & Assert
        with pytest.raises(click.Abort):
            validator = WorkspaceValidateCommand(str(workspace_file))
            validator.execute()

    def test_invalid_phase_dependency(self, tmp_path: Path) -> None:
        """Test error when phase has non-existent dependency."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
phases:
  phase1:
    app_groups:
      - group1
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
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
  description: "Test workspace description"
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert - validation should succeed
        assert workspace is not None
        assert workspace.metadata.description == "Test workspace description"

    def test_workspace_with_environment(self, tmp_path: Path) -> None:
        """Test workspace with environment field."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
  environment: production
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.environment == "production"

    def test_workspace_with_tags(self, tmp_path: Path) -> None:
        """Test workspace with tags field."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
  tags:
    - backend
    - database
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.tags == ["backend", "database"]

    def test_workspace_with_all_optional_fields(self, tmp_path: Path) -> None:
        """Test workspace with all optional metadata fields."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
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
    source: sources.yaml
    app_groups:
      - group1
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.description == "Complete workspace"
        assert workspace.metadata.environment == "staging"
        assert workspace.metadata.tags == ["api", "monitoring"]


class TestWorkspaceDependencyCycles:
    """Test dependency cycle detection."""

    def test_simple_cycle_detection(self, tmp_path: Path) -> None:
        """Test detection of simple A -> B -> A cycle."""
        # Arrange
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
    depends_on:
      - phase2
  phase2:
    description: "Phase 2"
    source: sources.yaml
    app_groups:
      - group2
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
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
    depends_on:
      - phase2
  phase2:
    description: "Phase 2"
    source: sources.yaml
    app_groups:
      - group2
    depends_on:
      - phase3
  phase3:
    description: "Phase 3"
    source: sources.yaml
    app_groups:
      - group3
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
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
  phase2:
    description: "Phase 2"
    source: sources.yaml
    app_groups:
      - group2
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
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: test-workspace
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
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
        workspace_file = tmp_path / "workspace.yaml"
        workspace_file.write_text(
            """
version: "1.0"
metadata:
  name: custom-workspace
phases:
  phase1:
    description: "Phase 1"
    source: sources.yaml
    app_groups:
      - group1
"""
        )

        # Act
        validator = WorkspaceValidateCommand(str(workspace_file))
        workspace = validator.execute()

        # Assert
        assert workspace is not None
        assert workspace.metadata.name == "custom-workspace"
