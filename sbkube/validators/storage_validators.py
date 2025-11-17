"""스토리지 검증기 모듈.

PV/PVC 요구사항 검증 및 클러스터 스토리지 상태 확인을 담당합니다.
"""

import json
import subprocess
from typing import Any

from sbkube.models.config_model import HelmApp, SBKubeConfig
from sbkube.utils.diagnostic_system import DiagnosticLevel
from sbkube.utils.logger import logger
from sbkube.utils.validation_system import (
    ValidationCheck,
    ValidationContext,
    ValidationResult,
    ValidationSeverity,
)


class StorageValidator(ValidationCheck):
    """PV/PVC 검증기.

    kubernetes.io/no-provisioner StorageClass 사용 시
    필요한 PV가 클러스터에 존재하는지 확인합니다.
    """

    def __init__(self, kubeconfig: str | None = None) -> None:
        """StorageValidator 초기화.

        Args:
            kubeconfig: kubeconfig 파일 경로 (None이면 기본값 사용)

        """
        super().__init__(
            name="storage_validation",
            description="PV/PVC 요구사항 검증",
            category="infrastructure",
        )
        self.kubeconfig = kubeconfig

    async def run_validation(self, context: ValidationContext) -> ValidationResult:
        """스토리지 검증 실행.

        Args:
            context: 검증 컨텍스트 (config 포함)

        Returns:
            검증 결과

        """
        # context.config는 동적으로 추가되는 속성이므로 getattr 사용
        config = getattr(context, "config", None)

        if not config:
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.LOW,
                message="설정 파일이 로드되지 않아 스토리지 검증을 건너뜁니다",
                details="ValidationContext에 config가 없습니다",
                risk_level="low",
            )

        # PV 요구사항 추출
        required_pvs = self._extract_required_pvs(config)

        if not required_pvs:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message="수동 PV가 필요한 앱이 없습니다",
                details="모든 앱이 동적 프로비저닝 또는 PV 불필요",
                risk_level="low",
            )

        # 클러스터 PV 조회
        cluster_pvs = self._get_cluster_pvs()

        if cluster_pvs is None:
            # kubectl 실행 실패 (클러스터 접근 불가)
            return self.create_validation_result(
                level=DiagnosticLevel.WARNING,
                severity=ValidationSeverity.MEDIUM,
                message="클러스터에 접근할 수 없어 PV 검증을 건너뜁니다",
                details="kubectl get pv 명령 실패 - 클러스터 접근 권한 확인 필요",
                recommendation="kubeconfig 설정을 확인하거나 --skip-storage-check 사용",
                risk_level="medium",
            )

        # PV 존재 여부 확인
        missing = []
        existing = []

        for req in required_pvs:
            if self._pv_exists(req, cluster_pvs):
                existing.append(req)
            else:
                missing.append(req)

        if not missing:
            return self.create_validation_result(
                level=DiagnosticLevel.SUCCESS,
                severity=ValidationSeverity.INFO,
                message=f"모든 필요한 PV가 존재합니다 ({len(existing)}개)",
                details="\n".join(
                    [
                        f"  ✓ {pv['app']}: {pv['storage_class']} ({pv['size']})"
                        for pv in existing
                    ]
                ),
                risk_level="low",
            )

        # PV 누락 발견
        missing_details = "\n".join(
            [f"  ✗ {pv['app']}: {pv['storage_class']} ({pv['size']})" for pv in missing]
        )

        recommendation = (
            "다음 방법 중 하나를 선택하세요:\n"
            "  1. 수동 PV 생성: kubectl apply -f pv.yaml\n"
            "  2. Dynamic Provisioner 설치:\n"
            "     - Rancher Local Path: https://github.com/rancher/local-path-provisioner\n"
            "     - NFS Provisioner: https://github.com/kubernetes-sigs/nfs-subdir-external-provisioner\n"
            "  3. 검증 건너뛰기: sbkube validate --skip-storage-check\n"
            "\n"
            "📚 자세한 내용: docs/05-best-practices/storage-management.md"
        )

        return self.create_validation_result(
            level=DiagnosticLevel.ERROR,
            severity=ValidationSeverity.HIGH,
            message=f"{len(missing)}개의 PV가 없습니다",
            details=f"누락된 PV:\n{missing_details}",
            recommendation=recommendation,
            risk_level="high",
            affected_components=[pv["app"] for pv in missing],
        )

    def _extract_required_pvs(self, config: SBKubeConfig) -> list[dict[str, Any]]:
        """설정에서 PV가 필요한 앱들 추출.

        Args:
            config: SBKube 설정

        Returns:
            필요한 PV 정보 리스트

        """
        required = []

        for app_name, app in config.apps.items():
            if isinstance(app, HelmApp):
                storage_info = self._check_helm_app_storage(app_name, app)
                if storage_info:
                    required.append(storage_info)

        return required

    def _check_helm_app_storage(
        self, app_name: str, app: HelmApp
    ) -> dict[str, Any] | None:
        """Helm 앱의 스토리지 설정 확인.

        NOTE: v0.8.0 implementation limitation:
        - HelmApp.values is a list of file paths, not inline dict
        - Cannot parse values files in validation phase (files may not exist yet)
        - Future enhancement: Support inline values in config or load values files

        Args:
            app_name: 앱 이름
            app: Helm 앱 설정

        Returns:
            PV 정보 (항상 None, v0.8.0 limitation)

        """
        # v0.8.0: Cannot detect PV requirements from HelmApp
        # because values is list[str] (file paths), not dict
        # This will be enhanced in future versions
        return None

    def _is_no_provisioner(self, storage_class: str) -> bool:
        """StorageClass가 no-provisioner인지 확인.

        Args:
            storage_class: StorageClass 이름

        Returns:
            no-provisioner 여부

        """
        try:
            cmd = ["kubectl", "get", "storageclass", storage_class, "-o", "json"]
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            sc_data = json.loads(result.stdout)

            provisioner = sc_data.get("provisioner", "")
            return provisioner == "kubernetes.io/no-provisioner"
        except subprocess.TimeoutExpired:
            logger.debug(f"StorageClass 조회 timeout: {storage_class}")
            return False
        except subprocess.CalledProcessError:
            logger.debug(f"StorageClass 조회 실패: {storage_class}")
            return False
        except json.JSONDecodeError:
            logger.debug(f"StorageClass JSON 파싱 실패: {storage_class}")
            return False
        except Exception as e:
            logger.debug(f"StorageClass 조회 오류: {e}")
            return False

    def _get_cluster_pvs(self) -> list[dict] | None:
        """클러스터의 모든 PV 조회.

        Returns:
            PV 리스트 (조회 실패 시 None)

        """
        try:
            cmd = ["kubectl", "get", "pv", "-o", "json"]
            if self.kubeconfig:
                cmd.extend(["--kubeconfig", self.kubeconfig])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            pv_list = json.loads(result.stdout)

            return pv_list.get("items", [])
        except subprocess.TimeoutExpired:
            logger.warning("PV 조회 timeout (10초)")
            return None
        except subprocess.CalledProcessError as e:
            logger.debug(f"kubectl get pv 실패: {e.stderr}")
            return None
        except json.JSONDecodeError:
            logger.warning("PV 조회 결과 JSON 파싱 실패")
            return None
        except Exception as e:
            logger.debug(f"PV 조회 오류: {e}")
            return None

    def _pv_exists(self, required: dict[str, Any], cluster_pvs: list[dict]) -> bool:
        """필요한 PV가 클러스터에 존재하는지 확인.

        Args:
            required: 필요한 PV 정보
            cluster_pvs: 클러스터의 PV 리스트

        Returns:
            존재 여부

        """
        storage_class = required.get("storage_class")
        required_size = required.get("size")

        for pv in cluster_pvs:
            spec = pv.get("spec", {})
            status = pv.get("status", {})

            pv_sc = spec.get("storageClassName")
            pv_capacity = spec.get("capacity", {}).get("storage")
            pv_phase = status.get("phase")

            # Match by StorageClass and Available status
            if (
                pv_sc == storage_class
                and pv_phase == "Available"
                and self._size_sufficient(pv_capacity, required_size)
            ):
                return True

        return False

    def _size_sufficient(self, pv_size: str | None, required_size: str) -> bool:
        """PV 크기가 요구사항을 만족하는지 확인.

        Args:
            pv_size: PV 크기 (예: "8Gi", "10Gi")
            required_size: 필요한 크기 (예: "8Gi")

        Returns:
            충분 여부

        """
        if not pv_size:
            return False

        # Simplified: 정확한 비교 (단위 변환 생략)
        # 실제로는 8Gi >= 8Gi, 10Gi >= 8Gi 등 비교 필요
        try:
            pv_value, pv_unit = self._parse_size(pv_size)
            req_value, req_unit = self._parse_size(required_size)

            # 같은 단위면 단순 비교
            if pv_unit == req_unit:
                return pv_value >= req_value

            # 다른 단위면 바이트로 변환하여 비교
            pv_bytes = self._to_bytes(pv_value, pv_unit)
            req_bytes = self._to_bytes(req_value, req_unit)

            return pv_bytes >= req_bytes
        except ValueError:
            # 파싱 실패 시 문자열 일치로 폴백
            return pv_size == required_size

    def _parse_size(self, size: str) -> tuple[float, str]:
        """크기 문자열 파싱.

        Args:
            size: 크기 문자열 (예: "8Gi", "10G")

        Returns:
            (값, 단위) 튜플

        Raises:
            ValueError: 파싱 실패

        """
        size = size.strip()

        # 단위 찾기 (Gi, G, Mi, M, Ki, K)
        units = ["Gi", "G", "Mi", "M", "Ki", "K", "Ti", "T"]
        for unit in units:
            if size.endswith(unit):
                value_str = size[: -len(unit)]
                return (float(value_str), unit)

        # 단위 없으면 bytes로 가정
        return (float(size), "")

    def _to_bytes(self, value: float, unit: str) -> int:
        """크기를 바이트로 변환.

        Args:
            value: 값
            unit: 단위 (Gi, G, Mi, M, Ki, K, Ti, T)

        Returns:
            바이트 크기

        """
        multipliers = {
            "Ti": 1024**4,
            "Gi": 1024**3,
            "Mi": 1024**2,
            "Ki": 1024,
            "T": 1000**4,
            "G": 1000**3,
            "M": 1000**2,
            "K": 1000,
            "": 1,
        }

        return int(value * multipliers.get(unit, 1))


class StorageValidatorLegacy:
    """Legacy StorageValidator (validate 명령에서 직접 사용).

    ValidationCheck를 상속하지 않는 간단한 버전.
    기존 validate 명령과 호환성 유지를 위해 제공.
    """

    def __init__(self, kubeconfig: str | None = None) -> None:
        """StorageValidatorLegacy 초기화.

        Args:
            kubeconfig: kubeconfig 파일 경로

        """
        self.kubeconfig = kubeconfig
        self._validator = StorageValidator(kubeconfig=kubeconfig)

    def check_required_pvs(self, config: SBKubeConfig) -> dict[str, Any]:
        """앱이 필요로 하는 PV들이 클러스터에 존재하는지 확인.

        Args:
            config: SBKube 설정

        Returns:
            {
                "all_exist": bool,
                "missing": [{"app": str, "storage_class": str, "size": str}],
                "existing": [{"app": str, "storage_class": str, "size": str}],
            }

        """
        required_pvs = self._validator._extract_required_pvs(config)

        if not required_pvs:
            return {"all_exist": True, "missing": [], "existing": []}

        cluster_pvs = self._validator._get_cluster_pvs()

        if cluster_pvs is None:
            # 클러스터 접근 실패 시 경고만 하고 통과
            logger.warning("클러스터 PV 조회 실패 - 스토리지 검증 건너뜀")
            return {"all_exist": True, "missing": [], "existing": []}

        missing = []
        existing = []

        for req in required_pvs:
            if self._validator._pv_exists(req, cluster_pvs):
                existing.append(req)
            else:
                missing.append(req)

        return {
            "all_exist": len(missing) == 0,
            "missing": missing,
            "existing": existing,
        }
