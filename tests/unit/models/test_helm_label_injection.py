"""Unit tests for helm_label_injection option in HelmApp model.

Tests verify that HelmApp Pydantic model validates helm_label_injection
field correctly for charts with strict schema validation.
"""

from sbkube.models.config_model import HelmApp
from sbkube.utils.app_labels import (
    KNOWN_INCOMPATIBLE_CHARTS,
    get_label_injection_recommendation,
    is_chart_label_injection_compatible,
)


class TestHelmLabelInjectionPydanticModel:
    """Test that HelmApp Pydantic model validates helm_label_injection correctly."""

    def test_default_helm_label_injection_is_true(self) -> None:
        """Default value should be True (automatic label injection enabled)."""
        app = HelmApp(
            type="helm",
            chart="grafana/grafana",
        )
        assert app.helm_label_injection is True

    def test_helm_label_injection_can_be_false(self) -> None:
        """Should accept False value (for strict schema charts like Authelia)."""
        app = HelmApp(
            type="helm",
            chart="authelia/authelia",
            helm_label_injection=False,
        )
        assert app.helm_label_injection is False

    def test_helm_label_injection_can_be_true(self) -> None:
        """Should accept explicit True value."""
        app = HelmApp(
            type="helm",
            chart="grafana/grafana",
            helm_label_injection=True,
        )
        assert app.helm_label_injection is True

    def test_helm_label_injection_accepts_truthy_values(self) -> None:
        """Pydantic should coerce truthy values to boolean (e.g., 'yes', 1, True)."""
        # Pydantic automatically converts truthy values to bool
        app1 = HelmApp(
            type="helm",
            chart="grafana/grafana",
            helm_label_injection="yes",  # type: ignore[arg-type]
        )
        assert app1.helm_label_injection is True

        app2 = HelmApp(
            type="helm",
            chart="grafana/grafana",
            helm_label_injection=1,  # type: ignore[arg-type]
        )
        assert app2.helm_label_injection is True

        # Test integer 0 = False
        app3 = HelmApp(
            type="helm",
            chart="grafana/grafana",
            helm_label_injection=0,  # type: ignore[arg-type]
        )
        assert app3.helm_label_injection is False

    def test_helm_label_injection_with_full_config(self) -> None:
        """Test helm_label_injection works with full Helm app configuration."""
        app = HelmApp(
            type="helm",
            chart="authelia/authelia",
            version="0.9.3",
            namespace="auth",
            values=["authelia.yaml"],
            helm_label_injection=False,  # Disabled for strict schema
            labels={"env": "production"},
            annotations={"description": "Authentication service"},
            create_namespace=True,
            wait=True,
            timeout="10m",
        )

        assert app.helm_label_injection is False
        assert app.chart == "authelia/authelia"
        assert app.version == "0.9.3"
        assert app.namespace == "auth"

    def test_model_serialization_includes_helm_label_injection(self) -> None:
        """Test that helm_label_injection is included in model serialization."""
        app = HelmApp(
            type="helm",
            chart="authelia/authelia",
            helm_label_injection=False,
        )

        # Test model_dump (Pydantic v2)
        data = app.model_dump()
        assert "helm_label_injection" in data
        assert data["helm_label_injection"] is False

    def test_model_with_default_serialization(self) -> None:
        """Test that default value (True) is serialized correctly."""
        app = HelmApp(
            type="helm",
            chart="grafana/grafana",
        )

        data = app.model_dump()
        assert data["helm_label_injection"] is True

    def test_strict_schema_use_case_config(self) -> None:
        """Test configuration pattern for strict schema charts (Authelia use case)."""
        # Simulate config.yaml entry for Authelia
        config_dict = {
            "type": "helm",
            "chart": "authelia/authelia",
            "version": "0.9.3",
            "namespace": "auth",
            "values": ["authelia.yaml"],
            "helm_label_injection": False,  # Key setting for strict schema
        }

        app = HelmApp(**config_dict)
        assert app.helm_label_injection is False
        assert app.chart == "authelia/authelia"

    def test_normal_chart_use_case_config(self) -> None:
        """Test configuration pattern for normal charts (Grafana use case)."""
        # Simulate config.yaml entry for Grafana (supports commonLabels)
        config_dict = {
            "type": "helm",
            "chart": "grafana/grafana",
            "version": "6.50.0",
            # helm_label_injection not specified = defaults to True
        }

        app = HelmApp(**config_dict)
        assert app.helm_label_injection is True
        assert app.chart == "grafana/grafana"


class TestChartCompatibility:
    """Test chart compatibility detection for label injection."""

    def test_known_incompatible_charts_list_exists(self) -> None:
        """Known incompatible charts list should exist and contain key charts."""
        assert "traefik" in KNOWN_INCOMPATIBLE_CHARTS
        assert "traefik/traefik" in KNOWN_INCOMPATIBLE_CHARTS
        assert "authelia" in KNOWN_INCOMPATIBLE_CHARTS

    def test_traefik_is_incompatible(self) -> None:
        """Traefik chart should be detected as incompatible."""
        assert is_chart_label_injection_compatible("traefik/traefik") is False
        assert is_chart_label_injection_compatible("traefik") is False
        assert is_chart_label_injection_compatible("Traefik/Traefik") is False  # case insensitive

    def test_authelia_is_incompatible(self) -> None:
        """Authelia chart should be detected as incompatible."""
        assert is_chart_label_injection_compatible("authelia/authelia") is False
        assert is_chart_label_injection_compatible("authelia") is False

    def test_cert_manager_is_incompatible(self) -> None:
        """cert-manager chart should be detected as incompatible."""
        assert is_chart_label_injection_compatible("cert-manager/cert-manager") is False
        assert is_chart_label_injection_compatible("cert-manager") is False
        assert is_chart_label_injection_compatible("jetstack/cert-manager") is False

    def test_grafana_is_compatible(self) -> None:
        """Grafana chart should be compatible (supports commonLabels)."""
        assert is_chart_label_injection_compatible("grafana/grafana") is True
        assert is_chart_label_injection_compatible("grafana") is True

    def test_bitnami_redis_is_compatible(self) -> None:
        """Bitnami Redis chart should be compatible."""
        assert is_chart_label_injection_compatible("bitnami/redis") is True

    def test_prometheus_is_compatible(self) -> None:
        """Prometheus chart should be compatible."""
        assert is_chart_label_injection_compatible("prometheus-community/prometheus") is True

    def test_recommendation_for_incompatible_chart(self) -> None:
        """Should return recommendation message for incompatible charts."""
        recommendation = get_label_injection_recommendation("traefik/traefik")
        assert recommendation is not None
        assert "traefik" in recommendation.lower()
        assert "commonlabels" in recommendation.lower() or "label injection" in recommendation.lower()

    def test_no_recommendation_for_compatible_chart(self) -> None:
        """Should return None for compatible charts."""
        recommendation = get_label_injection_recommendation("grafana/grafana")
        assert recommendation is None

    def test_empty_chart_name(self) -> None:
        """Empty chart name should be treated as compatible."""
        assert is_chart_label_injection_compatible("") is True

    def test_chart_name_extraction(self) -> None:
        """Should extract chart name from repo/chart format."""
        # Full path should work
        assert is_chart_label_injection_compatible("traefik/traefik") is False
        # Just chart name should also work
        assert is_chart_label_injection_compatible("traefik") is False


class TestSourcesConfiguration:
    """Test sources.yaml configuration for label injection."""

    def test_extra_incompatible_charts(self) -> None:
        """Should treat extra_incompatible charts as incompatible."""
        # Without extra, my-custom-chart is compatible
        assert is_chart_label_injection_compatible("my-custom-chart") is True

        # With extra, my-custom-chart becomes incompatible
        assert is_chart_label_injection_compatible(
            "my-custom-chart",
            extra_incompatible=["my-custom-chart"],
        ) is False

    def test_force_compatible_overrides_builtin(self) -> None:
        """force_compatible should override built-in incompatible list."""
        # Traefik is normally incompatible
        assert is_chart_label_injection_compatible("traefik") is False

        # But force_compatible overrides it
        assert is_chart_label_injection_compatible(
            "traefik",
            force_compatible=["traefik"],
        ) is True

    def test_force_compatible_overrides_extra_incompatible(self) -> None:
        """force_compatible should override extra_incompatible."""
        # my-chart is in extra_incompatible
        assert is_chart_label_injection_compatible(
            "my-chart",
            extra_incompatible=["my-chart"],
        ) is False

        # But force_compatible overrides it
        assert is_chart_label_injection_compatible(
            "my-chart",
            extra_incompatible=["my-chart"],
            force_compatible=["my-chart"],
        ) is True

    def test_case_insensitive_matching(self) -> None:
        """Matching should be case-insensitive."""
        assert is_chart_label_injection_compatible(
            "My-Custom-Chart",
            extra_incompatible=["my-custom-chart"],
        ) is False

        assert is_chart_label_injection_compatible(
            "TRAEFIK",
            force_compatible=["traefik"],
        ) is True

    def test_repo_chart_format_in_extra_list(self) -> None:
        """Should handle repo/chart format in extra lists."""
        assert is_chart_label_injection_compatible(
            "myrepo/mychart",
            extra_incompatible=["myrepo/mychart"],
        ) is False

        # Just chart name should also match
        assert is_chart_label_injection_compatible(
            "mychart",
            extra_incompatible=["myrepo/mychart"],
        ) is False
