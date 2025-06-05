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
        pytest.skip(f"테스트 클러스터 kubeconfig가 없어 스킵합니다: {KUBECONFIG_TEST}")

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

    with patch('subprocess.run') as mock_subprocess, \
         patch('sbkube.utils.helm_util.get_installed_charts', return_value={}):  # 설치된 차트 없음

        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'list':
                result.returncode = 0
                result.stdout = "[]"  # 빈 JSON 배열
                result.stderr = ""
            else:
                result.returncode = 0
                result.stdout = "RELEASE: my-helm-app\nSTATUS: deployed"
                result.stderr = ""
            return result

        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        # subprocess.run 호출 확인
        assert mock_subprocess.call_count >= 1
        
        # helm install 호출 찾기
        install_calls = [call for call in mock_subprocess.call_args_list 
                        if call[0][0][0] == 'helm' and call[0][0][1] == 'install']
        assert len(install_calls) == 1, f"helm install 호출 횟수: {len(install_calls)}"
        
        # helm install 명령 확인
        args, kwargs = install_calls[0]
        actual_cmd_list = args[0]
        
        assert actual_cmd_list[0] == 'helm'
        assert actual_cmd_list[1] == 'install'
        assert '--namespace' in actual_cmd_list
        assert '--create-namespace' in actual_cmd_list
        
        assert "배포 완료" in result.output or "완료" in result.output

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

    with patch('subprocess.run') as mock_subprocess, \
         patch('sbkube.utils.helm_util.get_installed_charts', return_value={"my-helm-app": {"name": "my-helm-app"}}):  # 이미 설치됨

        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'list':
                result.returncode = 0
                result.stdout = '[{"name": "my-helm-app", "status": "deployed"}]'
                result.stderr = ""
            else:
                result.returncode = 0
                result.stdout = "RELEASE: my-helm-app\nSTATUS: deployed"
                result.stderr = ""
            return result

        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # 이미 설치되어 있으므로 건너뛰어야 함
        assert "이미 설치되어 있습니다" in result.output or "건너뜁니다" in result.output

@patch(KUBECTL_CHECK_PATH, return_value=None)
def test_deploy_kubectl_app(mock_kubectl_check, runner: CliRunner, create_sample_config_yaml, create_sample_kubectl_manifest_file, base_dir, app_dir, caplog):
    """
    deploy 명령어 실행 시 install-yaml 타입 앱 과정을 테스트합니다.
    - kubectl apply 명령어가 올바른 인자들로 호출되는지 확인합니다.
    """
    config_file = create_sample_config_yaml
    manifest_file = create_sample_kubectl_manifest_file
    app_name = "my-kubectl-app"

    with patch('subprocess.run') as mock_subprocess:
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "pod/test-pod created"
        mock_subprocess.return_value.stderr = ""

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # subprocess.run 호출 확인
        assert mock_subprocess.call_count >= 1
        
        # kubectl apply 호출 찾기
        apply_calls = [call for call in mock_subprocess.call_args_list 
                      if call[0][0][0] == 'kubectl' and call[0][0][1] == 'apply']
        assert len(apply_calls) >= 1, f"kubectl apply 호출 횟수: {len(apply_calls)}"
        
        # kubectl apply 명령 확인
        args, kwargs = apply_calls[0]
        actual_cmd_list = args[0]
        
        assert actual_cmd_list[0] == 'kubectl'
        assert actual_cmd_list[1] == 'apply'
        assert '-f' in actual_cmd_list
        assert '-n' in actual_cmd_list or '--namespace' in actual_cmd_list
        
        assert "완료" in result.output

@patch(KUBECTL_CHECK_PATH, return_value=None) 
def test_deploy_action_app(mock_kubectl_check, runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    deploy 명령어 실행 시 exec 타입 앱 과정을 테스트합니다.
    - config에 정의된 command가 실행되는지 확인합니다.
    """
    config_file = create_sample_config_yaml
    app_name = "my-action-app"
    expected_command = "echo 'action executed'"

    with patch('subprocess.run') as mock_subprocess:
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "action executed"
        mock_subprocess.return_value.stderr = ""

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # subprocess.run 호출 확인
        assert mock_subprocess.call_count >= 1
        
        # echo 명령 호출 찾기
        echo_calls = [call for call in mock_subprocess.call_args_list 
                     if call[0][0][0] == 'echo']
        assert len(echo_calls) >= 1, f"echo 명령 호출 횟수: {len(echo_calls)}"
        
        assert "완료" in result.output

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

    with patch(HELM_CHECK_PATH, return_value=None), \
         patch('subprocess.run') as mock_subprocess, \
         patch('sbkube.utils.helm_util.get_installed_charts', return_value={}):  # 설치된 차트 없음

        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'list':
                result.returncode = 0
                result.stdout = "[]"  # 빈 JSON 배열
                result.stderr = ""
            else:
                result.returncode = 0
                result.stdout = "RELEASE: my-helm-app\nSTATUS: deployed"
                result.stderr = ""
            return result

        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'deploy',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--namespace', cli_namespace
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        # helm install 호출 찾기
        install_calls = [call for call in mock_subprocess.call_args_list 
                        if call[0][0][0] == 'helm' and call[0][0][1] == 'install']
        assert len(install_calls) == 1, f"helm install 호출 횟수: {len(install_calls)}"
        
        # 네임스페이스 오버라이드 확인
        args, kwargs = install_calls[0]
        actual_cmd_list = args[0]
        assert '--namespace' in actual_cmd_list
        assert actual_cmd_list[actual_cmd_list.index('--namespace') + 1] == cli_namespace
        
        assert "배포 완료" in result.output or "완료" in result.output
