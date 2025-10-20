"""
DEPRECATED: This file has been replaced by sources_model.py (formerly sources_model_v2.py)

This legacy sources model is kept for backward compatibility only.
New code should use sources_model.py which provides:
- Enhanced validation for Git/Helm/OCI repositories
- TLS configuration validation
- Better authentication validation
- Improved error messages

DO NOT USE THIS FILE FOR NEW DEVELOPMENT.
"""

import os
import warnings
from pathlib import Path
from textwrap import dedent

import yaml
from pydantic import BaseModel, ValidationError, field_validator

warnings.warn(
    "sources_model_legacy is deprecated. Use sources_model instead.",
    DeprecationWarning,
    stacklevel=2,
)


class GitRepoScheme(BaseModel):
    url: str
    branch: str

    def __repr__(self):
        return f"{self.url}#{self.branch}"

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, v):
        if (
            not v.startswith("http")
            and not v.startswith("oci")
            and not v.startswith("git")
        ):
            raise ValueError("Git url must start with http")
        return v


class SourceScheme(BaseModel):
    cluster: str
    kubeconfig: str
    helm_repos: dict[str, str]
    oci_repos: dict[str, dict[str, str]]
    git_repos: dict[str, GitRepoScheme]

    def __repr__(self):
        return dedent(
            f"""
            cluster: {self.cluster}
            kubeconfig: {self.kubeconfig}
            helm_repos: {self.helm_repos}
            oci_repos: {self.oci_repos}
            git_repos: {self.git_repos}
        """,
        )

    @field_validator("helm_repos")
    @classmethod
    def validate_helm_urls(cls, v):
        for name, url in v.items():
            if not url.startswith("http"):
                raise ValueError(f"Invalid Helm repo URL: {url}")
        return v

    @field_validator("oci_repos")
    @classmethod
    def validate_oci_urls(cls, v):
        for repo_group, charts in v.items():
            for chart_name, oci_url in charts.items():
                if not oci_url.startswith("oci://"):
                    raise ValueError(f"Invalid OCI URL: {oci_url}")
        return v


def load_sources() -> SourceScheme:
    """Load sources.yaml into a SourceScheme object."""
    config_path = Path(__file__).parent / "sources.yaml"
    config_path = Path(os.path.expanduser(str(config_path)))
    with open(config_path) as f:
        yaml_obj = yaml.safe_load(f)
    return SourceScheme.model_validate(yaml_obj)


if __name__ == "__main__":
    try:
        sources = load_sources()
        print(sources)
    except ValidationError as e:
        print(f"❌ Validation failed: {e}")
