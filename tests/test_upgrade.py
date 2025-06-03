from unittest.mock import patch, call
from pathlib import Path
import yaml

from click.testing import CliRunner
from sbkube.cli import main as sbkube_cli

SBKUBE_CLI_PATH = 'sbkube.cli'
HELM_CHECK_PATH = f'{SBKUBE_CLI_PATH}.check_helm_installed_or_exit'

@patch(HELM_CHECK_PATH, return_value=None) 
def test_upgrade_helm_app(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    upgrade 명령어 실행 시 install-helm 타입 앱에 대해 helm upgrade --install 이 호출되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file 
    app_name = "my-helm-app"

    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.1") 

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.is_dir', return_value=True): 
        mock_run_command.return_value = (0, "RELEASE: my-helm-app\nSTATUS: deployed", "") 

        result = runner.invoke(sbkube_cli, [
            'upgrade', 
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name 
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        expected_upgrade_call = call([
            'helm', 'upgrade', app_name, str(built_chart_path),
            '--install', 
            '--namespace', 'helm-ns', 
            '-f', str(values_file.resolve()), 
            '--set', 'master.replicaCount=1' 
        ], capture_output=True, text=True, check=False, env=None)
        
        upgrade_called = any(c == expected_upgrade_call for c in mock_run_command.call_args_list)
        assert upgrade_called, "helm upgrade --install 호출이 없습니다."

        assert f"Upgrading or Installing Helm app: {app_name}" in caplog.text
        assert f"Helm app {app_name} upgraded/installed successfully." in caplog.text

@patch(HELM_CHECK_PATH, return_value=None)
def test_upgrade_helm_app_with_no_install(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    upgrade 명령어 실행 시 --no-install 옵션이 적용되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file
    app_name = "my-helm-app"

    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.1")

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.is_dir', return_value=True):
        mock_run_command.return_value = (0, "RELEASE: my-helm-app\nSTATUS: deployed", "")

        result = runner.invoke(sbkube_cli, [
            'upgrade',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--no-install' 
        ])
        assert result.exit_code == 0

        called_cmd_args = mock_run_command.call_args_list[0].args[0] 
        assert '--install' not in called_cmd_args

        assert f"Upgrading Helm app (without install): {app_name}" in caplog.text

def test_upgrade_non_helm_app(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    upgrade 명령어가 install-helm 타입이 아닌 앱에 대해 실행되지 않고 메시지를 출력하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-kubectl-app"

    result = runner.invoke(sbkube_cli, [
        'upgrade',
        '--base-dir', str(base_dir),
        '--app-dir', str(app_dir.name),
        '--config-file', str(config_file.name),
        '--app', app_name
    ])
    assert result.exit_code != 0 
    assert f"App '{app_name}' is not of type 'install-helm'. Skipping upgrade." in caplog.text

def test_upgrade_app_not_found(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    upgrade 명령어 실행 시 존재하지 않는 앱 이름을 지정하면 오류 메시지를 출력하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    app_name = "non-existent-app"

    result = runner.invoke(sbkube_cli, [
        'upgrade',
        '--base-dir', str(base_dir),
        '--app-dir', str(app_dir.name),
        '--config-file', str(config_file.name),
        '--app', app_name
    ])
    assert result.exit_code != 0
    assert f"App '{app_name}' not found in configuration." in caplog.text

@patch(HELM_CHECK_PATH, return_value=None)
def test_upgrade_helm_app_namespace_override(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    upgrade 명령어 실행 시 --namespace 옵션으로 네임스페이스를 오버라이드 하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file
    app_name = "my-helm-app"
    cli_namespace = "cli-override-upgrade-ns"

    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.1")

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.is_dir', return_value=True):
        mock_run_command.return_value = (0, "RELEASE: my-helm-app\nSTATUS: deployed", "")

        result = runner.invoke(sbkube_cli, [
            'upgrade',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--namespace', cli_namespace 
        ])
        assert result.exit_code == 0

        called_cmd_args = mock_run_command.call_args_list[0].args[0]
        assert '--namespace' in called_cmd_args
        assert called_cmd_args[called_cmd_args.index('--namespace') + 1] == cli_namespace
        assert f"Overriding namespace for app {app_name} with CLI option: {cli_namespace}" in caplog.text 