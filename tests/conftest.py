from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner


@pytest.fixture(scope="session")
def runner():
    """Click CliRunner fixture."""
    return CliRunner()


@pytest.fixture
def base_dir(tmp_path):
    """테스트용 기본 디렉토리 fixture."""
    return tmp_path


@pytest.fixture
def app_dir(base_dir):
    """테스트용 앱 설정 디렉토리 fixture."""
    app_path = base_dir / "config"
    app_path.mkdir(parents=True, exist_ok=True)
    return app_path


@pytest.fixture
def charts_dir(base_dir):
    """테스트용 Helm 차트 저장 디렉토리 fixture."""
    charts_path = base_dir / "charts"
    charts_path.mkdir(parents=True, exist_ok=True)
    return charts_path


@pytest.fixture
def repos_dir(base_dir):
    """테스트용 Git 레포지토리 저장 디렉토리 fixture."""
    repos_path = base_dir / "repos"
    repos_path.mkdir(parents=True, exist_ok=True)
    return repos_path


@pytest.fixture
def build_dir(app_dir):
    """테스트용 빌드 결과물 디렉토리 fixture."""
    # build 디렉토리는 app_dir 내부에 생성됨
    # sbkube build --base-dir . --app-dir config  -> ./config/build/
    build_path = app_dir / "build"
    # build_path.mkdir(parents=True, exist_ok=True) # build 명령어가 직접 생성하도록 둠
    return build_path


@pytest.fixture
def sample_config_yaml_content():
    """테스트용 기본 config.yaml 내용."""
    return {
        "namespace": "test-ns",
        "apps": [
            {
                "name": "my-helm-app",
                "type": "helm",
                "namespace": "helm-ns",
                "specs": {
                    "repo": "grafana",
                    "chart": "grafana",
                    "version": "6.50.0",
                    "values": ["values/helm-app-values.yaml"],
                    "set": ["replicas=1"],
                },
            },
            {
                "name": "my-kubectl-app",
                "type": "yaml",
                "specs": {
                    "actions": [
                        {"type": "apply", "path": "manifests/kubectl-app.yaml"}
                    ],
                    "namespace": "kubectl-ns",
                },
            },
            {
                "name": "my-action-app",
                "type": "exec",
                "specs": {"commands": ["echo 'action executed'"]},
            },
            {
                "name": "my-helm-app",
                "type": "helm",
                "specs": {
                    "repo": "ingress-nginx",
                    "chart": "ingress-nginx",
                    "version": "4.0.0",
                    "dest": "pulled-ingress",  # charts/<dest>
                },
            },
            {
                "name": "my-pull-git-app",
                "type": "git",
                "specs": {
                    "repo": "pulled-git-repo",
                    "paths": [{"src": ".", "dest": "."}],
                },
            },
            {
                "name": "my-copy-app",
                "type": "http",
                "specs": {
                    "paths": [
                        {
                            "src": "local-src/my-app",
                            "dest": "copied-app-dest",
                        }  # base_dir 기준
                    ]
                },
            },
        ],
    }


@pytest.fixture
def sample_sources_yaml_content():
    """테스트용 기본 sources.yaml 내용."""
    return {
        "helm_repos": {"grafana": "https://grafana.github.io/helm-charts"},
        "git_repos": {
            "my-repo": {  # 사용되지 않음, pull-git은 직접 URL 명시
                "url": "https://github.com/some/other-repo.git",
                "branch": "develop",
            }
        },
    }


@pytest.fixture
def create_sample_config_yaml(app_dir, sample_config_yaml_content):
    """샘플 config.yaml 파일을 생성하는 fixture."""
    config_file = app_dir / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(sample_config_yaml_content, f)
    return config_file


@pytest.fixture
def create_sample_sources_yaml(app_dir, sample_sources_yaml_content):
    """샘플 sources.yaml 파일을 생성하는 fixture."""
    sources_file = app_dir / "sources.yaml"
    with open(sources_file, "w") as f:
        yaml.dump(sample_sources_yaml_content, f)
    return sources_file


@pytest.fixture
def create_sample_values_file(app_dir):
    """샘플 values.yaml 파일을 생성하는 fixture."""
    values_dir = app_dir / "values"
    values_dir.mkdir(exist_ok=True)
    values_file = values_dir / "helm-app-values.yaml"
    with open(values_file, "w") as f:
        yaml.dump({"persistence": {"enabled": False}}, f)
    return values_file


@pytest.fixture
def create_sample_kubectl_manifest_file(app_dir):
    """샘플 kubectl manifest 파일을 생성하는 fixture."""
    manifests_dir = app_dir / "manifests"
    manifests_dir.mkdir(exist_ok=True)
    manifest_file = manifests_dir / "kubectl-app.yaml"
    with open(manifest_file, "w") as f:
        yaml.dump(
            {"apiVersion": "v1", "kind": "Pod", "metadata": {"name": "test-pod"}}, f
        )
    return manifest_file


@pytest.fixture
def create_sample_local_copy_source_dir(base_dir):
    """샘플 로컬 복사 원본 디렉토리 및 파일을 생성하는 fixture."""
    local_src_path = base_dir / "local-src" / "my-app"
    local_src_path.mkdir(parents=True, exist_ok=True)
    (local_src_path / "file1.txt").write_text("content1")
    (local_src_path / "Chart.yaml").write_text(
        "apiVersion: v2\nname: my-chart\nversion: 0.1.0"
    )
    return local_src_path


@pytest.fixture(autouse=True)
def setup_test_environment(base_dir, app_dir, charts_dir, repos_dir, monkeypatch):
    """각 테스트 실행 전후로 환경을 설정하고 정리합니다."""
    monkeypatch.setattr(Path, "cwd", lambda: base_dir)
    monkeypatch.setattr(
        "sbkube.utils.common.get_absolute_path",
        lambda x, base: Path(base) / x if not Path(x).is_absolute() else Path(x),
    )
    # monkeypatch.setattr('sbkube.cli.DEFAULT_APP_DIR', app_dir.name)
    # monkeypatch.setattr('sbkube.cli.DEFAULT_SOURCES_FILE', "sources.yaml")
    # monkeypatch.setattr('sbkube.cli.DEFAULT_CONFIG_FILE', "config.yaml")

    # monkeypatch.setattr('sbkube.commands.prepare.DEFAULT_CHARTS_DIR', charts_dir.name)
    # monkeypatch.setattr('sbkube.commands.prepare.DEFAULT_REPOS_DIR', repos_dir.name)
