"""
배포 전 종합 안전성 검증기 모듈

실제 배포 전 모든 구성 요소의 안전성과 배포 가능성을 종합적으로 검증합니다.
롤백 계획 및 위험도 평가를 포함하여 안전한 배포를 보장합니다.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.logger import logger
from sbkube.utils.validation_system import (
    ValidationCheck,
    ValidationContext,
    ValidationResult,
    ValidationSeverity,
)


class DeploymentSimulator(ValidationCheck):
    """배포 시뮬레이션 및 드라이런 실행 검증기"""

    def __init__(self):
        super().__init__(
            name="deployment_simulator",
            description="배포 시뮬레이션 및 드라이런 실행",
            category="pre-deployment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """배포 시뮬레이션을 실행합니다"""
        issues = []
        warnings = []
        simulation_results = []

        try:
            # 설정에서 앱들 확인
            apps = await self._get_deployment_apps(context)

            if not apps:
                return self.create_validation_result(
                    level=DiagnosticLevel.INFO,
                    severity=ValidationSeverity.INFO,
                    message="배포할 앱이 없습니다",
                    details="배포 시뮬레이션을 수행할 앱이 없어 검증을 건너뜁니다.",
                    risk_level="low",
                )

            # 네임스페이스 확인 및 생성 시뮬레이션
            namespace_issues = await self._simulate_namespace_creation(context)
            issues.extend(namespace_issues)

            # 각 앱별 배포 시뮬레이션
            for app_name, app_config in apps:
                app_results = await self._simulate_app_deployment(
                    app_name, app_config, context
                )
                if app_results["issues"]:
                    issues.extend(app_results["issues"])
                if app_results["warnings"]:
                    warnings.extend(app_results["warnings"])
                simulation_results.append(app_results)

            # 전체 배포 시뮬레이션 요약
            total_resources = sum(
                result.get("resource_count", 0) for result in simulation_results
            )

        except Exception as e:
            issues.append(f"배포 시뮬레이션 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.CRITICAL,
                message=f"배포 시뮬레이션 실패 ({len(issues)}개 문제)",
                details="다음 배포 시뮬레이션 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="배포 설정을 확인하고 문제를 해결한 후 다시 시도하세요.",
                risk_level="critical",
                affected_components=["deployment", "kubernetes"],
                metadata={
                    "simulation_results": simulation_results,
                    "total_resources": total_resources,
                },
            )
        elif warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message=f"배포 시뮬레이션 경고사항이 있습니다 ({total_resources}개 리소스)",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="경고사항을 검토하여 배포 안정성을 개선해보세요.",
                risk_level="medium",
                metadata={
                    "simulation_results": simulation_results,
                    "total_resources": total_resources,
                },
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message=f"배포 시뮬레이션 성공 ({total_resources}개 리소스)",
                details=f"모든 앱의 배포 시뮬레이션이 성공적으로 완료되었습니다. 총 {total_resources}개의 Kubernetes 리소스가 생성될 예정입니다.",
                risk_level="low",
                metadata={
                    "simulation_results": simulation_results,
                    "total_resources": total_resources,
                },
            )

    async def _get_deployment_apps(
        self, context: ValidationContext
    ) -> list[tuple[str, dict[str, Any]]]:
        """배포할 앱들 추출"""
        apps = []

        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                all_apps = config.get("apps", [])
                for app in all_apps:
                    if isinstance(app, dict):
                        app_type = app.get("type")
                        # 실제 배포하는 타입들만 포함
                        if app_type in ["helm", "yaml"]:
                            app_name = app.get("name", "unknown")
                            apps.append((app_name, app))

        except Exception as e:
            logger.debug(f"배포 앱 찾기 중 오류: {e}")

        return apps

    async def _simulate_namespace_creation(
        self, context: ValidationContext
    ) -> list[str]:
        """네임스페이스 생성 시뮬레이션"""
        issues = []

        try:
            # 설정에서 네임스페이스 확인
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                namespace = config.get("namespace", "default")

                if namespace != "default":
                    # 네임스페이스 존재 확인
                    result = subprocess.run(
                        ["kubectl", "get", "namespace", namespace],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if result.returncode != 0:
                        # 네임스페이스가 없는 경우 생성 가능한지 확인
                        create_result = subprocess.run(
                            [
                                "kubectl",
                                "create",
                                "namespace",
                                namespace,
                                "--dry-run=client",
                                "-o",
                                "yaml",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )

                        if create_result.returncode != 0:
                            issues.append(
                                f"네임스페이스 '{namespace}' 생성 시뮬레이션 실패: {create_result.stderr.strip()}"
                            )

        except subprocess.TimeoutExpired:
            issues.append("네임스페이스 생성 시뮬레이션 시간 초과")
        except Exception as e:
            issues.append(f"네임스페이스 시뮬레이션 실패: {e}")

        return issues

    async def _simulate_app_deployment(
        self, app_name: str, app_config: dict[str, Any], context: ValidationContext
    ) -> dict[str, Any]:
        """개별 앱 배포 시뮬레이션"""
        result = {
            "app_name": app_name,
            "app_type": app_config.get("type"),
            "issues": [],
            "warnings": [],
            "resource_count": 0,
            "resources": [],
        }

        app_type = app_config.get("type")
        specs = app_config.get("specs", {})

        try:
            if app_type == "helm":
                await self._simulate_helm_deployment(app_name, specs, context, result)
            elif app_type == "yaml":
                await self._simulate_yaml_deployment(app_name, specs, context, result)

        except Exception as e:
            result["issues"].append(f"앱 '{app_name}' 배포 시뮬레이션 실패: {e}")

        return result

    async def _simulate_helm_deployment(
        self,
        app_name: str,
        specs: dict[str, Any],
        context: ValidationContext,
        result: dict[str, Any],
    ):
        """Helm 앱 배포 시뮬레이션"""
        base_path = Path(context.base_dir)

        # 차트 경로 확인
        chart_path_str = specs.get("path")
        if not chart_path_str:
            result["issues"].append(f"앱 '{app_name}': 차트 경로가 지정되지 않았습니다")
            return

        chart_path = base_path / chart_path_str
        if not chart_path.exists():
            result["issues"].append(
                f"앱 '{app_name}': 차트 경로 '{chart_path_str}'가 존재하지 않습니다"
            )
            return

        try:
            # helm template으로 리소스 생성 시뮬레이션
            cmd = ["helm", "template", app_name, str(chart_path)]

            # values 파일 추가
            values_files = specs.get("values", [])
            for values_file in values_files:
                values_path = base_path / values_file
                if values_path.exists():
                    cmd.extend(["-f", str(values_path)])

            # 네임스페이스 추가
            namespace = await self._get_namespace(context)
            cmd.extend(["--namespace", namespace])

            result_proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            )

            if result_proc.returncode != 0:
                result["issues"].append(
                    f"앱 '{app_name}': Helm 템플릿 렌더링 실패 - {result_proc.stderr.strip()}"
                )
                return

            # 생성된 리소스 분석
            rendered_yaml = result_proc.stdout
            resources = await self._analyze_rendered_resources(rendered_yaml)
            result["resources"] = resources
            result["resource_count"] = len(resources)

            # kubectl apply --dry-run으로 실제 배포 가능성 확인
            dry_run_issues = await self._test_kubectl_dry_run(rendered_yaml, namespace)
            result["issues"].extend(dry_run_issues)

        except subprocess.TimeoutExpired:
            result["issues"].append(f"앱 '{app_name}': Helm 배포 시뮬레이션 시간 초과")
        except Exception as e:
            result["issues"].append(f"앱 '{app_name}': Helm 배포 시뮬레이션 실패 - {e}")

    async def _simulate_yaml_deployment(
        self,
        app_name: str,
        specs: dict[str, Any],
        context: ValidationContext,
        result: dict[str, Any],
    ):
        """YAML 앱 배포 시뮬레이션"""
        base_path = Path(context.base_dir)
        actions = specs.get("actions", [])

        if not actions:
            result["issues"].append(f"앱 '{app_name}': actions가 정의되지 않았습니다")
            return

        all_yaml_content = []

        for action in actions:
            if not isinstance(action, dict):
                continue

            action_type = action.get("type")
            action_path = action.get("path")

            if action_type == "apply" and action_path:
                yaml_path = base_path / action_path
                if not yaml_path.exists():
                    result["issues"].append(
                        f"앱 '{app_name}': YAML 파일 '{action_path}'이 존재하지 않습니다"
                    )
                    continue

                try:
                    with open(yaml_path, encoding="utf-8") as f:
                        yaml_content = f.read()
                    all_yaml_content.append(yaml_content)
                except Exception as e:
                    result["issues"].append(
                        f"앱 '{app_name}': YAML 파일 '{action_path}' 읽기 실패 - {e}"
                    )

        if all_yaml_content:
            combined_yaml = "\n---\n".join(all_yaml_content)

            # 생성된 리소스 분석
            resources = await self._analyze_rendered_resources(combined_yaml)
            result["resources"] = resources
            result["resource_count"] = len(resources)

            # kubectl apply --dry-run으로 실제 배포 가능성 확인
            namespace = await self._get_namespace(context)
            dry_run_issues = await self._test_kubectl_dry_run(combined_yaml, namespace)
            result["issues"].extend(dry_run_issues)

    async def _analyze_rendered_resources(
        self, yaml_content: str
    ) -> list[dict[str, Any]]:
        """렌더링된 YAML에서 리소스 분석"""
        resources = []

        try:
            # YAML 문서들을 분리하여 각각 분석
            yaml_docs = yaml_content.split("---")
            for doc in yaml_docs:
                doc = doc.strip()
                if not doc:
                    continue

                try:
                    resource = yaml.safe_load(doc)
                    if isinstance(resource, dict) and "kind" in resource:
                        resources.append(
                            {
                                "kind": resource.get("kind"),
                                "apiVersion": resource.get("apiVersion"),
                                "name": resource.get("metadata", {}).get("name"),
                                "namespace": resource.get("metadata", {}).get(
                                    "namespace"
                                ),
                            }
                        )
                except yaml.YAMLError:
                    continue

        except Exception as e:
            logger.debug(f"리소스 분석 중 오류: {e}")

        return resources

    async def _test_kubectl_dry_run(
        self, yaml_content: str, namespace: str
    ) -> list[str]:
        """kubectl apply --dry-run 테스트"""
        issues = []

        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".yaml", delete=False
            ) as temp_file:
                temp_file.write(yaml_content)
                temp_file.flush()

                # kubectl apply --dry-run 실행
                result = subprocess.run(
                    [
                        "kubectl",
                        "apply",
                        "-f",
                        temp_file.name,
                        "--dry-run=server",
                        "--namespace",
                        namespace,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    error_msg = result.stderr.strip()
                    issues.append(f"kubectl 배포 검증 실패: {error_msg}")

                # 임시 파일 정리
                Path(temp_file.name).unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            issues.append("kubectl 배포 검증 시간 초과")
        except Exception as e:
            issues.append(f"kubectl 배포 검증 실패: {e}")

        return issues

    async def _get_namespace(self, context: ValidationContext) -> str:
        """네임스페이스 추출"""
        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                namespace = config.get("namespace", "default")
                return namespace if isinstance(namespace, str) else "default"
        except Exception:
            pass

        return "default"


class RiskAssessmentValidator(ValidationCheck):
    """배포 위험도 평가 및 분석 검증기"""

    def __init__(self):
        super().__init__(
            name="risk_assessment",
            description="배포 위험도 평가 및 분석",
            category="pre-deployment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """배포 위험도를 평가합니다"""
        risk_factors = []
        risk_score = 0
        risk_level = "LOW"

        try:
            # 리소스 영향도 평가
            resource_risk = await self._assess_resource_impact(context)
            risk_factors.extend(resource_risk["factors"])
            risk_score += resource_risk["score"]

            # 네트워크 정책 위험도 평가
            network_risk = await self._assess_network_impact(context)
            risk_factors.extend(network_risk["factors"])
            risk_score += network_risk["score"]

            # 데이터 지속성 위험도 평가
            persistence_risk = await self._assess_persistence_impact(context)
            risk_factors.extend(persistence_risk["factors"])
            risk_score += persistence_risk["score"]

            # 보안 위험도 평가
            security_risk = await self._assess_security_impact(context)
            risk_factors.extend(security_risk["factors"])
            risk_score += security_risk["score"]

            # 전체 위험도 분류
            if risk_score >= 80:
                risk_level = "CRITICAL"
                level = DiagnosticLevel.ERROR
                severity = ValidationSeverity.CRITICAL
            elif risk_score >= 60:
                risk_level = "HIGH"
                level = DiagnosticLevel.ERROR
                severity = ValidationSeverity.HIGH
            elif risk_score >= 40:
                risk_level = "MEDIUM"
                level = DiagnosticLevel.WARNING
                severity = ValidationSeverity.MEDIUM
            else:
                risk_level = "LOW"
                level = DiagnosticLevel.SUCCESS
                severity = ValidationSeverity.INFO

        except Exception as e:
            risk_factors.append(f"위험도 평가 중 오류 발생: {e}")
            risk_score = 100
            risk_level = "CRITICAL"
            level = DiagnosticLevel.ERROR
            severity = ValidationSeverity.CRITICAL

        recommendation = self._get_risk_recommendation(risk_level, risk_factors)

        return self.create_validation_result(
            level=level,
            severity=severity,
            message=f"배포 위험도: {risk_level} (점수: {risk_score}/100)",
            details="위험 요소 분석:\n"
            + "\n".join(f"• {factor}" for factor in risk_factors)
            if risk_factors
            else "식별된 위험 요소가 없습니다.",
            recommendation=recommendation,
            risk_level=risk_level.lower(),
            metadata={
                "risk_score": risk_score,
                "risk_level": risk_level,
                "risk_factors": risk_factors,
            },
        )

    async def _assess_resource_impact(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """리소스 영향도 평가"""
        factors = []
        score = 0

        try:
            # 설정에서 앱 정보 추출
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                apps = config.get("apps", [])

                # 앱 수량 위험도
                if len(apps) > 10:
                    factors.append(f"대량 앱 배포 (앱 수: {len(apps)}개)")
                    score += 20
                elif len(apps) > 5:
                    factors.append(f"중량 앱 배포 (앱 수: {len(apps)}개)")
                    score += 10

                # 높은 권한 요구 앱 확인
                privileged_apps = []
                for app in apps:
                    if isinstance(app, dict):
                        app_name = app.get("name", "unknown")
                        app_type = app.get("type")

                        # Helm 차트의 경우 values에서 권한 확인
                        if app_type == "helm":
                            specs = app.get("specs", {})
                            values_files = specs.get("values", [])

                            for values_file in values_files:
                                values_path = base_path / values_file
                                if values_path.exists():
                                    try:
                                        with open(values_path, encoding="utf-8") as f:
                                            values_data = yaml.safe_load(f) or {}

                                        # 높은 권한 설정 탐지
                                        if self._has_privileged_settings(values_data):
                                            privileged_apps.append(app_name)
                                    except Exception:
                                        pass

                if privileged_apps:
                    factors.append(f"높은 권한 요구 앱: {', '.join(privileged_apps)}")
                    score += len(privileged_apps) * 15

        except Exception as e:
            factors.append(f"리소스 영향도 평가 실패: {e}")
            score += 10

        return {"factors": factors, "score": score}

    async def _assess_network_impact(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """네트워크 정책 위험도 평가"""
        factors = []
        score = 0

        try:
            # 네임스페이스 확인
            namespace = await self._get_namespace(context)

            # Ingress 리소스 확인
            result = subprocess.run(
                ["kubectl", "get", "ingress", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                ingress_data = json.loads(result.stdout)
                ingresses = ingress_data.get("items", [])

                if ingresses:
                    factors.append(
                        f"외부 노출 서비스 존재 (Ingress: {len(ingresses)}개)"
                    )
                    score += len(ingresses) * 10

            # LoadBalancer 서비스 확인
            result = subprocess.run(
                ["kubectl", "get", "service", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                service_data = json.loads(result.stdout)
                services = service_data.get("items", [])

                loadbalancer_count = sum(
                    1
                    for svc in services
                    if svc.get("spec", {}).get("type") == "LoadBalancer"
                )

                if loadbalancer_count > 0:
                    factors.append(f"LoadBalancer 서비스 존재 ({loadbalancer_count}개)")
                    score += loadbalancer_count * 15

        except Exception as e:
            factors.append(f"네트워크 영향도 평가 실패: {e}")
            score += 5

        return {"factors": factors, "score": score}

    async def _assess_persistence_impact(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """데이터 지속성 위험도 평가"""
        factors = []
        score = 0

        try:
            namespace = await self._get_namespace(context)

            # PVC 확인
            result = subprocess.run(
                ["kubectl", "get", "pvc", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                pvc_data = json.loads(result.stdout)
                pvcs = pvc_data.get("items", [])

                if pvcs:
                    total_storage: float = 0.0
                    for pvc in pvcs:
                        storage_str = (
                            pvc.get("spec", {})
                            .get("resources", {})
                            .get("requests", {})
                            .get("storage", "0")
                        )
                        # 간단한 스토리지 크기 파싱 (정확하지 않을 수 있음)
                        if "Gi" in storage_str:
                            storage_gb = float(storage_str.replace("Gi", ""))
                            total_storage = total_storage + storage_gb

                    factors.append(
                        f"영구 스토리지 사용 (PVC: {len(pvcs)}개, 총 {total_storage:.1f}GB)"
                    )

                    if total_storage > 100:
                        score += 25
                    elif total_storage > 10:
                        score += 15
                    else:
                        score += 5

        except Exception as e:
            factors.append(f"데이터 지속성 평가 실패: {e}")
            score += 5

        return {"factors": factors, "score": score}

    async def _assess_security_impact(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """보안 위험도 평가"""
        factors = []
        score = 0

        try:
            namespace = await self._get_namespace(context)

            # ServiceAccount 확인
            result = subprocess.run(
                ["kubectl", "get", "serviceaccount", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                sa_data = json.loads(result.stdout)
                service_accounts = sa_data.get("items", [])

                custom_sa_count = len(
                    [
                        sa
                        for sa in service_accounts
                        if sa.get("metadata", {}).get("name") != "default"
                    ]
                )

                if custom_sa_count > 0:
                    factors.append(
                        f"사용자 정의 ServiceAccount 사용 ({custom_sa_count}개)"
                    )
                    score += custom_sa_count * 5

            # Role/RoleBinding 확인
            result = subprocess.run(
                ["kubectl", "get", "role,rolebinding", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                rbac_data = json.loads(result.stdout)
                rbac_items = rbac_data.get("items", [])

                if rbac_items:
                    factors.append(f"RBAC 설정 존재 ({len(rbac_items)}개)")
                    score += len(rbac_items) * 3

        except Exception as e:
            factors.append(f"보안 영향도 평가 실패: {e}")
            score += 5

        return {"factors": factors, "score": score}

    def _has_privileged_settings(self, values_data: dict[str, Any]) -> bool:
        """values 파일에서 높은 권한 설정 탐지"""
        if not isinstance(values_data, dict):
            return False

        # 일반적인 높은 권한 설정 패턴들
        privileged_patterns = [
            "privileged",
            "runAsRoot",
            "allowPrivilegeEscalation",
            "hostNetwork",
            "hostPID",
            "hostIPC",
        ]

        def check_nested_dict(data):
            if isinstance(data, dict):
                for key, value in data.items():
                    if any(
                        pattern in str(key).lower() for pattern in privileged_patterns
                    ):
                        if value is True or str(value).lower() == "true":
                            return True
                    if check_nested_dict(value):
                        return True
            elif isinstance(data, list):
                for item in data:
                    if check_nested_dict(item):
                        return True
            return False

        return bool(check_nested_dict(values_data))

    def _get_risk_recommendation(self, risk_level: str, risk_factors: list[str]) -> str:
        """위험도별 권장사항 생성"""
        if risk_level == "CRITICAL":
            return "배포를 중단하고 위험 요소를 해결한 후 다시 시도하세요. 클러스터 관리자와 상의가 필요합니다."
        elif risk_level == "HIGH":
            return "배포 전 위험 요소를 신중히 검토하고 필요시 백업을 수행하세요. 모니터링을 강화하여 배포하세요."
        elif risk_level == "MEDIUM":
            return (
                "위험 요소를 검토하고 배포 후 모니터링을 통해 시스템 상태를 확인하세요."
            )
        else:
            return "안전한 배포입니다. 배포를 진행할 수 있습니다."

    async def _get_namespace(self, context: ValidationContext) -> str:
        """네임스페이스 추출"""
        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                namespace = config.get("namespace", "default")
                return namespace if isinstance(namespace, str) else "default"
        except Exception:
            pass

        return "default"


class RollbackPlanValidator(ValidationCheck):
    """롤백 가능성 및 계획 검증기"""

    def __init__(self):
        super().__init__(
            name="rollback_plan",
            description="롤백 가능성 및 계획 검증",
            category="pre-deployment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """롤백 가능성 및 계획을 검증합니다"""
        rollback_issues = []
        rollback_warnings = []
        rollback_plan = {}

        try:
            # Helm 릴리스 기반 롤백 계획
            helm_plan = await self._assess_helm_rollback(context)
            rollback_plan.update(helm_plan)

            # 네임스페이스 백업 가능성 확인
            backup_plan = await self._assess_backup_capability(context)
            rollback_plan.update(backup_plan)

            # 데이터 영속성 롤백 계획
            persistence_plan = await self._assess_persistence_rollback(context)
            rollback_plan.update(persistence_plan)

            # 종합 롤백 가능성 평가
            overall_rollback = self._evaluate_overall_rollback(rollback_plan)

            if overall_rollback["critical_issues"]:
                rollback_issues.extend(overall_rollback["critical_issues"])
            if overall_rollback["warnings"]:
                rollback_warnings.extend(overall_rollback["warnings"])

        except Exception as e:
            rollback_issues.append(f"롤백 계획 검증 중 오류 발생: {e}")

        if rollback_issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"롤백 계획에 심각한 문제가 있습니다 ({len(rollback_issues)}개)",
                details="다음 롤백 관련 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in rollback_issues),
                recommendation="롤백 전략을 수립하고 백업을 준비한 후 배포를 진행하세요.",
                risk_level="high",
                metadata={"rollback_plan": rollback_plan},
            )
        elif rollback_warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="롤백 계획 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in rollback_warnings),
                recommendation="롤백 권장사항을 검토하여 안전성을 개선해보세요.",
                risk_level="medium",
                metadata={"rollback_plan": rollback_plan},
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="롤백 계획이 수립되었습니다",
                details="롤백 가능성이 확인되었으며 필요시 안전한 롤백이 가능합니다.",
                risk_level="low",
                metadata={"rollback_plan": rollback_plan},
            )

    async def _assess_helm_rollback(self, context: ValidationContext) -> dict[str, Any]:
        """Helm 기반 롤백 평가"""
        plan = {"helm_releases": [], "helm_rollback_possible": True, "helm_issues": []}

        try:
            # 현재 Helm 릴리스 확인
            namespace = await self._get_namespace(context)

            result = subprocess.run(
                ["helm", "list", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                releases = json.loads(result.stdout)
                plan["helm_releases"] = [
                    {
                        "name": release.get("name"),
                        "revision": release.get("revision"),
                        "status": release.get("status"),
                        "app_version": release.get("app_version"),
                    }
                    for release in releases
                ]

                # 각 릴리스의 히스토리 확인
                for release in releases:
                    release_name = release.get("name")
                    history_result = subprocess.run(
                        [
                            "helm",
                            "history",
                            release_name,
                            "-n",
                            namespace,
                            "-o",
                            "json",
                        ],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if history_result.returncode == 0:
                        history = json.loads(history_result.stdout)
                        if len(history) < 2:
                            plan["helm_issues"].append(
                                f"릴리스 '{release_name}': 롤백할 이전 버전이 없습니다"
                            )
            else:
                plan["helm_rollback_possible"] = False
                plan["helm_issues"].append("Helm 릴리스 목록 조회 실패")

        except Exception as e:
            plan["helm_rollback_possible"] = False
            plan["helm_issues"].append(f"Helm 롤백 평가 실패: {e}")

        return plan

    async def _assess_backup_capability(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """백업 가능성 평가"""
        plan = {"backup_tools": [], "backup_possible": False, "backup_issues": []}

        try:
            # Velero 백업 도구 확인
            result = subprocess.run(
                ["kubectl", "get", "deployment", "velero", "-n", "velero"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                plan["backup_tools"].append("velero")
                plan["backup_possible"] = True

            # etcd 백업 가능성 (클러스터 관리자 권한 필요)
            result = subprocess.run(
                ["kubectl", "get", "nodes", "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                # 클러스터 접근 가능하므로 수동 백업은 가능
                plan["backup_tools"].append("manual")
                plan["backup_possible"] = True

            if not plan["backup_possible"]:
                plan["backup_issues"].append("자동 백업 도구가 설치되지 않았습니다")

        except Exception as e:
            plan["backup_issues"].append(f"백업 가능성 평가 실패: {e}")

        return plan

    async def _assess_persistence_rollback(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """데이터 영속성 롤백 평가"""
        plan = {
            "persistent_volumes": [],
            "data_rollback_risk": "low",
            "persistence_issues": [],
        }

        try:
            namespace = await self._get_namespace(context)

            # PVC 및 PV 확인
            result = subprocess.run(
                ["kubectl", "get", "pvc", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                pvc_data = json.loads(result.stdout)
                pvcs = pvc_data.get("items", [])

                for pvc in pvcs:
                    pvc_name = pvc.get("metadata", {}).get("name")
                    volume_name = pvc.get("spec", {}).get("volumeName")

                    plan["persistent_volumes"].append(
                        {"pvc_name": pvc_name, "volume_name": volume_name}
                    )

                if len(pvcs) > 0:
                    plan["data_rollback_risk"] = "high"
                    plan["persistence_issues"].append(
                        f"영구 볼륨 데이터 롤백 위험 ({len(pvcs)}개 PVC)"
                    )

        except Exception as e:
            plan["persistence_issues"].append(f"영속성 롤백 평가 실패: {e}")

        return plan

    def _evaluate_overall_rollback(
        self, rollback_plan: dict[str, Any]
    ) -> dict[str, Any]:
        """종합 롤백 가능성 평가"""
        critical_issues = []
        warnings = []

        # Helm 롤백 문제
        if not rollback_plan.get("helm_rollback_possible", True):
            critical_issues.append("Helm 기반 롤백이 불가능합니다")

        helm_issues = rollback_plan.get("helm_issues", [])
        if helm_issues:
            critical_issues.extend(helm_issues)

        # 백업 가능성
        if not rollback_plan.get("backup_possible", False):
            warnings.append("자동 백업 시스템이 없어 수동 롤백만 가능합니다")

        # 데이터 영속성 위험
        if rollback_plan.get("data_rollback_risk") == "high":
            warnings.append("영구 볼륨 데이터 롤백 시 데이터 손실 위험이 있습니다")

        return {"critical_issues": critical_issues, "warnings": warnings}

    async def _get_namespace(self, context: ValidationContext) -> str:
        """네임스페이스 추출"""
        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                namespace = config.get("namespace", "default")
                return namespace if isinstance(namespace, str) else "default"
        except Exception:
            pass

        return "default"


class ImpactAnalysisValidator(ValidationCheck):
    """기존 워크로드에 미치는 영향 분석 검증기"""

    def __init__(self):
        super().__init__(
            name="impact_analysis",
            description="기존 워크로드에 미치는 영향 분석",
            category="pre-deployment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """기존 워크로드에 미치는 영향을 분석합니다"""
        impact_issues = []
        impact_warnings = []
        impact_analysis = {}

        try:
            # 네임스페이스 충돌 분석
            namespace_impact = await self._analyze_namespace_impact(context)
            impact_analysis.update(namespace_impact)

            # 리소스 이름 충돌 분석
            resource_impact = await self._analyze_resource_conflicts(context)
            impact_analysis.update(resource_impact)

            # 포트 및 서비스 충돌 분석
            service_impact = await self._analyze_service_conflicts(context)
            impact_analysis.update(service_impact)

            # 리소스 사용량 영향 분석
            usage_impact = await self._analyze_resource_usage_impact(context)
            impact_analysis.update(usage_impact)

            # 종합 영향도 평가
            overall_impact = self._evaluate_overall_impact(impact_analysis)

            if overall_impact["critical_issues"]:
                impact_issues.extend(overall_impact["critical_issues"])
            if overall_impact["warnings"]:
                impact_warnings.extend(overall_impact["warnings"])

        except Exception as e:
            impact_issues.append(f"영향 분석 중 오류 발생: {e}")

        if impact_issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"기존 워크로드에 심각한 영향이 예상됩니다 ({len(impact_issues)}개)",
                details="다음 영향 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in impact_issues),
                recommendation="충돌하는 리소스를 확인하고 이름을 변경하거나 네임스페이스를 분리하세요.",
                risk_level="high",
                metadata={"impact_analysis": impact_analysis},
            )
        elif impact_warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="기존 워크로드에 일부 영향이 예상됩니다",
                details="\n".join(f"• {warning}" for warning in impact_warnings),
                recommendation="영향을 검토하고 필요시 리소스 할당을 조정하세요.",
                risk_level="medium",
                metadata={"impact_analysis": impact_analysis},
            )
        else:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="기존 워크로드에 영향이 없습니다",
                details="배포가 기존 시스템에 미치는 영향이 최소화되었습니다.",
                risk_level="low",
                metadata={"impact_analysis": impact_analysis},
            )

    async def _analyze_namespace_impact(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """네임스페이스 충돌 분석"""
        analysis: dict[str, Any] = {"namespace_conflicts": [], "existing_workloads": 0}

        try:
            namespace = await self._get_namespace(context)

            # 네임스페이스의 기존 워크로드 확인
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "deployments,statefulsets,daemonsets",
                    "-n",
                    namespace,
                    "-o",
                    "json",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                workloads_data = json.loads(result.stdout)
                existing_workloads = workloads_data.get("items", [])
                analysis["existing_workloads"] = len(existing_workloads)

                if existing_workloads:
                    workload_names = [
                        workload.get("metadata", {}).get("name", "unknown")
                        for workload in existing_workloads
                    ]
                    analysis["namespace_conflicts"].append(
                        f"네임스페이스 '{namespace}'에 기존 워크로드 {len(existing_workloads)}개 존재: {', '.join(workload_names[:5])}"
                        + ("..." if len(workload_names) > 5 else "")
                    )

        except Exception as e:
            analysis["namespace_conflicts"].append(f"네임스페이스 분석 실패: {e}")

        return analysis

    async def _analyze_resource_conflicts(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """리소스 이름 충돌 분석"""
        analysis: dict[str, Any] = {"resource_conflicts": [], "potential_conflicts": []}

        try:
            # 배포될 리소스 이름 추출
            new_resources = await self._get_new_resource_names(context)

            # 기존 리소스와 비교
            namespace = await self._get_namespace(context)

            for resource_type in ["deployments", "services", "configmaps", "secrets"]:
                result = subprocess.run(
                    ["kubectl", "get", resource_type, "-n", namespace, "-o", "json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    existing_data = json.loads(result.stdout)
                    existing_names = [
                        item.get("metadata", {}).get("name")
                        for item in existing_data.get("items", [])
                    ]

                    # 충돌 검사
                    new_names = new_resources.get(resource_type, [])
                    conflicts = set(new_names) & set(existing_names)

                    if conflicts:
                        analysis["resource_conflicts"].append(
                            f"{resource_type} 이름 충돌: {', '.join(conflicts)}"
                        )

        except Exception as e:
            analysis["resource_conflicts"].append(f"리소스 충돌 분석 실패: {e}")

        return analysis

    async def _analyze_service_conflicts(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """서비스 및 포트 충돌 분석"""
        analysis: dict[str, Any] = {"service_conflicts": [], "port_conflicts": []}

        try:
            namespace = await self._get_namespace(context)

            # 기존 서비스의 포트 확인
            result = subprocess.run(
                ["kubectl", "get", "services", "-n", namespace, "-o", "json"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                services = services_data.get("items", [])

                existing_ports = set()
                for service in services:
                    ports = service.get("spec", {}).get("ports", [])
                    for port in ports:
                        port_number = port.get("port")
                        if port_number:
                            existing_ports.add(port_number)

                # NodePort 서비스의 경우 클러스터 전체 충돌 가능성
                nodeport_services = [
                    service
                    for service in services
                    if service.get("spec", {}).get("type") == "NodePort"
                ]

                if nodeport_services:
                    analysis["service_conflicts"].append(
                        f"NodePort 서비스 {len(nodeport_services)}개 존재 - 포트 충돌 위험"
                    )

                if len(existing_ports) > 20:
                    analysis["port_conflicts"].append(
                        f"네임스페이스에 많은 포트 사용 중 ({len(existing_ports)}개)"
                    )

        except Exception as e:
            analysis["service_conflicts"].append(f"서비스 충돌 분석 실패: {e}")

        return analysis

    async def _analyze_resource_usage_impact(
        self, context: ValidationContext
    ) -> dict[str, Any]:
        """리소스 사용량 영향 분석"""
        analysis: dict[str, Any] = {"resource_pressure": [], "usage_warnings": []}

        try:
            # 노드 리소스 사용량 확인
            result = subprocess.run(
                ["kubectl", "top", "nodes", "--no-headers"],
                capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode == 0:
                node_lines = result.stdout.strip().split("\n")
                high_usage_nodes = []

                for line in node_lines:
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 5:
                            node_name = parts[0]
                            cpu_usage = parts[1]
                            memory_usage = parts[3]

                            # CPU/메모리 사용률 파싱 (간단한 방법)
                            cpu_percent = (
                                int(cpu_usage.rstrip("%"))
                                if cpu_usage.endswith("%")
                                else 0
                            )
                            memory_percent = (
                                int(memory_usage.rstrip("%"))
                                if memory_usage.endswith("%")
                                else 0
                            )

                            if cpu_percent > 80 or memory_percent > 80:
                                high_usage_nodes.append(
                                    f"{node_name} (CPU: {cpu_percent}%, Memory: {memory_percent}%)"
                                )

                if high_usage_nodes:
                    analysis["resource_pressure"].append(
                        f"높은 리소스 사용률 노드: {', '.join(high_usage_nodes)}"
                    )

            # 네임스페이스별 리소스 사용량
            namespace = await self._get_namespace(context)
            result = subprocess.run(
                ["kubectl", "top", "pods", "-n", namespace, "--no-headers"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                pod_lines = result.stdout.strip().split("\n")
                if pod_lines and pod_lines[0]:  # 빈 결과가 아닌 경우
                    analysis["usage_warnings"].append(
                        f"네임스페이스 '{namespace}'에 {len(pod_lines)}개 파드가 리소스 사용 중"
                    )

        except Exception as e:
            analysis["usage_warnings"].append(f"리소스 사용량 분석 실패: {e}")

        return analysis

    async def _get_new_resource_names(
        self, context: ValidationContext
    ) -> dict[str, list[str]]:
        """배포될 새 리소스 이름들 추출"""
        resource_names: dict[str, list[str]] = {
            "deployments": [],
            "services": [],
            "configmaps": [],
            "secrets": [],
        }

        try:
            # 설정에서 앱 이름들 추출 (간단한 방법)
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                apps = config.get("apps", [])
                for app in apps:
                    if isinstance(app, dict):
                        app_name = app.get("name")
                        if app_name:
                            # 일반적으로 앱 이름이 deployment/service 이름이 됨
                            resource_names["deployments"].append(app_name)
                            resource_names["services"].append(app_name)

        except Exception as e:
            logger.debug(f"새 리소스 이름 추출 실패: {e}")

        return resource_names

    def _evaluate_overall_impact(
        self, impact_analysis: dict[str, Any]
    ) -> dict[str, Any]:
        """종합 영향도 평가"""
        critical_issues = []
        warnings = []

        # 리소스 충돌
        resource_conflicts = impact_analysis.get("resource_conflicts", [])
        if resource_conflicts:
            critical_issues.extend(resource_conflicts)

        # 네임스페이스 충돌
        namespace_conflicts = impact_analysis.get("namespace_conflicts", [])
        if namespace_conflicts:
            warnings.extend(namespace_conflicts)

        # 서비스 충돌
        service_conflicts = impact_analysis.get("service_conflicts", [])
        if service_conflicts:
            warnings.extend(service_conflicts)

        # 리소스 압박
        resource_pressure = impact_analysis.get("resource_pressure", [])
        if resource_pressure:
            warnings.extend(resource_pressure)

        return {"critical_issues": critical_issues, "warnings": warnings}

    async def _get_namespace(self, context: ValidationContext) -> str:
        """네임스페이스 추출"""
        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                namespace = config.get("namespace", "default")
                return namespace if isinstance(namespace, str) else "default"
        except Exception:
            pass

        return "default"
