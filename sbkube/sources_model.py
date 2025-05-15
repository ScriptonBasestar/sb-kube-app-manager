from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
import os

from dataclass_wizard import YAMLWizard


@dataclass(unsafe_hash=True)
class GitRepoScheme(YAMLWizard):
    url: str
    branch: str

    def __repr__(self):
        return f"{self.url}#{self.branch}"


@dataclass(unsafe_hash=True)
class SourceScheme(YAMLWizard):
    cluster: str
    kubeconfig: str
    helm_repos: dict[str, str]
    oci_repos: dict[str, dict[str, str]]
    git_repos: dict[str, GitRepoScheme]

    def __repr__(self):
        return dedent(f"""
            cluster: {self.cluster}
            kubeconfig: {self.kubeconfig}
            helm_repos: {self.helm_repos}
            oci_repos: {self.oci_repos}
            git_repos: {self.git_repos}
        """)


def load_sources() -> SourceScheme:
    """Load sources.yaml into a SourceScheme object."""
    config_path = Path(__file__).parent / "sources.yaml"
    config_path = Path(os.path.expanduser(str(config_path)))
    return SourceScheme.from_yaml_file(config_path)


def validate_loaded_sources(sources: SourceScheme):
    """(Optional) Basic validation of loaded source structure."""
    assert isinstance(sources.helm_repos, dict)
    for name, url in sources.helm_repos.items():
        assert isinstance(name, str) and isinstance(url, str)
        assert url.startswith("http"), f"Invalid Helm repo URL: {url}"
    for repo_group, charts in sources.oci_repos.items():
        assert isinstance(charts, dict)
        for chart_name, oci_url in charts.items():
            assert oci_url.startswith("oci://"), f"Invalid OCI URL: {oci_url}"
    for name, repo in sources.git_repos.items():
        assert isinstance(repo, GitRepoScheme)
        assert repo.url.startswith("http"), f"Invalid Git URL: {repo.url}"


if __name__ == "__main__":
    sources = load_sources()
    print(sources)

    # Optional: validate correctness
    validate_loaded_sources(sources)
