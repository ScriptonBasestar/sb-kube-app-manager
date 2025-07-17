import subprocess
import asyncio
from pathlib import Path
import yaml
import requests
import shutil
import os
from typing import Optional

from sbkube.utils.diagnostic_system import DiagnosticCheck, DiagnosticLevel, DiagnosticResult
from sbkube.utils.logger import logger


class KubernetesConnectivityCheck(DiagnosticCheck):
    """Kubernetes 연결성 검사"""
    
    def __init__(self):
        super().__init__("k8s_connectivity", "Kubernetes 클러스터 연결")
    
    async def run(self) -> DiagnosticResult:
        try:
            # kubectl 설치 확인
            result = subprocess.run(
                ["kubectl", "version", "--client=true", "--short"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "kubectl이 설치되지 않았습니다",
                    "Kubernetes CLI 도구가 필요합니다",
                    "curl -LO \"https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/$(uname -s | tr '[:upper:]' '[:lower:]')/$(uname -m)/kubectl\" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/",
                    "kubectl 최신 버전 설치"
                )
            
            # 클러스터 연결 확인
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "Kubernetes 클러스터에 연결할 수 없습니다",
                    result.stderr.strip(),
                    "kubectl config get-contexts",
                    "kubeconfig 설정 확인"
                )
            
            # 클러스터 버전 확인
            result = subprocess.run(
                ["kubectl", "version", "--short"],
                capture_output=True, text=True, timeout=10
            )
            
            cluster_info = result.stdout.strip() if result.returncode == 0 else "버전 정보 없음"
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "Kubernetes 클러스터 연결 정상",
                cluster_info
            )
            
        except subprocess.TimeoutExpired:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "Kubernetes 연결 시간 초과",
                "클러스터 응답이 너무 느립니다"
            )
        except FileNotFoundError:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "kubectl 명령어를 찾을 수 없습니다",
                "kubectl이 설치되지 않았거나 PATH에 없습니다",
                "curl -LO \"https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/$(uname -s | tr '[:upper:]' '[:lower:]')/$(uname -m)/kubectl\" && chmod +x kubectl && sudo mv kubectl /usr/local/bin/",
                "kubectl 설치"
            )
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"Kubernetes 연결 검사 실패: {str(e)}"
            )


class HelmInstallationCheck(DiagnosticCheck):
    """Helm 설치 상태 검사"""
    
    def __init__(self):
        super().__init__("helm_installation", "Helm 설치 상태")
    
    async def run(self) -> DiagnosticResult:
        try:
            # Helm 설치 확인
            result = subprocess.run(
                ["helm", "version", "--short"],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "Helm이 설치되지 않았습니다",
                    "Kubernetes 패키지 매니저가 필요합니다",
                    "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                    "Helm 3 최신 버전 설치"
                )
            
            # 버전 확인
            version_output = result.stdout.strip()
            if "v2." in version_output:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "Helm v2가 설치되어 있습니다",
                    "Helm v3 사용을 권장합니다",
                    "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                    "Helm v3로 업그레이드"
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                f"Helm 설치 상태 정상: {version_output}"
            )
            
        except FileNotFoundError:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "Helm이 설치되지 않았습니다",
                "PATH에서 helm 명령어를 찾을 수 없습니다",
                "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash",
                "Helm 3 설치"
            )
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"Helm 설치 확인 실패: {str(e)}"
            )


class ConfigValidityCheck(DiagnosticCheck):
    """설정 파일 유효성 검사"""
    
    def __init__(self, config_dir: str = "config"):
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
                    "프로젝트 초기화로 설정 파일 생성"
                )
            
            # 첫 번째 설정 파일 검사
            config_file = config_files[0]
            
            # YAML 파싱 확인
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                if not config:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        "설정 파일이 비어있습니다",
                        f"{config_file}에 유효한 설정이 없습니다"
                    )
                
                # 필수 필드 확인
                required_fields = ['namespace', 'apps']
                missing_fields = [field for field in required_fields if field not in config]
                
                if missing_fields:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        f"필수 설정이 누락되었습니다: {', '.join(missing_fields)}",
                        "설정 파일을 확인하고 필수 필드를 추가해주세요"
                    )
                
                # 앱 설정 검증
                apps = config.get('apps', [])
                if not apps:
                    return self.create_result(
                        DiagnosticLevel.WARNING,
                        "배포할 앱이 정의되지 않았습니다",
                        "apps 섹션에 하나 이상의 앱을 정의해주세요"
                    )
                
                # 각 앱의 필수 필드 확인
                for i, app in enumerate(apps):
                    if 'name' not in app:
                        return self.create_result(
                            DiagnosticLevel.ERROR,
                            f"앱 #{i+1}에 name 필드가 없습니다",
                            "모든 앱에는 name 필드가 필요합니다"
                        )
                    
                    if 'type' not in app:
                        return self.create_result(
                            DiagnosticLevel.ERROR,
                            f"앱 '{app.get('name', f'#{i+1}')}에 type 필드가 없습니다",
                            "앱 타입(install-helm, install-yaml 등)을 지정해주세요"
                        )
                
                return self.create_result(
                    DiagnosticLevel.SUCCESS,
                    f"설정 파일 유효성 검사 통과 ({len(apps)}개 앱 정의됨)",
                    f"설정 파일: {config_file}"
                )
                
            except yaml.YAMLError as e:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "설정 파일 YAML 문법 오류",
                    f"YAML 파싱 실패: {str(e)}"
                )
                
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"설정 파일 검사 실패: {str(e)}"
            )


class NetworkAccessCheck(DiagnosticCheck):
    """네트워크 접근성 검사"""
    
    def __init__(self):
        super().__init__("network_access", "네트워크 접근성")
    
    async def run(self) -> DiagnosticResult:
        try:
            # 주요 서비스 연결 테스트
            test_urls = [
                ("Docker Hub", "https://registry-1.docker.io/v2/", 5),
                ("Bitnami Charts", "https://charts.bitnami.com/bitnami/index.yaml", 5),
                ("Kubernetes", "https://kubernetes.io/", 5)
            ]
            
            failed_connections = []
            
            for name, url, timeout in test_urls:
                try:
                    response = requests.get(url, timeout=timeout)
                    if response.status_code >= 400:
                        failed_connections.append(f"{name}: HTTP {response.status_code}")
                except requests.RequestException as e:
                    failed_connections.append(f"{name}: {str(e)}")
            
            if failed_connections:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "일부 네트워크 연결에 문제가 있습니다",
                    "; ".join(failed_connections)
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "네트워크 연결 상태 정상",
                "Docker Hub, Bitnami Charts, Kubernetes 연결 확인됨"
            )
            
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.ERROR,
                f"네트워크 접근성 검사 실패: {str(e)}"
            )


class PermissionsCheck(DiagnosticCheck):
    """권한 검사"""
    
    def __init__(self):
        super().__init__("permissions", "Kubernetes 권한")
    
    async def run(self) -> DiagnosticResult:
        try:
            # 기본 권한 확인
            permissions_to_check = [
                ("get", "namespaces"),
                ("create", "namespaces"), 
                ("get", "pods"),
                ("create", "deployments"),
                ("create", "services")
            ]
            
            failed_permissions = []
            
            for action, resource in permissions_to_check:
                try:
                    result = subprocess.run([
                        "kubectl", "auth", "can-i", action, resource
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode != 0 or "no" in result.stdout.lower():
                        failed_permissions.append(f"{action} {resource}")
                        
                except subprocess.TimeoutExpired:
                    failed_permissions.append(f"{action} {resource} (시간 초과)")
                except FileNotFoundError:
                    return self.create_result(
                        DiagnosticLevel.ERROR,
                        "kubectl 명령어를 찾을 수 없습니다",
                        "kubectl이 설치되지 않았거나 PATH에 없습니다"
                    )
            
            if failed_permissions:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "필요한 Kubernetes 권한이 부족합니다",
                    f"부족한 권한: {', '.join(failed_permissions)}",
                    "kubectl config view --minify",
                    "현재 사용자 권한 확인"
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                "Kubernetes 권한 확인 완료",
                "필요한 모든 권한이 있습니다"
            )
            
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.WARNING,
                f"권한 검사를 완료할 수 없습니다: {str(e)}",
                "수동으로 권한을 확인해주세요"
            )


class ResourceAvailabilityCheck(DiagnosticCheck):
    """리소스 가용성 검사"""
    
    def __init__(self):
        super().__init__("resource_availability", "클러스터 리소스")
    
    async def run(self) -> DiagnosticResult:
        try:
            # 노드 상태 확인
            result = subprocess.run([
                "kubectl", "get", "nodes", "--no-headers"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    "노드 정보를 가져올 수 없습니다",
                    result.stderr.strip()
                )
            
            nodes = result.stdout.strip().split('\n') if result.stdout.strip() else []
            ready_nodes = [node for node in nodes if 'Ready' in node and 'NotReady' not in node]
            
            if not ready_nodes:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    "사용 가능한 노드가 없습니다",
                    "모든 노드가 NotReady 상태입니다"
                )
            
            # 디스크 공간 확인 (로컬)
            disk_usage = shutil.disk_usage('.')
            free_gb = disk_usage.free / (1024**3)
            
            if free_gb < 1:
                return self.create_result(
                    DiagnosticLevel.ERROR,
                    f"디스크 공간이 부족합니다 ({free_gb:.1f}GB 남음)",
                    "최소 1GB 이상의 여유 공간이 필요합니다"
                )
            elif free_gb < 5:
                return self.create_result(
                    DiagnosticLevel.WARNING,
                    f"디스크 공간이 부족합니다 ({free_gb:.1f}GB 남음)",
                    "5GB 이상의 여유 공간을 권장합니다"
                )
            
            return self.create_result(
                DiagnosticLevel.SUCCESS,
                f"리소스 상태 정상 ({len(ready_nodes)}개 노드, {free_gb:.1f}GB 여유 공간)",
                f"Ready 노드: {len(ready_nodes)}, 전체 노드: {len(nodes)}"
            )
            
        except FileNotFoundError:
            return self.create_result(
                DiagnosticLevel.ERROR,
                "kubectl 명령어를 찾을 수 없습니다",
                "kubectl이 설치되지 않았거나 PATH에 없습니다"
            )
        except Exception as e:
            return self.create_result(
                DiagnosticLevel.WARNING,
                f"리소스 가용성 검사 실패: {str(e)}"
            )