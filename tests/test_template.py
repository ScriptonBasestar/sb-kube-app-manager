from unittest.mock import patch, call
from pathlib import Path
import yaml

from click.testing import CliRunner
from sbkube.cli import main as sbkube_cli 

# SbkubeGroup의 CLI 실행 전 체크 로직 모킹 경로
SBKUBE_CLI_PATH = 'sbkube.cli'
KUBECTL_CHECK_PATH = f'{SBKUBE_CLI_PATH}.check_kubectl_installed_or_exit'
HELM_CHECK_PATH = f'{SBKUBE_CLI_PATH}.check_helm_installed_or_exit'


def test_template_helm_app(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, build_dir, caplog):
    """
    template 명령어 실행 시 빌드된 Helm 차트에 대해 helm template 명령어가 올바르게 호출되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-helm-app" 

    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"apiVersion: v2\nname: {app_name}\nversion: 1.0.0")
    (built_chart_path / "values.yaml").write_text("some: value")
    (built_chart_path / "templates").mkdir(exist_ok=True)
    (built_chart_path / "templates" / "service.yaml").write_text("kind: Service")

    values_dir = app_dir / "values"
    values_dir.mkdir(exist_ok=True)
    sample_values_file = values_dir / "helm-app-values.yaml"
    sample_values_file.write_text("persistence: {enabled: true}") 


    output_dir = base_dir / "rendered_yamls" 
    expected_output_file = output_dir / f"{app_name}.yaml"

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.is_dir', return_value=True): 
        mock_run_command.return_value = (0, "--- # Source: chart/templates/service.yaml", "") 

        result = runner.invoke(sbkube_cli, [
            'template',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--output-dir', str(output_dir.relative_to(base_dir)) 
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        expected_helm_template_call = call([
            'helm', 'template', app_name, str(built_chart_path),
            '--namespace', 'helm-ns', 
            '-f', str(sample_values_file.resolve()), 
            '--set', 'master.replicaCount=1' 
        ], capture_output=True, text=True, check=False, env=None)
        
        mock_run_command.assert_any_call(*expected_helm_template_call[1], **expected_helm_template_call[2])
        
        assert f"Templating app: {app_name}" in caplog.text
        assert f"Rendered template for {app_name} to {expected_output_file}" in caplog.text
        assert output_dir.exists()
        assert expected_output_file.exists()
        assert expected_output_file.read_text() == "--- # Source: chart/templates/service.yaml"


def test_template_app_not_templatable(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    템플릿 대상이 아닌 타입의 앱 (예: install-kubectl)에 대해 template 명령어가 스킵하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-kubectl-app"
    output_dir = base_dir / "rendered_yamls"

    with patch('sbkube.utils.common.run_command') as mock_run_command:
        result = runner.invoke(sbkube_cli, [
            'template',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--output-dir', str(output_dir.relative_to(base_dir))
        ])
        assert result.exit_code == 0
        mock_run_command.assert_not_called()
        assert f"Skipping app {app_name} (install-kubectl) as it is not a Helm chart based application." in caplog.text
        assert not output_dir.exists()


def test_template_with_custom_namespace(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, build_dir, caplog):
    """
    template 명령어 실행 시 --namespace 옵션으로 네임스페이스를 오버라이드하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-helm-app"
    
    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.0")
    
    values_dir = app_dir / "values" 
    values_dir.mkdir(exist_ok=True)
    sample_values_file = values_dir / "helm-app-values.yaml"
    sample_values_file.write_text("key: value") 


    custom_namespace = "custom-template-ns"
    output_dir = base_dir / "rendered_yamls"

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.is_dir', return_value=True):
        mock_run_command.return_value = (0, "templated output", "")

        result = runner.invoke(sbkube_cli, [
            'template',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--output-dir', str(output_dir.relative_to(base_dir)),
            '--namespace', custom_namespace
        ])
        assert result.exit_code == 0
        
        args, kwargs = mock_run_command.call_args
        actual_cmd_list = args[0] 
        
        assert '--namespace' in actual_cmd_list
        assert actual_cmd_list[actual_cmd_list.index('--namespace') + 1] == custom_namespace
        assert f"Overriding namespace with CLI option: {custom_namespace}" in caplog.text
        assert f"Using namespace from app specs: helm-ns" not in caplog.text 


@patch(HELM_CHECK_PATH, return_value=None) # Helm 설치 가정
def test_delete_helm_app(mock_helm_check, runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    delete 명령어 실행 시 install-helm 타입 앱에 대해 helm uninstall이 호출되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml # my-helm-app 포함
    app_name = "my-helm-app"

    # check_resource_exists 모킹 (리소스가 존재한다고 가정)
    # delete 로직 내부에서 sbkube.utils.common.check_resource_exists 또는
    # sbkube.commands.delete.check_resource_exists 를 호출할 수 있음. 경로 확인 필요.
    # 여기서는 common.check_resource_exists를 사용한다고 가정
    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('sbkube.utils.common.check_resource_exists', return_value=True) as mock_check_exists:
        mock_run_command.return_value = (0, f"release \"{app_name}\" uninstalled", "") # helm uninstall 성공

        result = runner.invoke(sbkube_cli, [
            'delete',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # check_resource_exists 호출 확인 (Helm의 경우 app_name, namespace, "helm" 타입으로 호출 예상)
        mock_check_exists.assert_called_once_with(
            app_name=app_name, 
            namespace='helm-ns', # from config
            resource_type="helm", 
            kubeconfig_path=None, # 기본값 또는 CLI 전역 옵션
            context_name=None     # 기본값 또는 CLI 전역 옵션
        )
        
        expected_uninstall_call = call([
            'helm', 'uninstall', app_name,
            '--namespace', 'helm-ns' # from config
        ], capture_output=True, text=True, check=False, env=None)
        
        uninstall_called = any(c == expected_uninstall_call for c in mock_run_command.call_args_list)
        assert uninstall_called, "helm uninstall 호출이 없습니다."

        assert f"Deleting Helm app: {app_name}" in caplog.text
        assert f"Helm app {app_name} deleted successfully." in caplog.text

@patch(KUBECTL_CHECK_PATH, return_value=None) # Kubectl 설치 가정
def test_delete_kubectl_app(mock_kubectl_check, runner: CliRunner, create_sample_config_yaml, create_sample_kubectl_manifest_file, base_dir, app_dir, caplog):
    """
    delete 명령어 실행 시 install-kubectl 타입 앱에 대해 kubectl delete가 호출되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    manifest_file = create_sample_kubectl_manifest_file # app_dir/manifests/kubectl-app.yaml
    app_name = "my-kubectl-app"
    abs_manifest_path = (app_dir / "manifests" / "kubectl-app.yaml").resolve()


    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('sbkube.utils.common.check_resource_exists', return_value=True) as mock_check_exists:
        mock_run_command.return_value = (0, "pod/test-pod deleted", "") # kubectl delete 성공

        result = runner.invoke(sbkube_cli, [
            'delete',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # check_resource_exists 호출 확인 (Kubectl의 경우 path, namespace, "kubectl" 타입으로 호출 예상)
        # delete 로직에서 어떤 이름으로 리소스를 확인하는지 확인 필요. 여기서는 manifest 파일 기반으로 가정.
        # 또는 config의 app_name으로 확인하고, manifest의 리소스를 직접 파싱해서 할 수도 있음.
        # 현재 delete 로직은 manifest 파일의 내용을 파싱하여 각 리소스의 kind/name을 확인.
        # 따라서 mock_check_exists가 여러번 호출될 수 있음. 여기서는 한번만 확인.
        mock_check_exists.assert_any_call(
            app_name='test-pod', # manifest의 name
            namespace='kubectl-ns', # from config
            resource_type="Pod", # manifest의 kind
            kubeconfig_path=None, 
            context_name=None
        )

        expected_delete_call = call([
            'kubectl', 'delete',
            '-f', str(abs_manifest_path),
            '--namespace', 'kubectl-ns', # from config
            '--ignore-not-found=true' # delete 명령어의 기본 동작
        ], capture_output=True, text=True, check=False, env=None)
        
        delete_called = any(c == expected_delete_call for c in mock_run_command.call_args_list)
        assert delete_called, "kubectl delete 호출이 없습니다."

        assert f"Deleting Kubectl app: {app_name}" in caplog.text
        assert f"Kubectl app {app_name} (resources from {abs_manifest_path}) deleted successfully." in caplog.text


@patch(KUBECTL_CHECK_PATH, return_value=None) # Action은 kubectl을 사용할 수 있음
def test_delete_action_app(mock_kubectl_check, runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    delete 명령어 실행 시 install-action 타입 앱에 대해 정의된 delete_command가 실행되는지 테스트합니다.
    만약 delete_command가 없으면 스킵되어야 합니다.
    """
    # Case 1: delete_command가 있는 경우
    config_content_with_delete_cmd = {
        "apps": [{
            "name": "my-action-app-with-delete",
            "type": "install-action",
            "specs": {
                "command": "echo 'action deployed'",
                "delete_command": "echo 'action deleted'", # 삭제 명령 정의
                "namespace": "action-ns"
            }
        }]
    }
    config_file_1 = app_dir / "config_action1.yaml"
    with open(config_file_1, 'w') as f: yaml.dump(config_content_with_delete_cmd, f)
    
    app_name_1 = "my-action-app-with-delete"
    expected_delete_action = "echo 'action deleted'"

    with patch('sbkube.utils.common.run_command') as mock_run_command:
        mock_run_command.return_value = (0, "action deleted", "")

        result1 = runner.invoke(sbkube_cli, [
            'delete',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file_1.name),
            '--app', app_name_1
        ])
        assert result1.exit_code == 0, f"CLI 실행 실패 (with delete_command): {result1.output}"
        
        import shlex
        action_delete_called = any(c.args[0] == shlex.split(expected_delete_action) for c in mock_run_command.call_args_list)
        assert action_delete_called, f"Action delete_command '{expected_delete_action}' 호출이 없습니다."
        assert f"Executing delete action for app: {app_name_1}" in caplog.text

    caplog.clear()
    # Case 2: delete_command가 없는 경우 (기존 my-action-app 사용)
    config_file_2 = create_sample_config_yaml # my-action-app에는 delete_command 없음
    app_name_2 = "my-action-app"

    with patch('sbkube.utils.common.run_command') as mock_run_command:
        result2 = runner.invoke(sbkube_cli, [
            'delete',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file_2.name), # conftest의 기본 config 사용
            '--app', app_name_2 
        ])
        assert result2.exit_code == 0 # 스킵하므로 성공으로 간주
        mock_run_command.assert_not_called() # 아무런 command도 실행되지 않아야 함
        assert f"App {app_name_2} is of type install-action but has no delete_command defined. Skipping deletion." in caplog.text


def test_delete_app_skip_not_found_option(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    delete 명령어 실행 시 --skip-not-found 옵션과 함께 존재하지 않는 리소스를 삭제 시도할 때,
    에러 없이 정상 종료되는지 테스트합니다. (check_resource_exists가 False 반환)
    """
    config_file = create_sample_config_yaml
    app_name = "my-helm-app"

    with patch(HELM_CHECK_PATH, return_value=None), \
         patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('sbkube.utils.common.check_resource_exists', return_value=False) as mock_check_exists: # 리소스가 없다고 가정

        result = runner.invoke(sbkube_cli, [
            'delete',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--skip-not-found' # 이 옵션 사용
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        mock_run_command.assert_not_called() # helm uninstall 등이 호출되지 않아야 함
        assert f"App {app_name} (helm) or its resources not found. Skipping deletion as --skip-not-found is True." in caplog.text

def test_delete_app_not_found_error(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    delete 명령어 실행 시 --skip-not-found 옵션 없이 존재하지 않는 리소스를 삭제 시도할 때,
    에러가 발생하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    app_name = "my-helm-app"

    with patch(HELM_CHECK_PATH, return_value=None), \
         patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('sbkube.utils.common.check_resource_exists', return_value=False) as mock_check_exists:

        result = runner.invoke(sbkube_cli, [
            'delete',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name
            # --skip-not-found 없음
        ])
        assert result.exit_code != 0 # 에러 발생해야 함
        mock_run_command.assert_not_called()
        assert f"App {app_name} (helm) or its resources not found. Use --skip-not-found to ignore." in caplog.text
