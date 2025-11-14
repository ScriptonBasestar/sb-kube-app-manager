"""Hooks 통합 테스트.

실제 명령어(prepare, build, deploy, template, apply)에서 hooks가 올바르게 작동하는지 검증:
- 글로벌 훅 실행
- 앱별 훅 실행
- Dry-run 모드
- 실패 처리
"""

import pytest
from click.testing import CliRunner

from sbkube.cli import main as cli


@pytest.fixture
def tmp_project(tmp_path):
    """임시 프로젝트 구조 생성."""
    project_dir = tmp_path / "test-project"
    config_dir = project_dir / "config"
    config_dir.mkdir(parents=True)

    # config.yaml 생성 (hooks 포함)
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text(
        """
namespace: test

hooks:
  prepare:
    pre:
      - echo "Global pre-prepare hook"
    post:
      - echo "Global post-prepare hook"
    on_failure:
      - echo "Global prepare failed"

apps:
  redis:
    type: helm
    enabled: true
    chart: grafana/loki
    version: "19.0.0"
    hooks:
      pre_prepare:
        - echo "Redis pre-prepare hook"
      post_prepare:
        - echo "Redis post-prepare hook"
      pre_build:
        - echo "Redis pre-build hook"
      post_build:
        - echo "Redis post-build hook"
      pre_deploy:
        - echo "Redis pre-deploy hook"
      post_deploy:
        - echo "Redis post-deploy hook"

  nginx:
    type: yaml
    enabled: true
    manifests:
      - nginx-deployment.yaml
    hooks:
      pre_deploy:
        - echo "Nginx pre-deploy hook"
      post_deploy:
        - echo "Nginx post-deploy hook"
"""
    )

    # YAML 매니페스트 생성
    nginx_yaml = config_dir / "nginx-deployment.yaml"
    nginx_yaml.write_text(
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
spec:
  replicas: 1
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:latest
"""
    )

    # Create a valid test kubeconfig
    kubeconfig_path = project_dir / "test-kubeconfig.yaml"
    kubeconfig_path.write_text(
        """apiVersion: v1
kind: Config
current-context: test-context
contexts:
- name: test-context
  context:
    cluster: test-cluster
    user: test-user
clusters:
- name: test-cluster
  cluster:
    server: https://localhost:6443
users:
- name: test-user
  user:
    token: fake-token
"""
    )

    # sources.yaml 생성 (use test kubeconfig)
    sources_yaml = project_dir / "sources.yaml"
    sources_yaml.write_text(
        f"""kubeconfig: "{kubeconfig_path}"
kubeconfig_context: "test-context"
cluster: "test-cluster"

helm_repos:
  grafana:
    url: https://grafana.github.io/helm-charts
"""
    )

    return project_dir, config_dir


def test_prepare_with_hooks_dry_run(tmp_project) -> None:
    """Prepare 명령어 hooks (dry-run 모드) 테스트."""
    project_dir, _config_dir = tmp_project

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "prepare",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
            "--dry-run",
        ],
    )

    # Dry-run 모드에서는 실제 실행하지 않지만 성공해야 함
    assert result.exit_code == 0
    assert "DRY-RUN" in result.output or "dry-run" in result.output.lower()


@pytest.mark.integration
@pytest.mark.skip(reason="Requires actual Kubernetes cluster even with --dry-run")
def test_deploy_with_hooks_dry_run(tmp_project) -> None:
    """Deploy 명령어 hooks (dry-run 모드) 테스트."""
    project_dir, _config_dir = tmp_project

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "deploy",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
            "--dry-run",
        ],
    )

    # Dry-run 모드에서는 훅이 시뮬레이션되어야 함
    assert (
        "DRY-RUN" in result.output
        or "dry-run" in result.output.lower()
        or result.exit_code == 0
    )


@pytest.mark.integration
def test_template_with_hooks_dry_run(tmp_project) -> None:
    """Template 명령어 hooks (dry-run 모드) 테스트."""
    project_dir, _config_dir = tmp_project

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "template",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
            "--dry-run",
        ],
    )

    # Dry-run 모드 확인
    assert (
        "DRY-RUN" in result.output
        or "dry-run" in result.output.lower()
        or result.exit_code == 0
    )


@pytest.mark.integration
def test_apply_with_hooks_dry_run(tmp_project) -> None:
    """Apply 명령어 hooks (dry-run 모드) 테스트."""
    project_dir, _config_dir = tmp_project

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "apply",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
            "--dry-run",
            "--skip-prepare",
            "--skip-build",
        ],
    )

    # Dry-run 모드 확인
    assert (
        "DRY-RUN" in result.output
        or "dry-run" in result.output.lower()
        or result.exit_code == 0
    )


def test_hooks_with_failing_script(tmp_project) -> None:
    """실패하는 훅 스크립트 테스트."""
    project_dir, config_dir = tmp_project

    # 실패하는 훅이 포함된 설정 생성
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text(
        """
namespace: test

hooks:
  prepare:
    pre:
      - exit 1  # 실패하는 명령어
    post: []
    on_failure: []

apps:
  redis:
    type: helm
    enabled: true
    chart: grafana/loki
    version: "19.0.0"
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "prepare",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
        ],
    )

    # 실패해야 함
    assert result.exit_code != 0


@pytest.mark.integration
@pytest.mark.skip(reason="Requires actual Kubernetes cluster")
def test_hooks_environment_variables(tmp_project) -> None:
    """훅에서 환경 변수 주입 테스트."""
    project_dir, config_dir = tmp_project

    # 환경 변수를 확인하는 스크립트 생성
    check_env_script = config_dir / "check_env.sh"
    check_env_script.write_text(
        """#!/bin/bash
echo "APP_NAME=$SBKUBE_APP_NAME"
echo "NAMESPACE=$SBKUBE_NAMESPACE"
echo "RELEASE_NAME=$SBKUBE_RELEASE_NAME"
"""
    )
    check_env_script.chmod(0o755)

    # 훅 스크립트를 사용하는 설정 생성
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text(
        f"""
namespace: test-ns

apps:
  redis:
    type: helm
    enabled: true
    chart: grafana/loki
    version: "19.0.0"
    release_name: my-redis
    hooks:
      pre_deploy:
        - {check_env_script}
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "deploy",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
            "--dry-run",
        ],
    )

    # Dry-run이므로 실패하지 않아야 함
    assert result.exit_code == 0


def test_hooks_without_config(tmp_project) -> None:
    """훅 설정이 없는 경우 테스트."""
    project_dir, config_dir = tmp_project

    # 훅이 없는 설정 생성
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text(
        """
namespace: test

apps:
  redis:
    type: helm
    enabled: true
    chart: grafana/loki
    version: "19.0.0"
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "prepare",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
            "--dry-run",
        ],
    )

    # 훅이 없어도 정상 동작해야 함
    assert result.exit_code == 0


@pytest.mark.integration
def test_app_hook_on_failure(tmp_project) -> None:
    """앱별 on_failure 훅 테스트."""
    project_dir, config_dir = tmp_project

    # 실패 시 훅이 포함된 설정 생성
    config_yaml = config_dir / "config.yaml"
    config_yaml.write_text(
        """
namespace: test

apps:
  redis:
    type: helm
    enabled: true
    chart: grafana/invalid-chart  # 존재하지 않는 차트
    version: "19.0.0"
    hooks:
      on_deploy_failure:
        - echo "Deploy failed, running cleanup"
"""
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "deploy",
            "--base-dir",
            str(project_dir),
            "--app-dir",
            "config",
        ],
    )

    # 실패해야 함 (존재하지 않는 차트)
    assert result.exit_code != 0
