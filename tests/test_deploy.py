import os
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, call, mock_open
import yaml
import pytest

from click.testing import CliRunner
from sbkube.cli import main as sbkube_cli
from sbkube.utils.common import run_command 

EXAMPLES_DIR = Path("examples/k3scode")
BUILD_DIR = Path("build")
KUBECONFIG_TEST = Path.home() / ".kube/test-kubeconfig"
RELEASE_NAME = "browserless"

SBKUBE_CLI_PATH = 'sbkube.cli'
KUBECTL_CHECK_PATH = f'{SBKUBE_CLI_PATH}.check_kubectl_installed_or_exit'
HELM_CHECK_PATH = f'{SBKUBE_CLI_PATH}.check_helm_installed_or_exit'

def clean():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

def run_cmd(args, env=None):
    result = subprocess.run(args, capture_output=True, text=True, env=env)
    print(result.stdout)
    print(result.stderr)
    return result

def test_deploy_on_test_cluster():
    clean()

    # 테스트 클러스터 kubeconfig로 설정
    if not KUBECONFIG_TEST.exists():
        raise RuntimeError(f"❌ 테스트 클러스터 kubeconfig가 없습니다: {KUBECONFIG_TEST}")

    env = os.environ.copy()
    env["KUBECONFIG"] = str(KUBECONFIG_TEST)

    # 1. prepare
    assert run_cmd([
        "sbkube", "prepare",
        "--apps", str(EXAMPLES_DIR / "config-browserless"),
        "--sources", str(EXAMPLES_DIR / "sources")
    ], env=env).returncode == 0

    # 2. build
    assert run_cmd([
        "sbkube", "build",
        "--apps", str(EXAMPLES_DIR / "config-browserless")
    ], env=env).returncode == 0

    # 3. deploy
    assert run_cmd([
        "sbkube", "deploy",
        "--apps", str(EXAMPLES_DIR / "config-browserless"),
        "--namespace", "devops"
    ], env=env).returncode == 0

    # 4. 검증: Helm 릴리스 존재 여부
    check = run_cmd(["helm", "ls", "-n", "devops"], env=env)
    assert RELEASE_NAME in check.stdout, f"❌ 릴리스 '{RELEASE_NAME}'이 배포되지 않았습니다."

    # 5. 검증: 리소스 생성 확인
    kget = run_cmd(["kubectl", "get", "all", "-n", "devops"], env=env)
    assert "pod" in kget.stdout or "deployment" in kget.stdout, "❌ 리소스 생성 안됨"

@patch(HELM_CHECK_PATH, return_value=None) 
def test_deploy_helm_app_install(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    deploy 명령어 실행 시 install-helm 타입 앱 (신규 설치) 과정을 테스트합니다.
    - helm install 명령어가 올바른 인자들로 호출되는지 확인합니다.
    - --dry-run 옵션도 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file 
    app_name = "my-helm-app"

    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.0")

    def mock_run_command_side_effect(cmd, *args, **kwargs):
        if cmd[:2] == ['helm', 'status']:
            return (1, "Error: release: not found", "") 
        elif cmd[:2] == ['helm', 'install']:
            return (0, "RELEASE: my-helm-app\nSTATUS: deployed", "") 
        return (0, "default success", "")

    with patch('sbkube.utils.common.run_command', side_effect=mock_run_command_side_effect) as mock_run_cmd, \
         patch('pathlib.Path.is_dir', return_value=True): 

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        expected_status_call = call([
            'helm', 'status', app_name, 
            '--namespace', 'helm-ns' 
        ], capture_output=True, text=True, check=False, env=None)

        expected_install_call = call([
            'helm', 'install', app_name, str(built_chart_path),
            '--namespace', 'helm-ns', 
            '-f', str(values_file.resolve()), 
            '--set', 'master.replicaCount=1' 
        ], capture_output=True, text=True, check=False, env=None)
        
        status_called = any(c == expected_status_call for c in mock_run_cmd.call_args_list)
        install_called = any(c == expected_install_call for c in mock_run_cmd.call_args_list)
        assert status_called, "helm status 호출이 없습니다."
        assert install_called, "helm install 호출이 없습니다."

        assert f"Installing Helm app: {app_name}" in caplog.text
        assert f"Helm app {app_name} installed successfully." in caplog.text

        mock_run_cmd.reset_mock()
        caplog.clear()
        
        def mock_run_command_dry_run_side_effect(cmd, *args, **kwargs):
            if cmd[:2] == ['helm', 'status']:
                return (1, "Error: release: not found", "") 
            elif cmd[:2] == ['helm', 'install'] and '--dry-run' in cmd: 
                return (0, "DRY RUN OUTPUT YAML...", "") 
            return (0, "default success", "")

        mock_run_cmd.side_effect = mock_run_command_dry_run_side_effect

        result_dry_run = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--dry-run'
        ])
        assert result_dry_run.exit_code == 0
        
        expected_install_dry_run_call = call([
            'helm', 'install', app_name, str(built_chart_path),
            '--namespace', 'helm-ns',
            '-f', str(values_file.resolve()),
            '--set', 'master.replicaCount=1',
            '--dry-run'
        ], capture_output=True, text=True, check=False, env=None)
        
        install_dry_run_called = any(c == expected_install_dry_run_call for c in mock_run_cmd.call_args_list)
        assert install_dry_run_called, "helm install --dry-run 호출이 없습니다."
        assert "Dry run for Helm app" in caplog.text
        assert "DRY RUN OUTPUT YAML..." in result_dry_run.output 

@patch(HELM_CHECK_PATH, return_value=None)
def test_deploy_helm_app_upgrade(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    deploy 명령어 실행 시 install-helm 타입 앱 (업그레이드) 과정을 테스트합니다.
    - helm upgrade 명령어가 올바른 인자들로 호출되는지 확인합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file
    app_name = "my-helm-app"

    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.1") 

    def mock_run_command_side_effect(cmd, *args, **kwargs):
        if cmd[:2] == ['helm', 'status']:
            return (0, "STATUS: deployed", "") 
        elif cmd[:2] == ['helm', 'upgrade']:
            return (0, "RELEASE: my-helm-app\nSTATUS: deployed", "") 
        return (0, "default success", "")

    with patch('sbkube.utils.common.run_command', side_effect=mock_run_command_side_effect) as mock_run_cmd, \
         patch('pathlib.Path.is_dir', return_value=True):

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        expected_upgrade_call = call([
            'helm', 'upgrade', app_name, str(built_chart_path),
            '--namespace', 'helm-ns',
            '-f', str(values_file.resolve()),
            '--set', 'master.replicaCount=1'
        ], capture_output=True, text=True, check=False, env=None)
        
        upgrade_called = any(c == expected_upgrade_call for c in mock_run_cmd.call_args_list)
        assert upgrade_called, "helm upgrade 호출이 없습니다."

        assert f"Upgrading Helm app: {app_name}" in caplog.text
        assert f"Helm app {app_name} upgraded successfully." in caplog.text

@patch(KUBECTL_CHECK_PATH, return_value=None)
def test_deploy_kubectl_app(mock_kubectl_check, runner: CliRunner, create_sample_config_yaml, create_sample_kubectl_manifest_file, base_dir, app_dir, caplog):
    """
    deploy 명령어 실행 시 install-kubectl 타입 앱 과정을 테스트합니다.
    - kubectl apply 명령어가 올바른 인자들로 호출되는지 확인합니다.
    """
    config_file = create_sample_config_yaml
    manifest_file = create_sample_kubectl_manifest_file 
    app_name = "my-kubectl-app"
    
    abs_manifest_path = (app_dir / "manifests" / "kubectl-app.yaml").resolve()


    with patch('sbkube.utils.common.run_command') as mock_run_command:
        mock_run_command.return_value = (0, "pod/test-pod created", "")

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        expected_kubectl_apply_call = call([
            'kubectl', 'apply',
            '-f', str(abs_manifest_path),
            '--namespace', 'kubectl-ns' 
        ], capture_output=True, text=True, check=False, env=None)
        
        apply_called = any(c == expected_kubectl_apply_call for c in mock_run_command.call_args_list)
        assert apply_called, "kubectl apply 호출이 없습니다."

        assert f"Deploying Kubectl app: {app_name}" in caplog.text
        assert f"Kubectl app {app_name} deployed successfully." in caplog.text

@patch(KUBECTL_CHECK_PATH, return_value=None) 
def test_deploy_action_app(mock_kubectl_check, runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    deploy 명령어 실행 시 install-action 타입 앱 과정을 테스트합니다.
    - config에 정의된 command가 실행되는지 확인합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-action-app"
    expected_command = "echo 'action executed'" 

    with patch('sbkube.utils.common.run_command') as mock_run_command:
        mock_run_command.return_value = (0, "action executed", "")

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        import shlex
        expected_action_call = call(
            shlex.split(expected_command), 
            capture_output=True, text=True, check=False, env=None 
        )
        
        action_called = any(c.args[0] == shlex.split(expected_command) for c in mock_run_command.call_args_list)
        assert action_called, f"Action command '{expected_command}' 호출이 없습니다."
        
        assert f"Executing action for app: {app_name}" in caplog.text
        assert f"Action app {app_name} executed successfully." in caplog.text

def test_deploy_specific_app_with_namespace_override(runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    deploy 명령어 실행 시 --app 및 --namespace 옵션으로 특정 앱에 대해 네임스페이스를 오버라이드하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file
    app_name = "my-helm-app"
    cli_namespace = "cli-override-ns"

    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.0")

    def mock_run_command_side_effect(cmd, *args, **kwargs):
        if cmd[:2] == ['helm', 'status']:
            return (1, "Error: release: not found", "") 
        elif cmd[:2] == ['helm', 'install']:
            assert '--namespace' in cmd
            assert cmd[cmd.index('--namespace') + 1] == cli_namespace
            return (0, "RELEASE: my-helm-app\nSTATUS: deployed", "")
        return (0, "default success", "")

    with patch(HELM_CHECK_PATH, return_value=None), \
         patch('sbkube.utils.common.run_command', side_effect=mock_run_command_side_effect) as mock_run_cmd, \
         patch('pathlib.Path.is_dir', return_value=True):

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--namespace', cli_namespace 
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        assert f"Overriding namespace for app {app_name} with CLI option: {cli_namespace}" in caplog.text
