"""Unit tests for SSA conflict detection in deploy_helm_app().

Tests verify:
- SSA conflict keyword detection
- Conflict info parsing from stderr
- SSAConflictError raised on conflict
- Non-SSA errors not misclassified
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sbkube.commands.deploy import _parse_ssa_conflict_info, deploy_helm_app
from sbkube.exceptions import SSAConflictError
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


class TestParseSSAConflictInfo:
    """Test _parse_ssa_conflict_info parser."""

    def test_parse_manager_and_fields(self) -> None:
        """Test extracting manager name and field paths from typical stderr."""
        stderr = (
            'UPGRADE FAILED: conflict occurred while applying object '
            'kube-system/traefik-configmap-providers /v1, Kind=ConfigMap: '
            'Apply failed with 6 conflicts: conflicts with '
            '"kubectl-client-side-apply" using v1:\n'
            "- .data.traefik2.toml\n"
            "- .data.traefik2_rules_common.toml\n"
            "- .data.traefik2_rules_devops.toml\n"
        )
        manager, fields = _parse_ssa_conflict_info(stderr)
        assert manager == "kubectl-client-side-apply"
        assert len(fields) == 3
        assert ".data.traefik2.toml" in fields
        assert ".data.traefik2_rules_common.toml" in fields

    def test_parse_no_manager(self) -> None:
        """Test when manager name cannot be extracted."""
        stderr = "Apply failed with conflicts: unknown error"
        manager, fields = _parse_ssa_conflict_info(stderr)
        assert manager is None
        assert fields == []

    def test_parse_fields_only(self) -> None:
        """Test when fields exist but manager pattern differs."""
        stderr = (
            "field manager conflict detected\n"
            "- .spec.template.spec.containers\n"
            "- .metadata.labels\n"
        )
        manager, fields = _parse_ssa_conflict_info(stderr)
        assert manager is None
        assert len(fields) == 2


class TestSSAConflictDetection:
    """Test SSA conflict detection in deploy_helm_app."""

    @patch("sbkube.commands.deploy.run_command")
    def test_ssa_conflict_raises_error(self, mock_run_command, tmp_path: Path) -> None:
        """Test that SSA conflict stderr raises SSAConflictError."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        app_build_dir = build_dir / "traefik"
        app_build_dir.mkdir()
        (app_build_dir / "Chart.yaml").write_text("name: traefik\nversion: 1.0.0")

        app = HelmApp(
            type="helm",
            chart="traefik/traefik",
            namespace="kube-system",
        )

        ssa_stderr = (
            'UPGRADE FAILED: conflict occurred while applying object '
            'kube-system/traefik-configmap /v1, Kind=ConfigMap: '
            'Apply failed with 2 conflicts: conflicts with '
            '"kubectl-client-side-apply" using v1:\n'
            "- .data.config.toml\n"
            "- .data.rules.toml\n"
        )

        # First call: namespace check (success), second call: helm upgrade (SSA conflict)
        mock_run_command.side_effect = [
            (0, '{"kind":"Namespace"}', ""),  # namespace check
            (1, "", ssa_stderr),  # helm upgrade fails with SSA conflict
        ]

        output = MagicMock(spec=OutputManager)

        with pytest.raises(SSAConflictError) as exc_info:
            deploy_helm_app(
                app_name="traefik",
                app=app,
                base_dir=tmp_path,
                charts_dir=tmp_path / "charts",
                build_dir=build_dir,
                app_config_dir=tmp_path / "config",
                output=output,
            )

        assert exc_info.value.release_name == "traefik"
        assert exc_info.value.conflicting_manager == "kubectl-client-side-apply"
        assert ".data.config.toml" in exc_info.value.conflicting_fields

    @patch("sbkube.commands.deploy.run_command")
    def test_non_ssa_error_not_caught(self, mock_run_command, tmp_path: Path) -> None:
        """Test that non-SSA errors are not misclassified."""
        build_dir = tmp_path / "build"
        build_dir.mkdir()
        app_build_dir = build_dir / "nginx"
        app_build_dir.mkdir()
        (app_build_dir / "Chart.yaml").write_text("name: nginx\nversion: 1.0.0")

        app = HelmApp(
            type="helm",
            chart="bitnami/nginx",
            namespace="default",
        )

        # Generic helm error (not SSA)
        mock_run_command.side_effect = [
            (0, '{"kind":"Namespace"}', ""),
            (1, "", "Error: UPGRADE FAILED: rendered manifests contain a resource that already exists"),
        ]

        output = MagicMock(spec=OutputManager)

        result = deploy_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path / "config",
            output=output,
        )

        assert result is False
        # Should NOT raise SSAConflictError
        output.print_error.assert_called()
