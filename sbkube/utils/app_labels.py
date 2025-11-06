"""Application labeling utilities for sbkube.

This module provides functionality to automatically inject sbkube-specific
labels and annotations into Helm charts and Kubernetes resources.
"""

import re
from datetime import UTC, datetime


def extract_app_group_from_name(app_name: str) -> str | None:
    """Extract app-group from app_name.

    App names follow the pattern: app_XXX_category_subcategory
    Example: app_000_infra_network -> app_000_infra_network
             traefik (under app_000_infra_network/) -> app_000_infra_network

    Args:
        app_name: Application name or directory name

    Returns:
        App group name if pattern matches, None otherwise

    Examples:
        >>> extract_app_group_from_name("app_000_infra_network")
        'app_000_infra_network'
        >>> extract_app_group_from_name("traefik")
        None

    """
    # Match pattern: app_XXX_... where XXX is 3 digits
    pattern = r"^(app_\d{3}(?:_[a-z0-9_]+)*)$"
    match = re.match(pattern, app_name)
    if match:
        return match.group(1)
    return None


def build_sbkube_labels(
    app_name: str,
    app_group: str | None = None,
    deployment_id: str | None = None,
) -> dict[str, str]:
    """Build sbkube-specific labels for Kubernetes resources.

    Args:
        app_name: Application name
        app_group: App group name (auto-extracted if None)
        deployment_id: Deployment ID (auto-generated if None)

    Returns:
        Dictionary of labels to inject

    Example:
        >>> build_sbkube_labels("traefik", "app_000_infra_network", "dep_20250131_143022")
        {
            'app.kubernetes.io/managed-by': 'sbkube',
            'sbkube.io/app-group': 'app_000_infra_network',
            'sbkube.io/app-name': 'traefik'
        }

    """
    labels = {
        "app.kubernetes.io/managed-by": "sbkube",
    }

    # Auto-extract app-group if not provided
    if not app_group:
        app_group = extract_app_group_from_name(app_name)

    if app_group:
        labels["sbkube.io/app-group"] = app_group

    # Always add app-name
    labels["sbkube.io/app-name"] = app_name

    return labels


def build_sbkube_annotations(
    deployment_id: str | None = None,
    operator: str | None = None,
) -> dict[str, str]:
    """Build sbkube-specific annotations for Kubernetes resources.

    Args:
        deployment_id: Deployment ID (auto-generated if None)
        operator: Operator name (e.g., "archmagece")

    Returns:
        Dictionary of annotations to inject

    Example:
        >>> build_sbkube_annotations("dep_20250131_143022", "archmagece")
        {
            'sbkube.io/deployment-id': 'dep_20250131_143022',
            'sbkube.io/deployed-at': '2025-01-31T14:30:22Z',
            'sbkube.io/deployed-by': 'archmagece'
        }

    """
    annotations = {}

    if deployment_id:
        annotations["sbkube.io/deployment-id"] = deployment_id

    # Always add deployed-at timestamp
    annotations["sbkube.io/deployed-at"] = datetime.now(UTC).isoformat()

    if operator:
        annotations["sbkube.io/deployed-by"] = operator

    return annotations


def build_helm_set_labels(labels: dict[str, str]) -> list[str]:
    """Convert labels dict to Helm --set arguments.

    This builds --set-string arguments for injecting labels into Helm charts
    using the commonLabels pattern.

    Args:
        labels: Dictionary of labels

    Returns:
        List of Helm CLI arguments

    Example:
        >>> build_helm_set_labels({"app.kubernetes.io/managed-by": "sbkube"})
        ['--set-string', 'commonLabels.app\\.kubernetes\\.io/managed-by=sbkube']

    Note:
        - Uses --set-string to ensure values are treated as strings
        - Escapes dots in label keys (required by Helm)
        - Not all Helm charts support commonLabels - this will fail gracefully

    """
    helm_args = []

    for key, value in labels.items():
        # Escape dots in key (Helm requirement)
        escaped_key = key.replace(".", "\\.")
        helm_args.extend(["--set-string", f"commonLabels.{escaped_key}={value}"])

    return helm_args


def build_helm_set_annotations(annotations: dict[str, str]) -> list[str]:
    """Convert annotations dict to Helm --set arguments.

    This builds --set-string arguments for injecting annotations into Helm charts
    using the commonAnnotations pattern.

    Args:
        annotations: Dictionary of annotations

    Returns:
        List of Helm CLI arguments

    Example:
        >>> build_helm_set_annotations({"sbkube.io/deployment-id": "dep_123"})
        ['--set-string', 'commonAnnotations.sbkube\\.io/deployment-id=dep_123']

    """
    helm_args = []

    for key, value in annotations.items():
        escaped_key = key.replace(".", "\\.")
        helm_args.extend(["--set-string", f"commonAnnotations.{escaped_key}={value}"])

    return helm_args
