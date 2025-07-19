import re
from pathlib import Path
from typing import Any


class ContextAwareSuggestions:
    """컨텍스트 인식 제안 시스템"""

    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.suggestion_rules = self._load_suggestion_rules()

    def get_suggestions(self, context: dict[str, Any]) -> list[dict[str, Any]]:
        """컨텍스트 기반 제안 생성"""
        suggestions = []

        # 오류 메시지 기반 제안
        if context.get("error_message"):
            suggestions.extend(self._suggest_from_error(context["error_message"]))

        # 실행 히스토리 기반 제안
        if context.get("recent_failures"):
            suggestions.extend(self._suggest_from_history(context["recent_failures"]))

        # 프로젝트 상태 기반 제안
        if context.get("project_status"):
            suggestions.extend(
                self._suggest_from_project_status(context["project_status"])
            )

        # 환경 기반 제안
        suggestions.extend(self._suggest_from_environment())

        return self._rank_suggestions(suggestions)

    def _suggest_from_error(self, error_message: str) -> list[dict[str, Any]]:
        """오류 메시지 기반 제안"""
        suggestions = []

        error_patterns = {
            r"connection.*refused": {
                "title": "Kubernetes 클러스터 연결 확인",
                "description": "클러스터가 실행 중인지 확인하고 kubeconfig를 점검하세요",
                "commands": ["kubectl cluster-info", "kubectl config current-context"],
                "priority": "high",
            },
            r"namespace.*not found": {
                "title": "네임스페이스 생성",
                "description": "필요한 네임스페이스를 생성하세요",
                "commands": ["kubectl create namespace <namespace-name>"],
                "priority": "medium",
            },
            r"helm.*not found": {
                "title": "Helm 설치",
                "description": "Helm이 설치되지 않았습니다",
                "commands": [
                    "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
                ],
                "priority": "high",
            },
            r"permission denied": {
                "title": "권한 확인",
                "description": "Kubernetes 클러스터에 대한 권한을 확인하세요",
                "commands": ['kubectl auth can-i "*" "*"'],
                "priority": "high",
            },
            r"timed out": {
                "title": "타임아웃 해결",
                "description": "네트워크 연결 또는 리소스 가용성을 확인하세요",
                "commands": ["kubectl get nodes", "kubectl get pods --all-namespaces"],
                "priority": "medium",
            },
            r"no such file or directory": {
                "title": "파일 경로 확인",
                "description": "설정 파일이 올바른 경로에 있는지 확인하세요",
                "commands": ["ls -la config/", 'find . -name "*.yaml"'],
                "priority": "medium",
            },
        }

        for pattern, suggestion in error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                suggestions.append(suggestion)

        return suggestions

    def _suggest_from_history(
        self, recent_failures: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """실행 히스토리 기반 제안"""
        suggestions = []

        # 반복되는 실패 패턴 분석
        failure_patterns = {}
        for failure in recent_failures:
            step = failure.get("step", "unknown")
            failure_patterns[step] = failure_patterns.get(step, 0) + 1

        # 가장 자주 실패하는 단계에 대한 제안
        if failure_patterns:
            most_failed_step = max(failure_patterns, key=failure_patterns.get)
            failure_count = failure_patterns[most_failed_step]

            if failure_count >= 3:
                suggestions.append(
                    {
                        "title": f"{most_failed_step} 단계 반복 실패 해결",
                        "description": f"{most_failed_step} 단계에서 {failure_count}번 실패했습니다. 설정을 점검해보세요.",
                        "commands": [f"sbkube doctor --check {most_failed_step}"],
                        "priority": "high",
                    }
                )

        # 최근 실패 패턴 분석
        if len(recent_failures) > 0:
            latest_failure = recent_failures[-1]
            error_type = latest_failure.get("error_type", "unknown")

            if error_type == "network":
                suggestions.append(
                    {
                        "title": "네트워크 연결 상태 점검",
                        "description": "최근 네트워크 관련 오류가 발생했습니다.",
                        "commands": [
                            "ping 8.8.8.8",
                            "nslookup kubernetes.default.svc.cluster.local",
                        ],
                        "priority": "medium",
                    }
                )
            elif error_type == "resource":
                suggestions.append(
                    {
                        "title": "리소스 사용량 확인",
                        "description": "최근 리소스 관련 오류가 발생했습니다.",
                        "commands": ["kubectl top nodes", "kubectl top pods"],
                        "priority": "medium",
                    }
                )

        return suggestions

    def _suggest_from_project_status(
        self, project_status: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """프로젝트 상태 기반 제안"""
        suggestions = []

        # 설정 파일 검사
        if not (self.base_dir / "config" / "config.yaml").exists():
            suggestions.append(
                {
                    "title": "프로젝트 초기화",
                    "description": "설정 파일이 없습니다. 프로젝트를 초기화하세요.",
                    "commands": ["sbkube init"],
                    "priority": "high",
                }
            )

        # 환경별 설정 확인
        config_dir = self.base_dir / "config"
        if config_dir.exists():
            config_files = list(config_dir.glob("config-*.yaml"))
            if not config_files:
                suggestions.append(
                    {
                        "title": "환경별 설정 추가",
                        "description": "환경별 배포를 위한 프로파일 설정을 추가하세요.",
                        "commands": [
                            "cp config/config.yaml config/config-production.yaml"
                        ],
                        "priority": "medium",
                    }
                )

        # 소스 설정 확인
        if not (self.base_dir / "config" / "sources.yaml").exists():
            suggestions.append(
                {
                    "title": "소스 설정 생성",
                    "description": "애플리케이션 소스 설정이 없습니다.",
                    "commands": ["sbkube init --sources"],
                    "priority": "medium",
                }
            )

        # 빌드 디렉토리 확인
        build_dir = self.base_dir / "build"
        if build_dir.exists() and len(list(build_dir.glob("*"))) == 0:
            suggestions.append(
                {
                    "title": "빌드 아티팩트 정리",
                    "description": "빈 빌드 디렉토리가 있습니다. 정리하거나 빌드를 실행하세요.",
                    "commands": ["rm -rf build/", "sbkube build"],
                    "priority": "low",
                }
            )

        return suggestions

    def _suggest_from_environment(self) -> list[dict[str, Any]]:
        """환경 기반 제안"""
        suggestions = []

        # Docker 확인
        import subprocess

        try:
            result = subprocess.run(
                ["docker", "version"], capture_output=True, timeout=5
            )
            if result.returncode != 0:
                suggestions.append(
                    {
                        "title": "Docker 설치 또는 시작",
                        "description": "Docker가 설치되지 않았거나 실행되지 않고 있습니다.",
                        "commands": ["docker version"],
                        "priority": "medium",
                    }
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            suggestions.append(
                {
                    "title": "Docker 설치",
                    "description": "Docker가 설치되지 않았습니다.",
                    "commands": ["# Docker 설치 가이드를 참조하세요"],
                    "priority": "low",
                }
            )

        # Kubectl 확인
        try:
            result = subprocess.run(
                ["kubectl", "version", "--client"], capture_output=True, timeout=5
            )
            if result.returncode != 0:
                suggestions.append(
                    {
                        "title": "Kubectl 설치",
                        "description": "Kubectl이 설치되지 않았습니다.",
                        "commands": ["# Kubectl 설치 가이드를 참조하세요"],
                        "priority": "medium",
                    }
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            suggestions.append(
                {
                    "title": "Kubectl 설치",
                    "description": "Kubectl이 설치되지 않았습니다.",
                    "commands": ["# Kubectl 설치 가이드를 참조하세요"],
                    "priority": "medium",
                }
            )

        # Helm 확인
        try:
            result = subprocess.run(["helm", "version"], capture_output=True, timeout=5)
            if result.returncode != 0:
                suggestions.append(
                    {
                        "title": "Helm 설치",
                        "description": "Helm이 설치되지 않았습니다.",
                        "commands": [
                            "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
                        ],
                        "priority": "medium",
                    }
                )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            suggestions.append(
                {
                    "title": "Helm 설치",
                    "description": "Helm이 설치되지 않았습니다.",
                    "commands": [
                        "curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
                    ],
                    "priority": "medium",
                }
            )

        return suggestions

    def _rank_suggestions(
        self, suggestions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """제안 우선순위 정렬"""
        priority_order = {"high": 3, "medium": 2, "low": 1}

        return sorted(
            suggestions,
            key=lambda x: priority_order.get(x.get("priority", "low"), 1),
            reverse=True,
        )

    def _load_suggestion_rules(self) -> dict[str, Any]:
        """제안 규칙 로드"""
        # 추후 외부 파일에서 로드 가능
        return {}
