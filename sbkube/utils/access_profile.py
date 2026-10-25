"""Invocation-scoped readonly/deployer selection for root access settings.

The scope travels with contextvars into workspace workers. It never changes the
process environment or a source model, and never falls back to an admin file.
"""

import base64
import contextvars
import functools
import json
import math
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click

from sbkube.models.unified_config_model import UnifiedSettings
from sbkube.utils.access_issue import TokenIssueError, same_file
from sbkube.utils.access_kubeconfig import KubeconfigError, entries, read_kubeconfig
from sbkube.utils.cluster_identity import cluster_identity
from sbkube.utils.config_inheritance import find_workspace_root
from sbkube.utils.file_loader import load_config_file
from sbkube.utils.target_resolver import resolve_target

MUTATING_PROFILE_COMMANDS = frozenset(
    {"apply", "deploy", "delete", "upgrade", "rollback"}
)
# Rollback resolves its owner from the recorded app directory after loading the
# deployment, rather than interpreting --target (a deployment ID) as a path.
PROFILE_COMMANDS = (MUTATING_PROFILE_COMMANDS - {"rollback"}) | {"status"}


class AccessProfileError(click.ClickException):
    """The selected credential is missing, expired or targets a different cluster."""


@dataclass(frozen=True)
class SelectedProfile:
    kubeconfig: Path
    context: str
    identity: dict[str, str]
    legacy_kubeconfig: Path | None
    owner: Path
    principal: str

    def resolve(self, kubeconfig: str | None, context: str | None) -> tuple[str, str]:
        """Replace credentials while refusing a child's different cluster target."""
        if context and context != self.context:
            raise AccessProfileError(
                "app/phase context differs from the selected access profile"
            )
        if kubeconfig:
            candidate = Path(kubeconfig).expanduser()
            known = same_file(candidate, self.kubeconfig) or (
                self.legacy_kubeconfig is not None
                and same_file(candidate, self.legacy_kubeconfig)
            )
            if candidate.exists() and not same_file(candidate, self.kubeconfig):
                if cluster_identity(candidate, self.context) != self.identity:
                    raise AccessProfileError(
                        "app/phase kubeconfig targets a different access cluster"
                    )
            elif not candidate.exists() and not known:
                raise AccessProfileError(
                    "cannot verify missing app/phase kubeconfig against the access profile"
                )
        return str(self.kubeconfig), self.context


_selected: contextvars.ContextVar[SelectedProfile | None] = contextvars.ContextVar(
    "sbkube_access_profile", default=None
)


def current_profile() -> SelectedProfile | None:
    return _selected.get()


def profile_cluster(
    kubeconfig: str | None, context: str | None
) -> tuple[str | None, str | None]:
    selected = current_profile()
    return selected.resolve(kubeconfig, context) if selected else (kubeconfig, context)


def profile_environment(
    environment: dict[str, str], explicit_environment: dict | None = None
) -> dict[str, str]:
    """Return child-only command environment constrained to the active profile."""
    child_environment = environment.copy()
    selected = current_profile()
    if selected is None:
        return child_environment

    if os.pathsep in str(selected.kubeconfig):
        raise AccessProfileError(
            "selected access kubeconfig must name exactly one file for raw command execution"
        )

    if explicit_environment and any(
        key.startswith("HELM_KUBE") for key in explicit_environment
    ):
        raise AccessProfileError(
            "explicit hook HELM_KUBE override conflicts with the selected access profile"
        )
    explicit_kubeconfig = (
        explicit_environment.get("KUBECONFIG") if explicit_environment else None
    )
    if explicit_kubeconfig is not None and (
        not isinstance(explicit_kubeconfig, str)
        or not same_file(Path(explicit_kubeconfig).expanduser(), selected.kubeconfig)
    ):
        raise AccessProfileError(
            "explicit hook KUBECONFIG conflicts with the selected access profile"
        )
    try:
        current_context = read_kubeconfig(selected.kubeconfig).get("current-context")
    except KubeconfigError as error:
        raise AccessProfileError(
            "cannot read selected access kubeconfig for raw command execution"
        ) from error
    if current_context != selected.context:
        raise AccessProfileError(
            "selected access kubeconfig current-context differs from the access profile"
        )
    for key in tuple(child_environment):
        if key.startswith("HELM_KUBE"):
            del child_environment[key]
    child_environment["KUBECONFIG"] = str(selected.kubeconfig.absolute())
    return child_environment


def validate_profile_document(
    document: dict[str, Any], selected: SelectedProfile | None = None
) -> None:
    """Validate all declared targets before hooks, pruning or nested execution."""
    selected = selected or current_profile()
    if selected is None:
        return
    settings = document.get("settings", {})
    if not isinstance(settings, dict):
        raise AccessProfileError("settings must be a mapping")
    selected.resolve(settings.get("kubeconfig"), settings.get("kubeconfig_context"))
    apps = document.get("apps", {})
    phases = document.get("phases", {})
    if not isinstance(apps, dict) or not isinstance(phases, dict):
        raise AccessProfileError("apps and phases must be mappings")
    for app in apps.values():
        context = (
            app.get("context")
            if isinstance(app, dict)
            else getattr(app, "context", None)
        )
        selected.resolve(None, context)
    for phase in phases.values():
        if isinstance(phase, dict):
            validate_profile_document(phase, selected)


def _configuration_chain(params: dict[str, Any]) -> list[Path]:
    """Ancestor documents inside the anchor boundary, shallowest first.

    A .sbkube-workspace marker can own only anchors (as in infra-ops), with
    separate cluster roots below it. The marker need not contain sbkube.yaml.
    """
    explicit = params.get("config_file")
    location = (
        Path(explicit)
        if explicit
        else Path(params.get("target") or params.get("base_dir") or Path.cwd())
    )
    location = location.expanduser().resolve()
    if not explicit and params.get("target"):
        try:
            # TARGET has an existing upward-lookup contract. Bind to that exact
            # document instead of independently guessing which config will run.
            resolved = resolve_target(str(location), base_dir=Path.cwd())
            location = resolved.config_file
            explicit = str(location)
        except ValueError:
            # Legacy TARGET handling remains owned by the original command.
            pass
    directory = location.parent if explicit else location
    boundary = find_workspace_root(directory)
    found: list[Path] = []
    while True:
        if explicit and directory == location.parent:
            candidate = location if location.is_file() else None
        else:
            candidate = next(
                (
                    directory / name
                    for name in ("sbkube.yaml", "sbkube.yml")
                    if (directory / name).is_file()
                ),
                None,
            )
        if candidate is not None:
            found.append(candidate)
        if boundary is None or directory == boundary:
            break
        directory = directory.parent
    return list(reversed(found))


def access_owner_config(params: dict[str, Any]) -> Path | None:
    """The outermost actual config document inside the declared workspace boundary."""
    chain = _configuration_chain(params)
    return chain[0] if chain else None


def _credential_token(path: Path, context: str) -> str:
    data = read_kubeconfig(path)
    contexts = [
        entry for entry in entries(data, "contexts") if entry.get("name") == context
    ]
    if len(contexts) != 1 or not isinstance(contexts[0].get("context"), dict):
        raise AccessProfileError("access kubeconfig must contain one selected context")
    user_name = contexts[0]["context"].get("user")
    users = [
        entry for entry in entries(data, "users") if entry.get("name") == user_name
    ]
    if len(users) != 1 or not isinstance(users[0].get("user"), dict):
        raise AccessProfileError(
            "access kubeconfig must contain one selected ServiceAccount user"
        )
    user = users[0]["user"]
    if set(user) == {"token"} and isinstance(user["token"], str):
        return user["token"]
    if set(user) == {"tokenFile"} and isinstance(user["tokenFile"], str):
        token_path = Path(user["tokenFile"])
        if not token_path.is_absolute():
            token_path = path.parent / token_path
        try:
            return token_path.read_text(encoding="ascii").strip()
        except (OSError, UnicodeError) as e:
            raise AccessProfileError(
                "cannot read access tokenFile; renew the selected credential"
            ) from e
    raise AccessProfileError(
        "access profile requires only token or tokenFile; admin/exec credentials are refused"
    )


def _check_token(token: str, subject: str, require_expiry: bool, renewal: str) -> None:
    """Inspect expiry locally; the API server still verifies signature and audience."""
    try:
        parts = token.split(".")
        if len(parts) != 3 or any(not part for part in parts):
            raise ValueError
        claims = json.loads(
            base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4))
        )
        if not isinstance(claims, dict) or claims.get("sub") != subject:
            raise ValueError
        expires = claims.get("exp")
        if expires is None and not require_expiry:
            return
        if (
            isinstance(expires, bool)
            or not isinstance(expires, (float, int))
            or not math.isfinite(expires)
        ):
            raise ValueError
        if expires <= time.time():
            raise AccessProfileError(
                f"access token has expired; run `sbkube access {renewal}`"
            )
    except (ValueError, TypeError, UnicodeError, OverflowError) as e:
        raise AccessProfileError(
            f"invalid ServiceAccount token or expiry; run `sbkube access {renewal}`"
        ) from e


def select_profile(
    command_name: str, params: dict[str, Any], obj: dict[str, Any]
) -> SelectedProfile | None:
    if command_name == "rollback" and params.get("list_points"):
        return None
    if command_name == "rollback":
        params = {**params, "target": None}
    owner = access_owner_config(params)
    if owner is None:
        return None
    raw = load_config_file(owner)
    if not str(raw.get("apiVersion", "")).startswith("sbkube/"):
        return None
    settings = UnifiedSettings(**raw.get("settings", {}))
    access = settings.access
    if access is None or not access.auto_profile:
        return None
    if any(key.startswith("HELM_KUBE") for key in os.environ):
        raise AccessProfileError(
            "inherited HELM_KUBE override conflicts with auto_profile"
        )
    mutating = command_name in MUTATING_PROFILE_COMMANDS
    profile = access.deployer if mutating else access.readonly
    renewal = "issue" if mutating else "init"
    if not profile.kubeconfig or not settings.kubeconfig_context:
        raise AccessProfileError(
            f"selected access profile has no kubeconfig/context; run `sbkube access {renewal}`"
        )
    chosen = Path(profile.kubeconfig).expanduser().absolute()
    context = settings.kubeconfig_context
    cli_path, cli_context = obj.get("kubeconfig"), obj.get("context")
    if (cli_path and not same_file(Path(cli_path).expanduser(), chosen)) or (
        cli_context and cli_context != context
    ):
        raise AccessProfileError(
            "CLI kubeconfig/context conflicts with auto_profile; choose the configured profile or set access.auto_profile=false"
        )
    try:
        identity = cluster_identity(chosen, context)
        if not access.readonly.kubeconfig:
            raise AccessProfileError(
                "readonly kubeconfig is required to identify the access cluster"
            )
        baseline = cluster_identity(
            Path(access.readonly.kubeconfig).expanduser(), context
        )
        if identity != baseline:
            raise AccessProfileError(
                "readonly and deployer profiles target different clusters"
            )
        token = _credential_token(chosen, context)
        _check_token(
            token,
            f"system:serviceaccount:{access.namespace}:{profile.service_account}",
            mutating,
            renewal,
        )
        del token
    except (KubeconfigError, TokenIssueError) as e:
        raise AccessProfileError(
            f"cannot use access profile: {e}; run `sbkube access {renewal}`"
        ) from e
    legacy = Path(settings.kubeconfig).expanduser() if settings.kubeconfig else None
    selected = SelectedProfile(
        chosen,
        context,
        identity,
        legacy,
        owner,
        f"system:serviceaccount:{access.namespace}:{profile.service_account}",
    )
    for config_file in _configuration_chain(params):
        validate_profile_document(load_config_file(config_file), selected)
    return selected


def install_profile(command: click.Command) -> None:
    """Apply selection before a command's gate/callback, restoring scope on exit."""
    callback = command.callback
    if callback is None or getattr(callback, "__sbkube_access_profile__", False):
        return

    @functools.wraps(callback)
    def scoped(*args: Any, **kwargs: Any) -> Any:
        ctx = click.get_current_context()
        obj = ctx.ensure_object(dict)
        selected = current_profile()
        if selected is not None:
            selected.resolve(obj.get("kubeconfig"), obj.get("context"))
        else:
            selected = select_profile(command.name or "", kwargs, obj)
        if selected is None:
            return callback(*args, **kwargs)
        previous = {
            key: (key in obj, obj.get(key)) for key in ("kubeconfig", "context")
        }
        obj.update(kubeconfig=str(selected.kubeconfig), context=selected.context)
        marker = _selected.set(selected)
        try:
            return callback(*args, **kwargs)
        finally:
            _selected.reset(marker)
            for key, (exists, value) in previous.items():
                if exists:
                    obj[key] = value
                else:
                    obj.pop(key, None)

    scoped.__sbkube_access_profile__ = True  # type: ignore[attr-defined]
    command.callback = scoped
