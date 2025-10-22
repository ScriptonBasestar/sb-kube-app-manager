"""
SBKube v0.3.0 Configuration Models - Breaking Change

완전히 새로운 설정 구조:
- apps: list → dict (key = app name)
- 타입 통합: pull-helm + install-helm → helm
- specs 제거: 모든 필드 평탄화
- 의존성 명시: depends_on 필드
"""

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from .base_model import ConfigBaseModel


# ============================================================================
# App Type Models (Discriminated Union)
# ============================================================================


class HelmApp(ConfigBaseModel):
    """
    Helm 차트 배포 앱.

    지원하는 chart 형식:
    1. Remote chart: "repo/chart" (예: "bitnami/redis")
       → 자동으로 pull 후 install
    2. Local chart: "./charts/my-chart" (상대 경로)
       → 로컬 차트를 직접 install
    3. Absolute path: "/path/to/chart"
       → 절대 경로 차트 install

    Examples:
        # Remote chart (자동 pull + install)
        redis:
          type: helm
          chart: bitnami/redis
          version: 17.13.2
          values:
            - redis.yaml

        # Local chart (install only)
        my-app:
          type: helm
          chart: ./charts/my-app
          values:
            - values.yaml
    """

    type: Literal["helm"] = "helm"
    chart: str  # "repo/chart", "./path", "/path" 형식
    version: str | None = None  # chart version (remote chart만 해당)
    values: list[str] = Field(default_factory=list)  # values 파일 목록

    # 커스터마이징 (v0.2.x 호환)
    overrides: list[str] = Field(default_factory=list)  # overrides/ 디렉토리의 파일로 교체
    removes: list[str] = Field(default_factory=list)  # 빌드 시 제거할 파일/디렉토리 패턴

    # Helm 옵션
    set_values: dict[str, Any] = Field(default_factory=dict)  # --set 옵션
    release_name: str | None = None  # 릴리스 이름 (기본값: 앱 이름)
    namespace: str | None = None  # 네임스페이스 오버라이드
    create_namespace: bool = False
    wait: bool = True
    timeout: str = "5m"
    atomic: bool = False

    # 메타데이터
    labels: dict[str, str] = Field(default_factory=dict)  # Kubernetes labels
    annotations: dict[str, str] = Field(default_factory=dict)  # Kubernetes annotations

    # 제어
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("chart")
    @classmethod
    def validate_chart(cls, v: str) -> str:
        """
        chart 형식 검증.

        허용되는 형식:
        - "repo/chart" (remote)
        - "./path" (relative local)
        - "/path" (absolute local)
        """
        if not v or not v.strip():
            raise ValueError("chart cannot be empty")
        return v.strip()

    def is_remote_chart(self) -> bool:
        """
        Remote chart 여부 판단.

        Returns:
            True if "repo/chart" 형식, False if local path
        """
        # 로컬 경로 패턴
        if self.chart.startswith("./") or self.chart.startswith("/"):
            return False
        # repo/chart 형식
        if "/" in self.chart and not self.chart.startswith("."):
            return True
        # chart만 있는 경우는 로컬로 간주
        return False

    def get_repo_name(self) -> str | None:
        """
        repo 이름 추출 (remote chart만).

        Returns:
            repo 이름 (예: 'bitnami/redis' → 'bitnami') 또는 None (local chart)
        """
        if not self.is_remote_chart():
            return None
        return self.chart.split("/")[0]

    def get_chart_name(self) -> str:
        """
        chart 이름 추출.

        Returns:
            chart 이름 (예: 'bitnami/redis' → 'redis', './my-chart' → 'my-chart')
        """
        if self.is_remote_chart():
            return self.chart.split("/")[1]
        # 로컬 경로에서 마지막 부분 추출
        return self.chart.rstrip("/").split("/")[-1]


class YamlApp(ConfigBaseModel):
    """
    YAML 매니페스트 직접 배포 앱.

    kubectl apply -f 로 배포.

    Examples:
        my-app:
          type: yaml
          files:
            - deployment.yaml
            - service.yaml
          namespace: custom-ns
    """

    type: Literal["yaml"] = "yaml"
    files: list[str]  # YAML 파일 목록
    namespace: str | None = None
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("files")
    @classmethod
    def validate_files(cls, v: list[str]) -> list[str]:
        """파일 목록이 비어있지 않은지 확인."""
        return cls.validate_non_empty_list(v, "files")


class ActionApp(ConfigBaseModel):
    """
    커스텀 액션 실행 앱 (apply/create/delete).

    Examples:
        setup:
          type: action
          actions:
            - type: apply
              path: setup.yaml
            - type: create
              path: configmap.yaml
    """

    type: Literal["action"] = "action"
    actions: list[dict[str, Any]]  # FileActionSpec 형태
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, v: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """액션 목록이 비어있지 않은지 확인."""
        return cls.validate_non_empty_list(v, "actions")


class ExecApp(ConfigBaseModel):
    """
    커스텀 명령어 실행 앱.

    Examples:
        post-install:
          type: exec
          commands:
            - echo "Deployment completed"
            - kubectl get pods
    """

    type: Literal["exec"] = "exec"
    commands: list[str]
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, v: list[str]) -> list[str]:
        """명령어 목록이 비어있지 않은지 확인."""
        return cls.validate_non_empty_list(v, "commands")


class GitApp(ConfigBaseModel):
    """
    Git 리포지토리에서 매니페스트 가져오기 앱.

    Examples:
        my-repo:
          type: git
          repo: https://github.com/user/repo
          path: k8s/
          branch: main
    """

    type: Literal["git"] = "git"
    repo: str  # Git repository URL
    path: str | None = None  # 리포지토리 내 경로
    branch: str = "main"  # Git branch/tag
    ref: str | None = None  # 특정 commit/tag (branch보다 우선)
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Git repo URL 검증."""
        if not v or not v.strip():
            raise ValueError("repo cannot be empty")
        return v.strip()


class KustomizeApp(ConfigBaseModel):
    """
    Kustomize 기반 배포 앱.

    Examples:
        kustomize-app:
          type: kustomize
          path: overlays/production
          namespace: prod
    """

    type: Literal["kustomize"] = "kustomize"
    path: str  # kustomization.yaml이 있는 디렉토리
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("path")
    @classmethod
    def validate_kustomize_path(cls, v: str) -> str:
        """Kustomize 경로 검증."""
        return cls.validate_path_exists(v, must_exist=False)


class HttpApp(ConfigBaseModel):
    """
    HTTP URL에서 파일 다운로드 앱.

    Examples:
        external-manifest:
          type: http
          url: https://raw.githubusercontent.com/example/repo/main/manifest.yaml
          dest: manifests/external.yaml
    """

    type: Literal["http"] = "http"
    url: str  # HTTP(S) URL
    dest: str  # 저장할 파일 경로 (app_dir 기준)
    headers: dict[str, str] = Field(default_factory=dict)  # HTTP 헤더
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, v: str) -> str:
        """HTTP URL 검증."""
        if not v or not v.strip():
            raise ValueError("url cannot be empty")
        if not v.startswith(("http://", "https://")):
            raise ValueError("url must start with http:// or https://")
        return v.strip()


# ============================================================================
# Discriminated Union
# ============================================================================

AppConfig = Annotated[
    Union[HelmApp, YamlApp, ActionApp, ExecApp, GitApp, KustomizeApp, HttpApp],
    Field(discriminator="type"),
]


# ============================================================================
# Main Configuration Model
# ============================================================================


class SBKubeConfigV3(ConfigBaseModel):
    """
    SBKube v0.3.0 메인 설정 모델.

    Breaking Changes:
    - apps: list → dict (key = app name)
    - pull-helm + install-helm → helm (자동 처리)
    - specs 제거 (모든 필드 평탄화)
    - 의존성 명시 (depends_on)

    Examples:
        namespace: production

        apps:
          redis:
            type: helm
            chart: bitnami/redis
            version: 17.13.2
            values:
              - redis.yaml

          backend:
            type: helm
            chart: my-org/backend
            depends_on:
              - redis

          custom:
            type: yaml
            files:
              - deployment.yaml
    """

    namespace: str
    apps: dict[str, AppConfig] = Field(default_factory=dict)
    global_labels: dict[str, str] = Field(default_factory=dict)
    global_annotations: dict[str, str] = Field(default_factory=dict)

    @field_validator("namespace")
    @classmethod
    def validate_namespace_name(cls, v: str) -> str:
        """네임스페이스 이름 검증."""
        return cls.validate_kubernetes_name(v, "namespace")

    @field_validator("apps")
    @classmethod
    def validate_app_names(cls, v: dict[str, AppConfig]) -> dict[str, AppConfig]:
        """앱 이름이 Kubernetes 네이밍 규칙을 따르는지 검증."""
        for app_name in v.keys():
            cls.validate_kubernetes_name(app_name, "app_name")
        return v

    @model_validator(mode="after")
    def apply_namespace_inheritance(self) -> "SBKubeConfigV3":
        """
        네임스페이스 상속 및 글로벌 레이블/어노테이션 적용.

        앱에 namespace가 없으면 전역 namespace 사용.
        """
        for app_name, app in self.apps.items():
            # 네임스페이스 상속 (HelmApp, YamlApp 등에만 적용)
            if hasattr(app, "namespace") and app.namespace is None:
                app.namespace = self.namespace

            # 글로벌 레이블/어노테이션은 Helm 앱에만 적용 가능
            # (향후 확장 가능)

        return self

    @model_validator(mode="after")
    def validate_dependencies(self) -> "SBKubeConfigV3":
        """
        의존성 검증:
        1. 존재하지 않는 앱에 대한 의존성 체크
        2. 순환 의존성 체크
        """
        app_names = set(self.apps.keys())

        # 1. 존재하지 않는 앱 참조 체크
        for app_name, app in self.apps.items():
            if hasattr(app, "depends_on"):
                for dep in app.depends_on:
                    if dep not in app_names:
                        raise ValueError(f"App '{app_name}' depends on non-existent app '{dep}'")

        # 2. 순환 의존성 체크 (DFS 기반)
        visited = set()
        rec_stack = set()

        def has_cycle(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            app = self.apps[node]
            if hasattr(app, "depends_on"):
                for dep in app.depends_on:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True

            rec_stack.remove(node)
            return False

        for app_name in self.apps.keys():
            if app_name not in visited:
                if has_cycle(app_name):
                    raise ValueError(f"Circular dependency detected involving app '{app_name}'")

        return self

    def get_enabled_apps(self) -> dict[str, AppConfig]:
        """활성화된 앱만 반환."""
        return {name: app for name, app in self.apps.items() if app.enabled}

    def get_deployment_order(self) -> list[str]:
        """
        의존성을 고려한 배포 순서 반환 (위상 정렬).

        Returns:
            배포할 앱 이름 리스트 (순서대로)
        """
        enabled_apps = self.get_enabled_apps()
        in_degree = {name: 0 for name in enabled_apps}
        graph = {name: [] for name in enabled_apps}

        # 그래프 구성
        for name, app in enabled_apps.items():
            if hasattr(app, "depends_on"):
                for dep in app.depends_on:
                    if dep in enabled_apps:  # 활성화된 앱에만 의존
                        graph[dep].append(name)
                        in_degree[name] += 1

        # 위상 정렬 (Kahn's algorithm)
        queue = [name for name, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # 알파벳 순서로 정렬하여 일관성 보장
            queue.sort()
            node = queue.pop(0)
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(enabled_apps):
            raise ValueError("Circular dependency detected (this should not happen)")

        return result

    def get_apps_by_type(self, app_type: str) -> dict[str, AppConfig]:
        """특정 타입의 앱만 반환."""
        return {name: app for name, app in self.apps.items() if app.type == app_type and app.enabled}
