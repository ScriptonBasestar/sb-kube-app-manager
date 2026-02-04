"""Application labeling utilities for sbkube.

This module provides functionality to automatically inject sbkube-specific
labels and annotations into Helm charts and Kubernetes resources.

Features:
- Dynamic label injection to YAML resources without modifying source files
- Consistent label format across Helm and YAML deployments
- Support for multi-document YAML files (---)
- Auto-detection of incompatible Helm charts
"""

import re
from datetime import UTC, datetime

import yaml

# ============================================================================
# Known Incompatible Charts
# ============================================================================
# These charts don't fully support commonLabels/commonAnnotations injection.
# Label injection is automatically disabled for these charts.
#
# Incompatibility reasons:
#   - NO_COMMON_ANNOTATIONS: supports commonLabels but not commonAnnotations
#   - DIFFERENT_NAMING: uses 'labels'/'annotations' instead of 'commonLabels'/'commonAnnotations'
#   - STRICT_SCHEMA: additionalProperties: false rejects unknown fields
#
# Format: "repo/chart" or just "chart" for any repo
# Matching is case-insensitive and supports partial matches
#
# To add a new chart:
#   1. Add to this list with reason
#   2. Test with: sbkube template --app-dir <path>
#   3. Submit PR with chart name and reason
#
# Sources:
#   - https://github.com/traefik/traefik-helm-chart (NO_COMMON_ANNOTATIONS)
#   - https://github.com/authelia/chartrepo (DIFFERENT_NAMING: uses 'labels')
#   - https://github.com/cert-manager/cert-manager/issues/7668 (STRICT_SCHEMA)

KNOWN_INCOMPATIBLE_CHARTS: set[str] = {
    # Traefik - supports commonLabels but NOT commonAnnotations
    # https://github.com/traefik/traefik-helm-chart/blob/master/traefik/values.yaml
    "traefik/traefik",
    "traefik",
    # Authelia - uses 'labels'/'annotations' instead of 'commonLabels'/'commonAnnotations'
    # https://github.com/authelia/chartrepo/blob/master/charts/authelia/values.yaml
    "authelia/authelia",
    "authelia",
    # cert-manager - strict schema with additionalProperties: false
    # https://github.com/cert-manager/cert-manager/issues/7668
    "cert-manager/cert-manager",
    "cert-manager",
    "jetstack/cert-manager",
}


def is_chart_label_injection_compatible(
    chart: str,
    extra_incompatible: list[str] | None = None,
    force_compatible: list[str] | None = None,
) -> bool:
    """Check if a Helm chart is compatible with label injection.

    Args:
        chart: Chart name in format "repo/chart" or just "chart"
        extra_incompatible: Additional charts to treat as incompatible (from sources.yaml)
        force_compatible: Charts to force as compatible, overriding built-in list

    Returns:
        True if compatible (label injection should work),
        False if known to be incompatible

    Examples:
        >>> is_chart_label_injection_compatible("grafana/grafana")
        True
        >>> is_chart_label_injection_compatible("traefik/traefik")
        False
        >>> is_chart_label_injection_compatible("traefik", force_compatible=["traefik"])
        True

    """
    chart_lower = chart.lower().strip()
    chart_name = chart_lower.split("/")[-1] if "/" in chart_lower else chart_lower

    # Build force compatible set (case-insensitive)
    force_set: set[str] = set()
    if force_compatible:
        for c in force_compatible:
            c_lower = c.lower().strip()
            force_set.add(c_lower)
            # Also add just the chart name
            if "/" in c_lower:
                force_set.add(c_lower.split("/")[-1])

    # Check force compatible first (highest priority)
    if chart_lower in force_set or chart_name in force_set:
        return True

    # Build incompatible set from built-in + extra
    incompatible_set = set(KNOWN_INCOMPATIBLE_CHARTS)
    if extra_incompatible:
        for c in extra_incompatible:
            c_lower = c.lower().strip()
            incompatible_set.add(c_lower)
            # Also add just the chart name
            if "/" in c_lower:
                incompatible_set.add(c_lower.split("/")[-1])

    # Check incompatible
    if chart_lower in incompatible_set or chart_name in incompatible_set:
        return False

    return True


def get_label_injection_recommendation(
    chart: str,
    extra_incompatible: list[str] | None = None,
    force_compatible: list[str] | None = None,
) -> str | None:
    """Get recommendation message for incompatible charts.

    Args:
        chart: Chart name
        extra_incompatible: Additional charts to treat as incompatible
        force_compatible: Charts to force as compatible

    Returns:
        Recommendation message if chart is incompatible, None otherwise

    """
    if is_chart_label_injection_compatible(chart, extra_incompatible, force_compatible):
        return None

    return (
        f"Chart '{chart}' may not support commonLabels/commonAnnotations.\n"
        f"  → Label injection automatically disabled.\n"
        f"  → To manually enable: set helm_label_injection: true in config\n"
        f"  → Or add to force_label_injection in sources.yaml"
    )


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
    r"""Convert labels dict to Helm --set arguments.

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
    r"""Convert annotations dict to Helm --set arguments.

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


def inject_labels_to_yaml(
    yaml_content: str,
    labels: dict[str, str] | None = None,
    annotations: dict[str, str] | None = None,
) -> str:
    r"""Inject labels and annotations into YAML resources dynamically.

    This function injects sbkube labels/annotations into YAML without modifying
    the source file. Supports multi-document YAML files.

    Args:
        yaml_content: Raw YAML content as string
        labels: Dictionary of labels to inject (optional)
        annotations: Dictionary of annotations to inject (optional)

    Returns:
        YAML string with injected labels/annotations

    Example:
        >>> yaml_text = "apiVersion: v1\\nkind: ConfigMap\\nmetadata:\\n  name: test"
        >>> result = inject_labels_to_yaml(yaml_text, {"app": "test"})

    """
    if not labels and not annotations:
        return yaml_content

    try:
        # Parse all documents in YAML (supports ---)
        documents = list(yaml.safe_load_all(yaml_content))
    except yaml.YAMLError:
        # If parsing fails, return original content
        return yaml_content

    # Process each document
    for doc in documents:
        if doc is None or not isinstance(doc, dict):
            continue

        # Only inject into Kubernetes resources with metadata
        if "kind" not in doc or "metadata" not in doc:
            continue

        metadata = doc["metadata"]
        if not isinstance(metadata, dict):
            continue

        # Inject labels
        if labels:
            if "labels" not in metadata:
                metadata["labels"] = {}
            if isinstance(metadata["labels"], dict):
                metadata["labels"].update(labels)

        # Inject annotations
        if annotations:
            if "annotations" not in metadata:
                metadata["annotations"] = {}
            if isinstance(metadata["annotations"], dict):
                metadata["annotations"].update(annotations)

    # Convert back to YAML string
    # Use safe_dump to maintain compatibility
    output_lines = []
    for i, doc in enumerate(documents):
        if i > 0:
            output_lines.append("---")
        if doc is not None:
            output_lines.append(yaml.safe_dump(doc, default_flow_style=False))

    return "\n".join(output_lines)
