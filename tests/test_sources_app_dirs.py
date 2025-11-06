"""Test for sources.yaml app_dirs feature.

이 테스트는 sources.yaml의 app_dirs 필드 기능을 검증합니다:
- app_dirs 필드 검증 (유효성 검사)
- get_app_dirs() 메서드 동작 확인 (명시적 목록 vs 자동 탐색)
"""

import pytest

from sbkube.exceptions import ConfigValidationError
from sbkube.models.sources_model import SourceScheme


def test_sources_app_dirs_validation() -> None:
    """app_dirs 필드 검증 테스트."""
    # 정상 케이스: app_dirs 지정
    sources = SourceScheme(
        kubeconfig="~/.kube/config",
        kubeconfig_context="test",
        app_dirs=["redis", "postgres", "nginx"],
    )
    assert sources.app_dirs == ["redis", "postgres", "nginx"]

    # 정상 케이스: app_dirs 미지정 (None)
    sources = SourceScheme(kubeconfig="~/.kube/config", kubeconfig_context="test")
    assert sources.app_dirs is None

    # 정상 케이스: 빈 값은 제거됨
    sources = SourceScheme(
        kubeconfig="~/.kube/config",
        kubeconfig_context="test",
        app_dirs=["redis", "  postgres  ", "nginx"],
    )
    assert sources.app_dirs == ["redis", "postgres", "nginx"]


def test_sources_app_dirs_validation_errors() -> None:
    """app_dirs 검증 오류 테스트."""
    # 빈 리스트 (오류)
    with pytest.raises(ConfigValidationError, match="app_dirs cannot be empty"):
        SourceScheme(
            kubeconfig="~/.kube/config", kubeconfig_context="test", app_dirs=[]
        )

    # 경로 포함 (오류)
    with pytest.raises(
        ConfigValidationError, match="must contain directory names only, not paths"
    ):
        SourceScheme(
            kubeconfig="~/.kube/config",
            kubeconfig_context="test",
            app_dirs=["redis", "apps/postgres"],
        )

    # 숨김 디렉토리 (오류)
    with pytest.raises(
        ConfigValidationError, match="cannot contain hidden directories"
    ):
        SourceScheme(
            kubeconfig="~/.kube/config",
            kubeconfig_context="test",
            app_dirs=[".hidden", "redis"],
        )

    # 중복 (오류)
    with pytest.raises(
        ConfigValidationError, match="cannot contain duplicate directory names"
    ):
        SourceScheme(
            kubeconfig="~/.kube/config",
            kubeconfig_context="test",
            app_dirs=["redis", "postgres", "redis"],
        )

    # 빈 문자열 (오류)
    with pytest.raises(
        ConfigValidationError, match="cannot contain empty directory names"
    ):
        SourceScheme(
            kubeconfig="~/.kube/config",
            kubeconfig_context="test",
            app_dirs=["redis", "", "postgres"],
        )


def test_get_app_dirs_explicit_mode(tmp_path) -> None:
    """명시적 app_dirs 목록 모드 테스트."""
    # 프로젝트 구조 생성
    (tmp_path / "redis" / "config.yaml").parent.mkdir(parents=True)
    (tmp_path / "redis" / "config.yaml").write_text("namespace: test\napps: {}")

    (tmp_path / "postgres" / "config.yaml").parent.mkdir(parents=True)
    (tmp_path / "postgres" / "config.yaml").write_text("namespace: test\napps: {}")

    (tmp_path / "nginx" / "config.yaml").parent.mkdir(parents=True)
    (tmp_path / "nginx" / "config.yaml").write_text("namespace: test\napps: {}")

    # sources.yaml with app_dirs
    sources = SourceScheme(
        kubeconfig="~/.kube/config",
        kubeconfig_context="test",
        app_dirs=["redis", "postgres"],  # nginx는 제외
    )

    # get_app_dirs 호출
    app_dirs = sources.get_app_dirs(tmp_path, "config.yaml")

    # 검증: redis, postgres만 반환 (nginx 제외)
    assert len(app_dirs) == 2
    assert tmp_path / "redis" in app_dirs
    assert tmp_path / "postgres" in app_dirs
    assert tmp_path / "nginx" not in app_dirs


def test_get_app_dirs_auto_discovery_mode(tmp_path) -> None:
    """자동 탐색 모드 테스트 (app_dirs 미지정)."""
    # 프로젝트 구조 생성
    (tmp_path / "redis" / "config.yaml").parent.mkdir(parents=True)
    (tmp_path / "redis" / "config.yaml").write_text("namespace: test\napps: {}")

    (tmp_path / "postgres" / "config.yaml").parent.mkdir(parents=True)
    (tmp_path / "postgres" / "config.yaml").write_text("namespace: test\napps: {}")

    (tmp_path / "nginx" / "config.yaml").parent.mkdir(parents=True)
    (tmp_path / "nginx" / "config.yaml").write_text("namespace: test\napps: {}")

    # Excluded directories (exist_ok=True to avoid errors)
    (tmp_path / "charts").mkdir(exist_ok=True)
    (tmp_path / ".git").mkdir(exist_ok=True)
    (tmp_path / "node_modules").mkdir(exist_ok=True)

    # sources.yaml without app_dirs
    sources = SourceScheme(kubeconfig="~/.kube/config", kubeconfig_context="test")

    # get_app_dirs 호출 (자동 탐색)
    app_dirs = sources.get_app_dirs(tmp_path, "config.yaml")

    # 검증: redis, postgres, nginx 모두 반환 (제외 디렉토리는 제외)
    assert len(app_dirs) == 3
    assert tmp_path / "redis" in app_dirs
    assert tmp_path / "postgres" in app_dirs
    assert tmp_path / "nginx" in app_dirs

    # 제외 디렉토리는 포함되지 않음
    assert tmp_path / "charts" not in app_dirs
    assert tmp_path / ".git" not in app_dirs
    assert tmp_path / "node_modules" not in app_dirs


def test_get_app_dirs_missing_directory_error(tmp_path) -> None:
    """명시적 app_dirs에서 존재하지 않는 디렉토리 오류 테스트."""
    # redis만 생성
    (tmp_path / "redis" / "config.yaml").parent.mkdir(parents=True)
    (tmp_path / "redis" / "config.yaml").write_text("namespace: test\napps: {}")

    # sources.yaml with non-existent directory
    sources = SourceScheme(
        kubeconfig="~/.kube/config",
        kubeconfig_context="test",
        app_dirs=["redis", "postgres"],  # postgres는 없음
    )

    # get_app_dirs 호출 시 오류
    with pytest.raises(ValueError, match="Invalid app_dirs in sources.yaml"):
        sources.get_app_dirs(tmp_path, "config.yaml")


def test_get_app_dirs_missing_config_file_error(tmp_path) -> None:
    """명시적 app_dirs에서 config.yaml이 없는 경우 오류 테스트."""
    # redis 디렉토리만 생성 (config.yaml 없음)
    (tmp_path / "redis").mkdir(parents=True)

    # sources.yaml with directory that has no config.yaml
    sources = SourceScheme(
        kubeconfig="~/.kube/config", kubeconfig_context="test", app_dirs=["redis"]
    )

    # get_app_dirs 호출 시 오류
    with pytest.raises(ValueError, match="Config file not found: redis/config.yaml"):
        sources.get_app_dirs(tmp_path, "config.yaml")


def test_get_app_dirs_sorted_output(tmp_path) -> None:
    """app_dirs 반환 결과가 정렬되는지 테스트."""
    # 프로젝트 구조 생성 (역순)
    for name in ["zulu", "alpha", "bravo"]:
        (tmp_path / name / "config.yaml").parent.mkdir(parents=True)
        (tmp_path / name / "config.yaml").write_text("namespace: test\napps: {}")

    # sources.yaml with app_dirs (역순)
    sources = SourceScheme(
        kubeconfig="~/.kube/config",
        kubeconfig_context="test",
        app_dirs=["zulu", "alpha", "bravo"],
    )

    # get_app_dirs 호출
    app_dirs = sources.get_app_dirs(tmp_path, "config.yaml")

    # 검증: 정렬된 순서로 반환
    assert len(app_dirs) == 3
    assert app_dirs[0] == tmp_path / "alpha"
    assert app_dirs[1] == tmp_path / "bravo"
    assert app_dirs[2] == tmp_path / "zulu"
