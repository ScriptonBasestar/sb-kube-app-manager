import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, call, mock_open

from click.testing import CliRunner
from sbkube.cli import main as sbkube_cli

EXAMPLES_DIR = Path("examples/k3scode")
BUILD_DIR = Path("build")
TARGET_APP_NAME = "browserless"  # config-browserless 기준

def clean_build_dir():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

def test_build_command_runs_and_creates_output():
    clean_build_dir()

    result = subprocess.run(
        [
            "sbkube", "build",
            "--apps", str(EXAMPLES_DIR / "config-browserless")
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    # 1. 명령 실행 성공
    assert result.returncode == 0, "sbkube build 명령이 실패했습니다."

    # 2. build 디렉토리 존재 확인
    assert BUILD_DIR.exists(), "build 디렉토리가 생성되지 않았습니다."

    # 3. browserless 디렉토리 확인
    target_chart_path = BUILD_DIR / TARGET_APP_NAME / "Chart.yaml"
    assert target_chart_path.exists(), f"{target_chart_path} 파일이 존재하지 않습니다."

def test_build_pull_helm_app(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, charts_dir, build_dir, caplog):
    """
    build 명령어 실행 시 pull-helm 타입 앱의 빌드 과정을 테스트합니다.
    - prepare 단계에서 받아온 차트가 build_dir/<app_name>으로 복사되는지 확인합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-pull-helm-app"
    
    prepared_chart_source_dir = charts_dir / "pulled-apache" 
    prepared_chart_source_dir.mkdir(parents=True, exist_ok=True)
    (prepared_chart_source_dir / "Chart.yaml").write_text("name: apache\nversion: 9.0.0")
    (prepared_chart_source_dir / "values.yaml").write_text("replicaCount: 1")
    (prepared_chart_source_dir / "templates").mkdir(exist_ok=True)
    (prepared_chart_source_dir / "templates" / "deployment.yaml").write_text("kind: Deployment")


    expected_build_app_path = build_dir / app_name
    
    with patch('shutil.copytree') as mock_copytree, \
         patch('shutil.rmtree') as mock_rmtree: 

        result = runner.invoke(sbkube_cli, [
            'build',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name 
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        mock_rmtree.assert_any_call(expected_build_app_path) 
        mock_copytree.assert_called_once_with(prepared_chart_source_dir, expected_build_app_path, dirs_exist_ok=True)
        
        assert f"Building app: {app_name}" in caplog.text
        assert f"App '{app_name}' (pull-helm) built successfully to {expected_build_app_path}" in caplog.text

def test_build_pull_git_app(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, repos_dir, build_dir, caplog):
    """
    build 명령어 실행 시 pull-git 타입 앱의 빌드 과정을 테스트합니다.
    - prepare 단계에서 받아온 git repo가 build_dir/<app_name>으로 복사되는지 확인합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-pull-git-app"

    prepared_git_source_dir = repos_dir / "pulled-git-repo" 
    prepared_git_source_dir.mkdir(parents=True, exist_ok=True)
    (prepared_git_source_dir / "file.txt").write_text("git content")
    (prepared_git_source_dir / ".git").mkdir() 

    expected_build_app_path = build_dir / app_name

    with patch('shutil.copytree') as mock_copytree, \
         patch('shutil.rmtree') as mock_rmtree:

        result = runner.invoke(sbkube_cli, [
            'build',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name 
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}"
        mock_rmtree.assert_any_call(expected_build_app_path)
        mock_copytree.assert_called_once_with(prepared_git_source_dir, expected_build_app_path, dirs_exist_ok=True)
        
        assert f"App '{app_name}' (pull-git) built successfully to {expected_build_app_path}" in caplog.text

def test_build_copy_app(runner: CliRunner, create_sample_config_yaml, create_sample_local_copy_source_dir, base_dir, app_dir, build_dir, caplog):
    """
    build 명령어 실행 시 copy-app 타입 앱의 빌드 과정을 테스트합니다.
    - config에 정의된 local source가 build_dir/<app_name>/<destination_in_spec> 으로 복사되는지 확인합니다.
    """
    config_file = create_sample_config_yaml 
    source_dir_fixture = create_sample_local_copy_source_dir 
    
    app_name = "my-copy-app"
    expected_build_target_path = build_dir / app_name / "copied-app-dest"


    with patch('shutil.copytree') as mock_copytree, \
         patch('shutil.rmtree') as mock_rmtree, \
         patch('pathlib.Path.exists', side_effect=lambda p: True if p == source_dir_fixture else Path.exists(p)):

        result = runner.invoke(sbkube_cli, [
            'build',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name 
        ])
        
        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        mock_rmtree.assert_any_call(build_dir / app_name) 
        mock_copytree.assert_called_once_with(source_dir_fixture, expected_build_target_path, dirs_exist_ok=True)
        
        assert f"App '{app_name}' (copy-app) built successfully to {expected_build_target_path}" in caplog.text

def test_build_app_not_buildable(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    빌드 대상이 아닌 타입의 앱 (예: install-helm)에 대해 build 명령어가 스킵하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    app_name = "my-helm-app"

    with patch('shutil.copytree') as mock_copytree:
        result = runner.invoke(sbkube_cli, [
            'build',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name 
        ])
        assert result.exit_code == 0
        mock_copytree.assert_not_called()
        assert f"Skipping app {app_name} with type install-helm as it is not buildable." in caplog.text

def test_build_specific_app(runner: CliRunner, create_sample_config_yaml, create_sample_local_copy_source_dir, charts_dir, base_dir, app_dir, build_dir, caplog):
    """
    build 명령어 실행 시 --app 옵션으로 특정 앱만 빌드하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    copy_source_dir = create_sample_local_copy_source_dir
    
    prepared_chart_source_dir = charts_dir / "pulled-apache"
    prepared_chart_source_dir.mkdir(parents=True, exist_ok=True)
    (prepared_chart_source_dir / "Chart.yaml").write_text("name: apache\nversion: 9.0.0")


    app_to_build = "my-copy-app"
    other_app_not_to_build = "my-pull-helm-app"


    expected_copy_app_build_path = build_dir / app_to_build / "copied-app-dest"
    
    source_dir_for_copy_app = base_dir / "local-src" / "my-app"


    with patch('shutil.copytree') as mock_copytree, \
         patch('shutil.rmtree') as mock_rmtree, \
         patch('pathlib.Path.exists', side_effect=lambda p: True if p == source_dir_for_copy_app or p == prepared_chart_source_dir else Path.exists(p)):

        result = runner.invoke(sbkube_cli, [
            'build',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_to_build
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}"

        copy_call_for_my_copy_app = call(source_dir_for_copy_app, expected_copy_app_build_path, dirs_exist_ok=True)
        
        assert mock_copytree.call_count == 1
        mock_copytree.assert_called_once_with(source_dir_for_copy_app, expected_copy_app_build_path, dirs_exist_ok=True)
        
        assert f"Building app: {app_to_build}" in caplog.text
        assert f"App '{app_to_build}' (copy-app) built successfully to {expected_copy_app_build_path}" in caplog.text
        assert f"Building app: {other_app_not_to_build}" not in caplog.text

def test_build_pull_helm_app_uses_dest_as_build_directory_name(runner: CliRunner, base_dir, app_dir, charts_dir, build_dir):
    """
    pull-helm 타입 앱에서 dest 값이 지정되었을 때, 빌드 디렉토리 이름이 app_name 대신 dest 값을 사용하는지 테스트합니다.
    이것은 pull-helm에서 zabbix-pull 앱이 dest: zabbix로 설정했을 때 build/zabbix로 빌드되어야 하는 요구사항을 테스트합니다.
    """
    import yaml
    
    # 테스트용 config.yaml 내용 생성
    config_content = {
        "namespace": "test-ns",
        "apps": [
            {
                "name": "zabbix-pull",
                "type": "pull-helm",
                "specs": {
                    "repo": "zabbix-community",
                    "chart": "zabbix",
                    "dest": "zabbix"  # 이 값이 빌드 디렉토리 이름으로 사용되어야 함
                }
            }
        ]
    }
    
    # config.yaml 파일 생성
    config_file = app_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)
    
    # prepare 단계에서 생성될 차트 디렉토리 모킹 (dest 값인 "zabbix"로 생성)
    prepared_chart_source_dir = charts_dir / "zabbix"  # dest 값 사용
    prepared_chart_source_dir.mkdir(parents=True, exist_ok=True)
    (prepared_chart_source_dir / "Chart.yaml").write_text("name: zabbix\nversion: 1.0.0")
    (prepared_chart_source_dir / "values.yaml").write_text("replicaCount: 1")
    (prepared_chart_source_dir / "templates").mkdir(exist_ok=True)
    (prepared_chart_source_dir / "templates" / "deployment.yaml").write_text("kind: Deployment")
    
    # 예상되는 빌드 경로 (app_name이 아닌 dest 값 사용)
    expected_build_path = build_dir / "zabbix"  # dest 값 사용
    
    result = runner.invoke(sbkube_cli, [
        'build',
        '--base-dir', str(base_dir),
        '--app-dir', str(app_dir.name)
    ])
    
    assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
    
    # 빌드 디렉토리가 dest 값("zabbix")으로 생성되었는지 확인
    assert expected_build_path.exists(), f"빌드 디렉토리가 dest 값으로 생성되지 않았습니다: {expected_build_path}"
    
    # app_name("zabbix-pull")으로는 생성되지 않았는지 확인
    wrong_build_path = build_dir / "zabbix-pull"
    assert not wrong_build_path.exists(), f"빌드 디렉토리가 잘못된 이름(app_name)으로 생성되었습니다: {wrong_build_path}"
    
    # 로그에서 올바른 경로 사용 확인
    assert "zabbix-pull" in result.output, "앱 이름이 로그에 표시되어야 합니다"
    assert str(expected_build_path) in result.output, "dest 값으로 생성된 빌드 경로가 로그에 표시되어야 합니다"


def test_build_pull_helm_app_fallback_to_chart_name_when_no_dest(runner: CliRunner, base_dir, app_dir, charts_dir, build_dir):
    """
    pull-helm 타입 앱에서 dest 값이 지정되지 않았을 때, 빌드 디렉토리 이름이 chart 이름을 사용하는지 테스트합니다.
    """
    import yaml
    
    # 테스트용 config.yaml 내용 생성 (dest 없음)
    config_content = {
        "namespace": "test-ns",
        "apps": [
            {
                "name": "redis-pull",
                "type": "pull-helm",
                "specs": {
                    "repo": "bitnami",
                    "chart": "redis"
                    # dest 값이 없음 - chart 이름("redis")을 사용해야 함
                }
            }
        ]
    }
    
    # config.yaml 파일 생성
    config_file = app_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)
    
    # prepare 단계에서 생성될 차트 디렉토리 모킹 (chart 이름인 "redis"로 생성)
    prepared_chart_source_dir = charts_dir / "redis"  # chart 이름 사용
    prepared_chart_source_dir.mkdir(parents=True, exist_ok=True)
    (prepared_chart_source_dir / "Chart.yaml").write_text("name: redis\nversion: 1.0.0")
    (prepared_chart_source_dir / "values.yaml").write_text("replicaCount: 1")
    
    # 예상되는 빌드 경로 (chart 이름 사용)
    expected_build_path = build_dir / "redis"  # chart 이름 사용
    
    result = runner.invoke(sbkube_cli, [
        'build',
        '--base-dir', str(base_dir),
        '--app-dir', str(app_dir.name)
    ])
    
    assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
    
    # 빌드 디렉토리가 chart 이름("redis")으로 생성되었는지 확인
    assert expected_build_path.exists(), f"빌드 디렉토리가 chart 이름으로 생성되지 않았습니다: {expected_build_path}"
    
    # app_name("redis-pull")으로는 생성되지 않았는지 확인
    wrong_build_path = build_dir / "redis-pull"
    assert not wrong_build_path.exists(), f"빌드 디렉토리가 잘못된 이름(app_name)으로 생성되었습니다: {wrong_build_path}"
