---
assignee: gemini
---

### Context
The `pyproject.toml` file lists the project's Python dependencies in the `[project.dependencies]` section. Many of these dependencies do not have their versions pinned or have very loose version constraints (e.g., `pyyaml`, `gitpython`, `rich`).

### Problem
Using unpinned or loosely pinned dependencies can lead to build instability and unpredictable behavior. A new version of a dependency might be released with backward-incompatible changes, which could cause `sbkube` to fail unexpectedly during installation or at runtime. This makes the application less reliable and significantly harder to troubleshoot, as the underlying cause might be a silent dependency update.

### Recommendation
To ensure reproducible and stable builds, the dependency management strategy should be improved.

1.  **Add Upper Bounds for Runtime Dependencies**: Keep semver ranges but add upper bounds for safety (e.g., `PyYAML>=6.0,<7.0`). This reduces surprise breakage without hard pinning everything.

2.  **Use the Existing `uv.lock`**: The repo already has `uv.lock`. Make `uv sync --frozen` (or equivalent) part of CI/dev guidance so installs are reproducible from the lockfile.

3.  **Document the Policy**: Clarify in docs that `uv` and `uv.lock` are the source of truth for exact versions, and that `pyproject.toml` should keep compatible ranges with upper bounds.
