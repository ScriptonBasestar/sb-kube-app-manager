"""설정 파일 상세 검증기 모듈.

config.yaml과 sources.yaml 파일의 구조적/논리적 상세 검증을 수행합니다.
기존 JSON 스키마 검증을 넘어서 실제 배포 가능성까지 검증합니다.
"""

from pathlib import Path
from typing import Any

import yaml

from sbkube.models.validators import ValidatorMixin
from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.validation_system import (
    ValidationCheck,
    ValidationContext,
    ValidationResult,
    ValidationSeverity,
)


class ConfigStructureValidator(ValidationCheck, ValidatorMixin):
    """YAML 구조 및 필수 필드 검증기."""

    def __init__(self) -> None:
        super().__init__(
            name="config_structure",
            description="설정 파일 구조 및 필수 필드 검증",
            category="configuration",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """설정 파일 구조 및 필수 필드를 검증합니다."""
        base_path = Path(context.base_dir)
        config_path = base_path / context.config_dir

        issues = []
        warnings = []

        # config.yaml 구조 검증
        config_file = config_path / "config.yaml"
        if config_file.exists():
            config_issues = await self._validate_config_structure(config_file)
            issues.extend(config_issues)
        else:
            issues.append("config.yaml 파일이 존재하지 않습니다")

        # sources.yaml 구조 검증
        sources_file = config_path / "sources.yaml"
        if sources_file.exists():
            sources_issues = await self._validate_sources_structure(sources_file)
            issues.extend(sources_issues)
        else:
            warnings.append("sources.yaml 파일이 존재하지 않습니다 (선택적 파일)")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"설정 파일 구조 오류가 발견되었습니다 ({len(issues)}개)",
                details="다음 구조적 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="설정 파일의 구조를 올바르게 수정하고 필수 필드를 추가하세요.",
                risk_level="high",
                affected_components=["config.yaml", "sources.yaml"],
            )
        if warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="설정 파일 구조는 정상이나 일부 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="선택적 설정 파일 생성을 고려해보세요.",
                risk_level="low",
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="설정 파일 구조가 올바릅니다",
            details="모든 필수 필드와 구조가 정상적으로 구성되어 있습니다.",
            risk_level="low",
        )

    async def _validate_config_structure(self, config_file: Path) -> list[str]:
        """config.yaml 구조 검증."""
        issues = []

        try:
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            return [f"config.yaml 파일 읽기 실패: {e}"]

        if not isinstance(config, dict):
            return ["config.yaml이 올바른 YAML 객체가 아닙니다"]

        # 필수 필드 검증
        required_fields = ["namespace", "apps"]
        for field in required_fields:
            if field not in config:
                issues.append(f"필수 필드 '{field}'가 누락되었습니다")

        # namespace 검증
        if "namespace" in config:
            namespace = config["namespace"]
            if not isinstance(namespace, str):
                issues.append("namespace는 문자열이어야 합니다")
            elif not self.validate_kubernetes_name(namespace):
                issues.append(
                    f"namespace '{namespace}'는 Kubernetes 이름 규칙에 맞지 않습니다"
                )

        # apps 배열 검증
        if "apps" in config:
            apps = config["apps"]
            if not isinstance(apps, list):
                issues.append("apps는 배열이어야 합니다")
            else:
                for i, app in enumerate(apps):
                    app_issues = self._validate_app_structure(app, i)
                    issues.extend(app_issues)

        # deps 필드 검증 (선택적)
        if "deps" in config:
            deps = config["deps"]
            if not isinstance(deps, list):
                issues.append("deps는 배열이어야 합니다")

        return issues

    def _validate_app_structure(self, app: Any, index: int) -> list[str]:
        """개별 앱 구조 검증."""
        issues = []
        app_prefix = f"apps[{index}]"

        if not isinstance(app, dict):
            return [f"{app_prefix}: 앱 설정은 객체여야 합니다"]

        # 필수 필드 검증
        required_fields = ["name", "type"]
        for field in required_fields:
            if field not in app:
                issues.append(f"{app_prefix}: 필수 필드 '{field}'가 누락되었습니다")

        # name 검증
        if "name" in app:
            name = app["name"]
            if not isinstance(name, str):
                issues.append(f"{app_prefix}: name은 문자열이어야 합니다")
            elif not self.validate_kubernetes_name(name):
                issues.append(
                    f"{app_prefix}: name '{name}'는 Kubernetes 이름 규칙에 맞지 않습니다"
                )

        # type 검증
        if "type" in app:
            app_type = app["type"]
            valid_types = [
                "helm",
                "helm",
                "git",
                "http",
                "yaml",
                "exec",
            ]
            if app_type not in valid_types:
                issues.append(
                    f"{app_prefix}: 지원하지 않는 type '{app_type}'입니다. 지원되는 타입: {', '.join(valid_types)}"
                )

        # specs 검증
        if "specs" in app:
            specs = app["specs"]
            if not isinstance(specs, dict):
                issues.append(f"{app_prefix}: specs는 객체여야 합니다")

        return issues

    async def _validate_sources_structure(self, sources_file: Path) -> list[str]:
        """sources.yaml 구조 검증."""
        issues = []

        try:
            with open(sources_file, encoding="utf-8") as f:
                sources = yaml.safe_load(f)
        except Exception as e:
            return [f"sources.yaml 파일 읽기 실패: {e}"]

        if not isinstance(sources, dict):
            return ["sources.yaml이 올바른 YAML 객체가 아닙니다"]

        # Git 소스 검증
        if "git" in sources:
            git_sources = sources["git"]
            if not isinstance(git_sources, dict):
                issues.append("git 소스는 객체여야 합니다")
            else:
                for repo_name, repo_config in git_sources.items():
                    repo_issues = self._validate_git_source_structure(
                        repo_name, repo_config
                    )
                    issues.extend(repo_issues)

        # Helm 소스 검증
        if "helm" in sources:
            helm_sources = sources["helm"]
            if not isinstance(helm_sources, dict):
                issues.append("helm 소스는 객체여야 합니다")
            else:
                for repo_name, repo_config in helm_sources.items():
                    repo_issues = self._validate_helm_source_structure(
                        repo_name, repo_config
                    )
                    issues.extend(repo_issues)

        return issues

    def _validate_git_source_structure(
        self, repo_name: str, repo_config: Any
    ) -> list[str]:
        """Git 소스 구조 검증."""
        issues = []
        prefix = f"git.{repo_name}"

        if not isinstance(repo_config, dict):
            return [f"{prefix}: Git 저장소 설정은 객체여야 합니다"]

        # 필수 필드 검증
        required_fields = ["url"]
        for field in required_fields:
            if field not in repo_config:
                issues.append(f"{prefix}: 필수 필드 '{field}'가 누락되었습니다")

        # URL 검증
        if "url" in repo_config:
            url = repo_config["url"]
            if not isinstance(url, str):
                issues.append(f"{prefix}: url은 문자열이어야 합니다")
            elif not (
                url.startswith(("http://", "https://", "git@"))
            ):
                issues.append(f"{prefix}: url '{url}'는 올바른 Git URL 형식이 아닙니다")

        return issues

    def _validate_helm_source_structure(
        self, repo_name: str, repo_config: Any
    ) -> list[str]:
        """Helm 소스 구조 검증."""
        issues = []
        prefix = f"helm.{repo_name}"

        if not isinstance(repo_config, dict):
            return [f"{prefix}: Helm 저장소 설정은 객체여야 합니다"]

        # 필수 필드 검증
        required_fields = ["url"]
        for field in required_fields:
            if field not in repo_config:
                issues.append(f"{prefix}: 필수 필드 '{field}'가 누락되었습니다")

        # URL 검증
        if "url" in repo_config:
            url = repo_config["url"]
            if not isinstance(url, str):
                issues.append(f"{prefix}: url은 문자열이어야 합니다")
            elif not (url.startswith(("http://", "https://"))):
                issues.append(
                    f"{prefix}: url '{url}'는 올바른 HTTP/HTTPS URL이어야 합니다"
                )

        return issues


class ConfigContentValidator(ValidationCheck, ValidatorMixin):
    """설정값 유효성 및 참조 무결성 검증기."""

    def __init__(self) -> None:
        super().__init__(
            name="config_content",
            description="설정값 유효성 및 참조 무결성 검증",
            category="configuration",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """설정값 유효성 및 참조 무결성을 검증합니다."""
        base_path = Path(context.base_dir)
        config_path = base_path / context.config_dir

        issues = []
        warnings = []

        # config.yaml 내용 검증
        config_file = config_path / "config.yaml"
        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                content_issues = await self._validate_config_content(config, base_path)
                issues.extend(content_issues)

            except Exception as e:
                issues.append(f"config.yaml 파일 읽기 실패: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"설정값 유효성 오류가 발견되었습니다 ({len(issues)}개)",
                details="다음 유효성 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="설정값을 올바르게 수정하고 참조 무결성을 확인하세요.",
                risk_level="high",
                affected_components=["config.yaml"],
            )
        if warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="설정값은 유효하나 일부 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 설정을 개선해보세요.",
                risk_level="low",
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="모든 설정값이 유효합니다",
            details="설정값 유효성 및 참조 무결성이 정상적으로 확인되었습니다.",
            risk_level="low",
        )

    async def _validate_config_content(
        self, config: dict[str, Any], base_path: Path
    ) -> list[str]:
        """config.yaml 내용 검증."""
        issues = []

        if not isinstance(config, dict):
            return ["설정 파일이 올바른 형식이 아닙니다"]

        # 앱 이름 중복 검증
        if "apps" in config:
            app_names = []
            for app in config["apps"]:
                if isinstance(app, dict) and "name" in app:
                    app_name = app["name"]
                    if app_name in app_names:
                        issues.append(f"앱 이름 '{app_name}'가 중복되었습니다")
                    else:
                        app_names.append(app_name)

        # 앱별 상세 검증
        if "apps" in config and isinstance(config["apps"], list):
            for i, app in enumerate(config["apps"]):
                if isinstance(app, dict):
                    app_issues = await self._validate_app_content(app, i, base_path)
                    issues.extend(app_issues)

        return issues

    async def _validate_app_content(
        self, app: dict[str, Any], index: int, base_path: Path
    ) -> list[str]:
        """개별 앱 내용 검증."""
        issues = []
        app_prefix = f"apps[{index}] ({app.get('name', 'unnamed')})"

        app_type = app.get("type")
        specs = app.get("specs", {})

        if app_type == "helm":
            issues.extend(
                await self._validate_install_helm_content(app_prefix, specs, base_path)
            )
        elif app_type == "helm":
            issues.extend(await self._validate_pull_helm_content(app_prefix, specs))
        elif app_type == "git":
            issues.extend(await self._validate_pull_git_content(app_prefix, specs))
        elif app_type == "http":
            issues.extend(
                await self._validate_copy_app_content(app_prefix, specs, base_path)
            )
        elif app_type == "yaml":
            issues.extend(
                await self._validate_install_yaml_content(app_prefix, specs, base_path)
            )
        elif app_type == "exec":
            issues.extend(await self._validate_exec_content(app_prefix, specs))

        return issues

    async def _validate_install_helm_content(
        self, app_prefix: str, specs: dict[str, Any], base_path: Path
    ) -> list[str]:
        """Helm 앱 내용 검증."""
        issues = []

        # path 필드 검증
        if "path" not in specs:
            issues.append(f"{app_prefix}: helm 타입에는 path 필드가 필요합니다")
        else:
            chart_path = base_path / specs["path"]
            if not chart_path.exists():
                issues.append(
                    f"{app_prefix}: Helm 차트 경로 '{specs['path']}'가 존재하지 않습니다"
                )
            elif not (chart_path / "Chart.yaml").exists():
                issues.append(
                    f"{app_prefix}: '{specs['path']}'는 올바른 Helm 차트 디렉토리가 아닙니다 (Chart.yaml 없음)"
                )

        # values 파일 검증
        if "values" in specs:
            values = specs["values"]
            if isinstance(values, list):
                for value_file in values:
                    value_path = base_path / value_file
                    if not value_path.exists():
                        issues.append(
                            f"{app_prefix}: values 파일 '{value_file}'이 존재하지 않습니다"
                        )

        return issues

    async def _validate_pull_helm_content(
        self, app_prefix: str, specs: dict[str, Any]
    ) -> list[str]:
        """Helm 앱 내용 검증."""
        issues = []

        # 필수 필드 검증
        required_fields = ["repo", "chart"]
        for field in required_fields:
            if field not in specs:
                issues.append(f"{app_prefix}: helm 타입에는 {field} 필드가 필요합니다")

        # 버전 형식 검증
        if "version" in specs:
            version = specs["version"]
            if not isinstance(version, str):
                issues.append(f"{app_prefix}: version은 문자열이어야 합니다")

        return issues

    async def _validate_pull_git_content(
        self, app_prefix: str, specs: dict[str, Any]
    ) -> list[str]:
        """pull-git 앱 내용 검증."""
        issues = []

        # 필수 필드 검증
        if "repo" not in specs:
            issues.append(f"{app_prefix}: pull-git 타입에는 repo 필드가 필요합니다")

        # paths 검증
        if "paths" in specs:
            paths = specs["paths"]
            if not isinstance(paths, list):
                issues.append(f"{app_prefix}: paths는 배열이어야 합니다")
            else:
                for i, path_spec in enumerate(paths):
                    if not isinstance(path_spec, dict):
                        issues.append(f"{app_prefix}: paths[{i}]는 객체여야 합니다")
                    elif "src" not in path_spec or "dest" not in path_spec:
                        issues.append(
                            f"{app_prefix}: paths[{i}]에는 src와 dest 필드가 필요합니다"
                        )

        return issues

    async def _validate_copy_app_content(
        self, app_prefix: str, specs: dict[str, Any], base_path: Path
    ) -> list[str]:
        """copy-app 앱 내용 검증."""
        issues = []

        # paths 검증
        if "paths" not in specs:
            issues.append(f"{app_prefix}: copy-app 타입에는 paths 필드가 필요합니다")
        else:
            paths = specs["paths"]
            if not isinstance(paths, list):
                issues.append(f"{app_prefix}: paths는 배열이어야 합니다")
            else:
                for i, path_spec in enumerate(paths):
                    if not isinstance(path_spec, dict):
                        issues.append(f"{app_prefix}: paths[{i}]는 객체여야 합니다")
                    elif "src" not in path_spec or "dest" not in path_spec:
                        issues.append(
                            f"{app_prefix}: paths[{i}]에는 src와 dest 필드가 필요합니다"
                        )
                    else:
                        src_path = base_path / path_spec["src"]
                        if not src_path.exists():
                            issues.append(
                                f"{app_prefix}: 소스 경로 '{path_spec['src']}'가 존재하지 않습니다"
                            )

        return issues

    async def _validate_install_yaml_content(
        self, app_prefix: str, specs: dict[str, Any], base_path: Path
    ) -> list[str]:
        """Yaml 앱 내용 검증."""
        issues = []

        # actions 검증
        if "actions" not in specs:
            issues.append(f"{app_prefix}: yaml 타입에는 actions 필드가 필요합니다")
        else:
            actions = specs["actions"]
            if not isinstance(actions, list):
                issues.append(f"{app_prefix}: actions는 배열이어야 합니다")
            else:
                for i, action in enumerate(actions):
                    if not isinstance(action, dict):
                        issues.append(f"{app_prefix}: actions[{i}]는 객체여야 합니다")
                    elif "type" not in action:
                        issues.append(
                            f"{app_prefix}: actions[{i}]에는 type 필드가 필요합니다"
                        )
                    elif "path" in action:
                        yaml_path = base_path / action["path"]
                        if not yaml_path.exists():
                            issues.append(
                                f"{app_prefix}: YAML 파일 '{action['path']}'이 존재하지 않습니다"
                            )

        return issues

    async def _validate_exec_content(
        self, app_prefix: str, specs: dict[str, Any]
    ) -> list[str]:
        """Exec 앱 내용 검증."""
        issues = []

        # commands 검증
        if "commands" not in specs:
            issues.append(f"{app_prefix}: exec 타입에는 commands 필드가 필요합니다")
        else:
            commands = specs["commands"]
            if not isinstance(commands, list):
                issues.append(f"{app_prefix}: commands는 배열이어야 합니다")
            elif not commands:
                issues.append(f"{app_prefix}: commands 배열이 비어있습니다")
            else:
                for i, command in enumerate(commands):
                    if not isinstance(command, str):
                        issues.append(
                            f"{app_prefix}: commands[{i}]는 문자열이어야 합니다"
                        )

        return issues


class SourcesIntegrityValidator(ValidationCheck):
    """sources.yaml과 config.yaml 간 참조 검증기."""

    def __init__(self) -> None:
        super().__init__(
            name="sources_integrity",
            description="sources.yaml과 config.yaml 간 참조 무결성 검증",
            category="configuration",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """sources.yaml과 config.yaml 간 참조 무결성을 검증합니다."""
        base_path = Path(context.base_dir)
        config_path = base_path / context.config_dir

        issues = []

        # 파일 존재성 확인
        config_file = config_path / "config.yaml"
        sources_file = config_path / "sources.yaml"

        if not config_file.exists():
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message="config.yaml 파일이 존재하지 않습니다",
                details="참조 무결성 검증을 위해 config.yaml 파일이 필요합니다.",
                risk_level="high",
            )

        if not sources_file.exists():
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.LOW,
                message="sources.yaml 파일이 없어 참조 검증을 생략합니다",
                details="외부 소스를 사용하지 않는 경우 정상적인 상황입니다.",
                risk_level="low",
            )

        try:
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            with open(sources_file, encoding="utf-8") as f:
                sources = yaml.safe_load(f)

            integrity_issues = await self._validate_cross_references(config, sources)
            issues.extend(integrity_issues)

        except Exception as e:
            issues.append(f"파일 읽기 실패: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"참조 무결성 오류가 발견되었습니다 ({len(issues)}개)",
                details="다음 참조 무결성 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="config.yaml과 sources.yaml 간의 참조를 올바르게 수정하세요.",
                risk_level="high",
                affected_components=["config.yaml", "sources.yaml"],
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="모든 참조 무결성이 정상입니다",
            details="config.yaml과 sources.yaml 간의 모든 참조가 올바르게 구성되어 있습니다.",
            risk_level="low",
        )

    async def _validate_cross_references(
        self, config: dict[str, Any], sources: dict[str, Any]
    ) -> list[str]:
        """config.yaml과 sources.yaml 간 교차 참조 검증."""
        issues = []

        if not isinstance(config, dict) or not isinstance(sources, dict):
            return ["설정 파일 형식 오류"]

        # Git 저장소 참조 검증
        git_sources = sources.get("git", {})
        helm_sources = sources.get("helm", {})

        if "apps" in config and isinstance(config["apps"], list):
            for i, app in enumerate(config["apps"]):
                if not isinstance(app, dict):
                    continue

                app_name = app.get("name", f"app_{i}")
                app_type = app.get("type")
                specs = app.get("specs", {})

                if app_type == "git":
                    repo_name = specs.get("repo")
                    if repo_name and repo_name not in git_sources:
                        issues.append(
                            f"앱 '{app_name}': Git 저장소 '{repo_name}'가 sources.yaml에 정의되지 않았습니다"
                        )

                elif app_type == "helm":
                    repo_name = specs.get("repo")
                    if repo_name and repo_name not in helm_sources:
                        issues.append(
                            f"앱 '{app_name}': Helm 저장소 '{repo_name}'가 sources.yaml에 정의되지 않았습니다"
                        )

        # 사용되지 않는 소스 검증 (경고)
        used_git_repos = set()
        used_helm_repos = set()

        if "apps" in config and isinstance(config["apps"], list):
            for app in config["apps"]:
                if isinstance(app, dict):
                    app_type = app.get("type")
                    specs = app.get("specs", {})

                    if app_type == "git" and "repo" in specs:
                        used_git_repos.add(specs["repo"])
                    elif app_type == "helm" and "repo" in specs:
                        used_helm_repos.add(specs["repo"])

        # 사용되지 않는 Git 저장소
        unused_git = set(git_sources.keys()) - used_git_repos
        for repo in unused_git:
            issues.append(
                f"정보: Git 저장소 '{repo}'가 sources.yaml에 정의되었지만 사용되지 않습니다"
            )

        # 사용되지 않는 Helm 저장소
        unused_helm = set(helm_sources.keys()) - used_helm_repos
        for repo in unused_helm:
            issues.append(
                f"정보: Helm 저장소 '{repo}'가 sources.yaml에 정의되었지만 사용되지 않습니다"
            )

        return issues


class CrossReferenceValidator(ValidationCheck):
    """앱 간 의존성 및 충돌 검증기."""

    def __init__(self) -> None:
        super().__init__(
            name="cross_reference",
            description="앱 간 의존성 및 충돌 검증",
            category="configuration",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """앱 간 의존성 및 충돌을 검증합니다."""
        base_path = Path(context.base_dir)
        config_path = base_path / context.config_dir
        config_file = config_path / "config.yaml"

        issues = []

        if not config_file.exists():
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message="config.yaml 파일이 존재하지 않습니다",
                details="앱 간 의존성 검증을 위해 config.yaml 파일이 필요합니다.",
                risk_level="high",
            )

        try:
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            cross_ref_issues = await self._validate_app_dependencies(config)
            issues.extend(cross_ref_issues)

        except Exception as e:
            issues.append(f"설정 파일 읽기 실패: {e}")

        if issues:
            severity = (
                ValidationSeverity.HIGH
                if any("충돌" in issue or "순환" in issue for issue in issues)
                else ValidationSeverity.MEDIUM
            )
            return self.create_validation_result(
                level=(
                    DiagnosticLevel.ERROR
                    if severity == ValidationSeverity.HIGH
                    else DiagnosticLevel.WARNING
                ),
                severity=severity,
                message=f"앱 간 의존성/충돌 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 의존성/충돌 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="앱 간 의존성을 정리하고 충돌을 해결하세요.",
                risk_level="high" if severity == ValidationSeverity.HIGH else "medium",
                affected_components=["config.yaml"],
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="앱 간 의존성 및 충돌이 없습니다",
            details="모든 앱이 올바르게 구성되어 있으며 의존성 충돌이 발견되지 않았습니다.",
            risk_level="low",
        )

    async def _validate_app_dependencies(self, config: dict[str, Any]) -> list[str]:
        """앱 간 의존성 및 충돌 검증."""
        issues = []

        if not isinstance(config, dict) or "apps" not in config:
            return ["설정 파일에 앱 정보가 없습니다"]

        apps = config["apps"]
        if not isinstance(apps, list):
            return ["apps는 배열이어야 합니다"]

        # 앱 정보 수집
        app_info = {}

        for i, app in enumerate(apps):
            if not isinstance(app, dict):
                continue

            app_name = app.get("name", f"app_{i}")
            app_type = app.get("type")
            specs = app.get("specs", {})

            app_info[app_name] = {"type": app_type, "specs": specs, "index": i}

            # 포트 사용 검증 (Helm 차트의 경우)
            if app_type in ["helm", "helm"]:
                # 여기서는 기본적인 검증만 수행 (실제로는 values 파일을 파싱해야 함)
                if "values" in specs:
                    # values 파일에서 포트 정보 추출은 복잡하므로 기본 검증만 수행
                    pass

        # 중복 경로 검증
        dest_paths = {}
        for app_name, info in app_info.items():
            app_type = info["type"]
            specs = info["specs"]

            if app_type in ["helm", "git"]:
                dest = specs.get("dest")
                if dest:
                    if dest in dest_paths:
                        issues.append(
                            f"앱 '{app_name}'과 '{dest_paths[dest]}'가 같은 대상 경로 '{dest}'를 사용합니다"
                        )
                    else:
                        dest_paths[dest] = app_name

            if app_type == "http" and "paths" in specs:
                for path_spec in specs["paths"]:
                    if isinstance(path_spec, dict) and "dest" in path_spec:
                        dest = path_spec["dest"]
                        if dest in dest_paths:
                            issues.append(
                                f"앱 '{app_name}'과 '{dest_paths[dest]}'가 같은 대상 경로 '{dest}'를 사용합니다"
                            )
                        else:
                            dest_paths[dest] = app_name

        # 순서 의존성 검증
        issues.extend(self._validate_execution_order(app_info))

        return issues

    def _validate_execution_order(
        self, app_info: dict[str, dict[str, Any]]
    ) -> list[str]:
        """실행 순서 의존성 검증."""
        issues = []

        # 타입별 실행 순서 규칙
        # prepare -> build -> deploy 순서로 실행되어야 함
        prepare_types = ["helm", "git"]
        build_types = ["http"]
        deploy_types = ["helm", "yaml", "exec"]

        phases = {}
        for app_name, info in app_info.items():
            app_type = info["type"]
            if app_type in prepare_types:
                phases[app_name] = ("prepare", info["index"])
            elif app_type in build_types:
                phases[app_name] = ("build", info["index"])
            elif app_type in deploy_types:
                phases[app_name] = ("deploy", info["index"])
            else:
                phases[app_name] = ("unknown", info["index"])

        # 순서 검증
        phase_order = ["prepare", "build", "deploy"]
        last_index_by_phase = {"prepare": -1, "build": -1, "deploy": -1}

        for app_name, (phase, index) in phases.items():
            if phase in phase_order:
                phase_idx = phase_order.index(phase)

                # 이전 단계들이 모두 끝났는지 확인
                for prev_phase_idx in range(phase_idx):
                    prev_phase = phase_order[prev_phase_idx]
                    if last_index_by_phase[prev_phase] > index:
                        issues.append(
                            f"앱 '{app_name}' ({phase})가 이후의 {prev_phase} 단계 앱보다 먼저 정의되어 실행 순서에 문제가 있을 수 있습니다"
                        )

                last_index_by_phase[phase] = max(last_index_by_phase[phase], index)

        return issues
