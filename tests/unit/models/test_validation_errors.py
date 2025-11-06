"""Tests for validation errors and edge cases.
"""

import pytest

from sbkube.models.validators import ValidatorMixin, validate_spec_fields


class TestValidators:
    """Test custom validators."""

    def test_kubernetes_name_validation(self):
        """Test Kubernetes naming convention validation."""
        # Valid names
        assert ValidatorMixin.validate_kubernetes_name("my-app", "name") == "my-app"
        assert ValidatorMixin.validate_kubernetes_name("app-123", "name") == "app-123"
        assert ValidatorMixin.validate_kubernetes_name("a", "name") == "a"

        # Invalid names
        with pytest.raises(ValueError, match="must consist of lowercase"):
            ValidatorMixin.validate_kubernetes_name("My-App", "name")

        with pytest.raises(ValueError, match="cannot be empty"):
            ValidatorMixin.validate_kubernetes_name("", "name")

        with pytest.raises(ValueError, match="must start and end with"):
            ValidatorMixin.validate_kubernetes_name("-app", "name")

        with pytest.raises(ValueError, match="must start and end with"):
            ValidatorMixin.validate_kubernetes_name("app-", "name")

    def test_namespace_validation(self):
        """Test namespace validation."""
        # Valid namespaces
        assert ValidatorMixin.validate_namespace("default") == "default"
        assert ValidatorMixin.validate_namespace("my-namespace") == "my-namespace"
        assert ValidatorMixin.validate_namespace(None) is None

        # Invalid namespaces
        with pytest.raises(ValueError, match="must be less than 63"):
            ValidatorMixin.validate_namespace("a" * 64)

    def test_helm_version_validation(self):
        """Test Helm version format validation."""
        # Valid versions
        assert ValidatorMixin.validate_helm_version("1.2.3") == "1.2.3"
        assert ValidatorMixin.validate_helm_version("0.1.0-alpha.1") == "0.1.0-alpha.1"
        assert ValidatorMixin.validate_helm_version(None) is None

        # Invalid versions
        with pytest.raises(ValueError, match="Invalid Helm version"):
            ValidatorMixin.validate_helm_version("v1.2.3")

        with pytest.raises(ValueError, match="Invalid Helm version"):
            ValidatorMixin.validate_helm_version("1.2")

    def test_url_validation(self):
        """Test URL validation."""
        # Valid URLs
        assert (
            ValidatorMixin.validate_url("https://example.com", ["https"])
            == "https://example.com"
        )
        assert (
            ValidatorMixin.validate_url("http://localhost:8080", ["http", "https"])
            == "http://localhost:8080"
        )

        # Invalid URLs
        with pytest.raises(ValueError, match="URL cannot be empty"):
            ValidatorMixin.validate_url("", ["https"])

        with pytest.raises(ValueError, match="URL must start with"):
            ValidatorMixin.validate_url("ftp://example.com", ["http", "https"])

    def test_spec_fields_validation(self):
        """Test spec fields validation."""
        # Valid specs
        specs = validate_spec_fields("helm", {"repo": "grafana", "chart": "grafana"})
        assert specs["repo"] == "grafana"

        # Missing required fields
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_spec_fields("helm", {"repo": "grafana"})

        # Unknown app type
        with pytest.raises(ValueError, match="Unknown app type"):
            validate_spec_fields("unknown-type", {})
