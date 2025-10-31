"""
Helm 차트 및 의존성 검증기 모듈

Helm 차트 유효성, values 파일 정합성, 의존성 해결 가능성을 검증합니다.
네트워크 연결성 및 외부 의존성도 함께 검증하여 안전한 배포를 보장합니다.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
import yaml

from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.logger import logger
from sbkube.utils.validation_system import (
    ValidationCheck,
    ValidationContext,
    ValidationResult,
    ValidationSeverity,
)


class HelmChartValidator(ValidationCheck):
    """Helm 차트 구조 및 템플릿 유효성 검증기"""

    def __init__(self):
        super().__init__(
            name="helm_chart",
            description="Helm 차트 구조 및 템플릿 유효성 검증",
            category="dependencies",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """Helm 차트 구조 및 템플릿 유효성을 검증합니다"""
        issues = []
        warnings = []

        try:
            # Helm 설치 확인
            helm_check = await self._check_helm_installation()
            if helm_check:
                issues.append(helm_check)
                return self.create_validation_result(
                    level=DiagnosticLevel.ERROR,
                    severity=ValidationSeverity.CRITICAL,
                    message="Helm이 설치되지 않아 차트 검증을 할 수 없습니다",
                    details=helm_check,
                    recommendation="Helm을 설치한 후 다시 검증을 실행하세요.",
                    fix_command="curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                    fix_description="Helm 3 최신 버전 설치",
                    risk_level="critical",
                )

            # 설정에서 Helm 차트 앱들 찾기
            helm_apps = await self._find_helm_apps(context)

            if not helm_apps:
                return self.create_validation_result(
                    level=DiagnosticLevel.INFO,
                    severity=ValidationSeverity.INFO,
                    message="Helm 차트를 사용하는 앱이 없습니다",
                    details="검증할 Helm 차트가 없어 해당 검증을 건너뜁니다.",
                    risk_level="low",
                )

            # 각 Helm 앱 검증
            for app_name, app_config in helm_apps:
                app_issues = await self._validate_helm_app(
                    app_name, app_config, context
                )
                issues.extend(app_issues)

        except Exception as e:
            issues.append(f"Helm 차트 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"Helm 차트 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 Helm 차트 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="Helm 차트 구조와 템플릿을 확인하고 수정하세요.",
                risk_level="high",
                affected_components=["helm-charts", "templates"],
            )
        elif warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="Helm 차트 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 차트 품질을 개선해보세요.",
                risk_level="medium",
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="모든 Helm 차트가 유효합니다",
                details="차트 구조, 템플릿, 의존성이 모두 정상적으로 확인되었습니다.",
                risk_level="low",
            )

    async def _check_helm_installation(self) -> str | None:
        """Helm 설치 상태 확인"""
        try:
            result = subprocess.run(
                ["helm", "version", "--short"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return "Helm이 설치되지 않았거나 실행할 수 없습니다"

            # 버전 확인
            version_output = result.stdout.strip()
            if "v2." in version_output:
                return "Helm v2가 설치되어 있습니다. Helm v3 사용을 강력히 권장합니다"

            return None

        except FileNotFoundError:
            return "Helm 명령어를 찾을 수 없습니다"
        except subprocess.TimeoutExpired:
            return "Helm 버전 확인 시간 초과"
        except Exception as e:
            return f"Helm 설치 확인 실패: {e}"

    async def _find_helm_apps(
        self, context: ValidationContext
    ) -> list[tuple[str, dict[str, Any]]]:
        """설정에서 Helm 앱들 찾기"""
        helm_apps = []

        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                apps = config.get("apps", [])
                for app in apps:
                    if isinstance(app, dict):
                        app_type = app.get("type")
                        if app_type in ["helm", "helm"]:
                            app_name = app.get("name", "unknown")
                            helm_apps.append((app_name, app))

        except Exception as e:
            logger.debug(f"Helm 앱 찾기 중 오류: {e}")

        return helm_apps

    async def _validate_helm_app(
        self, app_name: str, app_config: dict[str, Any], context: ValidationContext
    ) -> list[str]:
        """개별 Helm 앱 검증"""
        issues = []
        app_type = app_config.get("type")
        specs = app_config.get("specs", {})

        if app_type == "helm":
            issues.extend(
                await self._validate_install_helm_chart(app_name, specs, context)
            )
        elif app_type == "helm":
            issues.extend(
                await self._validate_pull_helm_chart(app_name, specs, context)
            )

        return issues

    async def _validate_install_helm_chart(
        self, app_name: str, specs: dict[str, Any], context: ValidationContext
    ) -> list[str]:
        """helm 타입 차트 검증"""
        issues = []
        base_path = Path(context.base_dir)

        # 차트 경로 확인
        chart_path_str = specs.get("path")
        if not chart_path_str:
            return [f"앱 '{app_name}': 차트 경로가 지정되지 않았습니다"]

        chart_path = base_path / chart_path_str
        if not chart_path.exists():
            return [
                f"앱 '{app_name}': 차트 경로 '{chart_path_str}'가 존재하지 않습니다"
            ]

        # Chart.yaml 확인
        chart_yaml = chart_path / "Chart.yaml"
        if not chart_yaml.exists():
            issues.append(f"앱 '{app_name}': Chart.yaml 파일이 없습니다")
        else:
            chart_issues = await self._validate_chart_yaml(app_name, chart_yaml)
            issues.extend(chart_issues)

        # 템플릿 디렉토리 확인
        templates_dir = chart_path / "templates"
        if not templates_dir.exists():
            issues.append(f"앱 '{app_name}': templates 디렉토리가 없습니다")
        else:
            template_issues = await self._validate_templates(app_name, templates_dir)
            issues.extend(template_issues)

        # values 파일 확인
        values_files = specs.get("values", [])
        if values_files:
            for values_file in values_files:
                values_path = base_path / values_file
                if not values_path.exists():
                    issues.append(
                        f"앱 '{app_name}': values 파일 '{values_file}'이 존재하지 않습니다"
                    )
                else:
                    values_issues = await self._validate_values_file(
                        app_name, values_path
                    )
                    issues.extend(values_issues)

        # helm template 시뮬레이션
        if not issues:  # 기본 구조가 정상인 경우에만
            template_issues = await self._test_helm_template(
                app_name, chart_path, specs, base_path
            )
            issues.extend(template_issues)

        return issues

    async def _validate_pull_helm_chart(
        self, app_name: str, specs: dict[str, Any], context: ValidationContext
    ) -> list[str]:
        """helm 타입 차트 검증"""
        issues = []

        # 필수 필드 확인
        repo = specs.get("repo")
        chart = specs.get("chart")

        if not repo:
            issues.append(f"앱 '{app_name}': 저장소 이름이 지정되지 않았습니다")

        if not chart:
            issues.append(f"앱 '{app_name}': 차트 이름이 지정되지 않았습니다")

        if issues:
            return issues

        # 저장소 접근성 확인
        repo_issues = await self._validate_helm_repository(app_name, repo, context)
        issues.extend(repo_issues)

        # 차트 존재성 확인
        chart_issues = await self._validate_remote_chart(
            app_name, repo, chart, specs.get("version")
        )
        issues.extend(chart_issues)

        return issues

    async def _validate_chart_yaml(self, app_name: str, chart_yaml: Path) -> list[str]:
        """Chart.yaml 파일 검증"""
        issues = []

        try:
            with open(chart_yaml, encoding="utf-8") as f:
                chart_data = yaml.safe_load(f)

            if not isinstance(chart_data, dict):
                return [f"앱 '{app_name}': Chart.yaml이 올바른 YAML 객체가 아닙니다"]

            # 필수 필드 확인
            required_fields = ["name", "version"]
            for field in required_fields:
                if field not in chart_data:
                    issues.append(
                        f"앱 '{app_name}': Chart.yaml에 필수 필드 '{field}'가 없습니다"
                    )

            # API 버전 확인
            api_version = chart_data.get("apiVersion", "v1")
            if api_version not in ["v1", "v2"]:
                issues.append(
                    f"앱 '{app_name}': 지원하지 않는 Chart API 버전 '{api_version}'입니다"
                )

            # 의존성 확인
            dependencies = chart_data.get("dependencies", [])
            if dependencies:
                for i, dep in enumerate(dependencies):
                    if not isinstance(dep, dict):
                        issues.append(
                            f"앱 '{app_name}': Chart.yaml dependencies[{i}]가 올바른 객체가 아닙니다"
                        )
                        continue

                    # 의존성 필수 필드
                    dep_required = ["name", "version", "repository"]
                    for dep_field in dep_required:
                        if dep_field not in dep:
                            issues.append(
                                f"앱 '{app_name}': Chart.yaml dependencies[{i}]에 필수 필드 '{dep_field}'가 없습니다"
                            )

        except yaml.YAMLError as e:
            issues.append(f"앱 '{app_name}': Chart.yaml YAML 파싱 오류 - {e}")
        except Exception as e:
            issues.append(f"앱 '{app_name}': Chart.yaml 읽기 실패 - {e}")

        return issues

    async def _validate_templates(
        self, app_name: str, templates_dir: Path
    ) -> list[str]:
        """템플릿 디렉토리 검증"""
        issues = []

        try:
            template_files = list(templates_dir.glob("*.yaml")) + list(
                templates_dir.glob("*.yml")
            )

            if not template_files:
                issues.append(
                    f"앱 '{app_name}': templates 디렉토리에 템플릿 파일이 없습니다"
                )
            else:
                # 각 템플릿 파일의 기본 YAML 문법 확인
                for template_file in template_files:
                    if template_file.name.startswith("_"):
                        continue  # helper 템플릿은 건너뛰기

                    try:
                        with open(template_file, encoding="utf-8") as f:
                            content = f.read()

                        # 기본적인 Go 템플릿 문법 확인
                        if "{{" in content and "}}" not in content:
                            issues.append(
                                f"앱 '{app_name}': 템플릿 파일 '{template_file.name}'에 미완성된 템플릿 구문이 있습니다"
                            )

                        # 닫히지 않은 브래킷 확인
                        open_count = content.count("{{")
                        close_count = content.count("}}")
                        if open_count != close_count:
                            issues.append(
                                f"앱 '{app_name}': 템플릿 파일 '{template_file.name}'에 불균형한 템플릿 브래킷이 있습니다"
                            )

                    except Exception as e:
                        issues.append(
                            f"앱 '{app_name}': 템플릿 파일 '{template_file.name}' 읽기 실패 - {e}"
                        )

        except Exception as e:
            issues.append(f"앱 '{app_name}': templates 디렉토리 검증 실패 - {e}")

        return issues

    async def _validate_values_file(
        self, app_name: str, values_path: Path
    ) -> list[str]:
        """values 파일 검증"""
        issues = []

        try:
            with open(values_path, encoding="utf-8") as f:
                values_data = yaml.safe_load(f)

            # YAML 파싱이 성공하면 기본적인 구조 확인
            if values_data is not None and not isinstance(values_data, dict):
                issues.append(
                    f"앱 '{app_name}': values 파일 '{values_path.name}'이 올바른 YAML 객체가 아닙니다"
                )

        except yaml.YAMLError as e:
            issues.append(
                f"앱 '{app_name}': values 파일 '{values_path.name}' YAML 파싱 오류 - {e}"
            )
        except Exception as e:
            issues.append(
                f"앱 '{app_name}': values 파일 '{values_path.name}' 읽기 실패 - {e}"
            )

        return issues

    async def _test_helm_template(
        self, app_name: str, chart_path: Path, specs: dict[str, Any], base_path: Path
    ) -> list[str]:
        """helm template 명령어로 렌더링 테스트"""
        issues = []

        try:
            cmd = ["helm", "template", str(chart_path)]

            # values 파일 추가
            values_files = specs.get("values", [])
            for values_file in values_files:
                values_path = base_path / values_file
                if values_path.exists():
                    cmd.extend(["-f", str(values_path)])

            # 임시 네임스페이스 사용
            cmd.extend(["--namespace", "validation-test"])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                issues.append(f"앱 '{app_name}': Helm 템플릿 렌더링 실패 - {error_msg}")
            else:
                # 렌더링된 YAML의 기본 유효성 확인
                try:
                    rendered_content = result.stdout
                    if rendered_content.strip():
                        # YAML 문서들을 분리하여 각각 파싱
                        yaml_docs = rendered_content.split("---")
                        for i, doc in enumerate(yaml_docs):
                            doc = doc.strip()
                            if doc:
                                yaml.safe_load(doc)
                except yaml.YAMLError as e:
                    issues.append(
                        f"앱 '{app_name}': 렌더링된 YAML이 유효하지 않습니다 - {e}"
                    )

        except subprocess.TimeoutExpired:
            issues.append(f"앱 '{app_name}': Helm 템플릿 렌더링 시간 초과")
        except FileNotFoundError:
            issues.append(f"앱 '{app_name}': helm 명령어를 찾을 수 없습니다")
        except Exception as e:
            issues.append(f"앱 '{app_name}': Helm 템플릿 테스트 실패 - {e}")

        return issues

    async def _validate_helm_repository(
        self, app_name: str, repo_name: str, context: ValidationContext
    ) -> list[str]:
        """Helm 저장소 검증"""
        issues = []

        try:
            # sources.yaml에서 저장소 정보 확인
            base_path = Path(context.base_dir)
            sources_path = base_path / context.config_dir / "sources.yaml"

            if not sources_path.exists():
                return [
                    f"앱 '{app_name}': sources.yaml 파일이 없어 저장소 '{repo_name}' 정보를 확인할 수 없습니다"
                ]

            with open(sources_path, encoding="utf-8") as f:
                sources = yaml.safe_load(f)

            helm_sources = sources.get("helm", {})
            if repo_name not in helm_sources:
                return [
                    f"앱 '{app_name}': 저장소 '{repo_name}'이 sources.yaml에 정의되지 않았습니다"
                ]

            repo_config = helm_sources[repo_name]
            repo_url = repo_config.get("url")

            if not repo_url:
                return [
                    f"앱 '{app_name}': 저장소 '{repo_name}'의 URL이 정의되지 않았습니다"
                ]

            # 저장소 URL 접근성 확인
            try:
                response = requests.head(repo_url, timeout=10, allow_redirects=True)
                if response.status_code >= 400:
                    issues.append(
                        f"앱 '{app_name}': 저장소 '{repo_name}' ({repo_url}) 접근 실패 - HTTP {response.status_code}"
                    )
            except requests.exceptions.RequestException as e:
                issues.append(
                    f"앱 '{app_name}': 저장소 '{repo_name}' ({repo_url}) 연결 실패 - {e}"
                )

        except Exception as e:
            issues.append(f"앱 '{app_name}': 저장소 검증 실패 - {e}")

        return issues

    async def _validate_remote_chart(
        self, app_name: str, repo_name: str, chart_name: str, version: str | None
    ) -> list[str]:
        """원격 차트 존재성 확인"""
        issues = []

        try:
            # helm search로 차트 존재성 확인
            cmd = ["helm", "search", "repo", f"{repo_name}/{chart_name}"]
            if version:
                cmd.extend(["--version", version])

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode != 0:
                issues.append(
                    f"앱 '{app_name}': 차트 '{repo_name}/{chart_name}' 검색 실패"
                )
            else:
                output = result.stdout.strip()
                if not output or "No results found" in output:
                    version_info = f" (버전: {version})" if version else ""
                    issues.append(
                        f"앱 '{app_name}': 차트 '{repo_name}/{chart_name}'{version_info}을 찾을 수 없습니다"
                    )

        except subprocess.TimeoutExpired:
            issues.append(f"앱 '{app_name}': 차트 검색 시간 초과")
        except Exception as e:
            issues.append(f"앱 '{app_name}': 원격 차트 검증 실패 - {e}")

        return issues


class ValuesCompatibilityValidator(ValidationCheck):
    """values 파일과 차트 호환성 검증기"""

    def __init__(self):
        super().__init__(
            name="values_compatibility",
            description="values 파일과 차트 호환성 검증",
            category="dependencies",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """values 파일과 차트 호환성을 검증합니다"""
        issues = []
        warnings = []

        try:
            # Helm 앱들 찾기
            helm_apps = await self._find_helm_apps(context)

            if not helm_apps:
                return self.create_validation_result(
                    level=DiagnosticLevel.INFO,
                    severity=ValidationSeverity.INFO,
                    message="검증할 Helm values 파일이 없습니다",
                    details="Helm 차트를 사용하는 앱이 없어 values 호환성 검증을 건너뜁니다.",
                    risk_level="low",
                )

            # 각 앱의 values 호환성 검증
            for app_name, app_config in helm_apps:
                app_issues = await self._validate_values_compatibility(
                    app_name, app_config, context
                )
                issues.extend(app_issues)

        except Exception as e:
            issues.append(f"values 호환성 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"values 파일 호환성 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 values 호환성 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="values 파일의 설정을 차트의 템플릿과 호환되도록 수정하세요.",
                risk_level="high",
                affected_components=["values-files", "chart-templates"],
            )
        elif warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="values 파일 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 values 설정을 개선해보세요.",
                risk_level="medium",
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="모든 values 파일이 호환됩니다",
                details="values 파일과 차트 템플릿 간의 호환성이 정상적으로 확인되었습니다.",
                risk_level="low",
            )

    async def _find_helm_apps(
        self, context: ValidationContext
    ) -> list[tuple[str, dict[str, Any]]]:
        """설정에서 Helm 앱들 찾기"""
        helm_apps = []

        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                apps = config.get("apps", [])
                for app in apps:
                    if isinstance(app, dict):
                        app_type = app.get("type")
                        if app_type == "helm":  # values 파일이 있는 경우만
                            app_name = app.get("name", "unknown")
                            helm_apps.append((app_name, app))

        except Exception as e:
            logger.debug(f"Helm 앱 찾기 중 오류: {e}")

        return helm_apps

    async def _validate_values_compatibility(
        self, app_name: str, app_config: dict[str, Any], context: ValidationContext
    ) -> list[str]:
        """개별 앱의 values 호환성 검증"""
        issues = []
        base_path = Path(context.base_dir)
        specs = app_config.get("specs", {})

        # 차트 경로 확인
        chart_path_str = specs.get("path")
        if not chart_path_str:
            return [f"앱 '{app_name}': 차트 경로가 지정되지 않았습니다"]

        chart_path = base_path / chart_path_str
        if not chart_path.exists():
            return [
                f"앱 '{app_name}': 차트 경로 '{chart_path_str}'가 존재하지 않습니다"
            ]

        # values 파일들 확인
        values_files = specs.get("values", [])
        if not values_files:
            return []  # values 파일이 없으면 기본값 사용으로 정상

        # 차트의 기본 values.yaml 읽기
        default_values = {}
        default_values_path = chart_path / "values.yaml"
        if default_values_path.exists():
            try:
                with open(default_values_path, encoding="utf-8") as f:
                    default_values = yaml.safe_load(f) or {}
            except Exception as e:
                issues.append(
                    f"앱 '{app_name}': 차트의 기본 values.yaml 읽기 실패 - {e}"
                )
                return issues

        # 각 values 파일 검증
        for values_file in values_files:
            values_path = base_path / values_file
            if not values_path.exists():
                issues.append(
                    f"앱 '{app_name}': values 파일 '{values_file}'이 존재하지 않습니다"
                )
                continue

            try:
                with open(values_path, encoding="utf-8") as f:
                    custom_values = yaml.safe_load(f) or {}

                # values 구조 호환성 확인
                compatibility_issues = self._check_values_structure_compatibility(
                    app_name, values_file, default_values, custom_values
                )
                issues.extend(compatibility_issues)

                # 템플릿과의 실제 호환성 테스트
                template_issues = await self._test_values_with_templates(
                    app_name, chart_path, values_path
                )
                issues.extend(template_issues)

            except yaml.YAMLError as e:
                issues.append(
                    f"앱 '{app_name}': values 파일 '{values_file}' YAML 파싱 오류 - {e}"
                )
            except Exception as e:
                issues.append(
                    f"앱 '{app_name}': values 파일 '{values_file}' 검증 실패 - {e}"
                )

        return issues

    def _check_values_structure_compatibility(
        self,
        app_name: str,
        values_file: str,
        default_values: dict[str, Any],
        custom_values: dict[str, Any],
    ) -> list[str]:
        """values 구조 호환성 확인"""
        issues = []

        if not isinstance(custom_values, dict):
            return [
                f"앱 '{app_name}': values 파일 '{values_file}'이 올바른 YAML 객체가 아닙니다"
            ]

        # 깊은 구조 비교는 복잡하므로 기본적인 타입 호환성만 확인
        for key, custom_value in custom_values.items():
            if key in default_values:
                default_value = default_values[key]

                # 타입 호환성 확인 (기본값이 dict인데 문자열로 오버라이드하는 경우 등)
                if isinstance(default_value, dict) and not isinstance(
                    custom_value, dict
                ):
                    issues.append(
                        f"앱 '{app_name}': values 파일 '{values_file}'의 '{key}' 필드 타입이 호환되지 않습니다 (기본값: 객체, 설정값: {type(custom_value).__name__})"
                    )
                elif isinstance(default_value, list) and not isinstance(
                    custom_value, list
                ):
                    issues.append(
                        f"앱 '{app_name}': values 파일 '{values_file}'의 '{key}' 필드 타입이 호환되지 않습니다 (기본값: 배열, 설정값: {type(custom_value).__name__})"
                    )

        return issues

    async def _test_values_with_templates(
        self, app_name: str, chart_path: Path, values_path: Path
    ) -> list[str]:
        """values 파일로 템플릿 렌더링 테스트"""
        issues = []

        try:
            cmd = [
                "helm",
                "template",
                str(chart_path),
                "-f",
                str(values_path),
                "--namespace",
                "validation-test",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                issues.append(
                    f"앱 '{app_name}': values 파일 '{values_path.name}'로 템플릿 렌더링 실패 - {error_msg}"
                )

        except subprocess.TimeoutExpired:
            issues.append(
                f"앱 '{app_name}': values 파일 '{values_path.name}' 템플릿 렌더링 시간 초과"
            )
        except Exception as e:
            issues.append(
                f"앱 '{app_name}': values 파일 '{values_path.name}' 호환성 테스트 실패 - {e}"
            )

        return issues


class DependencyResolutionValidator(ValidationCheck):
    """차트 의존성 해결 가능성 검증기"""

    def __init__(self):
        super().__init__(
            name="dependency_resolution",
            description="차트 의존성 해결 가능성 검증",
            category="dependencies",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """차트 의존성 해결 가능성을 검증합니다"""
        issues = []
        warnings = []

        try:
            # Helm 앱들 찾기
            helm_apps = await self._find_helm_apps(context)

            if not helm_apps:
                return self.create_validation_result(
                    level=DiagnosticLevel.INFO,
                    severity=ValidationSeverity.INFO,
                    message="검증할 Helm 차트 의존성이 없습니다",
                    details="의존성이 있는 Helm 차트가 없어 의존성 해결 검증을 건너뜁니다.",
                    risk_level="low",
                )

            # 각 앱의 의존성 검증
            for app_name, app_config in helm_apps:
                app_issues = await self._validate_chart_dependencies(
                    app_name, app_config, context
                )
                issues.extend(app_issues)

        except Exception as e:
            issues.append(f"의존성 해결 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"차트 의존성 해결 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 의존성 해결 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="Chart.yaml의 의존성 설정을 확인하고 저장소 접근성을 점검하세요.",
                risk_level="high",
                affected_components=["chart-dependencies", "repositories"],
            )
        elif warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="차트 의존성 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 의존성 관리를 개선해보세요.",
                risk_level="medium",
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="모든 차트 의존성이 해결 가능합니다",
                details="차트 의존성이 정상적으로 해결되며 배포에 문제가 없습니다.",
                risk_level="low",
            )

    async def _find_helm_apps(
        self, context: ValidationContext
    ) -> list[tuple[str, dict[str, Any]]]:
        """설정에서 Helm 앱들 찾기"""
        helm_apps = []

        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                apps = config.get("apps", [])
                for app in apps:
                    if isinstance(app, dict):
                        app_type = app.get("type")
                        if app_type == "helm":  # 로컬 차트만 의존성 확인
                            app_name = app.get("name", "unknown")
                            helm_apps.append((app_name, app))

        except Exception as e:
            logger.debug(f"Helm 앱 찾기 중 오류: {e}")

        return helm_apps

    async def _validate_chart_dependencies(
        self, app_name: str, app_config: dict[str, Any], context: ValidationContext
    ) -> list[str]:
        """개별 차트의 의존성 검증"""
        issues = []
        base_path = Path(context.base_dir)
        specs = app_config.get("specs", {})

        # 차트 경로 확인
        chart_path_str = specs.get("path")
        if not chart_path_str:
            return []

        chart_path = base_path / chart_path_str
        if not chart_path.exists():
            return []

        # Chart.yaml에서 의존성 확인
        chart_yaml = chart_path / "Chart.yaml"
        if not chart_yaml.exists():
            return []

        try:
            with open(chart_yaml, encoding="utf-8") as f:
                chart_data = yaml.safe_load(f)

            dependencies = chart_data.get("dependencies", [])
            if not dependencies:
                return []  # 의존성이 없으면 정상

            # 각 의존성 검증
            for i, dep in enumerate(dependencies):
                if not isinstance(dep, dict):
                    continue

                dep_issues = await self._validate_single_dependency(
                    app_name, i, dep, context
                )
                issues.extend(dep_issues)

            # helm dependency update 시뮬레이션
            if not issues:  # 기본 의존성 정보가 정상인 경우
                update_issues = await self._test_dependency_update(app_name, chart_path)
                issues.extend(update_issues)

        except Exception as e:
            issues.append(f"앱 '{app_name}': 의존성 검증 실패 - {e}")

        return issues

    async def _validate_single_dependency(
        self,
        app_name: str,
        dep_index: int,
        dependency: dict[str, Any],
        context: ValidationContext,
    ) -> list[str]:
        """단일 의존성 검증"""
        issues = []

        dep_name = dependency.get("name", f"dependency_{dep_index}")
        dep_version = dependency.get("version")
        dep_repository = dependency.get("repository")

        # 필수 필드 확인
        if not dep_repository:
            issues.append(
                f"앱 '{app_name}': 의존성 '{dep_name}'에 저장소가 지정되지 않았습니다"
            )
            return issues

        if not dep_version:
            issues.append(
                f"앱 '{app_name}': 의존성 '{dep_name}'에 버전이 지정되지 않았습니다"
            )

        # 저장소 접근성 확인
        try:
            if dep_repository.startswith("http://") or dep_repository.startswith(
                "https://"
            ):
                # HTTP 저장소 접근성 확인
                response = requests.head(
                    dep_repository, timeout=10, allow_redirects=True
                )
                if response.status_code >= 400:
                    issues.append(
                        f"앱 '{app_name}': 의존성 '{dep_name}' 저장소 '{dep_repository}' 접근 실패 - HTTP {response.status_code}"
                    )
            elif dep_repository.startswith("file://"):
                # 로컬 파일 저장소 확인
                local_path = dep_repository[7:]  # file:// 제거
                if not Path(local_path).exists():
                    issues.append(
                        f"앱 '{app_name}': 의존성 '{dep_name}' 로컬 저장소 '{local_path}'가 존재하지 않습니다"
                    )
            # alias나 @ 형태의 저장소는 helm repo list에서 확인해야 하므로 일단 건너뛰기

        except requests.exceptions.RequestException as e:
            issues.append(
                f"앱 '{app_name}': 의존성 '{dep_name}' 저장소 연결 실패 - {e}"
            )
        except Exception as e:
            logger.debug(f"의존성 저장소 확인 중 오류: {e}")

        return issues

    async def _test_dependency_update(
        self, app_name: str, chart_path: Path
    ) -> list[str]:
        """helm dependency update 시뮬레이션"""
        issues = []

        try:
            # 임시 디렉토리에 차트 복사하여 테스트
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_chart_path = Path(temp_dir) / "chart"

                # 차트 복사 (간단한 파일들만)
                os.makedirs(temp_chart_path, exist_ok=True)

                # Chart.yaml만 복사해서 의존성 해결 테스트
                original_chart_yaml = chart_path / "Chart.yaml"
                temp_chart_yaml = temp_chart_path / "Chart.yaml"

                if original_chart_yaml.exists():
                    import shutil

                    shutil.copy2(original_chart_yaml, temp_chart_yaml)

                    # helm dependency update 실행
                    result = subprocess.run(
                        ["helm", "dependency", "update", str(temp_chart_path)],
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )

                    if result.returncode != 0:
                        error_msg = result.stderr.strip()
                        issues.append(
                            f"앱 '{app_name}': 의존성 해결 실패 - {error_msg}"
                        )

        except subprocess.TimeoutExpired:
            issues.append(f"앱 '{app_name}': 의존성 해결 시간 초과")
        except Exception as e:
            issues.append(f"앱 '{app_name}': 의존성 해결 테스트 실패 - {e}")

        return issues


class NetworkConnectivityValidator(ValidationCheck):
    """외부 저장소 및 서비스 연결성 검증기"""

    def __init__(self):
        super().__init__(
            name="network_connectivity",
            description="외부 저장소 및 서비스 연결성 검증",
            category="dependencies",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """외부 저장소 및 서비스 연결성을 검증합니다"""
        issues = []
        warnings = []

        try:
            # 설정된 외부 저장소들 확인
            repositories = await self._get_configured_repositories(context)

            if not repositories:
                return self.create_validation_result(
                    level=DiagnosticLevel.INFO,
                    severity=ValidationSeverity.INFO,
                    message="검증할 외부 저장소가 없습니다",
                    details="외부 저장소를 사용하지 않아 연결성 검증을 건너뜁니다.",
                    risk_level="low",
                )

            # 각 저장소 연결성 테스트
            for repo_type, repo_name, repo_url in repositories:
                repo_issues = await self._test_repository_connectivity(
                    repo_type, repo_name, repo_url
                )
                issues.extend(repo_issues)

            # 필수 서비스 연결성 테스트
            service_issues = await self._test_essential_services()
            warnings.extend(service_issues)

        except Exception as e:
            issues.append(f"네트워크 연결성 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"외부 저장소 연결 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 연결성 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="네트워크 설정, 방화벽, 프록시 설정을 확인하세요.",
                risk_level="high",
                affected_components=["external-repositories", "network"],
            )
        elif warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="네트워크 연결성 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 네트워크 안정성을 개선해보세요.",
                risk_level="medium",
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="모든 외부 저장소 연결이 정상입니다",
                details="설정된 모든 외부 저장소와 서비스에 정상적으로 연결됩니다.",
                risk_level="low",
            )

    async def _get_configured_repositories(
        self, context: ValidationContext
    ) -> list[tuple[str, str, str]]:
        """설정된 저장소 목록 추출"""
        repositories = []

        try:
            base_path = Path(context.base_dir)
            sources_path = base_path / context.config_dir / "sources.yaml"

            if sources_path.exists():
                with open(sources_path, encoding="utf-8") as f:
                    sources = yaml.safe_load(f)

                # Git 저장소
                git_sources = sources.get("git", {})
                for repo_name, repo_config in git_sources.items():
                    repo_url = repo_config.get("url")
                    if repo_url:
                        repositories.append(("git", repo_name, repo_url))

                # Helm 저장소
                helm_sources = sources.get("helm", {})
                for repo_name, repo_config in helm_sources.items():
                    repo_url = repo_config.get("url")
                    if repo_url:
                        repositories.append(("helm", repo_name, repo_url))

        except Exception as e:
            logger.debug(f"저장소 목록 추출 중 오류: {e}")

        return repositories

    async def _test_repository_connectivity(
        self, repo_type: str, repo_name: str, repo_url: str
    ) -> list[str]:
        """개별 저장소 연결성 테스트"""
        issues = []

        try:
            parsed_url = urlparse(repo_url)

            if repo_type == "git":
                if parsed_url.scheme in ["http", "https"]:
                    # HTTP Git 저장소 테스트
                    try:
                        response = requests.get(
                            repo_url, timeout=10, allow_redirects=True
                        )
                        if response.status_code >= 500:
                            issues.append(
                                f"Git 저장소 '{repo_name}' ({repo_url}) 서버 오류 - HTTP {response.status_code}"
                            )
                        elif response.status_code >= 400:
                            # Git 저장소는 인증이 필요할 수 있으므로 경고만
                            logger.debug(
                                f"Git 저장소 '{repo_name}' 인증 필요 또는 접근 제한"
                            )
                    except requests.exceptions.RequestException as e:
                        issues.append(
                            f"Git 저장소 '{repo_name}' ({repo_url}) 연결 실패 - {e}"
                        )

                elif parsed_url.scheme == "ssh" or repo_url.startswith("git@"):
                    # SSH Git 저장소는 실제 테스트가 어려우므로 기본 확인만
                    logger.debug(
                        f"SSH Git 저장소 '{repo_name}' - 실제 연결 테스트 생략"
                    )

            elif repo_type == "helm":
                if parsed_url.scheme in ["http", "https"]:
                    # Helm 저장소 index.yaml 확인
                    index_url = repo_url.rstrip("/") + "/index.yaml"
                    try:
                        response = requests.get(
                            index_url, timeout=10, allow_redirects=True
                        )
                        if response.status_code >= 400:
                            issues.append(
                                f"Helm 저장소 '{repo_name}' ({repo_url}) 접근 실패 - HTTP {response.status_code}"
                            )
                        else:
                            # index.yaml YAML 파싱 테스트
                            try:
                                yaml.safe_load(response.text)
                            except yaml.YAMLError:
                                issues.append(
                                    f"Helm 저장소 '{repo_name}' index.yaml이 유효하지 않습니다"
                                )
                    except requests.exceptions.RequestException as e:
                        issues.append(
                            f"Helm 저장소 '{repo_name}' ({repo_url}) 연결 실패 - {e}"
                        )

                elif parsed_url.scheme.startswith("oci"):
                    # OCI 레지스트리는 별도 테스트 필요
                    logger.debug(f"OCI Helm 저장소 '{repo_name}' - 고급 테스트 필요")

        except Exception as e:
            issues.append(f"저장소 '{repo_name}' 연결성 테스트 실패 - {e}")

        return issues

    async def _test_essential_services(self) -> list[str]:
        """필수 서비스 연결성 테스트"""
        warnings = []

        essential_services = [
            ("Docker Hub", "https://registry-1.docker.io/v2/", 10),
            ("Kubernetes", "https://kubernetes.io/", 5),
            ("GitHub API", "https://api.github.com", 5),
        ]

        for service_name, service_url, timeout in essential_services:
            try:
                response = requests.get(
                    service_url, timeout=timeout, allow_redirects=True
                )
                if response.status_code >= 500:
                    warnings.append(
                        f"{service_name} 서비스 응답 불안정 (HTTP {response.status_code})"
                    )
            except requests.exceptions.Timeout:
                warnings.append(f"{service_name} 서비스 응답 지연 (>{timeout}초)")
            except requests.exceptions.ConnectionError:
                warnings.append(f"{service_name} 서비스 연결 불가")
            except requests.exceptions.RequestException as e:
                logger.debug(f"{service_name} 서비스 테스트 오류: {e}")

        return warnings
