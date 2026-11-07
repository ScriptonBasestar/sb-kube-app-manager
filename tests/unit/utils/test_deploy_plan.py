"""Resolved metadata binds inputs without granting or executing deployment."""

import hashlib
import json
import os
import sys
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from sbkube.models.config_model import SBKubeConfig
from sbkube.models.sources_model import SourceScheme
from sbkube.utils import deploy_gate, deploy_plan
from sbkube.utils.deploy_plan import ExecutionContextError, capture_execution_context


@pytest.fixture
def inputs(tmp_path):
    secret = "fixture-private-value-must-not-be-exported"
    (tmp_path / ".sbkube-workspace").write_text("anchors: {}\n")
    config = SBKubeConfig(
        namespace="shared-ns",
        apps={
            "alpha": {
                "type": "helm", "chart": "fixture/alpha", "version": "1.0.0",
                "hooks": {"pre_deploy": [secret]},
            },
            "beta": {
                "type": "helm", "chart": "fixture/beta", "version": "1.0.0",
                "namespace": "override-ns",
            },
            "task": {"type": "noop"},
        },
        hooks={"deploy": {"pre": [secret]}},
    )
    sources = SourceScheme(
        kubeconfig=str(tmp_path / "cluster-config"), kubeconfig_context="source-context",
        global_values={"private": secret},
    )
    config_file = tmp_path / "sbkube.yaml"
    config_file.write_text(config.model_dump_json())
    sources_file = tmp_path / "sources.yaml"
    sources_file.write_text(sources.model_dump_json())
    kubeconfig = tmp_path / "cluster-config"
    kubeconfig.write_text(f"fixture-token: {secret}\n")

    def capture(**overrides):
        kwargs = {
            "operation": "deploy", "config_file": config_file, "config": config,
            "selected_apps": ("alpha", "beta", "task"), "kubeconfig": str(kubeconfig),
            "context": "effective-context", "sources": sources,
            "input_paths": (sources_file,),
        }
        kwargs.update(overrides)
        return capture_execution_context(**kwargs)

    return SimpleNamespace(
        root=tmp_path, secret=secret, config=config, sources=sources,
        config_file=config_file, sources_file=sources_file, kubeconfig=kubeconfig,
        capture=capture,
    )


@pytest.fixture
def external_gate(inputs, monkeypatch):
    gate_file = inputs.root / "sbkube-gate.yaml"
    gate_file.write_text("deploy_gate:\n  mode: enforce\n  command: fixture-gate\n  timeout: 3\n")
    # Grants are outside this transport fixture; no process inspection is needed.
    monkeypatch.setattr(deploy_gate, "_granted", lambda _gate: None)
    run = Mock(return_value=SimpleNamespace(returncode=0))
    monkeypatch.setattr(deploy_gate.subprocess, "run", run)
    return run


def test_typed_payload_binds_effective_context_and_hashes_without_raw_secrets(inputs):
    plan = inputs.capture()
    payload = json.loads(plan.payload_json)
    assert payload["schema"] == "sbkube-deploy-context/v1"
    assert payload["operation"] == "deploy"
    assert payload["target"] == str(inputs.root.resolve())
    assert payload["config_file"] == str(inputs.config_file.resolve())
    assert payload["kubeconfig"] == str(inputs.kubeconfig.resolve())
    assert payload["context"] == "effective-context"
    assert [(app["name"], app["namespace"]) for app in payload["apps"]] == [
        ("alpha", "shared-ns"), ("beta", "override-ns"), ("task", "shared-ns"),
    ]
    assert all(type(app["enabled"]) is bool for app in payload["apps"])
    assert payload["apps"][0]["opaque_effects"] is True
    assert type(payload["global_hooks"]) is bool
    assert payload["global_hooks"] is True
    bound = {item["path"]: item["sha256"] for item in payload["inputs"]}
    assert bound[str(inputs.sources_file.resolve())] == hashlib.sha256(
        inputs.sources_file.read_bytes()
    ).hexdigest()
    assert payload["inputs_complete"] is True
    assert payload["artifacts"] == "not-attested"
    assert payload["authority"] == "none"
    assert inputs.secret not in plan.payload_json
    assert inputs.secret not in repr(plan)
    plan.verify()


@pytest.mark.parametrize("reason", ["missing-input", "parent-source-trace-unavailable"])
def test_incomplete_inputs_do_not_claim_artifact_verification(inputs, reason):
    if reason == "missing-input":
        plan = inputs.capture(input_paths=(inputs.root / "not-prepared.yaml",))
    else:
        inputs.config_file.write_text("_parent: '@fixture/parent'\n")
        plan = inputs.capture()
    payload = json.loads(plan.payload_json)
    assert payload["inputs_complete"] is False
    assert reason in payload["incomplete_reasons"]
    assert payload["artifacts"] == "not-attested"
    assert payload["authority"] == "none"


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_yaml_escaped_parent_key_never_claims_complete_sources(inputs, encoding):
    document = 'apiVersion: sbkube/v1\n"\\u005fparent": "parent.yaml"\n'
    inputs.config_file.write_bytes(document.encode(encoding))
    assert b"_parent" not in inputs.config_file.read_bytes()
    payload = json.loads(inputs.capture().payload_json)
    assert payload["inputs_complete"] is False
    assert "parent-source-trace-unavailable" in payload["incomplete_reasons"]


def test_symlinked_config_keeps_execution_gate_directory(inputs, external_gate, tmp_path):
    origin = tmp_path / "external-config"
    origin.mkdir()
    actual = origin / "source.yaml"
    actual.write_bytes(inputs.config_file.read_bytes())
    inputs.config_file.unlink()
    inputs.config_file.symlink_to(actual)
    plan = inputs.capture()
    deploy_gate.run_resolved_gate(plan)
    assert plan.config_file.parent == inputs.root.resolve()
    assert external_gate.call_args.kwargs["env"]["SBKUBE_GATE_TARGET"] == str(inputs.root.resolve())
    alternate = origin / "same-bytes.yaml"
    alternate.write_bytes(actual.read_bytes())
    inputs.config_file.unlink()
    inputs.config_file.symlink_to(alternate)
    with pytest.raises(ExecutionContextError):
        plan.verify()


@pytest.mark.parametrize("mutation", ["file", "config", "sources", "symlink"])
def test_input_and_model_mutations_are_refused(inputs, mutation):
    extra = []
    if mutation == "symlink":
        original = inputs.root / "original-values.yaml"
        replacement = inputs.root / "replacement-values.yaml"
        original.write_text("identical: content\n")
        replacement.write_text("identical: content\n")
        link = inputs.root / "values.yaml"
        link.symlink_to(original)
        extra.append(link)
    plan = inputs.capture(input_paths=(inputs.sources_file, *extra))
    if mutation == "file":
        inputs.sources_file.write_text("changed: true\n")
    elif mutation == "config":
        inputs.config.apps["alpha"].namespace = "changed-ns"
    elif mutation == "sources":
        inputs.sources.kubeconfig_context = "changed-context"
    else:
        link.unlink()
        link.symlink_to(replacement)
    with pytest.raises(ExecutionContextError):
        plan.verify()


@pytest.mark.parametrize("kind", ["fifo", "oversize", "payload"])
def test_nonregular_and_oversize_inputs_are_bounded(inputs, monkeypatch, kind):
    extra = inputs.root / "bounded-input"
    if kind == "fifo":
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO fixture requires mkfifo")
        os.mkfifo(extra)
    elif kind == "oversize":
        monkeypatch.setattr(deploy_plan, "MAX_INPUT_BYTES", 4096)
        extra.write_bytes(b"x" * 4097)
    else:
        monkeypatch.setattr(deploy_plan, "MAX_CONTEXT_BYTES", 1)
        extra.write_text("fixture\n")
    with pytest.raises(ExecutionContextError):
        inputs.capture(input_paths=(extra,))


def test_apply_parent_accepts_exact_selected_subset(inputs):
    parent = inputs.capture(operation="apply", selected_apps=("alpha", "beta"))
    child = inputs.capture(selected_apps=("beta",))
    parent.verify_child(child)
    parent.verify()
    child.verify()


@pytest.mark.parametrize("difference", ["context", "kubeconfig", "source", "app", "path", "selection"])
def test_apply_parent_refuses_different_child_scope(inputs, difference):
    parent = inputs.capture(operation="apply", selected_apps=("alpha", "beta"))
    kwargs = {"selected_apps": ("alpha",)}
    if difference == "context":
        kwargs["context"] = "different-context"
    elif difference == "kubeconfig":
        another = inputs.root / "another-kubeconfig"
        another.write_text("fixture\n")
        kwargs["kubeconfig"] = str(another)
    elif difference == "source":
        sources = inputs.sources.model_copy(deep=True)
        sources.global_values = {"private": "different-fixture"}
        kwargs["sources"] = sources
    elif difference == "app":
        config = inputs.config.model_copy(deep=True)
        config.apps["alpha"].namespace = "different-ns"
        kwargs["config"] = config
    elif difference == "path":
        another = inputs.root / "another-config.yaml"
        another.write_bytes(inputs.config_file.read_bytes())
        kwargs["config_file"] = another
    else:
        kwargs["selected_apps"] = ("task",)
    child = inputs.capture(**kwargs)
    with pytest.raises(ExecutionContextError):
        parent.verify_child(child)


def test_external_gate_receives_resolved_json_and_matching_operation_target(
    inputs, external_gate, monkeypatch
):
    monkeypatch.setenv("SBKUBE_GATE_CONTEXT", "untrusted-inherited-context")
    monkeypatch.setenv("SBKUBE_GATE_PHASE", "untrusted-inherited-phase")
    monkeypatch.setenv("SBKUBE_GATE_OPERATION", "untrusted-inherited-operation")
    monkeypatch.setenv("SBKUBE_GATE_TARGET", "untrusted-inherited-target")
    monkeypatch.setenv("SBKUBE_GATE_UNDECLARED", "untrusted-extra")
    plan = inputs.capture()
    deploy_gate.run_resolved_gate(plan)
    external_gate.assert_called_once()
    args, kwargs = external_gate.call_args
    assert args[0] == ["fixture-gate", "deploy"]
    assert kwargs["cwd"] == inputs.root
    assert kwargs["timeout"] == 3
    env = kwargs["env"]
    assert env["SBKUBE_GATE_PHASE"] == "resolved"
    assert env["SBKUBE_GATE_OPERATION"] == plan.operation
    assert env["SBKUBE_GATE_TARGET"] == str(plan.config_file.parent)
    assert env["SBKUBE_GATE_CONTEXT"] == plan.payload_json
    assert json.loads(env["SBKUBE_GATE_CONTEXT"])["context"] == "effective-context"
    assert "SBKUBE_GATE_UNDECLARED" not in env


def test_preflight_discards_inherited_resolved_context(inputs, external_gate, monkeypatch):
    monkeypatch.setenv("SBKUBE_GATE_CONTEXT", "untrusted-inherited-context")
    monkeypatch.setenv("SBKUBE_GATE_PHASE", "resolved")
    monkeypatch.setenv("SBKUBE_GATE_UNDECLARED", "untrusted-extra")
    deploy_gate.run_gate("deploy", {"config_file": str(inputs.config_file)}, None)
    env = external_gate.call_args.kwargs["env"]
    assert env["SBKUBE_GATE_PHASE"] == "preflight"
    assert env["SBKUBE_GATE_OPERATION"] == "deploy"
    assert env["SBKUBE_GATE_TARGET"] == str(inputs.root.resolve())
    assert "SBKUBE_GATE_CONTEXT" not in env
    assert "SBKUBE_GATE_UNDECLARED" not in env


def test_resolved_gate_rechecks_mutation_after_external_callback(inputs, external_gate):
    plan = inputs.capture()

    def changed(*_args, **_kwargs):
        inputs.sources_file.write_text("changed-during-gate: true\n")
        return SimpleNamespace(returncode=0)

    external_gate.side_effect = changed
    with pytest.raises(ExecutionContextError):
        deploy_gate.run_resolved_gate(plan)


@pytest.mark.parametrize("difference", ["operation", "target"])
def test_gate_rejects_context_bound_to_another_invocation(inputs, external_gate, difference):
    plan = inputs.capture()
    operation = "apply" if difference == "operation" else "deploy"
    path = inputs.config_file
    if difference == "target":
        another = inputs.root / "child"
        another.mkdir()
        path = another / "sbkube.yaml"
    with pytest.raises(deploy_gate.DeployGateError):
        deploy_gate.run_gate(
            operation, {"config_file": str(path)}, None, execution_context=plan
        )
    external_gate.assert_not_called()


def test_recorded_human_skip_only_disables_resolved_gate_for_its_callback(
    inputs, external_gate, monkeypatch
):
    terminal_in, terminal_err = StringIO(), StringIO()
    monkeypatch.setattr(terminal_in, "isatty", lambda: True)
    monkeypatch.setattr(terminal_err, "isatty", lambda: True)
    monkeypatch.setattr(sys, "stdin", terminal_in)
    monkeypatch.setattr(sys, "stderr", terminal_err)
    record = Mock()
    monkeypatch.setattr(deploy_gate, "record_gate_skip", record)
    external_gate.return_value = SimpleNamespace(returncode=19)
    observed = []

    def body(*, config_file):
        assert config_file == str(inputs.config_file)
        observed.append(deploy_gate.resolved_gate_enabled(inputs.root))
        return "fixture-callback-complete"

    callback = deploy_gate.gate_callback("deploy", body)
    assert callback(
        config_file=str(inputs.config_file), skip_deploy_gate="fixture operator reason"
    ) == "fixture-callback-complete"
    assert observed == [False]
    record.assert_called_once_with(
        operation="deploy", target_dir=inputs.root.resolve(),
        reason="fixture operator reason", gate_file=inputs.root / "sbkube-gate.yaml",
    )
    external_gate.assert_not_called()
    assert deploy_gate.resolved_gate_enabled(inputs.root) is True

    # A subsequent invocation has no inherited skip and its failing gate refuses.
    with pytest.raises(deploy_gate.DeployGateError):
        callback(config_file=str(inputs.config_file))
    external_gate.assert_called_once()
    record.assert_called_once()
    assert observed == [False]
    assert deploy_gate.resolved_gate_enabled(inputs.root) is True


def test_failed_skip_record_does_not_disable_resolved_gate(inputs, external_gate, monkeypatch):
    terminal_in, terminal_err = StringIO(), StringIO()
    monkeypatch.setattr(terminal_in, "isatty", lambda: True)
    monkeypatch.setattr(terminal_err, "isatty", lambda: True)
    monkeypatch.setattr(sys, "stdin", terminal_in)
    monkeypatch.setattr(sys, "stderr", terminal_err)
    record = Mock(side_effect=RuntimeError("fixture recording failure"))
    monkeypatch.setattr(deploy_gate, "record_gate_skip", record)
    external_gate.return_value = SimpleNamespace(returncode=19)
    body = Mock()
    callback = deploy_gate.gate_callback("deploy", body)

    with pytest.raises(RuntimeError, match="fixture recording failure"):
        callback(config_file=str(inputs.config_file), skip_deploy_gate="fixture operator reason")
    record.assert_called_once()
    body.assert_not_called()
    external_gate.assert_not_called()
    assert deploy_gate.resolved_gate_enabled(inputs.root) is True
