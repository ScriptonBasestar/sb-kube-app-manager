---
assignee: gemini
---

### Context
The `ExecApp` feature in `sbkube` allows users to define arbitrary shell commands in `config.yaml` to be executed by the `deploy` command. The `deploy_exec_app` function in `sbkube/commands/deploy.py` reads these commands and executes them using `sbkube.utils.common.run_command`. A similar risk exists for `CommandHookTask` used in hooks.

### Problem
While `run_command` correctly uses `shlex.split` (no `shell=True`), the feature is **designed** to execute arbitrary commands. That means any user who can modify `config.yaml` (or hook definitions) can run code on the host where `sbkube` executes. This is a **trust boundary** risk rather than a classic injection bug. If a config repo is compromised, the attacker can compromise CI/CD runners or operator machines running `sbkube`.

### Recommendation
To mitigate this risk, the following measures are recommended:

1.  **Security Warning in Documentation**: Add a prominent warning in the `exec` app docs and hooks guide. The warning should state that these features execute arbitrary commands and must only be used with **trusted** configurations.
2.  **Global Disable Switch**: Introduce a global setting (e.g., `SBKUBE_ALLOW_EXEC=false` or top-level config flag) that disables `ExecApp` and command hooks. This enables hardening CI runners or shared servers.
3.  **Interactive Confirmation (Optional)**: For interactive sessions, require explicit confirmation before executing `exec`/hook commands. This must be auto-disabled for non-interactive sessions and bypassable via `--yes`/`--force-exec` for automation.
