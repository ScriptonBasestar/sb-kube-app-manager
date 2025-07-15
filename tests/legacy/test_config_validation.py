"""
Tests for configuration validation and inheritance system.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from sbkube.exceptions import ConfigValidationError
from sbkube.models.config_manager import ConfigManager
from sbkube.models.config_model_v2 import (AppGroupScheme, AppInfoScheme,
                                           AppInstallHelmSpec, AppPullGitSpec,
                                           CopyPair)
from sbkube.models.sources_model_v2 import (GitRepoScheme, HelmRepoScheme,
                                            SourceScheme)
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
        specs = validate_spec_fields("pull-helm", {"repo": "bitnami", "chart": "redis"})
        assert specs["repo"] == "bitnami"

        # Missing required fields
        with pytest.raises(ValueError, match="Missing required fields"):
            validate_spec_fields("pull-helm", {"repo": "bitnami"})

        # Unknown app type
        with pytest.raises(ValueError, match="Unknown app type"):
            validate_spec_fields("unknown-type", {})


class TestConfigModels:
    """Test configuration model validation."""

    def test_app_info_validation(self):
        """Test AppInfoScheme validation."""
        # Valid app
        app = AppInfoScheme(
            name="my-app",
            type="install-helm",
            namespace="default",
            specs={"path": "charts/my-app", "values": ["values.yaml"]},
        )
        assert app.name == "my-app"
        assert app.enabled is True

        # Invalid name
        with pytest.raises(ConfigValidationError, match="must consist of lowercase"):
            AppInfoScheme(name="My-App", type="install-helm", specs={})

        # Invalid type
        with pytest.raises(ConfigValidationError):
            AppInfoScheme(name="my-app", type="invalid-type", specs={})

    def test_app_group_validation(self):
        """Test AppGroupScheme validation."""
        # Valid group
        group = AppGroupScheme(
            namespace="my-namespace",
            apps=[
                AppInfoScheme(
                    name="app1", type="install-helm", specs={"path": "charts/app1"}
                ),
                AppInfoScheme(
                    name="app2",
                    type="install-kubectl",
                    specs={"paths": ["manifests/app2.yaml"]},
                ),
            ],
        )
        assert group.namespace == "my-namespace"
        assert len(group.apps) == 2

        # Namespace inheritance
        assert group.apps[0].namespace == "my-namespace"
        assert group.apps[1].namespace == "my-namespace"

        # Duplicate app names
        with pytest.raises(ConfigValidationError, match="Duplicate app names"):
            AppGroupScheme(
                namespace="default",
                apps=[
                    AppInfoScheme(name="app1", type="exec", specs={"commands": ["ls"]}),
                    AppInfoScheme(
                        name="app1", type="exec", specs={"commands": ["pwd"]}
                    ),
                ],
            )

    def test_helm_spec_validation(self):
        """Test Helm spec validation."""
        # Valid spec
        spec = AppInstallHelmSpec(
            path="charts/my-app",
            values=["values.yaml", "values-prod.yaml"],
            release_name="my-release",
            timeout="5m30s",
        )
        assert spec.path == "charts/my-app"
        assert spec.timeout == "5m30s"

        # Invalid timeout
        with pytest.raises(ConfigValidationError, match="timeout must be in format"):
            AppInstallHelmSpec(path="charts/my-app", timeout="invalid")

    def test_git_spec_validation(self):
        """Test Git spec validation."""
        # Valid spec
        spec = AppPullGitSpec(
            repo="my-repo", paths=[CopyPair(src="src/app", dest="dest/app")]
        )
        assert spec.repo == "my-repo"
        assert len(spec.paths) == 1

        # Empty repo
        with pytest.raises(ConfigValidationError, match="repo cannot be empty"):
            AppPullGitSpec(repo="", paths=[])


class TestSourcesModel:
    """Test sources model validation."""

    def test_sources_validation(self):
        """Test SourceScheme validation."""
        # Valid sources
        sources = SourceScheme(
            cluster="my-cluster",
            kubeconfig="~/.kube/config",
            helm_repos={
                "bitnami": HelmRepoScheme(url="https://charts.bitnami.com/bitnami")
            },
            git_repos={
                "my-repo": GitRepoScheme(
                    url="https://github.com/example/repo.git", branch="main"
                )
            },
        )
        assert sources.cluster == "my-cluster"
        assert "bitnami" in sources.helm_repos

        # Invalid Git URL
        with pytest.raises(ConfigValidationError, match="Git URL must start with"):
            SourceScheme(
                cluster="cluster",
                git_repos={"bad": GitRepoScheme(url="invalid-url", branch="main")},
            )

    def test_helm_repo_validation(self):
        """Test Helm repository validation."""
        # Valid repo
        repo = HelmRepoScheme(url="https://charts.example.com")
        assert repo.url == "https://charts.example.com"

        # With TLS
        repo = HelmRepoScheme(
            url="https://charts.example.com",
            ca_file="/path/ca.crt",
            cert_file="/path/client.crt",
            key_file="/path/client.key",
        )
        assert repo.ca_file == "/path/ca.crt"

        # Invalid TLS config
        with pytest.raises(
            ConfigValidationError, match="all three files must be specified"
        ):
            HelmRepoScheme(url="https://charts.example.com", ca_file="/path/ca.crt")

    def test_git_repo_validation(self):
        """Test Git repository validation."""
        # Valid repo
        repo = GitRepoScheme(
            url="https://github.com/example/repo.git", branch="develop"
        )
        assert repo.url == "https://github.com/example/repo.git"
        assert repo.branch == "develop"

        # With authentication
        repo = GitRepoScheme(
            url="https://github.com/example/repo.git",
            branch="main",
            username="user",
            password="pass",
        )
        assert repo.username == "user"

        # Multiple auth methods
        with pytest.raises(
            ConfigValidationError, match="Only one authentication method"
        ):
            GitRepoScheme(
                url="https://github.com/example/repo.git",
                branch="main",
                username="user",
                password="pass",
                ssh_key="/path/to/key",
            )


class TestConfigInheritance:
    """Test configuration inheritance functionality."""

    def test_model_merging(self):
        """Test model merge functionality."""
        base = AppGroupScheme(
            namespace="default",
            apps=[
                AppInfoScheme(
                    name="app1",
                    type="install-helm",
                    specs={"path": "charts/app1", "values": ["base.yaml"]},
                )
            ],
            global_labels={"env": "base", "team": "platform"},
        )

        overlay = {
            "namespace": "production",
            "apps": [
                {
                    "name": "app2",
                    "type": "install-kubectl",
                    "specs": {"paths": ["app2.yaml"]},
                }
            ],
            "global_labels": {"env": "prod"},
        }

        merged = base.merge_with(overlay)

        assert merged.namespace == "production"
        assert len(merged.apps) == 1  # Lists are replaced, not extended
        assert merged.apps[0].name == "app2"
        assert merged.global_labels["env"] == "prod"
        assert merged.global_labels["team"] == "platform"  # Preserved from base

    def test_inheritance_config_model(self):
        """Test InheritableConfigModel functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create parent config
            parent_path = Path(tmpdir) / "parent.yaml"
            parent_data = {
                "namespace": "default",
                "deps": ["dep1"],
                "apps": [
                    {
                        "name": "base-app",
                        "type": "install-helm",
                        "specs": {"path": "charts/base"},
                    }
                ],
            }
            with open(parent_path, "w") as f:
                yaml.dump(parent_data, f)

            # Create child config with inheritance
            child_data = {
                "_parent": str(parent_path),
                "namespace": "production",
                "apps": [
                    {
                        "name": "child-app",
                        "type": "install-kubectl",
                        "specs": {"paths": ["child.yaml"]},
                    }
                ],
            }

            # Load with inheritance
            config = AppGroupScheme(**child_data)

            assert config.namespace == "production"
            assert config.deps == ["dep1"]  # Inherited
            assert len(config.apps) == 1  # Overridden
            assert config.apps[0].name == "child-app"


class TestConfigManager:
    """Test ConfigManager functionality."""

    def create_test_configs(self, base_dir: Path):
        """Create test configuration files."""
        # Create sources.yaml
        sources_data = {
            "cluster": "test-cluster",
            "helm_repos": {"bitnami": "https://charts.bitnami.com/bitnami"},
            "git_repos": {
                "test-repo": {
                    "url": "https://github.com/test/repo.git",
                    "branch": "main",
                }
            },
        }
        sources_path = base_dir / "sources.yaml"
        with open(sources_path, "w") as f:
            yaml.dump(sources_data, f)

        # Create app config
        app_dir = base_dir / "apps" / "test-app"
        app_dir.mkdir(parents=True)

        config_data = {
            "namespace": "test-namespace",
            "apps": [
                {
                    "name": "test-app",
                    "type": "pull-helm",
                    "specs": {"repo": "bitnami", "chart": "redis"},
                }
            ],
        }
        config_path = app_dir / "config.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        return app_dir

    def test_config_manager_loading(self):
        """Test ConfigManager loading functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            app_dir = self.create_test_configs(base_dir)

            manager = ConfigManager(base_dir)

            # Load sources
            sources = manager.load_sources()
            assert sources.cluster == "test-cluster"
            assert "bitnami" in sources.helm_repos

            # Load app config
            config = manager.load_app_config(app_dir)
            assert config.namespace == "test-namespace"
            assert len(config.apps) == 1
            assert config.apps[0].name == "test-app"

    def test_config_validation_references(self):
        """Test reference validation between configs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            app_dir = self.create_test_configs(base_dir)

            manager = ConfigManager(base_dir)

            sources = manager.load_sources()
            config = manager.load_app_config(app_dir)

            # Valid references
            errors = manager.validate_config_references(config, sources)
            assert len(errors) == 0

            # Add invalid reference
            config.apps.append(
                AppInfoScheme(
                    name="invalid-app",
                    type="pull-helm",
                    specs={"repo": "unknown-repo", "chart": "test"},
                )
            )

            errors = manager.validate_config_references(config, sources)
            assert len(errors) == 1
            assert "unknown-repo" in errors[0]

    def test_config_export(self):
        """Test configuration export functionality."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            app_dir = self.create_test_configs(base_dir)

            manager = ConfigManager(base_dir)
            config = manager.load_app_config(app_dir)

            # Export as YAML
            export_path = base_dir / "exported.yaml"
            manager.export_merged_config(config, export_path, format="yaml")

            assert export_path.exists()

            with open(export_path, "r") as f:
                exported = yaml.safe_load(f)

            assert exported["namespace"] == "test-namespace"
            assert len(exported["apps"]) == 1

            # Export as JSON
            json_path = base_dir / "exported.json"
            manager.export_merged_config(config, json_path, format="json")

            assert json_path.exists()
