"""Manifest metadata cleaner utility.

This module provides functionality to clean Kubernetes manifest files by removing
metadata fields that are automatically managed by Kubernetes and should not be
included in user-provided manifests.

Typical use case: Remove metadata.managedFields and other server-side fields
from rendered Helm charts before deployment to avoid API server rejection.
"""

from typing import Any

import yaml

from sbkube.utils.logger import logger


def clean_manifest_metadata(manifest_content: str) -> str:
    """Clean Kubernetes manifest by removing server-managed metadata fields.

    Removes the following fields that are managed by Kubernetes API server:
    - metadata.managedFields (Server-Side Apply tracking)
    - metadata.creationTimestamp (auto-generated)
    - metadata.resourceVersion (auto-generated)
    - metadata.uid (auto-generated)
    - metadata.generation (auto-generated)
    - metadata.selfLink (deprecated)
    - status (entire section, managed by controllers)

    Args:
        manifest_content: Raw YAML manifest content as string

    Returns:
        str: Cleaned manifest content with server-managed fields removed

    Examples:
        >>> manifest = '''
        ... apiVersion: v1
        ... kind: Pod
        ... metadata:
        ...   name: my-pod
        ...   managedFields: [...]
        ...   creationTimestamp: "2024-01-01T00:00:00Z"
        ... spec:
        ...   containers:
        ...   - name: nginx
        ...     image: nginx:latest
        ... status:
        ...   phase: Running
        ... '''
        >>> cleaned = clean_manifest_metadata(manifest)
        >>> 'managedFields' in cleaned
        False
        >>> 'status:' in cleaned
        False

    """
    try:
        # Handle multi-document YAML (separated by ---)
        documents = yaml.safe_load_all(manifest_content)
        cleaned_docs = []

        for doc in documents:
            if doc is None:
                continue

            # Clean metadata fields
            if isinstance(doc, dict):
                _clean_metadata_dict(doc)
                cleaned_docs.append(doc)

        # Convert back to YAML
        if not cleaned_docs:
            return manifest_content

        # Use safe_dump_all for multi-document support
        return yaml.safe_dump_all(
            cleaned_docs,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse manifest as YAML, returning original: {e}")
        return manifest_content


def _clean_metadata_dict(resource: dict[str, Any]) -> None:
    """Clean metadata fields from a single Kubernetes resource dict (in-place).

    Args:
        resource: Kubernetes resource as dictionary

    """
    if not isinstance(resource, dict):
        return

    # Remove top-level status (entire section)
    resource.pop("status", None)

    # Clean metadata section
    metadata = resource.get("metadata")
    if isinstance(metadata, dict):
        fields_to_remove = [
            "managedFields",
            "creationTimestamp",
            "resourceVersion",
            "uid",
            "generation",
            "selfLink",  # deprecated in Kubernetes 1.20+
        ]

        for field in fields_to_remove:
            if field in metadata:
                logger.debug(f"Removing metadata.{field} from {resource.get('kind', 'unknown')}")
                del metadata[field]

    # Recursively clean nested resources (e.g., in List kinds)
    if resource.get("kind") in ["List", "ConfigMapList", "SecretList"]:
        items = resource.get("items", [])
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    _clean_metadata_dict(item)


def clean_manifest_file(input_path: str, output_path: str | None = None) -> None:
    """Clean a manifest file by removing server-managed metadata fields.

    Args:
        input_path: Path to input manifest file
        output_path: Path to output file (if None, overwrites input file)

    Raises:
        FileNotFoundError: If input file does not exist
        IOError: If file operations fail

    Examples:
        >>> # Clean and overwrite
        >>> clean_manifest_file("deployment.yaml")
        >>> # Clean and save to new file
        >>> clean_manifest_file("deployment.yaml", "deployment-clean.yaml")

    """
    try:
        with open(input_path, encoding="utf-8") as f:
            content = f.read()

        cleaned_content = clean_manifest_metadata(content)

        output = output_path or input_path
        with open(output, "w", encoding="utf-8") as f:
            f.write(cleaned_content)

        logger.info(f"Cleaned manifest written to: {output}")

    except FileNotFoundError:
        logger.error(f"Manifest file not found: {input_path}")
        raise
    except OSError as e:
        logger.error(f"Failed to clean manifest file: {e}")
        raise
