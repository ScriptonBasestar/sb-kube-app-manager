"""Tests for path_resolver utility module."""

import pytest

from sbkube.exceptions import SbkubeError
from sbkube.utils.path_resolver import expand_repo_variables, validate_variable_syntax


class TestValidateVariableSyntax:
    """Tests for validate_variable_syntax function."""

    def test_valid_variable_syntax(self):
        """Valid variable syntax should pass without error."""
        # Should not raise
        validate_variable_syntax("${repos.olm}/deploy/crds.yaml")
        validate_variable_syntax("prefix/${repos.my-app}/suffix")
        validate_variable_syntax("${repos.app_name}/path")
        validate_variable_syntax("${repos.app-123}/file.yaml")

    def test_multiple_variables(self):
        """Multiple variables in one path should be validated."""
        # Should not raise
        validate_variable_syntax("${repos.app1}/file1-${repos.app2}/file2.yaml")

    def test_no_variables(self):
        """Paths without variables should pass."""
        # Should not raise
        validate_variable_syntax("simple/path/file.yaml")
        validate_variable_syntax("/absolute/path.yaml")

    def test_invalid_empty_app_name(self):
        """Empty app name should raise error."""
        with pytest.raises(SbkubeError, match="Empty app name"):
            validate_variable_syntax("${repos.}/file.yaml")

    def test_invalid_syntax_unclosed_brace(self):
        """Unclosed brace should raise error."""
        with pytest.raises(SbkubeError, match="Invalid variable syntax"):
            validate_variable_syntax("${repos.app/file.yaml")

    def test_invalid_syntax_special_chars(self):
        """Special characters in app name should raise error."""
        with pytest.raises(SbkubeError, match="Invalid variable syntax"):
            validate_variable_syntax("${repos.app@name}/file.yaml")


class TestExpandRepoVariables:
    """Tests for expand_repo_variables function."""

    @pytest.fixture
    def repos_dir(self, tmp_path):
        """Create temporary repos directory."""
        repos = tmp_path / "repos"
        repos.mkdir()
        (repos / "olm").mkdir()
        (repos / "cert-manager").mkdir()
        return repos

    @pytest.fixture
    def apps_config(self):
        """Sample apps configuration."""
        return {
            "olm": {
                "type": "git",
                "repo": "olm",
                "branch": "master",
            },
            "cert-manager": {
                "type": "git",
                "repo": "cert-manager",
                "branch": "main",
            },
            "my-app": {
                "type": "yaml",
                "manifests": ["deployment.yaml"],
            },
        }

    def test_expand_single_variable(self, repos_dir, apps_config):
        """Expand single variable in path."""
        path = "${repos.olm}/deploy/crds.yaml"
        result = expand_repo_variables(path, repos_dir, apps_config)

        expected = str(repos_dir / "olm" / "deploy/crds.yaml")
        assert result == expected

    def test_expand_multiple_variables(self, repos_dir, apps_config):
        """Expand multiple variables in path."""
        path = "${repos.olm}/file1-${repos.cert-manager}/file2.yaml"
        result = expand_repo_variables(path, repos_dir, apps_config)

        expected = f"{repos_dir}/olm/file1-{repos_dir}/cert-manager/file2.yaml"
        assert result == expected

    def test_no_variables(self, repos_dir, apps_config):
        """Path without variables should remain unchanged."""
        path = "simple/path/file.yaml"
        result = expand_repo_variables(path, repos_dir, apps_config)
        assert result == path

    def test_error_nonexistent_app(self, repos_dir, apps_config):
        """Reference to non-existent app should raise error."""
        path = "${repos.nonexistent}/file.yaml"

        with pytest.raises(SbkubeError, match="references non-existent app"):
            expand_repo_variables(path, repos_dir, apps_config)

    def test_error_non_git_type(self, repos_dir, apps_config):
        """Reference to non-git app should raise error."""
        path = "${repos.my-app}/file.yaml"

        with pytest.raises(SbkubeError, match="can only reference git-type apps"):
            expand_repo_variables(path, repos_dir, apps_config)

    def test_error_invalid_syntax(self, repos_dir, apps_config):
        """Invalid variable syntax should raise error."""
        path = "${repos.}/file.yaml"

        # validate_variable_syntax is called internally
        with pytest.raises(SbkubeError):
            expand_repo_variables(path, repos_dir, apps_config)

    def test_preserve_path_structure(self, repos_dir, apps_config):
        """Path structure after variable should be preserved."""
        path = "${repos.olm}/deploy/upstream/quickstart/crds.yaml"
        result = expand_repo_variables(path, repos_dir, apps_config)

        expected = str(repos_dir / "olm" / "deploy/upstream/quickstart/crds.yaml")
        assert result == expected

    def test_absolute_path_prefix(self, repos_dir, apps_config):
        """Absolute-like prefix should work."""
        path = "/${repos.olm}/file.yaml"
        result = expand_repo_variables(path, repos_dir, apps_config)

        expected = f"/{repos_dir}/olm/file.yaml"
        assert result == expected


class TestIntegrationScenarios:
    """Integration test scenarios for real use cases."""

    def test_olm_operator_scenario(self, tmp_path):
        """Real-world OLM operator deployment scenario."""
        # Setup
        repos_dir = tmp_path / ".sbkube" / "repos"
        repos_dir.mkdir(parents=True)
        (repos_dir / "olm").mkdir()

        apps_config = {
            "olm": {
                "type": "git",
                "repo": "https://github.com/operator-framework/operator-lifecycle-manager.git",
                "branch": "master",
            },
            "olm-operator": {
                "type": "yaml",
                "manifests": [
                    "${repos.olm}/deploy/upstream/quickstart/crds.yaml",
                    "${repos.olm}/deploy/upstream/quickstart/olm.yaml",
                ],
                "depends_on": ["olm"],
            },
        }

        # Test expansion
        manifests = apps_config["olm-operator"]["manifests"]

        expanded1 = expand_repo_variables(manifests[0], repos_dir, apps_config)
        expanded2 = expand_repo_variables(manifests[1], repos_dir, apps_config)

        assert "olm/deploy/upstream/quickstart/crds.yaml" in expanded1
        assert "olm/deploy/upstream/quickstart/olm.yaml" in expanded2
        assert str(repos_dir) in expanded1
        assert str(repos_dir) in expanded2
