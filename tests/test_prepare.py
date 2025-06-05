import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, call
from click.testing import CliRunner
import yaml

from sbkube.cli import main as sbkube_cli

EXAMPLES_DIR = Path("examples/k3scode")
CHARTS_DIR = Path("charts")
REPOS_DIR = Path("repos")

def clean_output_dirs():
    if CHARTS_DIR.exists():
        shutil.rmtree(CHARTS_DIR)
    if REPOS_DIR.exists():
        shutil.rmtree(REPOS_DIR)

def test_prepare_command_runs_successfully():
    # 🧹 사전 정리
    clean_output_dirs()

    # 📦 prepare 실행
    result = subprocess.run(
        [
            "sbkube", "prepare",
            "--apps", str(EXAMPLES_DIR / "config.yaml"),
            "--sources", str(EXAMPLES_DIR / "sources.yaml")
        ],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    print(result.stderr)

    assert result.returncode == 0, "prepare 명령 실패"

    # ✅ 결과물 확인
    assert CHARTS_DIR.exists(), "charts 디렉토리가 생성되지 않았습니다"
    assert REPOS_DIR.exists(), "repos 디렉토리가 생성되지 않았습니다"

    # 예시: browserless chart가 정상 다운로드되었는지 확인
    browserless_chart = CHARTS_DIR / "browserless" / "Chart.yaml"
    assert browserless_chart.exists(), "browserless Helm 차트가 존재하지 않습니다"

def test_prepare_helm_repo_add_and_update(runner: CliRunner, create_sample_sources_yaml, base_dir, app_dir, charts_dir, caplog):
    """
    prepare 명령어 실행 시 helm repo add 및 update가 올바르게 호출되는지 테스트합니다.
    또한, pull-helm 타입 앱에 대해 helm pull 명령이 실행되는지 확인합니다.
    """
    sources_file = create_sample_sources_yaml
    
    config_content = {
        "apps": [{
            "name": "my-pull-helm-app",
            "type": "pull-helm",
            "specs": {
                "repo": "bitnami",
                "chart": "apache",
                "version": "9.0.0",
                "dest": "pulled-apache"
            }
        }]
    }
    config_file = app_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)

    with patch('subprocess.run') as mock_subprocess_run:
        # helm repo list 모킹 (빈 리스트)
        mock_subprocess_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0, stdout='[]', stderr=''),  # helm repo list
            subprocess.CompletedProcess(args=[], returncode=0, stdout='', stderr=''),    # helm repo add
            subprocess.CompletedProcess(args=[], returncode=0, stdout='', stderr=''),    # helm repo update
        ]

        result = runner.invoke(sbkube_cli, [
            'prepare',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--sources-file', str(sources_file)
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"
        
        # subprocess.run이 호출되었는지 확인
        assert mock_subprocess_run.call_count >= 2  # helm repo list, helm repo add, helm repo update
        
        # helm repo add 호출 확인 
        add_call_found = any('helm' in str(call) and 'repo' in str(call) and 'add' in str(call) 
                           for call in mock_subprocess_run.call_args_list)
        assert add_call_found, f"helm repo add가 호출되지 않음: {mock_subprocess_run.call_args_list}"


def test_prepare_pull_git(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, repos_dir, caplog):
    """
    prepare 명령어 실행 시 pull-git 타입 앱에 대해 git clone/pull이 올바르게 호출되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml

    git_repo_path = repos_dir / "pulled-git-repo"

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.exists') as mock_path_exists:

        mock_path_exists.return_value = False 
        mock_run_command.return_value = (0, "Cloned successfully", "")
        
        result_clone = runner.invoke(sbkube_cli, [
            'prepare',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', 'my-pull-git-app' 
        ])
        assert result_clone.exit_code == 0, f"CLI 실행 실패 (clone): {result_clone.output}"
        
        clone_call = call([
            'git', 'clone', '--branch', 'main', 
            'https://github.com/user/repo.git', str(git_repo_path)
        ], capture_output=True, text=True, check=False, env=None)
        assert clone_call in mock_run_command.call_args_list
        assert f"Cloning Git repository https://github.com/user/repo.git into {git_repo_path}" in caplog.text

        mock_run_command.reset_mock()
        caplog.clear()

        mock_path_exists.return_value = True
        mock_run_command.return_value = (0, "Pulled successfully", "")

        result_pull = runner.invoke(sbkube_cli, [
            'prepare',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', 'my-pull-git-app'
        ])
        assert result_pull.exit_code == 0, f"CLI 실행 실패 (pull): {result_pull.output}"

        pull_call = call(['git', 'pull'], capture_output=True, text=True, check=False, cwd=str(git_repo_path), env=None)
        assert pull_call in mock_run_command.call_args_list
        assert f"Updating Git repository {git_repo_path}" in caplog.text


def test_prepare_no_pull_apps(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, caplog):
    """
    prepare 명령어 실행 시 pull 타입 앱이 없으면 아무 작업도 수행하지 않는지 테스트합니다.
    """
    config_content = {
        "apps": [{
            "name": "my-helm-app", 
            "type": "install-helm",
            "specs": {"repo": "bitnami", "chart": "redis"}
        }]
    }
    config_file = app_dir / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config_content, f)

    with patch('sbkube.utils.common.run_command') as mock_run_command:
        result = runner.invoke(sbkube_cli, [
            'prepare',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name)
        ])
        assert result.exit_code == 0
        mock_run_command.assert_not_called() 
        assert "No apps found to prepare with types" in caplog.text

def test_prepare_specific_app(runner: CliRunner, create_sample_config_yaml, create_sample_sources_yaml, base_dir, app_dir, charts_dir, repos_dir, caplog):
    """
    prepare 명령어 실행 시 --app 옵션으로 특정 앱만 처리하는지 테스트합니다.
    """
    config_file = create_sample_config_yaml 
    sources_file = create_sample_sources_yaml

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.exists', return_value=False): 
        mock_run_command.return_value = (0, "Success", "")

        result = runner.invoke(sbkube_cli, [
            'prepare',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--sources-file', str(sources_file.name),
            '--app', 'my-pull-helm-app' 
        ])
        assert result.exit_code == 0

        helm_pull_call = call([
            'helm', 'pull', 'bitnami/apache',
            '--version', '9.0.0',
            '--destination', str(charts_dir / 'pulled-apache'),
            '--untar'
        ], capture_output=True, text=True, check=False, env=None)
        
        git_clone_call = call([
            'git', 'clone', '--branch', 'main', 
            'https://github.com/user/repo.git', str(repos_dir / "pulled-git-repo")
        ], capture_output=True, text=True, check=False, env=None)

        assert helm_pull_call in mock_run_command.call_args_list
        assert git_clone_call not in mock_run_command.call_args_list
        assert "Processing app: my-pull-helm-app" in caplog.text
        assert "Processing app: my-pull-git-app" not in caplog.text

def test_template_helm_app(runner: CliRunner, create_sample_config_yaml, base_dir, app_dir, build_dir, caplog):
    """
    template 명령어 실행 시 빌드된 Helm 차트에 대해 helm template 명령어가 올바르게 호출되는지 테스트합니다.
    """
    config_file = create_sample_config_yaml # my-helm-app (install-helm 타입) 포함
    app_name = "my-helm-app" # template은 install-helm 타입의 앱을 대상으로 함.

    # "build"된 차트 모킹: build_dir / <app_name> / Chart.yaml
    built_chart_path = build_dir / app_name
    built_chart_path.mkdir(parents=True, exist_ok=True)
    (built_chart_path / "Chart.yaml").write_text(f"apiVersion: v2\nname: {app_name}\nversion: 1.0.0")
    (built_chart_path / "values.yaml").write_text("some: value")
    (built_chart_path / "templates").mkdir(exist_ok=True)
    (built_chart_path / "templates" / "service.yaml").write_text("kind: Service")

    # config.yaml에서 my-helm-app의 values, namespace 등 사용
    values_dir = app_dir / "values"
    values_dir.mkdir(exist_ok=True)
    sample_values_file = values_dir / "helm-app-values.yaml"
    sample_values_file.write_text("persistence: {enabled: true}") # conftest.py에서 생성되는 파일과 매칭


    output_dir = base_dir / "rendered_yamls" # 테스트용 출력 디렉토리
    expected_output_file = output_dir / f"{app_name}.yaml"

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.is_dir', return_value=True): # 빌드된 차트 디렉토리가 존재한다고 가정
        mock_run_command.return_value = (0, "--- # Source: chart/templates/service.yaml", "") # helm template 출력 모킹

        result = runner.invoke(sbkube_cli, [
            'template',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--output-dir', str(output_dir.relative_to(base_dir)) # base_dir 기준 상대경로
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # helm template 명령어 호출 검증
        expected_helm_template_call = call([
            'helm', 'template', app_name, str(built_chart_path),
            '--namespace', 'helm-ns', # from config's app.specs.namespace
            '-f', str(sample_values_file.resolve()), # from config's app.specs.values
            '--set', 'master.replicaCount=1' # from config's app.specs.set
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
    config_file = create_sample_config_yaml # my-kubectl-app (install-kubectl 타입) 포함
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
    (built_chart_path / "Chart.yaml").write_text(f"apiVersion: v2\nname: {app_name}\nversion: 1.0.0")
    (built_chart_path / "values.yaml").write_text("some: value")
    (built_chart_path / "templates").mkdir(exist_ok=True)
    (built_chart_path / "templates" / "service.yaml").write_text("kind: Service")

    # config.yaml에서 my-helm-app의 values, namespace 등 사용
    values_dir = app_dir / "values"
    values_dir.mkdir(exist_ok=True)
    sample_values_file = values_dir / "helm-app-values.yaml"
    sample_values_file.write_text("persistence: {enabled: true}") # conftest.py에서 생성되는 파일과 매칭


    output_dir = base_dir / "rendered_yamls" # 테스트용 출력 디렉토리
    expected_output_file = output_dir / f"{app_name}.yaml"

    with patch('sbkube.utils.common.run_command') as mock_run_command, \
         patch('pathlib.Path.is_dir', return_value=True): # 빌드된 차트 디렉토리가 존재한다고 가정
        mock_run_command.return_value = (0, "--- # Source: chart/templates/service.yaml", "") # helm template 출력 모킹

        result = runner.invoke(sbkube_cli, [
            'template',
            '--base-dir', str(base_dir),
            '--app-dir', str(app_dir.name),
            '--config-file', str(config_file.name),
            '--app', app_name,
            '--output-dir', str(output_dir.relative_to(base_dir)), # base_dir 기준 상대경로
            '--namespace', 'custom-ns' # 오버라이드된 네임스페이스
        ])

        assert result.exit_code == 0, f"CLI 실행 실패: {result.output}\n{result.exception}"

        # helm template 명령어 호출 검증
        expected_helm_template_call = call([
            'helm', 'template', app_name, str(built_chart_path),
            '--namespace', 'custom-ns', # from config's app.specs.namespace
            '-f', str(sample_values_file.resolve()), # from config's app.specs.values
            '--set', 'master.replicaCount=1' # from config's app.specs.set
        ], capture_output=True, text=True, check=False, env=None)
        
        mock_run_command.assert_any_call(*expected_helm_template_call[1], **expected_helm_template_call[2])
        
        assert f"Templating app: {app_name}" in caplog.text
        assert f"Rendered template for {app_name} to {expected_output_file}" in caplog.text
        assert output_dir.exists()
        assert expected_output_file.exists()
        assert expected_output_file.read_text() == "--- # Source: chart/templates/service.yaml"
