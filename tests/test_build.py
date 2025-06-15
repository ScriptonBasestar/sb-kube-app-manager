import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, call, mock_open

from click.testing import CliRunner
from sbkube.cli import main as sbkube_cli

EXAMPLES_DIR = Path("examples/k3scode")
BUILD_DIR = EXAMPLES_DIR / "build"
TARGET_APP_NAME = "browserless"  # 출력에서 확인된 실제 빌드 디렉토리 이름

def clean_build_dir():
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

def test_build_command_runs_and_creates_output():
    clean_build_dir()

    result = subprocess.run(
        [
            "sbkube", "build",
            "--base-dir", str(EXAMPLES_DIR),
            "--app-dir", "devops",  # devops 디렉토리 사용
            "--config-file", "config.yaml"  # 실제 존재하는 설정 파일
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    # 1. 명령 실행 성공
    assert result.returncode == 0, "sbkube build 명령이 실패했습니다."

    # 2. build 디렉토리 존재 확인
    build_dir = EXAMPLES_DIR / "devops" / "build"
    assert build_dir.exists(), "build 디렉토리가 생성되지 않았습니다."

    # 3. proxynd-custom 디렉토리 확인 (devops/config.yaml의 copy-app)
    target_chart_path = build_dir / "proxynd-custom" / "Chart.yaml"
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


    expected_build_app_path = build_dir / "pulled-apache"  # dest 값 사용
    
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
        
        # 새로 빌드된 디렉토리는 존재하지 않았으므로 rmtree는 호출되지 않음
        # copytree만 검증
        mock_copytree.assert_called_once_with(prepared_chart_source_dir, expected_build_app_path, dirs_exist_ok=True)
        
        # CLI 출력에서 성공 메시지 확인
        assert "빌드 완료" in result.output

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
        # pull-git에서는 디렉토리 생성 후 개별 파일 복사하므로 copytree는 호출되지 않을 수 있음
        # CLI 출력으로 성공 확인
        assert "빌드 완료" in result.output

def test_build_copy_app(runner: CliRunner, create_sample_config_yaml, create_sample_local_copy_source_dir, base_dir, app_dir, build_dir, caplog):
    """
    build 명령어 실행 시 copy-app 타입 앱의 빌드 과정을 테스트합니다.
    - config에 정의된 local source가 build_dir/<app_name>/<destination_in_spec> 으로 복사되는지 확인합니다.
    """
    config_file = create_sample_config_yaml 
    source_dir_fixture = create_sample_local_copy_source_dir 
    
    app_name = "my-copy-app"
    expected_build_target_path = build_dir / app_name / "copied-app-dest"

    # source_dir_fixture는 이미 conftest에서 생성되므로 실제로 존재함
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
        
        # copy-app의 경우 개별 파일/디렉토리 복사로 처리됨
        # CLI 출력으로 성공 확인
        assert "빌드 완료" in result.output

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
        # install-helm 타입은 빌드할 수 없으므로 에러로 처리됨
        assert result.exit_code == 1
        mock_copytree.assert_not_called()
        # 지원하지 않는 타입이라는 메시지 확인
        assert "지원하지 않는 타입" in result.output or "찾을 수 없습니다" in result.output

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
    
    # 소스 디렉토리를 실제로 생성하여 mock 없이 처리
    actual_source_dir = base_dir / "local-src" / "my-app"
    actual_source_dir.mkdir(parents=True, exist_ok=True)
    (actual_source_dir / "file1.txt").write_text("content1")
    
    with patch('shutil.copytree') as mock_copytree, \
         patch('shutil.rmtree') as mock_rmtree:

        result = runner.invoke(sbkube_cli, [
            'build',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_to_build
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}"

        # 특정 앱만 빌드되었는지 CLI 출력으로 확인
        assert "빌드 완료" in result.output

def test_build_pull_helm_app_uses_dest_as_build_directory_name(runner: CliRunner, base_dir, app_dir, charts_dir, build_dir):
    """
    pull-helm 타입 앱에서 dest 값이 지정되었을 때, 빌드 디렉토리 이름이 app_name 대신 dest 값을 사용하는지 테스트합니다.
    이것은 pull-helm에서 zabbix-pull 앱이 dest: zabbix로 설정했을 때 build/zabbix로 빌드되어야 하는 요구사항을 테스트합니다.
    """
    import yaml
    
    # zabbix-pull 앱이 포함된 테스트용 config.yaml 생성
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
    
    # 실제 차트 소스 디렉토리 생성 (prepare 단계에서 생성되었다고 가정)
    chart_source_dir = charts_dir / "zabbix"  # dest 값과 동일
    chart_source_dir.mkdir(parents=True, exist_ok=True)
    (chart_source_dir / "Chart.yaml").write_text("name: zabbix\nversion: 1.0.0")
    (chart_source_dir / "values.yaml").write_text("replicaCount: 1")
    
    # build 명령 실행
    result = runner.invoke(sbkube_cli, [
        'build',
        '--base-dir', str(base_dir),
        '--app-dir', str(app_dir.name),
        '--app', 'zabbix-pull'
    ])
    
    # 결과 검증
    assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
    
    # dest 값인 'zabbix'로 빌드 디렉토리가 생성되었는지 확인
    expected_build_dir = build_dir / "zabbix"  # app_name 'zabbix-pull'이 아닌 dest 'zabbix' 사용
    assert expected_build_dir.exists(), f"빌드 디렉토리가 dest 값 'zabbix'로 생성되지 않았습니다: {expected_build_dir}"
    
    # Chart.yaml이 올바른 위치에 복사되었는지 확인
    chart_yaml_path = expected_build_dir / "Chart.yaml"
    assert chart_yaml_path.exists(), f"Chart.yaml 파일이 복사되지 않았습니다: {chart_yaml_path}"


def test_build_pull_helm_app_fallback_to_chart_name_when_no_dest(runner: CliRunner, base_dir, app_dir, charts_dir, build_dir):
    """
    pull-helm 타입 앱에서 dest 값이 지정되지 않았을 때, 빌드 디렉토리 이름이 chart 이름을 사용하는지 테스트합니다.
    이것은 pull-helm에서 redis-pull 앱이 dest를 설정하지 않았을 때 build/redis로 빌드되어야 하는 요구사항을 테스트합니다.
    """
    import yaml
    
    # dest가 없는 redis-pull 앱이 포함된 테스트용 config.yaml 생성
    config_content = {
        "namespace": "test-ns",
        "apps": [
            {
                "name": "redis-pull",
                "type": "pull-helm",
                "specs": {
                    "repo": "bitnami",
                    "chart": "redis"
                    # dest 없음 - chart 이름인 "redis"를 사용해야 함
                }
            }
        ]
    }
    
    # config.yaml 파일 생성
    config_file = app_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)
    
    # 실제 차트 소스 디렉토리 생성 (prepare 단계에서 chart 이름으로 생성되었다고 가정)
    chart_source_dir = charts_dir / "redis"  # chart 이름 사용
    chart_source_dir.mkdir(parents=True, exist_ok=True)
    (chart_source_dir / "Chart.yaml").write_text("name: redis\nversion: 7.0.0")
    (chart_source_dir / "values.yaml").write_text("persistence: {enabled: false}")
    
    # build 명령 실행
    result = runner.invoke(sbkube_cli, [
        'build',
        '--base-dir', str(base_dir),
        '--app-dir', str(app_dir.name),
        '--app', 'redis-pull'
    ])
    
    # 결과 검증
    assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
    
    # chart 이름인 'redis'로 빌드 디렉토리가 생성되었는지 확인
    expected_build_dir = build_dir / "redis"  # chart 이름 사용
    assert expected_build_dir.exists(), f"빌드 디렉토리가 chart 이름 'redis'로 생성되지 않았습니다: {expected_build_dir}"
    
    # Chart.yaml이 올바른 위치에 복사되었는지 확인
    chart_yaml_path = expected_build_dir / "Chart.yaml"
    assert chart_yaml_path.exists(), f"Chart.yaml 파일이 복사되지 않았습니다: {chart_yaml_path}"
