"""Error suggestions database for improved error messages.

이 모듈은 SbkubeError의 각 타입에 대한 해결 방법, 명령어 제안, 문서 링크를 제공합니다.
"""

import re
from typing import Any

_PLACEHOLDER_PATTERN = re.compile(r"<[^>]+>")

# 에러 타입별 가이드 데이터베이스
ERROR_GUIDE: dict[str, dict[str, Any]] = {
    "StorageClassNotFoundError": {
        "title": "StorageClass가 존재하지 않거나 PVC가 Pending 상태입니다",
        "suggestions": [
            "클러스터의 StorageClass 확인 → kubectl get storageclass",
            "K3s 기본값은 'local-path' (standard 아님!)",
            "values.yaml에서 storageClass 수정 필요",
            "PVC 상태 확인 → kubectl get pvc -n <namespace>",
            "기존 PVC 삭제 후 재배포 필요할 수 있음",
        ],
        "commands": {
            "doctor": "시스템 진단 및 StorageClass 확인",
        },
        "doc_link": "docs/07-troubleshooting/storage-issues.md",
        "quick_fix": "kubectl get storageclass",
        "auto_recoverable": False,
        "example_fix": """
# values.yaml 수정 예시 (K3s):
dataStorage:
  storageClass: "local-path"  # "standard" → "local-path"

# PVC 재생성:
kubectl delete pvc <pvc-name> -n <namespace>
sbkube apply <app-dir>
""",
    },
    "HelmRepoNotRegisteredError": {
        "title": "Helm 리포지토리가 로컬에 등록되지 않았습니다",
        "suggestions": [
            "등록된 repo 목록 확인 → helm repo list",
            "sbkube.yaml의 helm_repos 섹션 확인",
            "수동으로 repo 추가 → helm repo add <name> <url>",
            "repo 업데이트 → helm repo update",
        ],
        "commands": {
            "prepare": "소스 준비 (repo 등록 시도)",
            "validate": "설정 파일 유효성 검사",
        },
        "doc_link": "docs/03-configuration/helm-repos.md",
        "quick_fix": "helm repo list && helm repo update",
        "auto_recoverable": True,
        "example_fix": """
# sbkube.yaml에 helm_repos 추가:
settings:
  helm_repos:
    hashicorp: https://helm.releases.hashicorp.com
    bitnami: https://charts.bitnami.com/bitnami

# 또는 수동 추가:
helm repo add hashicorp https://helm.releases.hashicorp.com
helm repo update
""",
    },
    "SchemaValidationError": {
        "title": "Helm 차트 스키마 검증 실패",
        "suggestions": [
            "values.yaml의 필드명이 차트 스키마와 일치하는지 확인",
            "차트 버전 업데이트로 스키마가 변경되었을 수 있음",
            "helm show values <chart>로 허용된 필드 확인",
            "label injection 비활성화 시도 (sbkube 자동 주입 필드 거부 시)",
        ],
        "commands": {
            "validate": "설정 파일 유효성 검사",
        },
        "doc_link": "docs/07-troubleshooting/schema-validation.md",
        "quick_fix": None,
        "auto_recoverable": False,
        "example_fix": """
# 스키마 오류 해결 방법:

# 1. 허용되지 않는 필드 제거
# 오류: "additional properties 'username_attribute' not allowed"
# → values.yaml에서 해당 필드 제거 또는 올바른 필드명으로 변경

# 2. sbkube label injection 비활성화 (strict schema charts):
apps:
  my-app:
    helm_label_injection: false

# 3. 차트 스키마 확인:
helm show values <repo>/<chart> | head -100
""",
    },
    "WebhookConflictError": {
        "title": "Webhook 리소스 충돌이 발생했습니다",
        "suggestions": [
            "기존 webhook 확인 → kubectl get mutatingwebhookconfigurations",
            "충돌하는 webhook 삭제 후 재배포",
            "helm uninstall 후 clean install 시도",
            "Server-Side Apply 충돌일 수 있음",
        ],
        "commands": {
            "delete": "애플리케이션 삭제 후 재배포",
        },
        "doc_link": "docs/07-troubleshooting/webhook-conflicts.md",
        "quick_fix": "kubectl get mutatingwebhookconfigurations",
        "auto_recoverable": False,
        "example_fix": """
# Webhook 충돌 해결:

# 1. 기존 webhook 확인:
kubectl get mutatingwebhookconfigurations
kubectl get validatingwebhookconfigurations

# 2. 충돌하는 webhook 삭제:
kubectl delete mutatingwebhookconfiguration <webhook-name>

# 3. Helm release 완전 삭제 후 재설치:
helm uninstall <release> -n <namespace>
sbkube apply <app-dir>
""",
    },
    "DeploymentTimeoutError": {
        "title": "배포 시간 초과",
        "suggestions": [
            "Pod 상태 확인 → kubectl get pods -n <namespace>",
            "Pod 이벤트 확인 → kubectl describe pod <pod> -n <namespace>",
            "리소스 부족일 수 있음 → kubectl top nodes",
            "이미지 풀 실패일 수 있음 → ImagePullBackOff 확인",
            "timeout 값 증가 고려 (무거운 앱)",
        ],
        "commands": {
            "doctor": "시스템 진단",
            "status": "배포 상태 확인",
        },
        "doc_link": "docs/07-troubleshooting/timeout-issues.md",
        "quick_fix": "kubectl get pods -n <namespace> -o wide",
        "auto_recoverable": False,
        "example_fix": """
# Timeout 문제 진단:

# 1. Pod 상태 확인:
kubectl get pods -n <namespace>
kubectl describe pod <pod-name> -n <namespace>

# 2. 이벤트 확인 (최근 문제 파악):
kubectl get events -n <namespace> --sort-by='.lastTimestamp' | tail -20

# 3. 노드 리소스 확인:
kubectl top nodes
kubectl top pods -n <namespace>

# 4. Timeout 증가 (sbkube.yaml):
apps:
  heavy-app:
    timeout: "10m"  # 기본 5m → 10m
""",
    },
    "ConfigFileNotFoundError": {
        "title": "설정 파일을 찾을 수 없습니다",
        "suggestions": [
            "새 프로젝트인가요? → sbkube init 명령어로 초기화하세요",
            "파일 경로 확인 → ls config.yaml 또는 ls sources.yaml",
            "설정 검증 → sbkube validate <디렉토리>",
        ],
        "commands": {
            "init": "프로젝트 초기화 및 설정 파일 생성",
            "doctor": "시스템 진단 및 문제 파악",
            "validate": "설정 파일 유효성 검사",
        },
        "doc_link": "docs/02-features/commands.md#init",
        "quick_fix": "sbkube init",
        "auto_recoverable": True,
    },
    "KubernetesConnectionError": {
        "title": "Kubernetes 클러스터에 연결할 수 없습니다",
        "suggestions": [
            "클러스터 상태 확인 → kubectl cluster-info",
            "컨텍스트 확인 → kubectl config current-context",
            "kubeconfig 경로 확인 → echo $KUBECONFIG",
            "진단 실행 → sbkube doctor",
        ],
        "commands": {
            "doctor": "시스템 진단 및 Kubernetes 연결 확인",
        },
        "doc_link": "docs/07-troubleshooting/README.md#kubernetes-connection",
        "quick_fix": "sbkube doctor",
        "auto_recoverable": True,
    },
    "HelmNotFoundError": {
        "title": "Helm이 설치되지 않았거나 PATH에 없습니다",
        "suggestions": [
            "Helm 설치 확인 → helm version",
            "PATH 환경변수 확인 → echo $PATH",
            "Helm 설치 → https://helm.sh/docs/intro/install/",
            "진단 실행 → sbkube doctor",
        ],
        "commands": {
            "doctor": "시스템 진단 및 필수 도구 확인",
        },
        "doc_link": "docs/01-getting-started/README.md#prerequisites",
        "quick_fix": None,
        "auto_recoverable": False,
    },
    "HelmChartNotFoundError": {
        "title": "Helm 차트를 찾을 수 없습니다",
        "suggestions": [
            "차트 이름 확인 → helm search repo <차트명>",
            "리포지토리 추가 → helm repo add <이름> <URL>",
            "리포지토리 업데이트 → helm repo update",
            "설정 검증 → sbkube validate <디렉토리>",
        ],
        "commands": {
            "validate": "설정 파일 유효성 검사",
            "prepare": "소스 준비 (차트 다운로드 시도)",
        },
        "doc_link": "docs/02-features/application-types.md#helm",
        "quick_fix": "helm repo update",
        "auto_recoverable": True,
    },
    "GitRepositoryError": {
        "title": "Git 리포지토리를 클론할 수 없습니다",
        "suggestions": [
            "리포지토리 URL 확인 → git ls-remote <URL>",
            "인증 정보 확인 → Git 자격증명 또는 SSH 키",
            "네트워크 연결 확인 → ping github.com",
            "설정 검증 → sbkube validate <디렉토리>",
        ],
        "commands": {
            "validate": "설정 파일 유효성 검사",
            "prepare": "소스 준비 재시도",
        },
        "doc_link": "docs/02-features/application-types.md#git-repositories",
        "quick_fix": None,
        "auto_recoverable": False,
    },
    "NamespaceNotFoundError": {
        "title": "Kubernetes 네임스페이스를 찾을 수 없습니다",
        "suggestions": [
            "네임스페이스 목록 확인 → kubectl get namespaces",
            "네임스페이스 생성 → kubectl create namespace <이름>",
            "설정 파일 확인 → config.yaml의 namespace 필드",
        ],
        "commands": {
            "deploy": "--create-namespace 옵션 사용",
        },
        "doc_link": "docs/02-features/commands.md#deploy",
        "quick_fix": "kubectl create namespace <NAMESPACE>",
        "auto_recoverable": True,
    },
    "ValidationError": {
        "title": "설정 파일 검증 실패",
        "suggestions": [
            "설정 파일 구문 확인 → YAML 문법 오류",
            "필수 필드 확인 → name, type, specs 등",
            "스키마 참조 → docs/03-configuration/config-schema.md",
            "검증 도구 실행 → sbkube validate <디렉토리>",
        ],
        "commands": {
            "validate": "설정 파일 유효성 검사 (상세 오류 표시)",
        },
        "doc_link": "docs/03-configuration/config-schema.md",
        "quick_fix": "sbkube validate .",
        "auto_recoverable": True,
    },
    "DeploymentFailedError": {
        "title": "배포 실패",
        "suggestions": [
            "배포 로그 확인 → kubectl logs <pod-name> -n <namespace>",
            "이벤트 확인 → kubectl get events -n <namespace>",
            "리소스 상태 확인 → kubectl get all -n <namespace>",
            "히스토리 확인 → sbkube history --namespace <namespace>",
            "진단 실행 → sbkube doctor",
        ],
        "commands": {
            "history": "배포 히스토리 조회",
            "doctor": "시스템 진단",
            "state": "배포 상태 관리",
        },
        "doc_link": "docs/07-troubleshooting/README.md#deployment-failures",
        "quick_fix": "sbkube doctor",
        "auto_recoverable": True,
    },
    "PermissionDeniedError": {
        "title": "권한이 없습니다",
        "suggestions": [
            "현재 사용자 확인 → kubectl auth whoami",
            "권한 확인 → kubectl auth can-i <동사> <리소스>",
            "RBAC 설정 확인 → kubectl get rolebindings,clusterrolebindings",
            "클러스터 관리자에게 문의하세요",
        ],
        "commands": {},
        "doc_link": "docs/07-troubleshooting/README.md#permission-issues",
        "quick_fix": None,
        "auto_recoverable": False,
    },
    "ResourceQuotaExceededError": {
        "title": "리소스 쿼터 초과",
        "suggestions": [
            "네임스페이스 쿼터 확인 → kubectl get resourcequota -n <namespace>",
            "현재 리소스 사용량 확인 → kubectl top nodes",
            "불필요한 리소스 정리 → kubectl delete <리소스>",
            "쿼터 증설 요청 → 클러스터 관리자에게 문의",
        ],
        "commands": {
            "delete": "불필요한 애플리케이션 삭제",
            "state": "배포 상태 확인",
        },
        "doc_link": "docs/07-troubleshooting/README.md#resource-quota",
        "quick_fix": None,
        "auto_recoverable": False,
    },
    "DatabaseAuthenticationError": {
        "title": "데이터베이스 인증 실패",
        "suggestions": [
            "DB 사용자/비밀번호 확인 → kubectl get secret -n <namespace>",
            "Secret 내용 확인 → kubectl get secret <secret-name> -o jsonpath='{.data}'",
            "config.yaml의 database 설정 확인 (password, user, host)",
            "데이터베이스 직접 연결 테스트 → psql/mysql 명령어 사용",
            "Secret이 올바른 네임스페이스에 있는지 확인",
        ],
        "commands": {
            "validate": "설정 파일 검증",
            "doctor": "시스템 진단 및 연결 확인",
        },
        "doc_link": "docs/07-troubleshooting/database-connection.md",
        "quick_fix": "kubectl get secret -n <namespace>",
        "auto_recoverable": False,
    },
    "DatabaseConnectionError": {
        "title": "데이터베이스 연결 실패",
        "suggestions": [
            "DB 서비스 상태 확인 → kubectl get svc -n <namespace>",
            "DB Pod 상태 확인 → kubectl get pods -n <namespace>",
            "네트워크 정책 확인 → NetworkPolicy 설정",
            "DB 로그 확인 → kubectl logs <db-pod> -n <namespace>",
            "호스트명/포트 확인 → config.yaml의 database.host, database.port",
        ],
        "commands": {
            "doctor": "시스템 진단",
        },
        "doc_link": "docs/07-troubleshooting/database-connection.md",
        "quick_fix": "kubectl get svc,pods -n <namespace>",
        "auto_recoverable": False,
    },
    "SSAConflictError": {
        "title": "Helm SSA(Server-Side Apply) 필드 관리자 충돌",
        "suggestions": [
            "Helm 4는 SSA가 기본값 → Helm 3에서 업그레이드 시 필드 소유권 충돌 발생",
            "즉시 해결: sbkube.yaml의 해당 app에 force_conflicts: true 추가",
            "영구 해결: sbkube migrate 명령어로 필드 관리자 마이그레이션",
            "충돌 release 확인 → helm list -A | grep failed",
            "진단 실행 → sbkube doctor (helm_field_manager 검사)",
            "수동 해결 → kubectl apply --server-side --force-conflicts --field-manager=helm",
        ],
        "commands": {
            "migrate": "Helm 3→4 SSA 필드 관리자 마이그레이션",
            "doctor": "시스템 진단 및 SSA 충돌 확인",
        },
        "doc_link": "docs/07-troubleshooting/ssa-migration.md",
        "quick_fix": "sbkube migrate --dry-run",
        "auto_recoverable": False,
        "example_fix": """
# sbkube.yaml에서 즉시 해결:
apps:
  traefik:
    force_conflicts: true  # SSA 충돌 무시

# 또는 영구 마이그레이션:
sbkube migrate ph1_infra/app_010_infra_network
""",
    },
    "HelmReleaseError": {
        "title": "Helm 릴리스 배포 실패",
        "suggestions": [
            "Helm 릴리스 상태 확인 → helm list -n <namespace>",
            "릴리스 히스토리 확인 → helm history <release> -n <namespace>",
            "실패한 릴리스 삭제 → helm uninstall <release> -n <namespace>",
            "Pending 릴리스 정리 → helm rollback 또는 helm uninstall",
            "Pod 이벤트 확인 → kubectl describe pod <pod-name> -n <namespace>",
        ],
        "commands": {
            "delete": "애플리케이션 삭제 후 재배포",
            "state": "배포 상태 확인",
        },
        "doc_link": "docs/07-troubleshooting/deployment-failures.md#helm-release-errors",
        "quick_fix": "helm list -n <namespace>",
        "auto_recoverable": True,
    },
    "UnknownError": {
        "title": "분류되지 않은 에러",
        "suggestions": [
            "전체 에러 로그 확인",
            "시스템 진단 실행 → sbkube doctor",
            "배포 히스토리 확인 → sbkube history",
            "상세 로그 확인 → kubectl logs, kubectl describe",
        ],
        "commands": {
            "doctor": "시스템 진단",
            "history": "배포 히스토리 확인",
        },
        "doc_link": "docs/07-troubleshooting/README.md",
        "quick_fix": "sbkube doctor",
        "auto_recoverable": False,
    },
}


def get_error_suggestions(error_type: str) -> dict[str, Any] | None:
    """에러 타입에 대한 제안 정보를 반환합니다.

    Args:
        error_type: 에러 클래스 이름 (예: "ConfigFileNotFoundError")

    Returns:
        에러 가이드 딕셔너리 또는 None

    """
    return ERROR_GUIDE.get(error_type)


def format_suggestions(error_type: str) -> str:
    """에러 타입에 대한 제안을 포맷팅된 문자열로 반환합니다.

    Args:
        error_type: 에러 클래스 이름

    Returns:
        포맷팅된 제안 문자열

    """
    guide = get_error_suggestions(error_type)
    if not guide:
        return ""

    lines = []
    lines.append(f"\n💡 {guide['title']}")
    lines.append("\n📋 해결 방법:")
    for suggestion in guide["suggestions"]:
        lines.append(f"  • {suggestion}")

    if guide["commands"]:
        lines.append("\n🔧 유용한 명령어:")
        for cmd, desc in guide["commands"].items():
            lines.append(f"  • sbkube {cmd}: {desc}")

    if guide["doc_link"]:
        lines.append(f"\n📖 자세한 내용: {guide['doc_link']}")

    if guide["quick_fix"]:
        lines.append(f"\n⚡ 빠른 해결: {guide['quick_fix']}")

    return "\n".join(lines)


def get_quick_fix_command(error_type: str) -> str | None:
    """에러 타입에 대한 빠른 해결 명령어를 반환합니다.

    Args:
        error_type: 에러 클래스 이름

    Returns:
        빠른 해결 명령어 또는 None

    """
    guide = get_error_suggestions(error_type)
    if not guide:
        return None
    return guide.get("quick_fix")


def has_placeholder(command: str) -> bool:
    """Check whether a quick-fix command contains placeholders like <value>."""
    return bool(_PLACEHOLDER_PATTERN.search(command))


def is_auto_recoverable(error_type: str) -> bool:
    """에러가 자동 복구 가능한지 확인합니다.

    Args:
        error_type: 에러 클래스 이름

    Returns:
        자동 복구 가능 여부

    """
    guide = get_error_suggestions(error_type)
    if not guide:
        return False
    return guide.get("auto_recoverable", False)
