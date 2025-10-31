"""경로 해석 유틸리티 모듈.

변수 치환 기능을 제공하여 동적 경로 해석을 지원합니다.
"""

import re
from pathlib import Path
from typing import Any

from sbkube.exceptions import SbkubeError


def expand_repo_variables(
    manifest_path: str,
    repos_dir: Path,
    apps_config: dict[str, Any],
) -> str:
    """manifests 경로에서 ${repos.app-name} 변수를 실제 경로로 확장합니다.

    Args:
        manifest_path: 원본 경로 (변수 포함 가능)
        repos_dir: .sbkube/repos/ 디렉토리 경로
        apps_config: 전체 앱 설정 딕셔너리 (검증용)

    Returns:
        str: 변수가 확장된 경로

    Raises:
        SbkubeError: 변수 구문 오류 또는 참조된 앱이 존재하지 않을 때

    Examples:
        >>> expand_repo_variables(
        ...     "${repos.olm}/deploy/crds.yaml",
        ...     Path(".sbkube/repos"),
        ...     {"olm": {"type": "git", ...}}
        ... )
        ".sbkube/repos/olm/deploy/crds.yaml"
    """
    # 변수 구문 먼저 검증
    validate_variable_syntax(manifest_path)

    pattern = r"\$\{repos\.([^}]+)\}"

    def replace_var(match: re.Match) -> str:
        repo_name = match.group(1)

        # 1. 앱이 존재하는지 확인
        if repo_name not in apps_config:
            raise SbkubeError(
                f"Variable ${{repos.{repo_name}}} references non-existent app '{repo_name}'. "
                f"Available apps: {', '.join(apps_config.keys())}"
            )

        # 2. 해당 앱이 git 타입인지 확인
        app_config = apps_config[repo_name]
        app_type = app_config.get("type")
        if app_type != "git":
            raise SbkubeError(
                f"Variable ${{repos.{repo_name}}} can only reference git-type apps, "
                f"but '{repo_name}' is type '{app_type}'"
            )

        # 3. 리포지토리 경로 반환
        return str(repos_dir / repo_name)

    try:
        expanded = re.sub(pattern, replace_var, manifest_path)
        return expanded
    except SbkubeError:
        raise
    except Exception as e:
        raise SbkubeError(f"Failed to expand variables in path '{manifest_path}': {e}")


def validate_variable_syntax(path: str) -> None:
    """경로의 변수 구문이 올바른지 검증합니다.

    Args:
        path: 검증할 경로

    Raises:
        SbkubeError: 변수 구문이 잘못되었을 때

    Examples:
        >>> validate_variable_syntax("${repos.olm}/file.yaml")  # OK
        >>> validate_variable_syntax("${repos.}/file.yaml")  # Raises SbkubeError
    """
    # ${repos.로 시작하는 변수 찾기
    if "${repos." not in path:
        return

    # 닫히지 않은 중괄호 검사
    # ${로 시작하지만 }로 닫히지 않은 경우
    open_braces = path.count("${")
    close_braces = path.count("}")
    if open_braces > close_braces:
        raise SbkubeError(
            f"Invalid variable syntax: unclosed brace in path '{path}'. "
            f"Expected format: ${{repos.app-name}}"
        )

    # 올바른 형식 검증
    pattern = r"\$\{repos\.[a-zA-Z0-9_-]+\}"
    matches = re.findall(r"\$\{repos\.[^}]*\}", path)

    for match in matches:
        # 앱 이름 추출
        app_name = match[8:-1]  # "${repos." 이후 "}" 이전

        # 앱 이름이 비어있는 경우
        if not app_name:
            raise SbkubeError(f"Empty app name in variable '{match}' in path '{path}'")

        # 올바른 형식인지 검증
        if not re.fullmatch(pattern, match):
            raise SbkubeError(
                f"Invalid variable syntax: '{match}' in path '{path}'. "
                f"Expected format: ${{repos.app-name}} (alphanumeric, hyphens, underscores only)"
            )
