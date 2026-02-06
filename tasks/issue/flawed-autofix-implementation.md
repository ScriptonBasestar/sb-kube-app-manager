---
assignee: gemini
---

### Context
The `main_with_exception_handling` function in `sbkube/cli.py` includes an interactive "auto-fix" feature. When a recoverable error (as defined in `sbkube/utils/error_suggestions.py`) occurs, the system retrieves a `quick_fix` command string from the `ERROR_GUIDE` dictionary and offers to execute it on the user's behalf.

### Problem
The implementation is partially flawed and can create a confusing user experience **in specific cases**. The `quick_fix` commands are static strings, and some contain placeholders that require user input.

For example, for a `NamespaceNotFoundError`, the suggested command is `kubectl create namespace <NAMESPACE>`. The current implementation does not handle the `<NAMESPACE>` placeholder. If the user agrees to run the command, the application will literally execute `kubectl create namespace <NAMESPACE>`, which will either fail or create a namespace with the literal name `<NAMESPACE>`.

So while the auto-fix flow works for simple commands, placeholder-based fixes are unsafe to auto-execute.

### Recommendation
The auto-fix feature should be made safe for placeholder-based commands.

1.  **Immediate Guardrail**: Do not auto-execute any `quick_fix` that contains placeholders (e.g., `<...>`). Only show the command for manual use.
2.  **Improve Command Suggestions**: Update placeholder wording to be explicit, e.g., `kubectl create namespace <your-namespace-name>`.
3.  **(Optional) Templating System**: If auto-execution is important, implement a templating mechanism that fills placeholders from error context or prompts for required values before executing.
