"""Tests for cluster configuration resolver."""

import tempfile
from pathlib import Path

import pytest

from sbkube.models.sources_model import SourceScheme
from sbkube.utils.cluster_config import (
    ClusterConfigError,
    apply_cluster_config_to_command,
    resolve_cluster_config,
)


def test_resolve_cluster_config_cli_override() -> None:
    """CLI options should override sources.yaml."""
    # Create a temporary kubeconfig file for CLI
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        cli_kubeconfig = f.name
        f.write("apiVersion: v1\nkind: Config\n")

    try:
        # sources.yaml with different config
        sources = SourceScheme(
            kubeconfig="~/.kube/sources-config",
            kubeconfig_context="sources-context",
        )

        # CLI should override
        kubeconfig, context = resolve_cluster_config(
            cli_kubeconfig=cli_kubeconfig,
            cli_context="cli-context",
            sources=sources,
        )

        assert kubeconfig == cli_kubeconfig
        assert context == "cli-context"
    finally:
        Path(cli_kubeconfig).unlink()


def test_resolve_cluster_config_from_sources() -> None:
    """Should use sources.yaml when CLI options are not provided."""
    # Create a temporary kubeconfig file with valid context
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
        kubeconfig_path = f.name
        f.write("""apiVersion: v1
kind: Config
current-context: test-context
contexts:
- name: test-context
  context:
    cluster: test-cluster
    user: test-user
clusters:
- name: test-cluster
  cluster:
    server: https://localhost:6443
users:
- name: test-user
  user:
    token: fake-token
""")

    try:
        sources = SourceScheme(
            cluster="test-cluster",
            kubeconfig=kubeconfig_path,
            kubeconfig_context="test-context",
        )

        kubeconfig, context = resolve_cluster_config(
            cli_kubeconfig=None,
            cli_context=None,
            sources=sources,
        )

        assert kubeconfig == kubeconfig_path
        assert context == "test-context"
    finally:
        Path(kubeconfig_path).unlink()


def test_resolve_cluster_config_no_sources() -> None:
    """Should raise error when sources.yaml is missing."""
    with pytest.raises(ClusterConfigError) as exc_info:
        resolve_cluster_config(
            cli_kubeconfig=None,
            cli_context=None,
            sources=None,
        )

    assert "sources.yaml file is required" in str(exc_info.value)


def test_resolve_cluster_config_incomplete_sources() -> None:
    """Should raise error when sources.yaml is incomplete."""
    # Missing kubeconfig_context
    with pytest.raises(Exception):  # Pydantic validation error
        SourceScheme(
            kubeconfig="~/.kube/config",
            # kubeconfig_context is missing
        )


def test_resolve_cluster_config_cli_partial() -> None:
    """Should raise error when only one of --kubeconfig or --context is provided."""
    sources = SourceScheme(
        kubeconfig="~/.kube/config",
        kubeconfig_context="default",
    )

    # Only kubeconfig provided
    with pytest.raises(ClusterConfigError) as exc_info:
        resolve_cluster_config(
            cli_kubeconfig="~/.kube/test",
            cli_context=None,
            sources=sources,
        )
    assert "Both --kubeconfig and --context must be specified" in str(exc_info.value)

    # Only context provided
    with pytest.raises(ClusterConfigError) as exc_info:
        resolve_cluster_config(
            cli_kubeconfig=None,
            cli_context="test-context",
            sources=sources,
        )
    assert "Both --kubeconfig and --context must be specified" in str(exc_info.value)


def test_apply_cluster_config_to_helm_command() -> None:
    """Should add kubeconfig and context to helm commands."""
    cmd = ["helm", "upgrade", "my-release", "my-chart"]

    result = apply_cluster_config_to_command(
        cmd=cmd,
        kubeconfig="/path/to/kubeconfig",
        context="my-context",
    )

    assert "--kubeconfig" in result
    assert "/path/to/kubeconfig" in result
    assert "--kube-context" in result
    assert "my-context" in result


def test_apply_cluster_config_to_kubectl_command() -> None:
    """Should add kubeconfig and context to kubectl commands."""
    cmd = ["kubectl", "apply", "-f", "manifest.yaml"]

    result = apply_cluster_config_to_command(
        cmd=cmd,
        kubeconfig="/path/to/kubeconfig",
        context="my-context",
    )

    assert "--kubeconfig" in result
    assert "/path/to/kubeconfig" in result
    assert "--context" in result
    assert "my-context" in result


def test_apply_cluster_config_no_config() -> None:
    """Should return unchanged command when no config is provided."""
    cmd = ["helm", "version"]

    result = apply_cluster_config_to_command(
        cmd=cmd,
        kubeconfig=None,
        context=None,
    )

    assert result == cmd


def test_sources_model_validation() -> None:
    """Test SourceScheme validation."""
    # Valid sources
    sources = SourceScheme(
        cluster="test-cluster",
        kubeconfig="~/.kube/config",
        kubeconfig_context="default",
    )
    assert sources.cluster == "test-cluster"
    assert sources.kubeconfig == "~/.kube/config"
    assert sources.kubeconfig_context == "default"

    # Missing kubeconfig
    with pytest.raises(Exception):  # Pydantic validation error
        SourceScheme(
            kubeconfig_context="default",
        )

    # Missing kubeconfig_context
    with pytest.raises(Exception):  # Pydantic validation error
        SourceScheme(
            kubeconfig="~/.kube/config",
        )

    # Empty kubeconfig
    with pytest.raises(Exception):  # Pydantic validation error
        SourceScheme(
            kubeconfig="",
            kubeconfig_context="default",
        )

    # Empty kubeconfig_context
    with pytest.raises(Exception):  # Pydantic validation error
        SourceScheme(
            kubeconfig="~/.kube/config",
            kubeconfig_context="",
        )
