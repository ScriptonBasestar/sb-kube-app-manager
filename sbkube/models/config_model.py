"""SBKube Configuration Models.

설정 구조:
- apps: dict (key = app name)
- 타입: helm, yaml, git, http, action, exec, noop
- 의존성: depends_on 필드
"""

from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from .base_model import ConfigBaseModel

# ============================================================================
# Hook Models
# ============================================================================


# ----------------------------------------------------------------------------
# Phase 2: Hook Task Models (Type System)
# ----------------------------------------------------------------------------


class ManifestsHookTask(ConfigBaseModel):
    """Manifests 타입 Hook Task.

    YAML manifest 파일들을 배포합니다 (kubectl apply).

    Examples:
        - type: manifests
          name: deploy-issuers
          files:
            - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
            - manifests/issuers/cluster-issuer-letsencrypt-stg.yaml
          validation:
            kind: ClusterIssuer
            wait_for_ready: true
          dependency:
            depends_on:
              - deploy-secrets
          rollback:
            enabled: true
            manifests:
              - manifests/cleanup-issuers.yaml

    """

    type: Literal["manifests"] = "manifests"
    name: str = Field(..., description="Task 이름 (식별용)")
    files: list[str] = Field(
        ...,
        description="배포할 YAML manifest 파일 경로 리스트",
        json_schema_extra={
            "examples": [["manifests/issuer1.yaml", "manifests/issuer2.yaml"]]
        },
    )
    # Phase 3 fields (forward reference로 처리)
    validation: dict[str, Any] | None = Field(
        default=None,
        description="검증 설정 (ValidationRule 타입)",
    )
    dependency: dict[str, Any] | None = Field(
        default=None,
        description="의존성 설정 (DependencyConfig 타입)",
    )
    rollback: dict[str, Any] | None = Field(
        default=None,
        description="롤백 정책 (RollbackPolicy 타입)",
    )


class InlineHookTask(ConfigBaseModel):
    """Inline 타입 Hook Task.

    YAML 콘텐츠를 인라인으로 배포합니다.

    Examples:
        - type: inline
          name: create-certificate
          content:
            apiVersion: cert-manager.io/v1
            kind: Certificate
            metadata:
              name: wildcard-cert
            spec:
              secretName: wildcard-cert-tls
              issuerRef:
                name: letsencrypt-prd
                kind: ClusterIssuer
          validation:
            kind: Certificate
            name: wildcard-cert
            wait_for_ready: true
          dependency:
            depends_on:
              - deploy-issuers

    """

    type: Literal["inline"] = "inline"
    name: str = Field(..., description="Task 이름 (식별용)")
    content: dict[str, Any] = Field(
        ...,
        description="배포할 YAML 콘텐츠 (dict 형태)",
    )
    # Phase 3 fields
    validation: dict[str, Any] | None = Field(
        default=None,
        description="검증 설정 (ValidationRule 타입)",
    )
    dependency: dict[str, Any] | None = Field(
        default=None,
        description="의존성 설정 (DependencyConfig 타입)",
    )
    rollback: dict[str, Any] | None = Field(
        default=None,
        description="롤백 정책 (RollbackPolicy 타입)",
    )


class CommandHookTask(ConfigBaseModel):
    """Command 타입 Hook Task (개선된 shell 명령어 실행).

    Shell 명령어를 실행하며, retry 및 on_failure 정책을 지원합니다.

    Examples:
        - type: command
          name: verify-dns
          command: |
            dig +short letsencrypt.example.com @8.8.8.8
          retry:
            max_attempts: 3
            delay: 5
          on_failure: warn
          dependency:
            depends_on:
              - deploy-issuers
            wait_for:
              - kind: Pod
                label_selector: app=coredns
                condition: Ready

    """

    type: Literal["command"] = "command"
    name: str = Field(..., description="Task 이름 (식별용)")
    command: str = Field(..., description="실행할 shell 명령어")
    retry: dict[str, Any] | None = Field(
        default=None,
        description="재시도 설정 (max_attempts, delay)",
        json_schema_extra={"examples": [{"max_attempts": 3, "delay": 5}]},
    )
    on_failure: Literal["fail", "warn", "ignore"] = Field(
        default="fail",
        description="실패 시 동작 (fail: 중단, warn: 경고만, ignore: 무시)",
    )
    # Phase 3 fields
    validation: dict[str, Any] | None = Field(
        default=None,
        description="검증 설정 (ValidationRule 타입)",
    )
    dependency: dict[str, Any] | None = Field(
        default=None,
        description="의존성 설정 (DependencyConfig 타입)",
    )
    rollback: dict[str, Any] | None = Field(
        default=None,
        description="롤백 정책 (RollbackPolicy 타입)",
    )


# Discriminated Union for HookTask
HookTask = Annotated[
    ManifestsHookTask | InlineHookTask | CommandHookTask,
    Field(discriminator="type"),
]


# ----------------------------------------------------------------------------
# Phase 3: Validation, Dependency, Rollback Models
# ----------------------------------------------------------------------------


class ValidationRule(ConfigBaseModel):
    """Hook Task 실행 후 검증 규칙.

    Examples:
        validation:
          kind: ClusterIssuer
          name: letsencrypt-prd
          wait_for_ready: true
          timeout: 120
          conditions:
            - type: Ready
              status: "True"

    """

    kind: str | None = Field(
        default=None,
        description="검증할 리소스 Kind (예: Pod, ClusterIssuer)",
    )
    name: str | None = Field(
        default=None,
        description="검증할 리소스 이름 (지정하지 않으면 모든 리소스)",
    )
    namespace: str | None = Field(
        default=None,
        description="검증할 네임스페이스 (지정하지 않으면 전역 또는 기본 네임스페이스)",
    )
    wait_for_ready: bool = Field(
        default=False,
        description="리소스가 Ready 상태가 될 때까지 대기",
    )
    timeout: int = Field(
        default=60,
        description="검증 타임아웃 (초)",
    )
    conditions: list[dict[str, str]] | None = Field(
        default=None,
        description="검증할 Condition 리스트 (type, status 쌍)",
        json_schema_extra={
            "examples": [
                [{"type": "Ready", "status": "True"}],
                [
                    {"type": "Available", "status": "True"},
                    {"type": "Progressing", "status": "False"},
                ],
            ]
        },
    )


class DependencyConfig(ConfigBaseModel):
    """Hook Task 간 의존성 설정.

    Examples:
        depends_on:
          - deploy-secrets
          - verify-database
        wait_for:
          - kind: Pod
            label_selector: app=database
            condition: Ready
            timeout: 180

    """

    depends_on: list[str] = Field(
        default_factory=list,
        description="선행되어야 하는 Task 이름 리스트 (같은 hook 내에서)",
    )
    wait_for: list[dict[str, Any]] | None = Field(
        default=None,
        description="대기해야 하는 외부 리소스 조건",
        json_schema_extra={
            "examples": [
                [
                    {
                        "kind": "Pod",
                        "label_selector": "app=database",
                        "condition": "Ready",
                        "timeout": 180,
                    }
                ]
            ]
        },
    )


class RollbackPolicy(ConfigBaseModel):
    """실패 시 롤백 정책.

    Examples:
        rollback:
          enabled: true
          on_failure: always
          manifests:
            - manifests/cleanup.yaml
          commands:
            - kubectl delete certificate wildcard-cert
            - ./scripts/restore-backup.sh

    """

    enabled: bool = Field(
        default=False,
        description="롤백 활성화 여부",
    )
    on_failure: Literal["always", "manual", "never"] = Field(
        default="always",
        description="롤백 실행 조건 (always: 자동, manual: 수동 확인, never: 비활성화)",
    )
    manifests: list[str] = Field(
        default_factory=list,
        description="롤백 시 적용할 manifest 파일들",
    )
    commands: list[str] = Field(
        default_factory=list,
        description="롤백 시 실행할 shell 명령어들",
    )


# ----------------------------------------------------------------------------
# Command Hooks (전역 훅)
# ----------------------------------------------------------------------------


class CommandHooks(ConfigBaseModel):
    """명령어별 훅 설정.

    Examples:
        hooks:
          deploy:
            pre:
              - echo "Starting deployment"
              - ./scripts/pre-deploy.sh
            post:
              - echo "Deployment completed"
            on_failure:
              - ./scripts/rollback.sh

    """

    pre: list[str] = Field(default_factory=list, description="명령어 실행 전 훅")
    post: list[str] = Field(default_factory=list, description="명령어 실행 후 훅")
    on_failure: list[str] = Field(default_factory=list, description="명령어 실패 시 훅")


class AppHooks(ConfigBaseModel):
    """앱별 훅 설정.

    Examples:
        # Shell 명령어 hooks (기존 방식)
        database:
          type: helm
          chart: prometheus-community/kube-state-metrics
          hooks:
            pre_prepare:
              - echo "Preparing database chart"
            post_prepare:
              - echo "Chart ready"
            pre_deploy:
              - ./scripts/backup-db.sh
            post_deploy:
              - kubectl wait --for=condition=ready pod -l app=postgresql
            on_deploy_failure:
              - ./scripts/restore-backup.sh

        # Manifests hooks (신규 - Phase 1)
        cert-manager:
          type: helm
          chart: jetstack/cert-manager
          hooks:
            post_deploy_manifests:
              - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
              - manifests/issuers/cluster-issuer-letsencrypt-stg.yaml

    """

    # Shell command hooks (기존)
    pre_prepare: list[str] = Field(
        default_factory=list, description="prepare 실행 전 훅 (shell 명령어)"
    )
    post_prepare: list[str] = Field(
        default_factory=list, description="prepare 실행 후 훅 (shell 명령어)"
    )
    pre_build: list[str] = Field(
        default_factory=list, description="build 실행 전 훅 (shell 명령어)"
    )
    post_build: list[str] = Field(
        default_factory=list, description="build 실행 후 훅 (shell 명령어)"
    )
    pre_template: list[str] = Field(
        default_factory=list, description="template 실행 전 훅 (shell 명령어)"
    )
    post_template: list[str] = Field(
        default_factory=list, description="template 실행 후 훅 (shell 명령어)"
    )
    pre_deploy: list[str] = Field(
        default_factory=list, description="deploy 실행 전 훅 (shell 명령어)"
    )
    post_deploy: list[str] = Field(
        default_factory=list, description="deploy 실행 후 훅 (shell 명령어)"
    )
    on_deploy_failure: list[str] = Field(
        default_factory=list, description="deploy 실패 시 훅 (shell 명령어)"
    )

    # Manifests hooks (신규 - Phase 1: Manifests 지원)
    pre_deploy_manifests: list[str] = Field(
        default_factory=list,
        description="deploy 실행 전 배포할 YAML manifests (sbkube가 직접 처리)",
        json_schema_extra={
            "examples": [["manifests/pre-config.yaml"], ["manifests/secrets/*.yaml"]]
        },
    )
    post_deploy_manifests: list[str] = Field(
        default_factory=list,
        description="deploy 실행 후 배포할 YAML manifests (sbkube가 직접 처리)",
        json_schema_extra={
            "examples": [
                ["manifests/issuers/cluster-issuer-letsencrypt-prd.yaml"],
                ["manifests/post-config/*.yaml"],
            ]
        },
    )

    # Hook Tasks (신규 - Phase 2: Type System)
    pre_deploy_tasks: list[HookTask] = Field(
        default_factory=list,
        description="deploy 실행 전 Hook Tasks (타입별 처리)",
        json_schema_extra={
            "examples": [
                [
                    {
                        "type": "manifests",
                        "name": "prepare-secrets",
                        "files": ["manifests/secrets.yaml"],
                    },
                    {
                        "type": "command",
                        "name": "backup-db",
                        "command": "./scripts/backup.sh",
                    },
                ]
            ]
        },
    )
    post_deploy_tasks: list[HookTask] = Field(
        default_factory=list,
        description="deploy 실행 후 Hook Tasks (타입별 처리)",
        json_schema_extra={
            "examples": [
                [
                    {
                        "type": "manifests",
                        "name": "deploy-issuers",
                        "files": ["manifests/issuers/*.yaml"],
                    },
                    {
                        "type": "inline",
                        "name": "create-cert",
                        "content": {"apiVersion": "v1", "kind": "Certificate"},
                    },
                    {
                        "type": "command",
                        "name": "verify-dns",
                        "command": "dig +short example.com",
                        "on_failure": "warn",
                    },
                ]
            ]
        },
    )


# ============================================================================
# Phase 4: HookApp - Hook as First-class App
# ============================================================================


class HookApp(ConfigBaseModel):
    """Hook 타입 앱 (독립적인 리소스 관리).

    Phase 3의 HookTask를 앱 레벨로 승격한 형태.
    다른 앱의 post_deploy_tasks를 별도 앱으로 분리하여 관리.

    Examples:
        # cert-manager와 issuers를 별도 앱으로 분리
        apps:
          cert-manager:
            type: helm
            chart: jetstack/cert-manager

          cert-manager-issuers:
            type: hook
            depends_on:
              - cert-manager
            tasks:
              - type: manifests
                name: deploy-issuers
                files:
                  - manifests/issuers/cluster-issuer-letsencrypt-prd.yaml
                validation:
                  kind: ClusterIssuer
                  wait_for_ready: true

          wildcard-certificate:
            type: hook
            depends_on:
              - cert-manager-issuers
            tasks:
              - type: inline
                name: create-certificate
                content:
                  apiVersion: cert-manager.io/v1
                  kind: Certificate
                  metadata:
                    name: wildcard-cert
                  spec:
                    secretName: wildcard-cert-tls

    """

    type: Literal["hook"] = "hook"

    # Hook Tasks (Phase 2/3 기능 재사용)
    tasks: list[HookTask] = Field(
        default_factory=list,
        description="실행할 Hook Tasks (manifests, inline, command)",
        json_schema_extra={
            "examples": [
                [
                    {
                        "type": "manifests",
                        "name": "deploy-config",
                        "files": ["manifests/config.yaml"],
                    },
                    {
                        "type": "inline",
                        "name": "create-secret",
                        "content": {"apiVersion": "v1", "kind": "Secret"},
                    },
                    {
                        "type": "command",
                        "name": "verify",
                        "command": "kubectl get pods",
                    },
                ]
            ]
        },
    )

    # Phase 3 기능 (앱 레벨 validation, dependency, rollback)
    validation: dict[str, Any] | None = Field(
        default=None,
        description="앱 전체 검증 규칙 (ValidationRule 타입)",
    )
    dependency: dict[str, Any] | None = Field(
        default=None,
        description="앱 전체 의존성 설정 (DependencyConfig 타입)",
    )
    rollback: dict[str, Any] | None = Field(
        default=None,
        description="앱 전체 롤백 정책 (RollbackPolicy 타입)",
    )

    # 공통 필드
    namespace: str | None = Field(
        default=None,
        description="배포 대상 namespace (지정하지 않으면 기본 namespace 사용)",
    )
    depends_on: list[str] = Field(
        default_factory=list,
        description="의존하는 앱 이름 리스트 (선행 배포 필요)",
        json_schema_extra={"examples": [["cert-manager"], ["database", "redis"]]},
    )
    enabled: bool = Field(
        default=True,
        description="앱 활성화 여부 (False면 배포 건너뛰기)",
    )
    labels: dict[str, str] = Field(
        default_factory=dict,
        description="앱에 적용할 레이블",
    )
    annotations: dict[str, str] = Field(
        default_factory=dict,
        description="앱에 적용할 주석",
    )

    # HookApp은 hooks를 가질 수 없음 (재귀 방지)
    # hooks 필드는 의도적으로 제외


# ============================================================================
# App Type Models (Discriminated Union)
# ============================================================================


class HelmApp(ConfigBaseModel):
    """Helm 차트 배포 앱.

    지원하는 chart 형식:
    1. Remote chart: "repo/chart" (예: "grafana/grafana")
       → 자동으로 pull 후 install
    2. Local chart: "./charts/my-chart" (상대 경로)
       → 로컬 차트를 직접 install
    3. Absolute path: "/path/to/chart"
       → 절대 경로 차트 install

    Examples:
        # Remote chart (자동 pull + install)
        grafana:
          type: helm
          chart: grafana/grafana
          version: 6.50.0
          values:
            - grafana.yaml

        # Local chart (install only)
        my-app:
          type: helm
          chart: ./charts/my-app
          values:
            - values.yaml

    """

    type: Literal["helm"] = "helm"
    chart: str = Field(
        ...,
        description="Helm chart in format 'repo/chart', './path', or '/abs/path'",
        json_schema_extra={
            "examples": ["grafana/grafana", "./charts/my-app", "/path/to/chart"]
        },
    )
    version: str | None = Field(
        None,
        description="Chart version (for remote charts only)",
        json_schema_extra={"examples": ["6.50.0", "1.0.0"]},
    )
    values: list[str] = Field(
        default_factory=list,
        description="Values file paths relative to app directory",
        json_schema_extra={
            "examples": [["values.yaml"], ["values.dev.yaml", "values.shared.yaml"]]
        },
    )

    # 커스터마이징
    overrides: list[str] = Field(
        default_factory=list,
        description="Chart customization files from overrides/ directory",
    )
    removes: list[str] = Field(
        default_factory=list,
        description="File/directory patterns to remove during build",
    )

    # Helm 옵션
    set_values: dict[str, Any] = Field(
        default_factory=dict,
        description="Helm --set option values (key-value pairs)",
        json_schema_extra={"examples": [{"replicaCount": 3, "image.tag": "v1.2.3"}]},
    )
    release_name: str | None = Field(
        None, description="Helm release name (defaults to app name)"
    )
    namespace: str | None = Field(
        None, description="Namespace override (defaults to global namespace)"
    )
    context: str | None = Field(
        None, description="Kubernetes context to use (defaults to current context)"
    )
    create_namespace: bool = False
    wait: bool = True
    timeout: str = "5m"
    atomic: bool = False
    helm_label_injection: bool = Field(
        default=True,
        description="Enable automatic label/annotation injection via commonLabels/commonAnnotations. "
        "Set to false for charts with strict schema validation (e.g., Authelia).",
    )

    # 메타데이터
    labels: dict[str, str] = Field(default_factory=dict)  # Kubernetes labels
    annotations: dict[str, str] = Field(default_factory=dict)  # Kubernetes annotations

    # 제어
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True

    # 훅
    hooks: AppHooks | None = None

    @field_validator("chart")
    @classmethod
    def validate_chart(cls, v: str) -> str:
        """Chart 형식 검증.

        허용되는 형식:
        - "repo/chart" (remote)
        - "./path" (relative local)
        - "/path" (absolute local)

        금지 형식:
        - "oci://..." (OCI protocol은 sources.yaml에서 설정)
        """
        if not v or not v.strip():
            msg = "chart cannot be empty"
            raise ValueError(msg)

        v = v.strip()

        # OCI 프로토콜 직접 사용 감지
        if v.startswith("oci://"):
            msg = (
                "Direct OCI protocol in 'chart' field is not supported.\n"
                "\n"
                "SBKube requires OCI registries to be defined in sources.yaml:\n"
                "\n"
                "  sources.yaml:\n"
                "    oci_registries:\n"
                "      myregistry:\n"
                "        registry: oci://registry.example.com/path\n"
                "\n"
                "  config.yaml:\n"
                "    apps:\n"
                "      myapp:\n"
                "        type: helm\n"
                "        chart: myregistry/chartname\n"
                "\n"
                "Example for Docker Hub grafana charts:\n"
                "\n"
                "  sources.yaml:\n"
                "    oci_registries:\n"
                "      grafana:\n"
                "        registry: oci://ghcr.io/grafana/helm-charts\n"
                "\n"
                "  config.yaml:\n"
                "    apps:\n"
                "      supabase:\n"
                "        type: helm\n"
                "        chart: grafana/grafana\n"
                "\n"
                "For more details, see: docs/03-configuration/config-schema.md#oci-registry"
            )
            raise ValueError(msg)

        return v

    def is_remote_chart(self) -> bool:
        """Remote chart 여부 판단.

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

    def is_oci_chart(self) -> bool:
        """OCI 레지스트리 chart 여부 판단.

        Returns:
            True if chart가 OCI 레지스트리를 사용하는 경우

        """
        # OCI 프로토콜로 시작하는 경우
        if self.chart.startswith("oci://"):
            return True
        # repo 이름이 sources.yaml의 oci_registries에 있는 경우
        # (이 검증은 prepare.py에서 수행)
        return False

    def get_repo_name(self) -> str | None:
        """Repo 이름 추출 (remote chart만).

        Returns:
            repo 이름 (예: 'grafana/grafana' → 'grafana') 또는 None (local chart)

        """
        if not self.is_remote_chart():
            return None
        return self.chart.split("/")[0]

    def get_chart_name(self) -> str:
        """Chart 이름 추출.

        Returns:
            chart 이름 (예: 'grafana/grafana' → 'grafana', './my-chart' → 'my-chart')

        """
        if self.is_remote_chart():
            return self.chart.split("/")[1]
        # 로컬 경로에서 마지막 부분 추출
        return self.chart.rstrip("/").split("/")[-1]

    def get_version_or_default(self) -> str:
        """Chart 버전 추출 (없으면 'latest' 반환).

        Returns:
            버전 문자열 (예: '18.0.0') 또는 'latest'

        """
        return self.version if self.version else "latest"

    def get_chart_path(self, charts_dir: Path | str) -> Path | None:
        """Chart 저장 경로 생성 (repo/chart-version 구조).

        v0.8.0+에서 도입된 새 경로 구조를 사용하여 chart 저장 위치를 결정합니다.
        이 구조는 다음 문제를 해결합니다:
        - 다른 repo의 같은 chart 이름 충돌 방지
        - 같은 chart의 다른 버전 동시 사용 가능

        Args:
            charts_dir: charts 디렉토리 (Path 객체 또는 문자열)

        Returns:
            Chart 저장 경로 (Path 객체) 또는 None (로컬 차트인 경우)

        Examples:
            >>> app = HelmApp(chart="grafana/loki", version="18.0.0")
            >>> app.get_chart_path(Path(".sbkube/charts"))
            Path(".sbkube/charts/grafana/loki-18.0.0")

            >>> app = HelmApp(chart="grafana/loki")  # version 없음
            >>> app.get_chart_path(Path(".sbkube/charts"))
            Path(".sbkube/charts/grafana/loki-latest")

            >>> app = HelmApp(chart="./my-chart")  # 로컬 차트
            >>> app.get_chart_path(Path(".sbkube/charts"))
            None

        """
        from pathlib import Path

        if not self.is_remote_chart():
            # 로컬 차트는 경로 생성 불필요
            return None

        repo_name = self.get_repo_name()
        chart_name = self.get_chart_name()
        version = self.get_version_or_default()

        # charts_dir이 문자열이면 Path로 변환
        if isinstance(charts_dir, str):
            charts_dir = Path(charts_dir)

        return charts_dir / repo_name / f"{chart_name}-{version}"


class YamlApp(ConfigBaseModel):
    """YAML 매니페스트 직접 배포 앱.

    kubectl apply -f 로 배포.

    Examples:
        my-app:
          type: yaml
          manifests:
            - deployment.yaml
            - service.yaml
          namespace: custom-ns

    """

    type: Literal["yaml"] = "yaml"
    manifests: list[str] = Field(
        ...,
        description="YAML manifest files to deploy with kubectl apply",
        json_schema_extra={
            "examples": [["deployment.yaml", "service.yaml"], ["manifests/*.yaml"]]
        },
    )
    namespace: str | None = None
    context: str | None = Field(
        None, description="Kubernetes context to use (defaults to current context)"
    )
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
    hooks: AppHooks | None = None

    @field_validator("manifests")
    @classmethod
    def validate_manifests(cls, v: list[str]) -> list[str]:
        """파일 목록이 비어있지 않은지 확인하고 변수 구문을 검증."""
        # 순환 import 방지를 위해 함수 내부에서 import
        from sbkube.utils.path_resolver import validate_variable_syntax

        v = cls.validate_non_empty_list(v, "manifests")

        # 각 경로의 변수 구문 검증
        for path in v:
            validate_variable_syntax(path)

        return v


class ActionSpec(ConfigBaseModel):
    """Action specification for ActionApp.

    Defines a single action to be executed during deployment.
    Supported action types: apply, delete.

    Examples:
        - type: apply
          path: manifests/deployment.yaml
          namespace: default
        - type: delete
          path: manifests/old-resource.yaml

    """

    type: Literal["apply", "delete"] = Field(
        default="apply",
        description="Action type: 'apply' to create/update resources, 'delete' to remove resources",
    )
    path: str = Field(
        ..., description="Path to the YAML manifest file (relative to app directory)"
    )
    namespace: str | None = Field(
        None, description="Namespace for this action (overrides app-level namespace)"
    )

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str) -> str:
        """Validate that path is not empty and has reasonable format."""
        from sbkube.utils.path_resolver import validate_variable_syntax

        if not v or not v.strip():
            msg = "Action path cannot be empty"
            raise ValueError(msg)

        # Validate variable syntax if present
        validate_variable_syntax(v)

        # Check for common mistakes
        if v.startswith(("kubectl ", "helm ")):
            msg = (
                "Action 'path' should be a file path, not a command. "
                "For executing commands, use 'type: exec' instead of 'type: action'. "
                f"Invalid path: '{v}'"
            )
            raise ValueError(msg)

        return v.strip()


class ActionApp(ConfigBaseModel):
    """커스텀 액션 실행 앱 (apply/delete).

    Actions are a list of ActionSpec objects that define individual
    kubectl apply/delete operations to be executed in sequence.

    Examples:
        setup:
          type: action
          actions:
            - type: apply
              path: setup.yaml
            - type: apply
              path: configmap.yaml
              namespace: default
            - type: delete
              path: old-resource.yaml

    """

    type: Literal["action"] = "action"
    actions: list[ActionSpec] = Field(
        ..., description="List of actions to execute (apply/delete operations)"
    )
    namespace: str | None = None
    context: str | None = Field(
        None, description="Kubernetes context to use (defaults to current context)"
    )
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
    hooks: AppHooks | None = None

    @field_validator("actions")
    @classmethod
    def validate_actions(cls, v: list[ActionSpec]) -> list[ActionSpec]:
        """액션 목록이 비어있지 않은지 확인."""
        if not v:
            msg = (
                "ActionApp must have at least one action. "
                "Add actions with 'type' (apply/delete) and 'path' fields."
            )
            raise ValueError(msg)
        return v


class ExecApp(ConfigBaseModel):
    """커스텀 명령어 실행 앱.

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
    hooks: AppHooks | None = None

    @field_validator("commands")
    @classmethod
    def validate_commands(cls, v: list[str]) -> list[str]:
        """명령어 목록이 비어있지 않은지 확인."""
        return cls.validate_non_empty_list(v, "commands")


class GitApp(ConfigBaseModel):
    """Git 리포지토리에서 매니페스트 가져오기 앱.

    Examples:
        my-repo:
          type: git
          repo: https://github.com/user/repo
          path: k8s/
          branch: main

    """

    type: Literal["git"] = "git"
    repo: str = Field(
        ...,
        description="Git repository URL",
        json_schema_extra={
            "examples": ["https://github.com/user/repo", "git@github.com:user/repo.git"]
        },
    )
    path: str | None = Field(
        None,
        description="Path within repository (optional)",
        json_schema_extra={"examples": ["k8s/", "manifests/production/"]},
    )
    branch: str = Field(
        "main",
        description="Git branch or tag",
        json_schema_extra={"examples": ["main", "develop", "v1.2.3"]},
    )
    ref: str | None = None  # 특정 commit/tag (branch보다 우선)
    namespace: str | None = None
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
    hooks: AppHooks | None = None

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, v: str) -> str:
        """Git repo URL 검증."""
        if not v or not v.strip():
            msg = "repo cannot be empty"
            raise ValueError(msg)
        return v.strip()


class KustomizeApp(ConfigBaseModel):
    """Kustomize 기반 배포 앱.

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
    hooks: AppHooks | None = None

    @field_validator("path")
    @classmethod
    def validate_kustomize_path(cls, v: str) -> str:
        """Kustomize 경로 검증."""
        return cls.validate_path_exists(v, must_exist=False)


class HttpApp(ConfigBaseModel):
    """HTTP URL에서 파일 다운로드 앱.

    Examples:
        external-manifest:
          type: http
          url: https://raw.githubusercontent.com/example/repo/main/manifest.yaml
          dest: manifests/external.yaml

    """

    type: Literal["http"] = "http"
    url: str = Field(
        ...,
        description="HTTP(S) URL to download file from",
        json_schema_extra={
            "examples": [
                "https://raw.githubusercontent.com/example/repo/main/manifest.yaml"
            ]
        },
    )
    dest: str = Field(
        ...,
        description="Destination file path relative to app directory",
        json_schema_extra={
            "examples": ["manifests/external.yaml", "config/downloaded.yaml"]
        },
    )
    headers: dict[str, str] = Field(default_factory=dict)  # HTTP 헤더
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
    hooks: AppHooks | None = None

    @field_validator("url")
    @classmethod
    def validate_http_url(cls, v: str) -> str:
        """HTTP URL 검증."""
        if not v or not v.strip():
            msg = "url cannot be empty"
            raise ValueError(msg)
        if not v.startswith(("http://", "https://")):
            msg = "url must start with http:// or https://"
            raise ValueError(msg)
        return v.strip()


class NoopApp(ConfigBaseModel):
    """No-operation 앱 (수동 작업 또는 외부 의존성 표현).

    실제로 아무것도 배포하지 않지만 의존성 체인에서 수동 작업이나
    외부에서 관리되는 리소스를 표현하는 데 사용됩니다.

    Examples:
        manual-setup:
          type: noop
          description: "수동으로 설정된 네트워크 정책 (이미 완료)"
          enabled: true

        external-database:
          type: noop
          description: "외부 RDS 인스턴스 (AWS 콘솔에서 관리)"

    """

    type: Literal["noop"] = "noop"
    description: str | None = None  # 수동 작업 설명
    depends_on: list[str] = Field(default_factory=list)
    enabled: bool = True
    hooks: AppHooks | None = None


# ============================================================================
# Discriminated Union
# ============================================================================

AppConfig = Annotated[
    HelmApp
    | YamlApp
    | ActionApp
    | ExecApp
    | GitApp
    | KustomizeApp
    | HttpApp
    | NoopApp
    | HookApp,
    Field(discriminator="type"),
]


# ============================================================================
# Main Configuration Model
# ============================================================================


class SBKubeConfig(ConfigBaseModel):
    """SBKube 메인 설정 모델.

    Breaking Changes:
    - apps: list → dict (key = app name)
    - Unified helm type replaces legacy pull-helm and install-helm (자동 처리)
    - specs 제거 (모든 필드 평탄화)
    - 의존성 명시 (depends_on)

    Examples:
        namespace: production
        deps:
          - a000_infra_network
          - a101_data_rdb

        apps:
          grafana:
            type: helm
            chart: grafana/grafana
            version: 6.50.0
            values:
              - grafana.yaml

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
    deps: list[str] = Field(
        default_factory=list,
        description="App group dependencies (other app-dir names that must be deployed first)",
    )
    hooks: dict[str, CommandHooks] | None = Field(
        default=None,
        description="명령어별 전역 훅 (예: hooks.prepare.pre, hooks.deploy.post)",
    )
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
        for app_name in v:
            cls.validate_kubernetes_name(app_name, "app_name")
        return v

    @model_validator(mode="after")
    def apply_namespace_inheritance(self) -> "SBKubeConfig":
        """네임스페이스 상속 및 글로벌 레이블/어노테이션 적용.

        앱에 namespace가 없으면 전역 namespace 사용.
        """
        for app in self.apps.values():
            # 네임스페이스 상속 (HelmApp, YamlApp 등에만 적용)
            if hasattr(app, "namespace") and app.namespace is None:
                app.namespace = self.namespace

            # 글로벌 레이블/어노테이션은 Helm 앱에만 적용 가능
            # (향후 확장 가능)

        return self

    @model_validator(mode="after")
    def validate_dependencies(self) -> "SBKubeConfig":
        """의존성 검증:
        1. 존재하지 않는 앱에 대한 의존성 체크
        2. 순환 의존성 체크.
        """
        app_names = set(self.apps.keys())

        # 1. 존재하지 않는 앱 참조 체크
        for app_name, app in self.apps.items():
            if hasattr(app, "depends_on"):
                for dep in app.depends_on:
                    if dep not in app_names:
                        msg = f"App '{app_name}' depends on non-existent app '{dep}'"
                        raise ValueError(msg)

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

        for app_name in self.apps:
            if app_name not in visited and has_cycle(app_name):
                msg = f"Circular dependency detected involving app '{app_name}'"
                raise ValueError(msg)

        return self

    def get_enabled_apps(self) -> dict[str, AppConfig]:
        """활성화된 앱만 반환."""
        return {name: app for name, app in self.apps.items() if app.enabled}

    def get_deployment_order(self) -> list[str]:
        """의존성을 고려한 배포 순서 반환 (위상 정렬).

        Returns:
            배포할 앱 이름 리스트 (순서대로)

        """
        enabled_apps = self.get_enabled_apps()
        in_degree = dict.fromkeys(enabled_apps, 0)
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
            msg = "Circular dependency detected (this should not happen)"
            raise ValueError(msg)

        return result

    def get_apps_by_type(self, app_type: str) -> dict[str, AppConfig]:
        """특정 타입의 앱만 반환."""
        return {
            name: app
            for name, app in self.apps.items()
            if app.type == app_type and app.enabled
        }
