import shutil
import subprocess
from pathlib import Path

import requests
import yaml

from sbkube.utils.diagnostic_system import (
    DiagnosticCheck,
    DiagnosticLevel,
    DiagnosticResult,
)


class KubernetesConnectivityCheck(DiagnosticCheck):
    """Kubernetes 연결성 검사."""

    def __init__(self) -> None:
        super().__init__("k8s_connectivity", "Kubernetes 클러스터 연결")

    async def run(self) -> DiagnosticResult:
        try:
            # kubectl 설치 확인 (shutil.which로 먼저 체크)
            kubectl_path = shutil.which("kubectl")
            if not kubectl_path:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "kubectl이 설치되지 않았습니다",
                    "Kubernetes CLI 도구가 필요합니다. PATH에서 kubectl을 찾을 수 없습니다.",
                    "공식 문서를 참고하여 설치하세요: https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/",
                    "kubectl 설치 가이드 참조",
                )

            # 클러스터 연결 확인
            result = subprocess.run(
                ["kubectl", "cluster-info"], check=False, capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "Kubernetes 클러스터에 연결할 수 없습니다",
                    result.stderr.strip(),
                    "kubectl config get-contexts",
                    "kubeconfig 설정 확인",
                )

            # 클러스터 버전 확인
            result = subprocess.run(
                ["kubectl", "version", "--short"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            cluster_info = (
                result.stdout.strip() if result.returncode == 0 else "버전 정보 없음"
            )

            return self.create_result(
                DiagnosticLevel.SUCCESS, "Kubernetes 클러스터 연결 정상", cluster_info
            )

        except subprocess.TimeoutExpired:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "Kubernetes 연결 시간 초과",
                "클러스터 응답이 너무 느립니다. 네트워크 연결을 확인하세요.",
                "kubectl config get-contexts",
                "현재 kubeconfig 컨텍스트 확인",
            )
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "Kubernetes 연결 검사 실패",
                f"오류 상세: {e!s}",
                "kubectl version --client && kubectl cluster-info",
                "kubectl 상태 확인",
            )


class HelmInstallationCheck(DiagnosticCheck):
    """Helm 설치 상태 검사."""

    def __init__(self) -> None:
        super().__init__("helm_installation", "Helm 설치 상태")

    async def run(self) -> DiagnosticResult:
        try:
            # Helm 설치 확인 (shutil.which로 먼저 체크)
            helm_path = shutil.which("helm")
            if not helm_path:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "Helm이 설치되지 않았습니다",
                    "Kubernetes 패키지 매니저가 필요합니다. PATH에서 helm을 찾을 수 없습니다.",
                    "공식 문서를 참고하여 설치하세요: https://helm.sh/docs/intro/install/",
                    "Helm 설치 가이드 참조",
                )

            # Helm 버전 확인
            result = subprocess.run(
                ["helm", "version", "--short"],
                check=False, capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "Helm 실행 오류",
                    f"helm 명령어 실행 중 오류 발생: {result.stderr.strip()}",
                    "helm version --short",
                    "Helm 상태 확인",
                )

            # 버전 확인
            version_output = result.stdout.strip()
            if "v2." in version_output:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "Helm v2가 설치되어 있습니다",
                    "Helm v3 사용을 권장합니다. 공식 문서를 참고하여 업그레이드하세요.",
                    "https://helm.sh/docs/intro/install/",
                    "Helm v3 업그레이드 가이드",
                )

            return self.create_result(
                DiagnosticLevel.SUCCESS, f"Helm 설치 상태 정상: {version_output}"
            )

        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR, f"Helm 설치 확인 실패: {e!s}"
            )


class ConfigValidityCheck(DiagnosticCheck):
    """설정 파일 유효성 검사."""

    def __init__(self, config_dir: str = "config") -> None:
        super().__init__("config_validity", "설정 파일 유효성")
        self.config_dir = Path(config_dir)

    async def run(self) -> DiagnosticResult:
        try:
            # 기본 설정 파일 존재 확인
            config_files = []
            for ext in [".yaml", ".yml", ".toml"]:
                config_file = self.config_dir / f"config{ext}"
                if config_file.exists():
                    config_files.append(config_file)

            if not config_files:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "설정 파일이 없습니다",
                    f"{self.config_dir}/config.[yaml|yml|toml] 파일이 존재하지 않습니다",
                    "sbkube init",
                    "프로젝트 초기화로 설정 파일 생성",
                )

            # 첫 번째 설정 파일 검사
            config_file = config_files[0]

            # YAML 파싱 확인
            try:
                with open(config_file, encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                if not config:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        "설정 파일이 비어있습니다",
                        f"{config_file}에 유효한 설정이 없습니다",
                    )

                # 필수 필드 확인
                required_fields = ["namespace", "apps"]
                missing_fields = [
                    field for field in required_fields if field not in config
                ]

                if missing_fields:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        f"필수 설정이 누락되었습니다: {', '.join(missing_fields)}",
                        "설정 파일을 확인하고 필수 필드를 추가해주세요",
                    )

                # 앱 설정 검증
                apps = config.get("apps", [])
                if not apps:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        "배포할 앱이 정의되지 않았습니다",
                        "apps 섹션에 하나 이상의 앱을 정의해주세요",
                    )

                # 각 앱의 필수 필드 확인
                for i, app in enumerate(apps):
                    if "name" not in app:
                        return self.create_result(
                            DiagnosticLevel.ERROR,
                            f"앱 #{i + 1}에 name 필드가 없습니다",
                            "모든 앱에는 name 필드가 필요합니다",
                        )

                    if "type" not in app:
                        return self.create_result(
                            DiagnosticLevel.ERROR,
                            f"앱 '{app.get('name', f'#{i + 1}')}에 type 필드가 없습니다",
                            "앱 타입(helm, yaml, action 등)을 지정해주세요",
                        )

                # deps (app-group dependencies) 검증
                deps = config.get("deps", [])
                if deps:
                    base_dir = (
                        self.config_dir.parent
                        if self.config_dir.name != "."
                        else Path.cwd()
                    )
                    missing_deps = []
                    for dep in deps:
                        dep_path = base_dir / dep / "config.yaml"
                        if not dep_path.exists():
                            missing_deps.append(dep)

                    if missing_deps:
                        return self.create_result(
                            DiagnosticLevel.ERROR,
                            f"의존성 디렉토리를 찾을 수 없습니다: {', '.join(missing_deps)}",
                            "deps 필드에 명시된 app-group 디렉토리가 존재하지 않습니다",
                        )

                return self.create_result(
                    DiagnosticLevel.SUCCESS,
                    f"설정 파일 유효성 검사 통과 ({len(apps)}개 앱 정의됨)",
                    f"설정 파일: {config_file}",
                )

            except yaml.YAMLError as e:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "설정 파일 YAML 문법 오류",
                    f"YAML 파싱 실패: {e!s}",
                )

        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR, f"설정 파일 검사 실패: {e!s}"
            )


class NetworkAccessCheck(DiagnosticCheck):
    """네트워크 접근성 검사."""

    def __init__(self) -> None:
        super().__init__("network_access", "네트워크 접근성")

    async def run(self) -> DiagnosticResult:
        try:
            # 주요 서비스 연결 테스트
            test_urls = [
                ("Docker Hub", "https://registry-1.docker.io/v2/", 5),
                (
                    "Grafana Charts",
                    "https://grafana.github.io/helm-charts/index.yaml",
                    5,
                ),
                ("Kubernetes", "https://kubernetes.io/", 5),
            ]

            failed_connections = []

            for name, url, timeout in test_urls:
                try:
                    response = requests.get(url, timeout=timeout)
                    if response.status_code >= 400:
                        failed_connections.append(
                            f"{name}: HTTP {response.status_code}"
                        )
                except requests.RequestException as e:
                    failed_connections.append(f"{name}: {e!s}")

            if failed_connections:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "일부 네트워크 연결에 문제가 있습니다",
                    "; ".join(failed_connections),
                )

            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "네트워크 연결 상태 정상",
                "Docker Hub, Grafana Charts, Kubernetes 연결 확인됨",
            )

        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR, f"네트워크 접근성 검사 실패: {e!s}"
            )


class PermissionsCheck(DiagnosticCheck):
    """권한 검사."""

    def __init__(self) -> None:
        super().__init__("permissions", "Kubernetes 권한")

    async def run(self) -> DiagnosticResult:
        try:
            # 기본 권한 확인
            permissions_to_check = [
                ("get", "namespaces"),
                ("create", "namespaces"),
                ("get", "pods"),
                ("create", "deployments"),
                ("create", "services"),
            ]

            failed_permissions = []

            for action, resource in permissions_to_check:
                try:
                    result = subprocess.run(
                        ["kubectl", "auth", "can-i", action, resource],
                        check=False, capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    if result.returncode != 0 or "no" in result.stdout.lower():
                        failed_permissions.append(f"{action} {resource}")

                except subprocess.TimeoutExpired:
                    failed_permissions.append(f"{action} {resource} (시간 초과)")
                except FileNotFoundError:
                    return self.create_result(
                        DiagnosticLevel.ERROR,
                        "kubectl 명령어를 찾을 수 없습니다",
                        "kubectl이 설치되지 않았거나 PATH에 없습니다",
                    )

            if failed_permissions:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "필요한 Kubernetes 권한이 부족합니다",
                    f"부족한 권한: {', '.join(failed_permissions)}",
                    "kubectl config view --minify",
                    "현재 사용자 권한 확인",
                )

            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "Kubernetes 권한 확인 완료",
                "필요한 모든 권한이 있습니다",
            )

        except Exception as e:
            return self.create_result(
                DiagnosticLevel.WARNING,
                f"권한 검사를 완료할 수 없습니다: {e!s}",
                "수동으로 권한을 확인해주세요",
            )


class ResourceAvailabilityCheck(DiagnosticCheck):
    """리소스 가용성 검사."""

    def __init__(self) -> None:
        super().__init__("resource_availability", "클러스터 리소스")

    async def run(self) -> DiagnosticResult:
        try:
            # 노드 상태 확인
            result = subprocess.run(
                ["kubectl", "get", "nodes", "--no-headers"],
                check=False, capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "노드 정보를 가져올 수 없습니다",
                    result.stderr.strip(),
                )

            nodes = result.stdout.strip().split("\n") if result.stdout.strip() else []
            ready_nodes = [
                node for node in nodes if "Ready" in node and "NotReady" not in node
            ]

            if not ready_nodes:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "사용 가능한 노드가 없습니다",
                    "모든 노드가 NotReady 상태입니다",
                )

            # 디스크 공간 확인 (로컬)
            disk_usage = shutil.disk_usage(".")
            free_gb = disk_usage.free / (1024**3)

            if free_gb < 1:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    f"디스크 공간이 부족합니다 ({free_gb:.1f}GB 남음)",
                    "최소 1GB 이상의 여유 공간이 필요합니다",
                )
            if free_gb < 5:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    f"디스크 공간이 부족합니다 ({free_gb:.1f}GB 남음)",
                    "5GB 이상의 여유 공간을 권장합니다",
                )

            return self.create_result(
                DiagnosticLevel.SUCCESS,
                f"리소스 상태 정상 ({len(ready_nodes)}개 노드, {free_gb:.1f}GB 여유 공간)",
                f"Ready 노드: {len(ready_nodes)}, 전체 노드: {len(nodes)}",
            )

        except FileNotFoundError:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "kubectl 명령어를 찾을 수 없습니다",
                "kubectl이 설치되지 않았거나 PATH에 없습니다",
            )
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.WARNING, f"리소스 가용성 검사 실패: {e!s}"
            )
