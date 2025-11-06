"""Unit tests for helm_label_injection option in HelmApp model.

Tests verify that HelmApp Pydantic model validates helm_label_injection
field correctly for charts with strict schema validation.
"""

import pytest
from pydantic import ValidationError

from sbkube.models.config_model import HelmApp


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
