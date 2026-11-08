"""Resolved deploy metadata and execution must consume the same inputs."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import click
import pytest
import yaml
from click.testing import CliRunner

from sbkube.commands import deploy
from sbkube.utils import cli_check, deploy_gate
from sbkube.utils.deploy_plan import ExecutionContextError
from sbkube.utils.output_manager import OutputManager

REAL_RUN_GATE = deploy_gate.run_gate
REAL_RUN_RESOLVED_GATE = deploy_gate.run_resolved_gate


@pytest.fixture
def lane(monkeypatch, tmp_path):
    kubeconfig = tmp_path / "kubeconfig"
    kubeconfig.write_text("fixture-only\n")
    settings = {"kubeconfig": str(kubeconfig), "kubeconfig_context": "source-context"}
    app = {"type": "helm", "chart": "fixture/chart", "version": "1.0.0"}
    config_file = tmp_path / "sbkube.yaml"
    config_file.write_text(yaml.safe_dump({
        "apiVersion": "sbkube/v1", "settings": {**settings, "namespace": "group-ns"},
        "apps": {"web": app},
    }))
    gate = MagicMock()
    actual_helm_helper = deploy.deploy_helm_app
    helper = MagicMock(return_value=True)
    recorder = MagicMock()
    hooks = MagicMock()
    hooks.return_value.execute_command_hooks.return_value = True
    hooks.return_value.execute_app_hook_with_manifests.return_value = True
    hooks.return_value.execute_hook_tasks.return_value = True
    connectivity = MagicMock()
    monkeypatch.setattr(
        cli_check, "validate_context_exists", MagicMock(return_value=(True, [], None))
    )
    # Global CLI collection may have installed the separate preflight wrapper.
    # Its contract is covered by test_deploy_gate; this lane exercises resolved inputs.
    monkeypatch.setattr(deploy_gate, "run_gate", MagicMock())
    monkeypatch.setattr(deploy, "check_kubectl_installed_or_exit", MagicMock())
    monkeypatch.setattr(deploy, "check_helm_installed_or_exit", MagicMock())
    monkeypatch.setattr(deploy, "check_cluster_connectivity_or_exit", connectivity)
    monkeypatch.setattr(deploy, "run_resolved_gate", gate)
    monkeypatch.setattr(deploy, "resolved_gate_enabled", lambda _target: True)
    monkeypatch.setattr(deploy, "deploy_helm_app", helper)
    monkeypatch.setattr(deploy, "DeploymentRecorder", recorder)
    monkeypatch.setattr(deploy, "HookExecutor", hooks)
    capture = deploy.capture_execution_context
    captured = []

    def save_capture(*args, **kwargs):
        plan = capture(*args, **kwargs)
        captured.append((plan, args, kwargs))
        return plan

    monkeypatch.setattr(deploy, "capture_execution_context", save_capture)
    return SimpleNamespace(
        root=tmp_path, config_file=config_file, kubeconfig=kubeconfig, settings=settings,
        app=app, gate=gate, helper=helper, recorder=recorder, hooks=hooks,
        captured=captured, connectivity=connectivity,
        actual_helm_helper=actual_helm_helper,
    )


def invoke(lane, *args, **obj):
    return CliRunner().invoke(
        deploy.cmd, ["-f", str(lane.config_file), *args], obj={"format": "human", **obj}
    )


def test_gate_fields_and_executor_use_same_resolved_objects(lane):
    document = yaml.safe_load(lane.config_file.read_text())
    document["apps"]["web"]["namespace"] = "app-ns"
    document["apps"]["other"] = lane.app
    lane.config_file.write_text(yaml.safe_dump(document))
    override = lane.root / "override-kubeconfig"
    override.write_text("override-fixture\n")

    result = invoke(lane, "--app", "web", kubeconfig=str(override), context="override-context")

    assert result.exit_code == 0, result.output
    plan, capture_args, capture_kwargs = lane.captured[0]
    payload = json.loads(plan.payload_json)
    assert payload["config_file"] == str(lane.config_file.resolve())
    assert payload["kubeconfig"] == str(override.resolve())
    assert payload["context"] == "override-context"
    assert [(app["name"], app["namespace"]) for app in payload["apps"]] == [("web", "app-ns")]
    assert plan.selected_apps == ("web",)
    assert capture_args[3] == ("web",)
    lane.gate.assert_called_once_with(plan)
    args, kwargs = lane.helper.call_args
    assert args[0] == "web"
    assert args[1] is capture_args[2].apps["web"]
    assert args[7:9] == (str(override), "override-context")
    assert kwargs["git_apps"] is capture_args[2].apps
    assert kwargs["git_repos"] is capture_kwargs["sources"].git_repos
    assert lane.recorder.call_args.kwargs["sources_data"]["kubeconfig_context"] == "override-context"


def test_refusal_precedes_recorder_hooks_and_executor(lane):
    lane.gate.side_effect = click.ClickException("fixture gate refusal")
    result = invoke(lane)
    assert result.exit_code != 0
    assert "fixture gate refusal" in result.output
    lane.recorder.assert_not_called()
    lane.hooks.assert_not_called()
    lane.helper.assert_not_called()
    lane.connectivity.assert_not_called()


@pytest.mark.parametrize("gate_file", [False, True])
def test_gate_input_mutation_refused_before_recorder(lane, gate_file):
    changed_file = lane.config_file
    if gate_file:
        changed_file = lane.root / "sbkube-gate.yaml"
        changed_file.write_text("deploy_gate:\n  mode: enforce\n  command: fixture-only\n")
    lane.gate.side_effect = lambda _plan: changed_file.write_text("changed\n")
    result = invoke(lane)
    assert result.exit_code != 0
    assert isinstance(result.exception, ExecutionContextError)
    lane.recorder.assert_not_called()
    lane.hooks.assert_not_called()
    lane.helper.assert_not_called()


def test_global_pre_hook_mutation_prevents_helper(lane):
    # Command hooks are part of the existing legacy config contract.
    lane.config_file = lane.root / "config.yaml"
    lane.config_file.write_text(yaml.safe_dump({
        "namespace": "group-ns", "apps": {"web": lane.app},
        "hooks": {"deploy": {"pre": ["fixture-only"]}},
    }))
    (lane.root / "sources.yaml").write_text(yaml.safe_dump(lane.settings))

    def mutate(**_kwargs):
        lane.config_file.write_text("changed-by-hook\n")
        return True

    lane.hooks.return_value.execute_command_hooks.side_effect = mutate
    result = invoke(lane)
    assert result.exit_code != 0
    assert isinstance(result.exception, ExecutionContextError)
    lane.helper.assert_not_called()


def test_app_hook_sources_model_mutation_prevents_helper(lane):
    document = yaml.safe_load(lane.config_file.read_text())
    document["apps"]["web"]["hooks"] = {"pre_deploy": ["fixture-only"]}
    lane.config_file.write_text(yaml.safe_dump(document))

    def mutate(**_kwargs):
        lane.captured[0][2]["sources"].kubeconfig_context = "changed-context"
        return True

    lane.hooks.return_value.execute_app_hook_with_manifests.side_effect = mutate
    result = invoke(lane)
    assert result.exit_code != 0
    assert isinstance(result.exception, ExecutionContextError)
    lane.helper.assert_not_called()
    lane.recorder.return_value.finish.assert_called_once_with(failed=True)


def test_dry_run_skips_resolved_gate(lane):
    result = invoke(lane, "--dry-run")
    assert result.exit_code == 0, result.output
    lane.gate.assert_not_called()
    lane.recorder.assert_not_called()
    assert lane.helper.call_args.args[9] is True
    assert lane.captured == []


@pytest.mark.parametrize("mode", [None, "off", "warn"])
def test_no_resolved_gate_does_not_add_capture_or_verification(lane, monkeypatch, mode):
    from sbkube.utils.deploy_gate import resolved_gate_enabled

    if mode is not None:
        (lane.root / "sbkube-gate.yaml").write_text(
            f"deploy_gate:\n  command: fixture-only\n  mode: '{mode}'\n"
        )
    monkeypatch.setattr(deploy, "resolved_gate_enabled", resolved_gate_enabled)
    result = invoke(lane)
    assert result.exit_code == 0, result.output
    assert lane.captured == []
    lane.gate.assert_not_called()
    lane.helper.assert_called_once()


@pytest.mark.parametrize("refuse", [False, True])
def test_parent_apply_context_checked_before_child_gate(lane, refuse):
    parent = MagicMock()
    if refuse:
        parent.verify_child.side_effect = ExecutionContextError("fixture parent mismatch")
    result = invoke(lane, _sbkube_apply_execution=parent)
    parent.verify_child.assert_called_once_with(lane.captured[0][0])
    if refuse:
        assert result.exit_code != 0
        lane.gate.assert_not_called()
        lane.recorder.assert_not_called()
        lane.hooks.assert_not_called()
        lane.helper.assert_not_called()
    else:
        assert result.exit_code == 0, result.output
        lane.helper.assert_called_once()


def test_shared_resolver_preserves_parent_namespace_and_input_paths(lane):
    (lane.root / ".sbkube-workspace").write_text("anchors: {}\n")
    root_config = lane.root / "sbkube.yaml"
    root_config.write_text(yaml.safe_dump({
        "apiVersion": "sbkube/v1", "settings": {**lane.settings, "namespace": "parent-ns"},
        "apps": {},
    }))
    app_dir = lane.root / "child"
    app_dir.mkdir()
    config_file = app_dir / "sbkube.yaml"
    values_file = app_dir / "cluster-values.yaml"
    values_file.write_text("fixture: true\n")
    config_file.write_text(yaml.safe_dump({
        "apiVersion": "sbkube/v1", "settings": {"cluster_values_file": "cluster-values.yaml"},
        "apps": {"web": lane.app},
    }))
    ctx = click.Context(deploy.cmd, obj={"sources_file": "sbkube.yaml"})
    sources, values, kubeconfig, context, config, inputs = deploy.resolve_deploy_group_inputs(
        ctx, lane.root, app_dir, config_file, OutputManager(format_type="human")
    )
    assert config.namespace == config.apps["web"].namespace == "parent-ns"
    assert (kubeconfig, context) == (str(lane.kubeconfig), "source-context")
    assert sources.kubeconfig_context == context
    assert values == {"fixture": True}
    assert {root_config, config_file, values_file, lane.kubeconfig} <= set(inputs)


def test_helm_app_context_payload_matches_actual_helm_command(lane, monkeypatch):
    chart = lane.root / "chart"
    chart.mkdir()
    (chart / "Chart.yaml").write_text("apiVersion: v2\nname: fixture\nversion: 1.0.0\n")
    document = yaml.safe_load(lane.config_file.read_text())
    document["settings"]["kubeconfig_context"] = "dev"
    document["apps"]["web"] = {
        "type": "helm", "chart": "./chart", "context": "prod",
        "helm_label_injection": False,
    }
    lane.config_file.write_text(yaml.safe_dump(document))
    run = MagicMock(return_value=(0, "fixture-success", ""))
    monkeypatch.setattr(deploy, "run_command", run)
    monkeypatch.setattr(deploy, "deploy_helm_app", lane.actual_helm_helper)

    result = invoke(lane)

    assert result.exit_code == 0, result.output
    plan = lane.gate.call_args.args[0]
    payload = json.loads(plan.payload_json)
    assert payload["context"] == "dev"
    assert payload["apps"][0]["name"] == "web"
    assert payload["apps"][0]["context"] == "prod"
    commands = [call.args[0] for call in run.call_args_list]
    helm_commands = [command for command in commands if command[:2] == ["helm", "upgrade"]]
    assert len(helm_commands) == 1
    command = helm_commands[0]
    assert command[command.index("--kube-context") + 1] == payload["apps"][0]["context"]
    assert command[command.index("--kubeconfig") + 1] == payload["kubeconfig"]
    namespace_commands = [
        command for command in commands if command[:3] == ["kubectl", "get", "namespace"]
    ]
    assert len(namespace_commands) == 1
    assert namespace_commands[0][namespace_commands[0].index("--context") + 1] == "prod"


def test_yaml_app_context_payload_matches_actual_kubectl_command(lane, monkeypatch):
    manifest = lane.root / "manifest.yaml"
    manifest.write_text("apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: fixture\n")
    document = yaml.safe_load(lane.config_file.read_text())
    document["settings"]["kubeconfig_context"] = "dev"
    document["apps"]["web"] = {
        "type": "yaml", "manifests": ["manifest.yaml"], "context": "prod",
    }
    lane.config_file.write_text(yaml.safe_dump(document))
    run = MagicMock(return_value=(0, "fixture-success", ""))
    monkeypatch.setattr(deploy, "run_command", run)

    result = invoke(lane)

    assert result.exit_code == 0, result.output
    payload = json.loads(lane.gate.call_args.args[0].payload_json)
    assert payload["context"] == "dev"
    assert payload["apps"][0]["name"] == "web"
    assert payload["apps"][0]["context"] == "prod"
    run.assert_called_once()
    command = run.call_args.args[0]
    assert command[:2] == ["kubectl", "apply"]
    assert command[command.index("--context") + 1] == payload["apps"][0]["context"]
    assert command[command.index("--kubeconfig") + 1] == payload["kubeconfig"]
    lane.helper.assert_not_called()


def _strict_invoke(lane, monkeypatch, *, fail_resolved=False, omit_resolved=False, app="web", obj=None):
    from sbkube.cli import main

    (lane.root / ".sbkube-workspace").write_text("anchors: {}\n")
    (lane.root / "sbkube-gate.yaml").write_text(
        "deploy_gate:\n  mode: enforce\n  command: fixture-only\n"
    )
    events = []

    def external(_argv, **kwargs):
        phase = kwargs["env"]["SBKUBE_GATE_PHASE"]
        events.append(phase)
        return SimpleNamespace(returncode=3 if fail_resolved and phase == "resolved" else 0)

    monkeypatch.setattr(deploy_gate, "run_gate", REAL_RUN_GATE)
    monkeypatch.setattr(deploy_gate, "_granted", MagicMock(side_effect=AssertionError("grant consulted")))
    monkeypatch.setattr(deploy_gate.subprocess, "run", external)
    monkeypatch.setattr(deploy, "resolved_gate_enabled", deploy_gate.resolved_gate_enabled)
    monkeypatch.setattr(deploy, "run_resolved_gate", MagicMock() if omit_resolved else REAL_RUN_RESOLVED_GATE)
    lane.helper.side_effect = lambda *_args, **_kwargs: events.append("effect") or True
    result = CliRunner().invoke(main, [
        "deploy", "--require-resolved-gate", "-f", str(lane.config_file), "--app", app,
    ], obj=obj)
    return result, events


def test_strict_deploy_requires_both_actual_gate_phases_before_executor(lane, monkeypatch):
    result, events = _strict_invoke(lane, monkeypatch)
    assert result.exit_code == 0, result.output
    assert events == ["preflight", "resolved", "effect"]
    assert json.loads(lane.captured[0][0].payload_json)["authority"] == "none"
    assert not deploy_gate.strict_resolved_gate_required()


@pytest.mark.parametrize("omit", [False, True])
def test_strict_missing_or_refused_resolved_phase_has_no_effect(lane, monkeypatch, omit):
    result, events = _strict_invoke(lane, monkeypatch, fail_resolved=not omit, omit_resolved=omit)
    assert result.exit_code != 0
    assert "effect" not in events
    lane.connectivity.assert_not_called()
    lane.recorder.assert_not_called()
    lane.hooks.assert_not_called()
    lane.helper.assert_not_called()
    assert not deploy_gate.strict_resolved_gate_required()


@pytest.mark.parametrize("scope", ["multigroup", "nonhelm", "missing_app", "parent_apply", "phase"])
def test_strict_scope_rejected_before_connectivity_or_effect(lane, monkeypatch, scope):
    if scope == "multigroup":
        monkeypatch.setattr(deploy, "resolve_app_dirs", lambda *_a, **_kw: [lane.root, lane.root / "other"])
    elif scope in {"nonhelm", "phase"}:
        document = yaml.safe_load(lane.config_file.read_text())
        document["apps"] = {"web": {"type": "noop"}} if scope == "nonhelm" else {}
        if scope == "phase":
            document["phases"] = {"child": {"source": "child"}}
        lane.config_file.write_text(yaml.safe_dump(document))
    obj = {"_sbkube_apply_execution": object()} if scope == "parent_apply" else None
    result, events = _strict_invoke(
        lane, monkeypatch, app="missing" if scope == "missing_app" else "web", obj=obj
    )
    assert result.exit_code != 0
    assert "effect" not in events
    lane.connectivity.assert_not_called()
    lane.recorder.assert_not_called()
    lane.hooks.assert_not_called()
    lane.helper.assert_not_called()
    assert not deploy_gate.strict_resolved_gate_required()
