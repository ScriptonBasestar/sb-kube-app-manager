"""``kubectl auth can-i`` checks behind ``sbkube access verify``.

Every question goes to the API server with the readonly credential; a failure
to get an answer (connection, expired token, missing kubectl) is an ERROR,
never a ``no``. No credential value is read or printed here.
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from sbkube.models.access_model import AccessPolicyRule, AccessSettings

KUBECTL_TIMEOUT_SECONDS = 30

# What the readonly credential must (not) be able to do: (can-i args, expected).
# ``-A`` asks with an empty namespace, which only evaluates ClusterRoleBindings.
BASE_CHECKS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("get", "secrets", "-A"), "no"),
    (("list", "secrets", "-A"), "no"),
    (("watch", "secrets", "-A"), "no"),
    (("list", "pods", "-A"), "yes"),
    (("list", "nodes"), "yes"),
    (("list", "customresourcedefinitions.apiextensions.k8s.io"), "yes"),
    (("create", "deployments.apps", "-A"), "no"),
    (("delete", "pods", "-A"), "no"),
)

# The "no" checks repeated per namespace (``-n <ns>``): a RoleBinding in one
# namespace is invisible to the ``-A`` rows above.
PER_NAMESPACE_CHECKS: tuple[tuple[str, ...], ...] = (
    ("get", "secrets"),
    ("list", "secrets"),
    ("watch", "secrets"),
    ("create", "deployments.apps"),
    ("delete", "pods"),
)

MAX_WORKERS = 8
MAX_LISTED_NAMESPACES = 10

# stderr fragments meaning kubectl could not get an answer from the API server.
# Kept specific: kubectl also warns about e.g. resource type 'certificates'.
_ERROR_MARKERS = (
    "unauthorized",
    "connection refused",
    "unable to connect",
    "dial tcp",
    "i/o timeout",
    "no such host",
    "token has expired",
    "token is expired",
    "must be logged in",
    "x509:",
    "certificate signed by",
    "certificate has expired",
    "certificate is not trusted",
)


@dataclass(frozen=True)
class CanIResult:
    """Outcome of one ``kubectl auth can-i``: ``yes``, ``no`` or ``error``."""

    answer: str
    detail: str = ""


def run_can_i(kubeconfig: Path, context: str, args: tuple[str, ...]) -> CanIResult:
    """Ask the API server via ``kubectl auth can-i``; errors are never a ``no``."""
    command = [
        "kubectl",
        "--kubeconfig",
        str(kubeconfig),
        "--context",
        context,
        "auth",
        "can-i",
        *args,
    ]
    try:
        proc = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return CanIResult("error", "kubectl not found in PATH")
    except subprocess.TimeoutExpired:
        return CanIResult("error", f"kubectl timed out ({KUBECTL_TIMEOUT_SECONDS}s)")

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    first_word = stdout.split(maxsplit=1)[0] if stdout else ""
    detail = (stderr.splitlines() or [""])[0][:200]

    if any(marker in stderr.lower() for marker in _ERROR_MARKERS):
        return CanIResult("error", detail)
    if proc.returncode == 0 and first_word == "yes":
        return CanIResult("yes")
    if proc.returncode == 1 and first_word == "no":
        return CanIResult("no")
    return CanIResult("error", detail or f"kubectl exited {proc.returncode}")


def _resource_targets(rule: AccessPolicyRule) -> list[tuple[str, ...]]:
    """can-i argument tails (after the verb) that a rule says must be allowed.

    ``extra_rules`` become a cluster-wide read ClusterRole, so every target,
    named ones included, is asked cluster-wide (``-A``) like the other rows.
    """
    targets: list[tuple[str, ...]] = []
    for group in rule.api_groups or [""]:
        for resource in rule.resources:
            base, _, subresource = resource.partition("/")
            name = base if group in ("", "*") else f"{base}.{group}"
            flags = [f"--subresource={subresource}"] if subresource else []
            if rule.resource_names:
                targets.extend(
                    (f"{name}/{n}", "-A", *flags) for n in rule.resource_names
                )
            else:
                targets.append((name, "-A", *flags))
    targets.extend((url,) for url in rule.non_resource_urls)
    return targets


def build_checks(access: AccessSettings) -> list[tuple[tuple[str, ...], str]]:
    """Cluster-wide can-i table: base rows, token minting, ``extra_rules``."""
    checks = list(BASE_CHECKS)
    checks.append(
        (
            (
                "create",
                "serviceaccounts",
                "--subresource=token",
                "-n",
                access.namespace,
            ),
            "no",
        )
    )
    for rule in access.readonly.extra_rules:
        for verb in rule.verbs:
            checks.extend(((verb, *tail), "yes") for tail in _resource_targets(rule))
    seen: set[tuple[str, ...]] = set()
    unique = []
    for args, expected in checks:
        if args not in seen:
            seen.add(args)
            unique.append((args, expected))
    return unique


PASS, FAIL, ERROR = "PASS", "FAIL", "ERROR"
OUTCOME_STYLE = {
    PASS: "[green]PASS[/green]",
    FAIL: "[red]FAIL[/red]",
    ERROR: "[red]ERROR[/red]",
}

Row = tuple[str, str, str, str]  # check, expected, actual, PASS/FAIL/ERROR


class NamespaceListError(Exception):
    """The readonly credential could not list namespaces."""


def list_namespaces(kubeconfig: Path, context: str) -> list[str]:
    """Namespace names visible to the readonly credential (sorted, unique).

    Raises:
        NamespaceListError: On any failure; callers must not fall back to
            checking fewer namespaces.

    """
    command = [
        "kubectl",
        "--kubeconfig",
        str(kubeconfig),
        "--context",
        context,
        "get",
        "namespaces",
        "-o",
        "name",
    ]
    try:
        proc = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=KUBECTL_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError as e:
        raise NamespaceListError("kubectl not found in PATH") from e
    except subprocess.TimeoutExpired as e:
        raise NamespaceListError(
            f"kubectl timed out ({KUBECTL_TIMEOUT_SECONDS}s)"
        ) from e
    if proc.returncode != 0:
        detail = (proc.stderr.strip().splitlines() or [""])[0][:200]
        raise NamespaceListError(detail or f"kubectl exited {proc.returncode}")
    names = {
        line.strip().removeprefix("namespace/")
        for line in proc.stdout.splitlines()
        if line.strip()
    }
    return sorted(names)


def _cap(names: list[str]) -> str:
    """Comma list of at most ``MAX_LISTED_NAMESPACES`` names plus a count."""
    shown = ", ".join(names[:MAX_LISTED_NAMESPACES])
    extra = len(names) - MAX_LISTED_NAMESPACES
    return f"{shown} (+{extra} more)" if extra > 0 else shown


def _single_row(
    readonly: Path, context: str, args: tuple[str, ...], expected: str
) -> Row:
    result = run_can_i(readonly, context, args)
    check = " ".join(args)
    if result.answer == "error":
        return check, expected, result.detail or "error", ERROR
    return check, expected, result.answer, PASS if result.answer == expected else FAIL


def _namespace_rows(readonly: Path, context: str, namespaces: list[str]) -> list[Row]:
    """One row per ``PER_NAMESPACE_CHECKS`` entry, every namespace asked ``no``.

    Questions run concurrently; ``map`` keeps the result order deterministic.
    """
    jobs = [(base, ns) for base in PER_NAMESPACE_CHECKS for ns in namespaces]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(
            pool.map(
                lambda job: run_can_i(readonly, context, (*job[0], "-n", job[1])),
                jobs,
            )
        )
    rows: list[Row] = []
    count = len(namespaces)
    for index, base in enumerate(PER_NAMESPACE_CHECKS):
        chunk = results[index * count : (index + 1) * count]
        label = f"{' '.join(base)} -n <ns> (all {count} namespaces)"
        allowed = [
            ns for ns, r in zip(namespaces, chunk, strict=True) if r.answer == "yes"
        ]
        errors = [r for r in chunk if r.answer == "error"]
        if allowed:
            rows.append((label, "no", f"yes in: {_cap(allowed)}", FAIL))
        elif errors:
            rows.append(
                (
                    label,
                    "no",
                    f"{len(errors)} errors: {errors[0].detail or 'error'}",
                    ERROR,
                )
            )
        else:
            rows.append((label, "no", f"no in all {count} namespaces", PASS))
    return rows


def verify_rows(readonly: Path, context: str, access: AccessSettings) -> list[Row]:
    """All verify rows; an unlistable namespace set is an ERROR row, not a skip."""
    rows = [
        _single_row(readonly, context, args, expected)
        for args, expected in build_checks(access)
    ]
    try:
        discovered = list_namespaces(readonly, context)
    except NamespaceListError as e:
        rows.append(("get namespaces -o name", "listable", str(e) or "error", ERROR))
        return rows
    if not discovered:
        # A cluster always has namespaces; an empty list means the answer is
        # unreliable (filtered or partial), so checking only access.namespace
        # would silently cover less than it claims.
        rows.append(("get namespaces -o name", "non-empty", "0 namespaces", ERROR))
        return rows
    namespaces = sorted({*discovered, access.namespace})
    return [*rows, *_namespace_rows(readonly, context, namespaces)]
