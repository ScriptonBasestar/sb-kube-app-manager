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

    with patch('subprocess.run') as mock_subprocess:
        # helm version, helm template 모두 mock
        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'version':
                result.returncode = 0
                result.stdout = "version.BuildInfo{Version:\"v3.18.0\"}"
                result.stderr = ""
            elif cmd[0] == 'helm' and cmd[1] == 'template':
                result.returncode = 0
                result.stdout = "--- # Source: chart/templates/service.yaml"
                result.stderr = ""
            else:
                result.returncode = 1
                result.stdout = ""
                result.stderr = "unknown command"
            return result
        
        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'template',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--output-dir', str(output_dir.relative_to(base_dir)) 
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        # helm template이 호출되었는지 확인
        template_calls = [call for call in mock_subprocess.call_args_list 
                         if call[0][0][0] == 'helm' and call[0][0][1] == 'template']
        assert len(template_calls) == 1, f"helm template 호출 횟수: {len(template_calls)}"
        
        assert "템플릿 생성 완료" in result.output or "완료" in result.output


def test_template_app_not_templatable(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    템플릿 대상이 아닌 타입의 앱 (예: install-kubectl)에 대해 template 명령어가 에러로 처리되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-kubectl-app"
    output_dir = base_dir / "rendered_yamls"

    with patch('subprocess.run') as mock_subprocess:
        # helm version만 mock
        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'version':
                result.returncode = 0
                result.stdout = "version.BuildInfo{Version:\"v3.18.0\"}"
                result.stderr = ""
            return result
        
        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'template',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--output-dir', str(output_dir.relative_to(base_dir))
        ])
        # kubectl 앱은 template 대상이 아니므로 에러로 처리됨
        assert result.exit_code == 1
        
        # helm template은 호출되지 않아야 함
        template_calls = [call for call in mock_subprocess.call_args_list 
                         if call[0][0][0] == 'helm' and call[0][0][1] == 'template']
        assert len(template_calls) == 0, f"helm template이 호출되면 안됨: {template_calls}"
        
        assert "찾을 수 없거나" in result.output or "template 대상이 아닙니다" in result.output
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

    with patch('subprocess.run') as mock_subprocess:
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "templated output"
        mock_subprocess.return_value.stderr = ""

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
        
        # subprocess.run 호출 확인
        args, kwargs = mock_subprocess.call_args
        actual_cmd_list = args[0] 
        
        assert '--namespace' in actual_cmd_list
        assert actual_cmd_list[actual_cmd_list.index('--namespace') + 1] == custom_namespace
        assert "완료" in result.output
