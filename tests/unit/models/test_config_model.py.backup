"""
Tests for sbkube.models.config_model
"""

import pytest
from pydantic import ValidationError

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_model import (
    HelmApp,
    YamlApp,
    ActionApp,
    ExecApp,
    HttpApp,
)


class TestAppInfoScheme:
    """Test AppInfoScheme validation."""

    def test_valid_app_types(self):
        """Test that all supported app types are accepted."""
        # Each app type requires specific specs fields
        valid_types_with_specs = [
            ("exec", {"commands": ["echo test"]}),
            ("helm", {"values": []}),
            ("action", {"actions": []}),
            ("install-kustomize", {"kustomize_path": "."}),
            ("yaml", {"actions": []}),
            ("helm", {"repo": "test-repo", "chart": "test-chart"}),
            ("helm-oci", {"repo": "test-repo", "chart": "test-chart"}),
            ("git", {"repo": "https://github.com/test/repo", "paths": []}),
            ("pull-http", {"url": "https://example.com/file.yaml", "paths": []}),
            ("http", {"paths": []}),
        ]

        for app_type, specs in valid_types_with_specs:
            app = AppInfoScheme(name="test-app", type=app_type, specs=specs)
            assert app.type == app_type

    def test_invalid_app_type(self):
        """Test that invalid app types are rejected."""
        with pytest.raises(ConfigValidationError) as exc_info:
            AppInfoScheme(name="test-app", type="invalid-type", specs={})

        assert "Input should be" in str(exc_info.value)

    def test_copy_app_validation(self):
        """Test copy-app type validation."""
        app = AppInfoScheme(
            name="my-copy-app",
            type="http",
            specs={"paths": [{"src": "source-dir", "dest": "dest-dir"}]},
        )
        assert app.name == "my-copy-app"
        assert app.type == "http"

    def test_install_yaml_validation(self):
        """Test yaml type validation."""
        app = AppInfoScheme(
            name="my-yaml-app",
            type="yaml",
            specs={"actions": [{"type": "apply", "path": "manifest.yaml"}]},
        )
        assert app.name == "my-yaml-app"
        assert app.type == "yaml"


class TestGetSpecModel:
    """Test get_spec_model function."""

    def test_copy_app_spec_model(self):
        """Test that copy-app returns AppCopySpec."""
        spec_model = get_spec_model("http")
        assert spec_model == AppCopySpec

    def test_install_yaml_spec_model(self):
        """Test that yaml returns AppInstallActionSpec."""
        spec_model = get_spec_model("yaml")
        assert spec_model == AppInstallActionSpec

    def test_install_action_spec_model(self):
        """Test that install-action returns AppInstallActionSpec."""
        spec_model = get_spec_model("action")
        assert spec_model == AppInstallActionSpec

    def test_unknown_type(self):
        """Test that unknown type returns None."""
        spec_model = get_spec_model("unknown-type")
        assert spec_model is None

    def test_all_supported_types_have_specs(self):
        """Test that all supported types have corresponding spec models."""
        supported_types = [
            "exec",
            "helm",
            "action",
            "install-kustomize",
            "yaml",
            "helm",
            "helm-oci",
            "git",
            "pull-http",
            "http",
        ]

        for app_type in supported_types:
            spec_model = get_spec_model(app_type)
            assert spec_model is not None, f"No spec model found for type: {app_type}"


class TestSpecModels:
    """Test spec model validation."""

    def test_app_copy_spec(self):
        """Test AppCopySpec validation."""
        spec = AppCopySpec(
            paths=[
                {"src": "source1", "dest": "dest1"},
                {"src": "source2", "dest": "dest2"},
            ]
        )
        assert len(spec.paths) == 2
        assert spec.paths[0].src == "source1"
        assert spec.paths[0].dest == "dest1"

    def test_app_install_action_spec(self):
        """Test AppInstallActionSpec validation."""
        spec = AppInstallActionSpec(
            actions=[
                {"type": "apply", "path": "manifest1.yaml"},
                {"type": "create", "path": "manifest2.yaml"},
            ]
        )
        assert len(spec.actions) == 2
        assert spec.actions[0].type == "apply"
        assert spec.actions[0].path == "manifest1.yaml"
