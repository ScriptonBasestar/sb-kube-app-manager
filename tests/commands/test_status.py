"""Tests for sbkube status command (Phase 1-7)."""

import pytest
from click.testing import CliRunner

from sbkube.cli import main


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestStatusBasic:
    """Basic status command tests."""

    def test_status_help(self, runner) -> None:
        """Test status --help displays correctly."""
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0
        assert "Display application and cluster status" in result.output
        assert "--by-group" in result.output
        assert "--deps" in result.output
        assert "--health-check" in result.output

    def test_status_requires_sources_yaml(self, runner, tmp_path) -> None:
        """Test status fails without sources.yaml."""
        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "sources.yaml not found" in result.output


class TestStatusByGroup:
    """Tests for --by-group option (Phase 4)."""

    def test_status_by_group_option_exists(self, runner) -> None:
        """Test --by-group option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--by-group" in result.output
        assert "Group applications by app-group" in result.output


@pytest.mark.integration
class TestStatusDeps:
    """Tests for --deps option (Phase 6)."""

    def test_status_deps_option_exists(self, runner) -> None:
        """Test --deps option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--deps" in result.output
        assert "Show dependency tree" in result.output

    @pytest.mark.unit
    def test_status_deps_without_config(self, runner, tmp_path) -> None:
        """Test --deps fails gracefully without config.yaml."""
        # Create minimal sources.yaml
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("""
kubeconfig: ~/.kube/config
kubeconfig_context: test-context
cluster: test-cluster
""")

        result = runner.invoke(main, ["status", "--deps", "--base-dir", str(tmp_path)])
        # Should fail because config.yaml is missing
        assert result.exit_code != 0


class TestStatusHealthCheck:
    """Tests for --health-check option (Phase 7)."""

    def test_status_health_check_option_exists(self, runner) -> None:
        """Test --health-check option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--health-check" in result.output
        assert "Show detailed health check status" in result.output


@pytest.mark.integration
class TestStatusManaged:
    """Tests for --managed option (Phase 4)."""

    def test_status_managed_option_exists(self, runner) -> None:
        """Test --managed option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--managed" in result.output
        assert "Show only sbkube-managed applications" in result.output


class TestStatusUnhealthy:
    """Tests for --unhealthy option (Phase 4)."""

    def test_status_unhealthy_option_exists(self, runner) -> None:
        """Test --unhealthy option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--unhealthy" in result.output
        assert "Show only unhealthy resources" in result.output


class TestStatusShowNotes:
    """Tests for --show-notes option (Documentation as Code feature)."""

    def test_status_show_notes_option_exists(self, runner) -> None:
        """Test --show-notes option is available."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--show-notes" in result.output
        assert "Show application notes" in result.output


class TestStatusAppGroup:
    """Tests for app-group argument (Phase 4)."""

    def test_status_specific_app_group(self, runner) -> None:
        """Test status with specific app-group argument."""
        result = runner.invoke(main, ["status", "--help"])
        assert "app_group" in result.output or "APP_GROUP" in result.output


class TestStatusLLMOutput:
    """Tests for LLM-friendly output format (Phase 3)."""

    def test_status_with_llm_format_help(self, runner) -> None:
        """Test --format option is available."""
        result = runner.invoke(main, ["--help"])
        assert "--format" in result.output
        assert "llm" in result.output

    def test_status_requires_sources_even_with_llm_format(
        self, runner, tmp_path
    ) -> None:
        """Test status with --format llm still requires sources.yaml."""
        result = runner.invoke(
            main, ["--format", "llm", "status", "--base-dir", str(tmp_path)]
        )
        assert result.exit_code != 0
        # Should still show error about missing sources.yaml


class TestStatusOptionCombinations:
    """Tests for option combinations."""

    def test_status_by_group_and_health_check(self, runner) -> None:
        """Test combining --by-group and --health-check."""
        result = runner.invoke(main, ["status", "--help"])
        # Both options should be available
        assert "--by-group" in result.output
        assert "--health-check" in result.output

    def test_status_managed_and_unhealthy(self, runner) -> None:
        """Test combining --managed and --unhealthy."""
        result = runner.invoke(main, ["status", "--help"])
        assert "--managed" in result.output
        assert "--unhealthy" in result.output


class TestStatusValidation:
    """Tests for sources.yaml validation."""

    def test_status_with_invalid_sources_yaml(self, runner, tmp_path) -> None:
        """Test status with invalid sources.yaml content."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("invalid: [unclosed")

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "Failed to load sources.yaml" in result.output

    def test_status_without_kubeconfig_field(self, runner, tmp_path) -> None:
        """Test status fails without kubeconfig field."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("""
cluster: test-cluster
kubeconfig_context: test-context
""")

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "kubeconfig" in result.output

    def test_status_without_kubeconfig_context(self, runner, tmp_path) -> None:
        """Test status fails without kubeconfig_context field."""
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text("""
cluster: test-cluster
kubeconfig: ~/.kube/config
""")

        result = runner.invoke(main, ["status", "--base-dir", str(tmp_path)])
        assert result.exit_code != 0
        assert "kubeconfig_context" in result.output


class TestStatusHelperFunctions:
    """Tests for status command helper functions."""

    def test_format_health_statuses(self) -> None:
        """Test _format_health() with various health statuses."""
        from sbkube.commands.status import _format_health

        # Function expects lowercase, returns formatted string
        assert "Healthy" in _format_health("healthy")
        assert "Unhealthy" in _format_health("unhealthy")
        assert "Unhealthy" in _format_health("unknown")  # Default fallback
        assert "Degraded" in _format_health("degraded")

    def test_format_release_statuses(self) -> None:
        """Test _format_release_status() with various statuses."""
        from sbkube.commands.status import _format_release_status

        assert "deployed" in _format_release_status("deployed")
        assert "failed" in _format_release_status("failed")
        assert "pending" in _format_release_status("pending-install")
        assert "pending" in _format_release_status("pending-upgrade")
        assert "unknown" in _format_release_status("unknown")

    def test_format_age_various_durations(self) -> None:
        """Test _format_age() with various durations."""
        from sbkube.commands.status import _format_age

        # Test None
        assert _format_age(None) == "unknown"

        # Test seconds (< 60)
        assert _format_age(30) == "30s"
        assert _format_age(59) == "59s"

        # Test minutes (60-3599)
        assert _format_age(60) == "1m 0s"
        assert _format_age(90) == "1m 30s"
        assert _format_age(3599) == "59m 59s"

        # Test hours (>= 3600)
        assert _format_age(3600) == "1h 0m"
        assert _format_age(7200) == "2h 0m"
        assert _format_age(86399) == "23h 59m"

    def test_format_duration(self) -> None:
        """Test _format_duration() for various durations."""
        from sbkube.commands.status import _format_duration

        # _format_duration is an alias for _format_age
        assert _format_duration(30) == "30s"
        assert _format_duration(60) == "1m 0s"
        assert _format_duration(125) == "2m 5s"

    def test_get_pod_health_status(self) -> None:
        """Test _get_pod_health_status() with various pod states."""
        from sbkube.commands.status import _get_pod_health_status

        # Healthy running pod (all containers ready)
        pod = {
            "phase": "Running",
            "ready_containers": 2,
            "total_containers": 2,
            "restart_count": 0,
            "conditions": [{"type": "Ready", "status": "True"}],
        }
        assert _get_pod_health_status(pod) == "Healthy"

        # Failed pod
        pod = {"phase": "Failed"}
        assert "failed" in _get_pod_health_status(pod).lower()

        # Pending pod (waiting to start)
        pod = {
            "phase": "Pending",
            "ready_containers": 0,
            "total_containers": 1,
            "conditions": [],
        }
        assert "Waiting to start" in _get_pod_health_status(pod)

        # Running but not all containers ready
        pod = {
            "phase": "Running",
            "ready_containers": 1,
            "total_containers": 2,
            "restart_count": 0,
        }
        result = _get_pod_health_status(pod)
        assert "1/2" in result or "containers ready" in result.lower()

        # Completed/Succeeded pod
        pod = {"phase": "Succeeded"}
        assert "Completed" in _get_pod_health_status(pod)

        # Missing phase defaults to Unknown
        pod = {}
        assert "Unknown" in _get_pod_health_status(pod)


class TestStatusDependencyTree:
    """Tests for dependency tree functionality."""

    def test_build_dependency_map(self) -> None:
        """Test _build_dependency_map() creates correct mapping."""
        from sbkube.commands.status import _build_dependency_map
        from types import SimpleNamespace

        # Create app objects (function expects app.name and app.deps attributes)
        apps = [
            SimpleNamespace(name="app1", deps=None),
            SimpleNamespace(name="app2", deps=["app1"]),
            SimpleNamespace(name="app3", deps=["app1", "app2"]),
        ]

        dep_map = _build_dependency_map(apps)

        # Function only includes apps with dependencies
        assert dep_map == {
            "app2": ["app1"],
            "app3": ["app1", "app2"],
        }

    def test_build_dependency_map_empty(self) -> None:
        """Test _build_dependency_map() with no dependencies."""
        from sbkube.commands.status import _build_dependency_map
        from types import SimpleNamespace

        apps = [
            SimpleNamespace(name="app1", deps=None),
            SimpleNamespace(name="app2", deps=[]),
        ]

        dep_map = _build_dependency_map(apps)

        # No apps with dependencies
        assert dep_map == {}

    def test_detect_circular_dependencies_none(self) -> None:
        """Test _detect_circular_dependencies() with no cycles."""
        from sbkube.commands.status import _detect_circular_dependencies

        dep_map = {
            "app2": ["app1"],
            "app3": ["app2"],
        }

        cycles = _detect_circular_dependencies(dep_map)
        assert cycles == []

    def test_detect_circular_dependencies_simple_cycle(self) -> None:
        """Test _detect_circular_dependencies() with simple cycle."""
        from sbkube.commands.status import _detect_circular_dependencies

        dep_map = {
            "app1": ["app2"],
            "app2": ["app1"],
        }

        cycles = _detect_circular_dependencies(dep_map)
        assert len(cycles) > 0

    def test_find_root_apps(self) -> None:
        """Test _find_root_apps() identifies root apps."""
        from sbkube.commands.status import _find_root_apps
        from types import SimpleNamespace

        apps = [
            SimpleNamespace(name="app1", deps=None),
            SimpleNamespace(name="app2", deps=["app1"]),
            SimpleNamespace(name="app3", deps=["app2"]),
        ]

        # Dependency map includes apps with dependencies
        # all_deps will be {"app1", "app2"}
        dep_map = {"app2": ["app1"], "app3": ["app2"]}
        roots = _find_root_apps(apps, dep_map)

        # Function returns app objects
        # app1: not in dep_map OR not in all_deps -> root (not in all_deps)
        # app2: in dep_map AND in all_deps -> not root
        # app3: in dep_map AND not in all_deps -> root (not depended upon)
        root_names = [app.name for app in roots]
        assert "app1" in root_names  # Not depended upon by anyone
        assert "app2" not in root_names  # Depended upon by app3
        assert "app3" in root_names  # Not depended upon by anyone


class TestStatusCacheData:
    """Tests for cache data preparation."""

    def test_prepare_cache_data_structure(self) -> None:
        """Test _prepare_cache_data() returns raw status data."""
        from sbkube.commands.status import _prepare_cache_data
        from sbkube.utils.cluster_cache import ClusterCache
        from pathlib import Path
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            cache = ClusterCache(
                cache_dir=Path(tmpdir),
                context="test-context",
                cluster="test-cluster",
                by_group=False,
            )

            status_data = {
                "releases": [
                    {"name": "app1", "namespace": "default", "status": "deployed"}
                ],
                "pods": [
                    {"name": "app1-pod", "namespace": "default", "phase": "Running"}
                ],
            }

            # Function returns status_data as-is (no metadata added)
            cached_data = _prepare_cache_data(status_data, cache)

            assert "releases" in cached_data
            assert "pods" in cached_data
            assert cached_data == status_data  # Returns input unchanged


# Integration tests (require actual cluster)
@pytest.mark.integration
class TestStatusIntegration:
    """Integration tests for status command."""
