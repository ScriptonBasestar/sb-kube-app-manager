"""Administration and safe local outputs for access initialization and revocation."""

import base64
import binascii
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sbkube.models.access_model import AccessSettings
from sbkube.models.unified_config_model import UnifiedSettings
from sbkube.utils.access_admin import NodeAdmin, cluster_ca
from sbkube.utils.access_issue import (
    TokenIssueError,
    build_deployer_kubeconfig,
    check_token_dir,
    check_writable_parent,
    collision,
    overwrite_problem,
    protected_files,
    same_file,
    token_from_output,
)
from sbkube.utils.access_kubeconfig import context_cluster, entries, read_kubeconfig
from sbkube.utils.access_templates import readonly_secret_name, service_account_manifest


@dataclass
class AdminSession:
    """A selected local admin or node transport and its trusted public cluster data."""

    source: Path
    data: dict[str, Any]
    context: str
    admin: Path | None
    node: NodeAdmin | None

    def verify(self) -> None:
        _, cluster = context_cluster(self.data, self.context, self.source)
        ca = cluster_ca(cluster, self.source)
        if self.node is not None:
            self.node.verify(ca)

    def run(self, args: list[str], input_text: str | None = None) -> str:
        if self.node is not None:
            return self.node.run_kubectl(args, input_text)
        command = [
            "kubectl",
            "--kubeconfig",
            str(self.admin),
            "--context",
            self.context,
            *args,
        ]
        try:
            proc = subprocess.run(  # noqa: S603
                command,
                **(
                    {"stdin": subprocess.DEVNULL}
                    if input_text is None
                    else {"input": input_text}
                ),
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
        except FileNotFoundError as e:
            raise TokenIssueError("kubectl not found in PATH") from e
        except subprocess.TimeoutExpired as e:
            raise TokenIssueError("admin kubectl request timed out") from e
        if proc.returncode:
            raise TokenIssueError(
                f"admin kubectl request failed (exit {proc.returncode}); credential output suppressed"
            )
        return proc.stdout


def admin_session(
    settings: UnifiedSettings, access: AccessSettings, obj: dict
) -> AdminSession:
    context = obj.get("context") or settings.kubeconfig_context
    if not context:
        raise TokenIssueError("set settings.kubeconfig_context or pass --context")
    admin_setting = obj.get("kubeconfig") or settings.kubeconfig
    admin = Path(admin_setting).expanduser() if admin_setting else None
    node = NodeAdmin(access.admin) if access.admin.ssh_host else None
    source_setting = access.readonly.kubeconfig if node is not None else admin_setting
    if not source_setting:
        raise TokenIssueError(
            "node access requires a readonly kubeconfig; local access requires an admin kubeconfig"
        )
    source = Path(source_setting).expanduser().absolute()
    data = read_kubeconfig(source)
    context_cluster(data, context, source)
    return AdminSession(source, data, context, admin, node)


@dataclass(frozen=True)
class InitOutputs:
    readonly: Path
    deployer: Path
    readonly_token: Path
    deployer_token: Path
    readonly_config: dict[str, Any]
    deployer_config: dict[str, Any]


def init_outputs(access: AccessSettings, session: AdminSession) -> InitOutputs:
    """Refuse unsafe overwrites and aliases before any cluster call or local write."""
    if not access.readonly.kubeconfig or not access.deployer.kubeconfig:
        raise TokenIssueError(
            "init requires readonly.kubeconfig and deployer.kubeconfig"
        )
    readonly = Path(access.readonly.kubeconfig).expanduser().absolute()
    deployer = Path(access.deployer.kubeconfig).expanduser().absolute()
    token_dir = Path(access.token_dir).expanduser().absolute()
    ro_token, dep_token = token_dir / "readonly.token", token_dir / "deploy.token"
    outputs = [readonly, deployer, ro_token, dep_token]
    for index, path in enumerate(outputs):
        if any(same_file(path, other) for other in outputs[:index]):
            raise TokenIssueError(
                "readonly/deployer kubeconfigs and token files must be different files"
            )

    readonly_generated = overwrite_problem(readonly, ro_token, "readonly") is None
    if readonly.exists() and not readonly_generated:
        existing = read_kubeconfig(readonly)
        # A public-only bootstrap descriptor may become the generated agent config.
        bootstrap = (
            not existing.get("users")
            and len(entries(existing, "contexts")) == 1
            and entries(existing, "contexts")[0].get("name") == session.context
            and len(entries(existing, "clusters")) == 1
        )
        if not bootstrap:
            raise TokenIssueError(
                "readonly kubeconfig is manually managed; preserve it and choose a new output path or use init --print"
            )
    problem = overwrite_problem(deployer, dep_token)
    if problem:
        raise TokenIssueError(problem)

    admin_source = session.admin
    if (
        session.node is not None
        and admin_source is not None
        and same_file(admin_source, session.source)
    ):
        # Node mode reads this public readonly descriptor only to establish
        # cluster identity; it is also the generated readonly output.
        admin_source = None
    protected = protected_files(admin_source, None)
    readonly_protected = protected_files(None, readonly)
    readonly_protected.pop(readonly, None)
    if readonly_generated:
        # Only this role's generated token may be refreshed, never another credential.
        for path in list(readonly_protected):
            if same_file(path, ro_token):
                readonly_protected.pop(path)
    if readonly.exists():
        # A path referenced both as tokenFile and CA must remain protected as a CA.
        for entry in entries(read_kubeconfig(readonly), "clusters"):
            cluster = entry.get("cluster")
            ref = (
                cluster.get("certificate-authority")
                if isinstance(cluster, dict)
                else None
            )
            if isinstance(ref, str) and ref:
                ca_path = Path(ref)
                if not ca_path.is_absolute():
                    ca_path = readonly.parent / ca_path
                readonly_protected[ca_path] = "readonly server CA file"
    protected.update(readonly_protected)
    for path in outputs:
        hit = collision(path, protected)
        if hit:
            raise TokenIssueError(f"init output {path} must not be the {hit}")
    check_token_dir(token_dir)
    check_writable_parent(readonly)
    check_writable_parent(deployer)
    deploy_config = build_deployer_kubeconfig(
        session.data, session.context, session.source, dep_token
    )
    readonly_config = build_deployer_kubeconfig(
        session.data, session.context, session.source, ro_token
    )
    readonly_config["users"][0]["name"] = "readonly"
    readonly_config["contexts"][0]["context"]["user"] = "readonly"
    return InitOutputs(
        readonly, deployer, ro_token, dep_token, readonly_config, deploy_config
    )


def _json_mapping(output: str) -> dict[str, Any]:
    try:
        data = json.loads(output)
    except (ValueError, TypeError) as e:
        raise TokenIssueError(
            "admin kubectl returned invalid JSON (content suppressed)"
        ) from e
    if not isinstance(data, dict):
        raise TokenIssueError(
            "admin kubectl returned a non-object (content suppressed)"
        )
    return data


def _secret_fields(data: dict[str, Any], access: AccessSettings) -> dict[str, Any]:
    metadata = data.get("metadata")
    annotations = metadata.get("annotations") if isinstance(metadata, dict) else None
    if (
        data.get("type") != "kubernetes.io/service-account-token"
        or not isinstance(metadata, dict)
        or metadata.get("name") != readonly_secret_name(access)
        or metadata.get("namespace") != access.namespace
        or not isinstance(annotations, dict)
        or annotations.get("kubernetes.io/service-account.name")
        != access.readonly.service_account
    ):
        raise TokenIssueError(
            "readonly Secret is not owned by the expected ServiceAccount"
        )
    fields = data.get("data", {})
    if not isinstance(fields, dict):
        raise TokenIssueError(
            "readonly Secret contains invalid data (content suppressed)"
        )
    return fields


def check_readonly_secret(session: AdminSession, access: AccessSettings) -> None:
    """Do not adopt or retarget an unrelated existing Secret during apply."""
    output = session.run(
        [
            "-n",
            access.namespace,
            "get",
            "secret",
            readonly_secret_name(access),
            "--ignore-not-found",
            "-o",
            "json",
        ]
    )
    if output.strip():
        _secret_fields(_json_mapping(output), access)


def readonly_token(session: AdminSession, access: AccessSettings) -> str:
    """Wait for the SA token controller without exposing the Secret JSON or token."""
    deadline = time.monotonic() + 15
    while True:
        data = _json_mapping(
            session.run(
                [
                    "-n",
                    access.namespace,
                    "get",
                    "secret",
                    readonly_secret_name(access),
                    "-o",
                    "json",
                ]
            )
        )
        encoded = _secret_fields(data, access).get("token")
        if encoded:
            try:
                return token_from_output(
                    base64.b64decode(encoded, validate=True).decode("ascii")
                )
            except (ValueError, TypeError, binascii.Error, UnicodeError) as e:
                raise TokenIssueError(
                    "readonly Secret contains invalid token data"
                ) from e
        if time.monotonic() >= deadline:
            raise TokenIssueError(
                "readonly token controller did not populate the Secret within 15 seconds"
            )
        time.sleep(0.5)


def revoke_deployer(session: AdminSession, access: AccessSettings) -> None:
    """Replace the deployer SA UID, preserving custom metadata and pull secrets."""
    import yaml

    args = ["-n", access.namespace]
    output = session.run(
        [
            *args,
            "get",
            "serviceaccount",
            access.deployer.service_account,
            "--ignore-not-found",
            "-o",
            "json",
        ]
    )
    original = (
        _json_mapping(output)
        if output.strip()
        else service_account_manifest(access, "deployer")
    )
    if (
        original.get("kind") != "ServiceAccount"
        or not isinstance(original.get("metadata"), dict)
        or original["metadata"].get("name") != access.deployer.service_account
    ):
        raise TokenIssueError("unexpected deployer ServiceAccount identity")
    metadata = original["metadata"]
    if metadata.get("namespace") != access.namespace:
        raise TokenIssueError("unexpected deployer ServiceAccount namespace")
    for key in (
        "uid",
        "resourceVersion",
        "creationTimestamp",
        "managedFields",
        "deletionTimestamp",
        "deletionGracePeriodSeconds",
        "generateName",
    ):
        metadata.pop(key, None)
    original.pop("secrets", None)
    original["automountServiceAccountToken"] = False
    replacement = yaml.safe_dump(original)
    session.run(
        [
            *args,
            "delete",
            "serviceaccount",
            access.deployer.service_account,
            "--ignore-not-found",
            "--wait=true",
            "--timeout=20s",
        ]
    )
    try:
        session.run(["create", "-f", "-"], replacement)
    except TokenIssueError as e:
        raise TokenIssueError(
            "deployer ServiceAccount was deleted, but recreation failed; run init to restore it (previous tokens stay revoked)"
        ) from e
