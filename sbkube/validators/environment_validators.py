"""Kubernetes 환경 종합 검증기 모듈

Kubernetes 클러스터 환경, 권한, 리소스 가용성을 종합적으로 검증합니다.
배포 전 환경 적합성을 사전 점검하여 안전한 배포를 보장합니다.
"""

import json
import subprocess
from pathlib import Path

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


class ClusterResourceValidator(ValidationCheck):
    """클러스터 리소스 가용성 검증기"""

    def __init__(self):
        super().__init__(
            name="cluster_resource",
            description="클러스터 CPU/메모리/스토리지 가용성 검증",
            category="environment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """클러스터 리소스 가용성을 검증합니다"""
        issues = []
        warnings = []

        try:
            # 노드 리소스 확인
            node_issues = await self._check_node_resources()
            issues.extend(node_issues)

            # 네임스페이스 리소스 쿼터 확인
            quota_issues = await self._check_resource_quotas(context)
            issues.extend(quota_issues)

            # 스토리지 클래스 확인
            storage_issues = await self._check_storage_classes()
            warnings.extend(storage_issues)

        except Exception as e:
            issues.append(f"리소스 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"클러스터 리소스 부족 또는 오류 ({len(issues)}개)",
                details="다음 리소스 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="클러스터 리소스를 확인하고 필요시 노드를 추가하거나 리소스 제한을 조정하세요.",
                risk_level="high",
                affected_components=["cluster", "nodes", "storage"],
            )
        if warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="클러스터 리소스 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 클러스터 안정성을 개선해보세요.",
                risk_level="medium",
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="클러스터 리소스가 충분합니다",
            details="CPU, 메모리, 스토리지 모든 리소스가 배포 요구사항을 충족합니다.",
            risk_level="low",
        )

    async def _check_node_resources(self) -> list[str]:
        """노드 리소스 상태 확인"""
        issues = []

        try:
            # 노드 목록 및 상태 확인
            result = subprocess.run(
                ["kubectl", "get", "nodes", "-o", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=15,
            )

            if result.returncode != 0:
                return [f"노드 정보 조회 실패: {result.stderr.strip()}"]

            nodes_data = json.loads(result.stdout)
            nodes = nodes_data.get("items", [])

            if not nodes:
                return ["클러스터에 노드가 없습니다"]

            ready_nodes = 0
            total_cpu = 0
            total_memory = 0
            allocatable_cpu = 0
            allocatable_memory = 0

            for node in nodes:
                # 노드 상태 확인
                conditions = node.get("status", {}).get("conditions", [])
                is_ready = any(
                    condition.get("type") == "Ready"
                    and condition.get("status") == "True"
                    for condition in conditions
                )

                if is_ready:
                    ready_nodes += 1

                    # 리소스 정보 수집
                    capacity = node.get("status", {}).get("capacity", {})
                    allocatable = node.get("status", {}).get("allocatable", {})

                    cpu_capacity = self._parse_cpu_resource(capacity.get("cpu", "0"))
                    memory_capacity = self._parse_memory_resource(
                        capacity.get("memory", "0")
                    )
                    cpu_alloc = self._parse_cpu_resource(allocatable.get("cpu", "0"))
                    memory_alloc = self._parse_memory_resource(
                        allocatable.get("memory", "0")
                    )

                    total_cpu += cpu_capacity
                    total_memory += memory_capacity
                    allocatable_cpu += cpu_alloc
                    allocatable_memory += memory_alloc

            # 노드 상태 검증
            if ready_nodes == 0:
                issues.append("사용 가능한 Ready 노드가 없습니다")
            elif ready_nodes < len(nodes):
                issues.append(
                    f"일부 노드가 NotReady 상태입니다 ({ready_nodes}/{len(nodes)} 노드만 Ready)"
                )

            # 리소스 충분성 검증
            if allocatable_cpu < 1.0:
                issues.append(
                    f"사용 가능한 CPU가 부족합니다 ({allocatable_cpu:.2f} cores)"
                )
            elif allocatable_cpu < 2.0:
                issues.append(
                    f"CPU 리소스가 제한적입니다 ({allocatable_cpu:.2f} cores). 2 cores 이상 권장"
                )

            if allocatable_memory < 2 * 1024 * 1024 * 1024:  # 2GB
                issues.append(
                    f"사용 가능한 메모리가 부족합니다 ({allocatable_memory / (1024**3):.2f}GB)"
                )
            elif allocatable_memory < 4 * 1024 * 1024 * 1024:  # 4GB
                issues.append(
                    f"메모리 리소스가 제한적입니다 ({allocatable_memory / (1024**3):.2f}GB). 4GB 이상 권장"
                )

        except subprocess.TimeoutExpired:
            issues.append("노드 정보 조회 시간 초과")
        except json.JSONDecodeError:
            issues.append("노드 정보 파싱 실패")
        except Exception as e:
            issues.append(f"노드 리소스 확인 실패: {e}")

        return issues

    async def _check_resource_quotas(self, context: ValidationContext) -> list[str]:
        """리소스 쿼터 확인"""
        issues = []

        try:
            # 네임스페이스별 리소스 쿼터 확인
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                namespace = config.get("namespace", "default")

                # 리소스 쿼터 확인
                result = subprocess.run(
                    ["kubectl", "get", "resourcequota", "-n", namespace, "-o", "json"],
                    check=False, capture_output=True,
                    text=True,
                    timeout=10,
                )

                if result.returncode == 0:
                    quotas_data = json.loads(result.stdout)
                    quotas = quotas_data.get("items", [])

                    for quota in quotas:
                        status = quota.get("status", {})
                        hard = status.get("hard", {})
                        used = status.get("used", {})

                        # CPU 쿼터 확인
                        if "requests.cpu" in hard and "requests.cpu" in used:
                            hard_cpu = self._parse_cpu_resource(hard["requests.cpu"])
                            used_cpu = self._parse_cpu_resource(used["requests.cpu"])

                            if used_cpu / hard_cpu > 0.9:
                                issues.append(
                                    f"네임스페이스 '{namespace}' CPU 쿼터 거의 소진 ({used_cpu:.2f}/{hard_cpu:.2f} cores)"
                                )

                        # 메모리 쿼터 확인
                        if "requests.memory" in hard and "requests.memory" in used:
                            hard_memory = self._parse_memory_resource(
                                hard["requests.memory"]
                            )
                            used_memory = self._parse_memory_resource(
                                used["requests.memory"]
                            )

                            if used_memory / hard_memory > 0.9:
                                issues.append(
                                    f"네임스페이스 '{namespace}' 메모리 쿼터 거의 소진 ({used_memory / (1024**3):.2f}/{hard_memory / (1024**3):.2f}GB)"
                                )

        except Exception as e:
            logger.debug(f"리소스 쿼터 확인 중 오류 (무시): {e}")

        return issues

    async def _check_storage_classes(self) -> list[str]:
        """스토리지 클래스 확인"""
        warnings = []

        try:
            result = subprocess.run(
                ["kubectl", "get", "storageclass", "-o", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                warnings.append("스토리지 클래스 정보를 조회할 수 없습니다")
                return warnings

            storage_data = json.loads(result.stdout)
            storage_classes = storage_data.get("items", [])

            if not storage_classes:
                warnings.append(
                    "스토리지 클래스가 정의되지 않았습니다. PV/PVC 사용 시 문제가 발생할 수 있습니다"
                )
            else:
                default_storage = any(
                    sc.get("metadata", {})
                    .get("annotations", {})
                    .get("storageclass.kubernetes.io/is-default-class")
                    == "true"
                    for sc in storage_classes
                )

                if not default_storage:
                    warnings.append("기본 스토리지 클래스가 설정되지 않았습니다")

        except Exception as e:
            logger.debug(f"스토리지 클래스 확인 중 오류 (무시): {e}")

        return warnings

    def _parse_cpu_resource(self, cpu_str: str) -> float:
        """CPU 리소스 문자열을 float으로 변환"""
        if not cpu_str:
            return 0.0

        cpu_str = str(cpu_str).strip()

        if cpu_str.endswith("m"):
            return float(cpu_str[:-1]) / 1000.0
        if cpu_str.endswith("n"):
            return float(cpu_str[:-1]) / 1000000000.0
        return float(cpu_str)

    def _parse_memory_resource(self, memory_str: str) -> int:
        """메모리 리소스 문자열을 바이트로 변환"""
        if not memory_str:
            return 0

        memory_str = str(memory_str).strip()

        units = {
            "Ki": 1024,
            "Mi": 1024**2,
            "Gi": 1024**3,
            "Ti": 1024**4,
            "K": 1000,
            "M": 1000**2,
            "G": 1000**3,
            "T": 1000**4,
        }

        for unit, multiplier in units.items():
            if memory_str.endswith(unit):
                return int(float(memory_str[: -len(unit)]) * multiplier)

        return int(memory_str)


class NamespacePermissionValidator(ValidationCheck):
    """네임스페이스별 권한 검증기"""

    def __init__(self):
        super().__init__(
            name="namespace_permission",
            description="네임스페이스별 권한 및 RBAC 검증",
            category="environment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """네임스페이스별 권한을 검증합니다"""
        issues = []
        warnings = []

        try:
            # 설정에서 네임스페이스 확인
            namespace = await self._get_target_namespace(context)

            # 네임스페이스 존재성 및 접근성 확인
            ns_issues = await self._check_namespace_access(namespace)
            issues.extend(ns_issues)

            # 필수 권한 확인
            permission_issues = await self._check_required_permissions(namespace)
            issues.extend(permission_issues)

            # ServiceAccount 확인
            sa_issues = await self._check_service_accounts(namespace)
            warnings.extend(sa_issues)

        except Exception as e:
            issues.append(f"권한 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"네임스페이스 권한 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 권한 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="클러스터 관리자에게 필요한 권한을 요청하거나 RBAC 설정을 확인하세요.",
                risk_level="high",
                affected_components=["namespace", "rbac", "serviceaccount"],
            )
        if warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="네임스페이스 권한 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 보안 설정을 개선해보세요.",
                risk_level="medium",
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="네임스페이스 권한이 적절합니다",
            details="모든 필수 권한이 확인되었으며 배포 가능한 상태입니다.",
            risk_level="low",
        )

    async def _get_target_namespace(self, context: ValidationContext) -> str:
        """대상 네임스페이스 추출"""
        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                return config.get("namespace", "default")
        except Exception:
            pass

        return "default"

    async def _check_namespace_access(self, namespace: str) -> list[str]:
        """네임스페이스 접근성 확인"""
        issues = []

        try:
            # 네임스페이스 존재 확인
            result = subprocess.run(
                ["kubectl", "get", "namespace", namespace],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                # 네임스페이스가 없는 경우 생성 권한 확인
                create_result = subprocess.run(
                    ["kubectl", "auth", "can-i", "create", "namespaces"],
                    check=False, capture_output=True,
                    text=True,
                    timeout=5,
                )

                if (
                    create_result.returncode != 0
                    or "no" in create_result.stdout.lower()
                ):
                    issues.append(
                        f"네임스페이스 '{namespace}'가 존재하지 않으며 생성 권한도 없습니다"
                    )
                else:
                    # 네임스페이스 생성 가능하다면 경고만
                    pass

            # 네임스페이스 내 리소스 목록 권한 확인
            result = subprocess.run(
                ["kubectl", "get", "pods", "-n", namespace, "--no-headers"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0 and "forbidden" in result.stderr.lower():
                issues.append(
                    f"네임스페이스 '{namespace}' 내 리소스 조회 권한이 없습니다"
                )

        except subprocess.TimeoutExpired:
            issues.append("네임스페이스 접근성 확인 시간 초과")
        except Exception as e:
            issues.append(f"네임스페이스 접근성 확인 실패: {e}")

        return issues

    async def _check_required_permissions(self, namespace: str) -> list[str]:
        """필수 권한 확인"""
        issues = []

        # 배포에 필요한 권한들
        required_permissions = [
            ("create", "deployments"),
            ("create", "services"),
            ("create", "configmaps"),
            ("create", "secrets"),
            ("get", "pods"),
            ("list", "pods"),
            ("delete", "pods"),
            ("patch", "deployments"),
            ("update", "deployments"),
        ]

        for action, resource in required_permissions:
            try:
                result = subprocess.run(
                    ["kubectl", "auth", "can-i", action, resource, "-n", namespace],
                    check=False, capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode != 0 or "no" in result.stdout.lower():
                    issues.append(
                        f"권한 부족: {action} {resource} (네임스페이스: {namespace})"
                    )

            except subprocess.TimeoutExpired:
                issues.append(f"권한 확인 시간 초과: {action} {resource}")
            except Exception as e:
                issues.append(f"권한 확인 실패: {action} {resource} - {e}")

        return issues

    async def _check_service_accounts(self, namespace: str) -> list[str]:
        """ServiceAccount 확인"""
        warnings = []

        try:
            result = subprocess.run(
                ["kubectl", "get", "serviceaccount", "-n", namespace, "-o", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                sa_data = json.loads(result.stdout)
                service_accounts = sa_data.get("items", [])

                if len(service_accounts) <= 1:  # default SA만 있는 경우
                    warnings.append(
                        f"네임스페이스 '{namespace}'에 사용자 정의 ServiceAccount가 없습니다. 보안 강화를 위해 고려해보세요"
                    )

        except Exception as e:
            logger.debug(f"ServiceAccount 확인 중 오류 (무시): {e}")

        return warnings


class NetworkPolicyValidator(ValidationCheck):
    """네트워크 정책 및 접근성 검증기"""

    def __init__(self):
        super().__init__(
            name="network_policy",
            description="네트워크 정책 및 접근성 검증",
            category="environment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """네트워크 정책 및 접근성을 검증합니다"""
        issues = []
        warnings = []

        try:
            # 네트워크 연결성 테스트
            connectivity_issues = await self._test_network_connectivity()
            issues.extend(connectivity_issues)

            # 네트워크 정책 확인
            policy_warnings = await self._check_network_policies(context)
            warnings.extend(policy_warnings)

            # Ingress 설정 검증
            ingress_issues = await self._check_ingress_setup()
            warnings.extend(ingress_issues)

        except Exception as e:
            issues.append(f"네트워크 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"네트워크 연결 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 네트워크 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="네트워크 설정을 확인하고 방화벽이나 프록시 설정을 점검하세요.",
                risk_level="high",
                affected_components=["network", "dns", "registry"],
            )
        if warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="네트워크 설정 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 네트워크 보안과 성능을 개선해보세요.",
                risk_level="medium",
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="네트워크 설정이 적절합니다",
            details="모든 필수 네트워크 연결이 정상이며 배포에 문제가 없습니다.",
            risk_level="low",
        )

    async def _test_network_connectivity(self) -> list[str]:
        """네트워크 연결성 테스트"""
        issues = []

        # 주요 서비스 연결 테스트
        test_endpoints = [
            ("Docker Hub", "https://registry-1.docker.io/v2/", 10),
            ("Kubernetes API", "https://kubernetes.io/", 5),
            ("GitHub", "https://api.github.com", 5),
            (
                "Prometheus Charts",
                "https://prometheus-community.github.io/helm-charts/index.yaml",
                10,
            ),
        ]

        for name, url, timeout in test_endpoints:
            try:
                response = requests.get(url, timeout=timeout, allow_redirects=True)
                if response.status_code >= 500:
                    issues.append(f"{name} 서버 오류 (HTTP {response.status_code})")
                elif response.status_code >= 400:
                    # 일부 서비스는 인증이 필요할 수 있어 경고만
                    logger.debug(
                        f"{name} 인증 필요 또는 접근 제한 (HTTP {response.status_code})"
                    )
            except requests.exceptions.Timeout:
                issues.append(f"{name} 연결 시간 초과 (>{timeout}초)")
            except requests.exceptions.ConnectionError as e:
                issues.append(f"{name} 연결 실패: {e!s}")
            except requests.exceptions.RequestException as e:
                issues.append(f"{name} 요청 실패: {e!s}")

        return issues

    async def _check_network_policies(self, context: ValidationContext) -> list[str]:
        """네트워크 정책 확인"""
        warnings = []

        try:
            namespace = await self._get_target_namespace(context)

            result = subprocess.run(
                ["kubectl", "get", "networkpolicy", "-n", namespace, "-o", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                policies_data = json.loads(result.stdout)
                policies = policies_data.get("items", [])

                if not policies:
                    warnings.append(
                        f"네임스페이스 '{namespace}'에 네트워크 정책이 설정되지 않았습니다. 보안 강화를 위해 고려해보세요"
                    )
                else:
                    # 정책이 너무 제한적인지 확인
                    restrictive_policies = []
                    for policy in policies:
                        spec = policy.get("spec", {})
                        if not spec.get("ingress") and not spec.get("egress"):
                            policy_name = policy.get("metadata", {}).get(
                                "name", "unknown"
                            )
                            restrictive_policies.append(policy_name)

                    if restrictive_policies:
                        warnings.append(
                            f"일부 네트워크 정책이 매우 제한적입니다: {', '.join(restrictive_policies)}"
                        )

        except Exception as e:
            logger.debug(f"네트워크 정책 확인 중 오류 (무시): {e}")

        return warnings

    async def _check_ingress_setup(self) -> list[str]:
        """Ingress 설정 검증"""
        warnings = []

        try:
            # Ingress 컨트롤러 확인
            result = subprocess.run(
                [
                    "kubectl",
                    "get",
                    "pods",
                    "-A",
                    "-l",
                    "app.kubernetes.io/name=ingress-nginx",
                    "-o",
                    "json",
                ],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                pods_data = json.loads(result.stdout)
                ingress_pods = pods_data.get("items", [])

                if not ingress_pods:
                    warnings.append(
                        "Ingress 컨트롤러가 설치되지 않았습니다. 외부 접근이 필요한 경우 설치를 고려해보세요"
                    )
                else:
                    # Ingress 컨트롤러 상태 확인
                    ready_pods = 0
                    for pod in ingress_pods:
                        conditions = pod.get("status", {}).get("conditions", [])
                        is_ready = any(
                            condition.get("type") == "Ready"
                            and condition.get("status") == "True"
                            for condition in conditions
                        )
                        if is_ready:
                            ready_pods += 1

                    if ready_pods == 0:
                        warnings.append(
                            "Ingress 컨트롤러 파드가 모두 비정상 상태입니다"
                        )
                    elif ready_pods < len(ingress_pods):
                        warnings.append(
                            f"일부 Ingress 컨트롤러 파드가 비정상 상태입니다 ({ready_pods}/{len(ingress_pods)})"
                        )

        except Exception as e:
            logger.debug(f"Ingress 설정 확인 중 오류 (무시): {e}")

        return warnings

    async def _get_target_namespace(self, context: ValidationContext) -> str:
        """대상 네임스페이스 추출"""
        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                return config.get("namespace", "default")
        except Exception:
            pass

        return "default"


class SecurityContextValidator(ValidationCheck):
    """보안 컨텍스트 및 RBAC 검증기"""

    def __init__(self):
        super().__init__(
            name="security_context",
            description="보안 컨텍스트 및 RBAC 검증",
            category="environment",
        )

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """보안 컨텍스트 및 RBAC을 검증합니다"""
        issues = []
        warnings = []

        try:
            # RBAC 설정 확인
            rbac_issues = await self._check_rbac_configuration()
            issues.extend(rbac_issues)

            # Pod Security Standards 확인
            pss_warnings = await self._check_pod_security_standards(context)
            warnings.extend(pss_warnings)

            # 보안 정책 확인
            policy_warnings = await self._check_security_policies()
            warnings.extend(policy_warnings)

        except Exception as e:
            issues.append(f"보안 검증 중 오류 발생: {e}")

        if issues:
            return self.create_validation_result(
                level=DiagnosticLevel.ERROR,
                severity=ValidationSeverity.HIGH,
                message=f"보안 설정 문제가 발견되었습니다 ({len(issues)}개)",
                details="다음 보안 문제들이 발견되었습니다:\n"
                + "\n".join(f"• {issue}" for issue in issues),
                recommendation="클러스터 관리자와 협의하여 보안 정책을 확인하고 필요한 권한을 설정하세요.",
                risk_level="high",
                affected_components=["rbac", "security-policy", "pod-security"],
            )
        if warnings:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="보안 설정 권장사항이 있습니다",
                details="\n".join(f"• {warning}" for warning in warnings),
                recommendation="권장사항을 검토하여 보안 수준을 강화해보세요.",
                risk_level="medium",
            )
        return self.create_validation_result(
            level=DiagnosticLevel.SUCCESS,
            severity=ValidationSeverity.INFO,
            message="보안 설정이 적절합니다",
            details="RBAC 및 보안 정책이 올바르게 구성되어 있습니다.",
            risk_level="low",
        )

    async def _check_rbac_configuration(self) -> list[str]:
        """RBAC 설정 확인"""
        issues = []

        try:
            # RBAC가 활성화되어 있는지 확인
            result = subprocess.run(
                ["kubectl", "auth", "can-i", "create", "clusterroles"],
                check=False, capture_output=True,
                text=True,
                timeout=5,
            )

            # 클러스터 수준 권한이 없어도 정상 (일반적인 상황)

            # 현재 사용자의 권한 확인
            result = subprocess.run(
                ["kubectl", "auth", "can-i", "--list"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                issues.append("사용자 권한 목록을 조회할 수 없습니다")
            else:
                permissions = result.stdout.strip()
                if not permissions or len(permissions.split("\n")) < 5:
                    issues.append("사용자에게 할당된 권한이 매우 제한적입니다")

        except subprocess.TimeoutExpired:
            issues.append("RBAC 설정 확인 시간 초과")
        except Exception as e:
            issues.append(f"RBAC 설정 확인 실패: {e}")

        return issues

    async def _check_pod_security_standards(
        self, context: ValidationContext
    ) -> list[str]:
        """Pod Security Standards 확인"""
        warnings = []

        try:
            namespace = await self._get_target_namespace(context)

            # 네임스페이스 레이블 확인
            result = subprocess.run(
                ["kubectl", "get", "namespace", namespace, "-o", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                ns_data = json.loads(result.stdout)
                labels = ns_data.get("metadata", {}).get("labels", {})

                # Pod Security Standards 레이블 확인
                pss_labels = [
                    "pod-security.kubernetes.io/enforce",
                    "pod-security.kubernetes.io/audit",
                    "pod-security.kubernetes.io/warn",
                ]

                missing_pss = [label for label in pss_labels if label not in labels]

                if missing_pss:
                    warnings.append(
                        f"네임스페이스 '{namespace}'에 Pod Security Standards 레이블이 설정되지 않았습니다"
                    )
                else:
                    # 보안 수준 확인
                    enforce_level = labels.get("pod-security.kubernetes.io/enforce", "")
                    if enforce_level == "privileged":
                        warnings.append(
                            f"네임스페이스 '{namespace}'의 Pod Security 수준이 'privileged'로 설정되어 보안이 약합니다"
                        )

        except Exception as e:
            logger.debug(f"Pod Security Standards 확인 중 오류 (무시): {e}")

        return warnings

    async def _check_security_policies(self) -> list[str]:
        """보안 정책 확인"""
        warnings = []

        try:
            # Pod Security Policy 확인 (deprecated이지만 여전히 사용될 수 있음)
            result = subprocess.run(
                ["kubectl", "get", "podsecuritypolicy", "-o", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                psp_data = json.loads(result.stdout)
                policies = psp_data.get("items", [])

                if policies:
                    warnings.append(
                        "Pod Security Policy가 설정되어 있습니다. Kubernetes 1.25+에서는 deprecated되었으니 Pod Security Standards로 마이그레이션을 고려하세요"
                    )

            # Security Context Constraints 확인 (OpenShift)
            result = subprocess.run(
                ["kubectl", "get", "securitycontextconstraints", "-o", "json"],
                check=False, capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                scc_data = json.loads(result.stdout)
                sccs = scc_data.get("items", [])

                if sccs:
                    logger.debug("OpenShift Security Context Constraints 감지됨")

        except Exception as e:
            logger.debug(f"보안 정책 확인 중 오류 (무시): {e}")

        return warnings

    async def _get_target_namespace(self, context: ValidationContext) -> str:
        """대상 네임스페이스 추출"""
        try:
            base_path = Path(context.base_dir)
            config_path = base_path / context.config_dir / "config.yaml"

            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                return config.get("namespace", "default")
        except Exception:
            pass

        return "default"
