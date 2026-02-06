---
assignee: gemini
---

### Context
The application's primary mechanism for interacting with the Kubernetes cluster is by shelling out to the `kubectl` and `helm` command-line tools. Core components like `ClusterStatusCollector` in `sbkube/utils/cluster_status.py` and the deployment functions in `sbkube/commands/deploy.py` construct and execute CLI commands, then parse the resulting stdout and stderr.

Although the `kubernetes` Python client library is included as a project dependency in `pyproject.toml`, it appears to be unused for these fundamental cluster operations.

### Problem
This architectural reliance on external CLI tools presents tradeoffs and potential issues:

1.  **Performance Overhead**: Each call to `subprocess.run` creates a new process, which is significantly slower and more resource-intensive than using a persistent, native Python client that communicates directly with the Kubernetes API server.
2.  **Fragile Parsing**: The application relies on parsing the JSON or text output of `kubectl` and `helm`. This is brittle and highly susceptible to breaking when the output format of these tools changes in new versions.
3.  **Poor Error Handling**: Error detection is limited to checking process return codes and parsing stderr. A native client provides structured, typed exceptions, allowing for much more robust and precise error handling.
4.  **External Dependencies**: It creates a hard requirement for users to have `kubectl` and `helm` installed on their system and available in the `PATH`. This complicates the setup and introduces potential version incompatibility issues between the CLI tools and the target cluster.
5.  **Unused Dependency**: Including the `kubernetes` library as a dependency without using it for its core purpose is misleading and adds unnecessary bloat.

### Recommendation
Given this project’s CLI-first design (and explicit `kubectl`/`helm` checks), a full migration to the Python client may be disproportionate. Instead:

1.  **Clarify Intent**: Decide whether `kubernetes` is a required dependency. If not, remove it from runtime deps to reduce bloat.
2.  **Targeted Adoption (Optional)**: If the team wants better error handling in specific read-only areas (e.g., cluster status), introduce the Python client **selectively**, not as a full replacement.
3.  **Document the Choice**: Add a short note in architecture docs explaining why CLI tools are used (compatibility with Helm workflows, consistency with user environment, etc.).
