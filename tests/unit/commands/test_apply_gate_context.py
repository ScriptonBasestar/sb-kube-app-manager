"""Apply must bind its complete selected group before hooks or pruning."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import click
import pytest
import yaml

from sbkube.commands import apply, build, deploy, prepare
from sbkube.models.config_model import SBKubeConfig
from sbkube.utils import deploy_gate, prune_helper
from sbkube.utils.deploy_plan import ExecutionContextError
from sbkube.utils.output_manager import OutputManager


@pytest.fixture
def lane(tmp_path, monkeypatch):
    path = tmp_path / "sbkube.yaml"
    kube = tmp_path / "kubeconfig"
    kube.write_text("synthetic-private-credential\n")
    apps = {
        "db": {"type": "noop"},
        "web": {"type": "noop", "depends_on": ["db"]},
        "old": {"type": "helm", "chart": "fixture/chart", "enabled": False},
    }
    path.write_text(yaml.safe_dump({
        "apiVersion": "sbkube/v1", "settings": {"namespace": "actual-group"},
        "apps": apps,
    }))
    config = SBKubeConfig(namespace="original-namespace", apps=apps,
                          hooks={"apply": {"pre": ["synthetic-hook"]}})
    ctx = click.Context(click.Command("fixture-apply"))
    ctx.obj = {"format": "human", "kubeconfig": str(kube), "context": "actual-context"}
    events = []
    captured = []
    invoked = []

    def accept(plan):
        events.append("gate")
        captured.append(plan)

    def hook(*_args, **_kwargs):
        events.append("hook")
        return True

    hook_mock = MagicMock()
    hook_mock.execute_command_hooks.side_effect = hook
    monkeypatch.setattr(apply, "HookExecutor", lambda **_kwargs: hook_mock)
    monkeypatch.setattr(deploy_gate, "resolved_gate_enabled", lambda _target: True)
    monkeypatch.setattr(deploy_gate, "run_resolved_gate", accept)

    def stage(name):
        @click.command()
        @click.pass_context
        def command(child_ctx, **kwargs):
            events.append(name)
            invoked.append((name, kwargs, child_ctx.obj))
        return command

    monkeypatch.setattr(prepare, "cmd", stage("prepare"))
    monkeypatch.setattr(build, "cmd", stage("build"))
    monkeypatch.setattr(deploy, "cmd", stage("deploy"))
    prune = MagicMock(return_value=True)
    monkeypatch.setattr(prune_helper, "prune_disabled_apps", prune)

    def run(**overrides):
        kwargs = {
            "ctx": ctx, "config": config, "base_dir": str(tmp_path), "app_config_dir": tmp_path,
            "current_app_dir": ".", "config_file_name": path.name, "sources_file_name": path.name,
            "app_name": "web", "dry_run": False, "skip_prepare": False, "skip_build": False,
            "skip_deps_check": True, "strict_deps": False, "no_progress": True,
            "output": OutputManager(format_type="human"), "prune_disabled": False,
        }
        return apply._execute_apps_deployment(**(kwargs | overrides))

    return SimpleNamespace(run=run, path=path, kube=kube, config=config, ctx=ctx,
                           events=events, captured=captured, invoked=invoked,
                           hooks=hook_mock, prune=prune)


def test_apply_gate_precedes_hooks_and_binds_shared_child_plan(lane):
    assert lane.run()
    assert lane.events[:2] == ["gate", "hook"]
    plan = lane.captured[0]
    payload = json.loads(plan.payload_json)
    assert [app["name"] for app in payload["apps"]] == ["db", "web"]
    assert {app["namespace"] for app in payload["apps"]} == {"actual-group"}
    assert payload["context"] == "actual-context"
    assert payload["kubeconfig"] == str(lane.kube)
    assert "synthetic-private-credential" not in plan.payload_json
    children = [obj for name, _, obj in lane.invoked if name == "deploy"]
    assert len(children) == 2
    assert all(obj["_sbkube_apply_execution"] is plan for obj in children)
    assert "_sbkube_apply_execution" not in lane.ctx.obj


def test_apply_refusal_prevents_hooks_prune_and_stages(lane, monkeypatch):
    def refuse(_plan):
        raise ExecutionContextError("fixture refusal")
    monkeypatch.setattr(deploy_gate, "run_resolved_gate", refuse)
    with pytest.raises(ExecutionContextError, match="fixture refusal"):
        lane.run(prune_disabled=True)
    lane.hooks.execute_command_hooks.assert_not_called()
    lane.prune.assert_not_called()
    assert lane.invoked == []


def test_pre_apply_hook_input_change_prevents_prune_and_stages(lane):
    def mutate(*_args, **_kwargs):
        lane.path.write_text("changed after the resolved gate\n")
        return True
    lane.hooks.execute_command_hooks.side_effect = mutate
    with pytest.raises(ExecutionContextError):
        lane.run(prune_disabled=True)
    lane.prune.assert_not_called()
    assert lane.invoked == []


def test_apply_plan_binds_prune_set_and_effective_cluster(lane):
    assert lane.run(prune_disabled=True)
    payload = json.loads(lane.captured[0].payload_json)
    assert payload["prune_apps"] == ["old"]
    assert payload["operation"] == "prune"
    assert lane.prune.call_args.kwargs["kubeconfig"] == str(lane.kube)
    assert lane.prune.call_args.kwargs["context"] == "actual-context"


@pytest.mark.parametrize("dry_run", [False, True])
def test_inactive_or_dry_run_does_not_resolve_new_context(lane, monkeypatch, dry_run):
    if not dry_run:
        monkeypatch.setattr(deploy_gate, "resolved_gate_enabled", lambda _target: False)
    resolver = MagicMock(side_effect=AssertionError("unexpected context resolution"))
    monkeypatch.setattr(deploy, "resolve_deploy_group_inputs", resolver)
    assert lane.run(dry_run=dry_run)
    resolver.assert_not_called()
    assert lane.captured == []
