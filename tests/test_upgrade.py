from unittest.mock import patch, call
from pathlib import Path
import yaml

from click.testing import CliRunner
from sbkube.cli import main as sbkube_cli

# CLI 체크 모킹 경로
HELM_CHECK_PATH = 'sbkube.commands.upgrade.check_helm_installed'


@patch(HELM_CHECK_PATH, return_value=None) 
def test_upgrade_helm_app(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    upgrade 명령어 실행 시 install-helm 타입 앱에 대해 helm upgrade --install 이 호출되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file 
    app_name = "my-helm-app"

    # 빌드된 차트 디렉토리 준비
    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.1") 

    with patch('subprocess.run') as mock_subprocess:
        # helm version과 helm upgrade 모두 성공 시뮬레이션
        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'version':
                result.returncode = 0
                result.stdout = "version.BuildInfo{Version:\"v3.18.0\"}"
                result.stderr = ""
            elif cmd[0] == 'helm' and cmd[1] == 'upgrade':
                result.returncode = 0
                result.stdout = f"Release \"{app_name}\" has been upgraded. Happy Helming!"
                result.stderr = ""
            else:
                result.returncode = 1
                result.stdout = ""
                result.stderr = "unknown command"
            return result
        
        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'upgrade', 
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name 
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        # subprocess.run 호출 확인
        assert mock_subprocess.call_count >= 1  # 최소 1번은 호출되어야 함
        
        # helm upgrade 호출 찾기
        upgrade_calls = [call for call in mock_subprocess.call_args_list 
                       if call[0][0][0] == 'helm' and call[0][0][1] == 'upgrade']
        assert len(upgrade_calls) == 1, f"helm upgrade 호출 횟수: {len(upgrade_calls)}"
        
        # helm upgrade 명령 확인
        args, kwargs = upgrade_calls[0]
        actual_cmd_list = args[0]
        
        assert actual_cmd_list[0] == 'helm'
        assert actual_cmd_list[1] == 'upgrade'
        assert '--install' in actual_cmd_list
        assert '--namespace' in actual_cmd_list
        # values 파일이 존재하면 --values가 포함됨
        values_in_cmd = '--values' in actual_cmd_list
        
        assert "업그레이드/설치 성공" in result.output or "성공" in result.output


@patch(HELM_CHECK_PATH, return_value=None)
def test_upgrade_helm_app_with_no_install(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    upgrade 명령어 실행 시 --no-install 옵션이 적용되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file
    app_name = "my-helm-app"

    # 빌드된 차트 디렉토리 준비
    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.1")

    with patch('subprocess.run') as mock_subprocess:
        # helm version과 helm upgrade 모두 성공 시뮬레이션
        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'version':
                result.returncode = 0
                result.stdout = "version.BuildInfo{Version:\"v3.18.0\"}"
                result.stderr = ""
            elif cmd[0] == 'helm' and cmd[1] == 'upgrade':
                result.returncode = 0
                result.stdout = "Release updated"
                result.stderr = ""
            else:
                result.returncode = 1
                result.stdout = ""
                result.stderr = "unknown command"
            return result
        
        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'upgrade',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--no-install' 
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # --install 플래그가 없어야 함 (helm upgrade 호출에서만 확인)
        upgrade_calls = [call for call in mock_subprocess.call_args_list 
                       if call[0][0][0] == 'helm' and call[0][0][1] == 'upgrade']
        assert len(upgrade_calls) == 1
        
        args, kwargs = upgrade_calls[0]
        actual_cmd_list = args[0] 
        assert '--install' not in actual_cmd_list
        
        assert "성공" in result.output


@patch(HELM_CHECK_PATH, return_value=None)
def test_upgrade_non_helm_app(mock_helm_check, runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    upgrade 명령어가 install-helm 타입이 아닌 앱에 대해 올바른 메시지를 출력하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-kubectl-app"  # install-yaml 타입

    result = runner.invoke(sbkube_cli, [
        'upgrade',
        '--base-dir', str(base_dir),
        '--app-dir', str(app_dir.name),
        '--config-file', str(config_file.name),
        '--app', app_name
    ])
    # 현재 구현에서는 타입이 맞지 않으면 성공으로 종료하고 메시지 출력
    assert result.exit_code == 0
    assert "지원하지 않는" in result.output or "대상이 아닙니다" in result.output


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
    assert result.exit_code == 1  # 앱을 찾을 수 없으면 실패
    assert "찾을 수 없습니다" in result.output


@patch(HELM_CHECK_PATH, return_value=None)
def test_upgrade_helm_app_namespace_override(mock_helm_check, runner: CliRunner, create_sample_config_yaml, create_sample_values_file, base_dir, app_dir, build_dir, caplog):
    """
    upgrade 명령어 실행 시 --namespace 옵션으로 네임스페이스를 오버라이드 하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml
    values_file = create_sample_values_file
    app_name = "my-helm-app"
    cli_namespace = "cli-override-upgrade-ns"

    # 빌드된 차트 디렉토리 준비
    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"name: {app_name}\nversion: 1.0.1")

    with patch('subprocess.run') as mock_subprocess:
        # helm version과 helm upgrade 모두 성공 시뮬레이션
        def mock_run_side_effect(cmd, *args, **kwargs):
            from unittest.mock import MagicMock
            result = MagicMock()
            if cmd[0] == 'helm' and cmd[1] == 'version':
                result.returncode = 0
                result.stdout = "version.BuildInfo{Version:\"v3.18.0\"}"
                result.stderr = ""
            elif cmd[0] == 'helm' and cmd[1] == 'upgrade':
                result.returncode = 0
                result.stdout = "Release upgraded"
                result.stderr = ""
            else:
                result.returncode = 1
                result.stdout = ""
                result.stderr = "unknown command"
            return result
        
        mock_subprocess.side_effect = mock_run_side_effect

        result = runner.invoke(sbkube_cli, [
            'upgrade',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--namespace', cli_namespace 
        ])
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # 네임스페이스 옵션 확인 (helm upgrade 호출에서만)
        upgrade_calls = [call for call in mock_subprocess.call_args_list 
                       if call[0][0][0] == 'helm' and call[0][0][1] == 'upgrade']
        assert len(upgrade_calls) == 1
        
        args, kwargs = upgrade_calls[0]
        actual_cmd_list = args[0]
        assert '--namespace' in actual_cmd_list
        assert actual_cmd_list[actual_cmd_list.index('--namespace') + 1] == cli_namespace
        
        assert "성공" in result.output 