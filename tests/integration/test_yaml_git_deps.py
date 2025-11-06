"""Integration tests for YAML apps depending on Git repositories."""

from pathlib import Path

import pytest
import yaml

from sbkube.models.config_model import SBKubeConfig


class TestYamlGitDependencies:
    """Test YAML apps that reference files from Git repositories."""

    @pytest.fixture
    def project_dir(self, tmp_path):
        """Create a test project directory structure."""
        # Project structure:
        # project/
        #   ├── sources.yaml
        #   ├── app_olm/
        #   │   └── config.yaml
        #   └── .sbkube/
        #       └── repos/
        #           └── olm/
        #               └── deploy/
        #                   └── upstream/
        #                       └── quickstart/
        #                           ├── crds.yaml
        #                           └── olm.yaml

        project = tmp_path / "project"
        project.mkdir()

        # Create sources.yaml
        sources = project / "sources.yaml"
        sources.write_text(
            yaml.dump(
                {
                    "repos": {
                        "olm": "https://github.com/operator-framework/operator-lifecycle-manager.git",
                    },
                    "cluster": "dev",
                }
            )
        )

        # Create app directory
        app_dir = project / "app_olm"
        app_dir.mkdir()

        # Create .sbkube/repos/olm structure
        olm_dir = (
            project / ".sbkube" / "repos" / "olm" / "deploy" / "upstream" / "quickstart"
        )
        olm_dir.mkdir(parents=True)

        # Create dummy YAML files
        (olm_dir / "crds.yaml").write_text(
            "apiVersion: v1\nkind: CustomResourceDefinition\n"
        )
        (olm_dir / "olm.yaml").write_text("apiVersion: v1\nkind: Deployment\n")

        return project

    def test_config_with_repo_variables(self, project_dir) -> None:
        """Test config.yaml with ${repos.app-name} variables."""
        app_dir = project_dir / "app_olm"

        # Create config with variable syntax
        config_data = {
            "namespace": "infra",
            "apps": {
                "olm": {
                    "type": "git",
                    "repo": "olm",
                    "branch": "master",
                    "enabled": True,
                },
                "olm-operator": {
                    "type": "yaml",
                    "enabled": True,
                    "manifests": [
                        "${repos.olm}/deploy/upstream/quickstart/crds.yaml",
                        "${repos.olm}/deploy/upstream/quickstart/olm.yaml",
                    ],
                    "namespace": "",
                    "depends_on": ["olm"],
                },
            },
        }

        config_file = app_dir / "config.yaml"
        config_file.write_text(yaml.dump(config_data))

        # Load and validate config
        config = SBKubeConfig(**config_data)

        # Verify config loaded correctly
        assert config.namespace == "infra"
        assert "olm" in config.apps
        assert "olm-operator" in config.apps

        # Verify YamlApp manifests with variables
        olm_operator = config.apps["olm-operator"]
        assert olm_operator.type == "yaml"
        assert len(olm_operator.manifests) == 2
        assert "${repos.olm}" in olm_operator.manifests[0]
        assert "${repos.olm}" in olm_operator.manifests[1]

    def test_variable_expansion_with_real_paths(self, project_dir) -> None:
        """Test variable expansion resolves to real file paths."""
        from sbkube.utils.path_resolver import expand_repo_variables

        repos_dir = project_dir / ".sbkube" / "repos"

        apps_config = {
            "olm": {
                "type": "git",
                "repo": "olm",
                "branch": "master",
            },
        }

        # Expand variable
        manifest_path = "${repos.olm}/deploy/upstream/quickstart/crds.yaml"
        expanded = expand_repo_variables(manifest_path, repos_dir, apps_config)

        # Verify expanded path
        expected_path = repos_dir / "olm" / "deploy/upstream/quickstart/crds.yaml"
        assert expanded == str(expected_path)

        # Verify file exists
        assert Path(expanded).exists()
        content = Path(expanded).read_text()
        assert "CustomResourceDefinition" in content

    def test_backward_compatibility_relative_paths(self, project_dir) -> None:
        """Test that old relative path syntax still works."""
        app_dir = project_dir / "app_olm"

        # Old-style config with relative paths
        config_data = {
            "namespace": "infra",
            "apps": {
                "olm": {
                    "type": "git",
                    "repo": "olm",
                    "branch": "master",
                },
                "olm-operator": {
                    "type": "yaml",
                    "manifests": [
                        "../.sbkube/repos/olm/deploy/upstream/quickstart/crds.yaml",
                        "../.sbkube/repos/olm/deploy/upstream/quickstart/olm.yaml",
                    ],
                    "depends_on": ["olm"],
                },
            },
        }

        config_file = app_dir / "config.yaml"
        config_file.write_text(yaml.dump(config_data))

        # Load config - should work without errors
        config = SBKubeConfig(**config_data)

        assert config.namespace == "infra"
        olm_operator = config.apps["olm-operator"]
        assert "../.sbkube/repos" in olm_operator.manifests[0]


class TestErrorHandling:
    """Test error handling for invalid configurations."""

    def test_invalid_variable_syntax_detected(self) -> None:
        """Invalid variable syntax should be caught at validation."""
        from pydantic import ValidationError

        from sbkube.exceptions import SbkubeError

        # Invalid: empty app name
        config_data = {
            "namespace": "test",
            "apps": {
                "bad-app": {
                    "type": "yaml",
                    "manifests": ["${repos.}/file.yaml"],  # Invalid: empty app name
                },
            },
        }

        with pytest.raises((ValidationError, SbkubeError)):
            SBKubeConfig(**config_data)

    def test_nonexistent_app_reference(self) -> None:
        """Reference to non-existent git app should fail at expansion time."""
        from sbkube.exceptions import SbkubeError
        from sbkube.utils.path_resolver import expand_repo_variables

        apps_config = {
            "my-app": {
                "type": "yaml",
                "manifests": ["file.yaml"],
            },
        }

        repos_dir = Path("/tmp/repos")
        manifest_path = "${repos.nonexistent}/file.yaml"

        with pytest.raises(SbkubeError, match="non-existent app"):
            expand_repo_variables(manifest_path, repos_dir, apps_config)

    def test_non_git_app_reference(self) -> None:
        """Reference to non-git type app should fail."""
        from sbkube.exceptions import SbkubeError
        from sbkube.utils.path_resolver import expand_repo_variables

        apps_config = {
            "my-app": {
                "type": "yaml",  # Not a git type
                "manifests": ["file.yaml"],
            },
        }

        repos_dir = Path("/tmp/repos")
        manifest_path = "${repos.my-app}/file.yaml"

        with pytest.raises(SbkubeError, match="git-type apps"):
            expand_repo_variables(manifest_path, repos_dir, apps_config)
