"""
DEPRECATED: This file has been replaced by config_model.py (formerly config_model_v2.py)

This legacy configuration model is kept for backward compatibility only.
New code should use config_model.py which provides:
- Enhanced Pydantic validation
- Configuration inheritance support
- Better error handling
- Path and URL validation

DO NOT USE THIS FILE FOR NEW DEVELOPMENT.
"""

import warnings

warnings.warn(
    "config_model_legacy is deprecated. Use config_model instead.",
    DeprecationWarning,
    stacklevel=2,
)

import os
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator

# --- 각 spec 정의 ---


class CopyPair(BaseModel):
    src: str
    dest: str


class FileActionSpec(BaseModel):
    type: Literal["apply", "create", "delete"]
    path: str
    # n: Optional[str] = None


class AppSpecBase(BaseModel):
    pass


class AppExecSpec(AppSpecBase):
    commands: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_commands(self) -> "AppExecSpec":
        if not isinstance(self.commands, list) or not all(
            isinstance(cmd, str) for cmd in self.commands
        ):
            raise ValueError("commands must be a list of str")
        return self


class AppInstallHelmSpec(AppSpecBase):
    values: list[str] = Field(default_factory=list)


class AppInstallKubectlSpec(AppSpecBase):
    paths: list[str] = Field(default_factory=list)


class AppInstallShellSpec(AppSpecBase):
    commands: list[str] = Field(default_factory=list)


class AppInstallActionSpec(AppSpecBase):
    """
    spec:
      files:
        - type: apply
          path: file1.yaml
        - type: create
          path: file2.yml
        - type: create
          path: http://example.com/file.yaml
    """

    app_type: Literal["install-yaml"] = "install-yaml"
    actions: list[FileActionSpec] = Field(default_factory=list)


class AppInstallKustomizeSpec(AppSpecBase):
    kustomize_path: str


class AppRenderSpec(AppSpecBase):
    templates: list[str] = Field(default_factory=list)


class AppCopySpec(AppSpecBase):
    paths: list[CopyPair] = Field(default_factory=list)


class AppPullHelmSpec(AppSpecBase):
    repo: str
    chart: str
    dest: str | None = None
    chart_version: str | None = None
    app_version: str | None = None
    removes: list[str] = Field(default_factory=list)
    overrides: list[str] = Field(default_factory=list)


class AppPullHelmOciSpec(AppSpecBase):
    repo: str
    chart: str
    dest: str | None = None
    chart_version: str | None = None
    app_version: str | None = None
    removes: list[str] = Field(default_factory=list)
    overrides: list[str] = Field(default_factory=list)
    registry_url: str | None = None


class AppPullGitSpec(AppSpecBase):
    repo: str
    paths: list[CopyPair] = Field(default_factory=list)


class AppPullHttpSpec(AppSpecBase):
    name: Literal["pull-http"] = "pull-http"
    url: str
    paths: list[CopyPair] = Field(default_factory=list)


# --- 상위 스키마 ---


class AppInfoScheme(BaseModel):
    name: str
    type: Literal[
        "exec",
        "install-helm",
        "install-action",
        "install-kustomize",
        "install-yaml",
        "pull-helm",
        "pull-helm-oci",
        "pull-git",
        "pull-http",
        "copy-app",
    ]
    path: str | None = None
    enabled: bool = False
    namespace: str | None = None
    release_name: str | None = None
    specs: dict[str, Any] = Field(default_factory=dict)


class AppGroupScheme(BaseModel):
    namespace: str
    deps: list[str] = Field(default_factory=list)
    apps: list[AppInfoScheme] = Field(default_factory=list)


# --- YAML 로더 (pydantic 활용) ---


def load_apps(group_name: str) -> AppGroupScheme:
    curr_file_path = Path(__file__).parent.resolve()
    yaml_path = Path(
        os.path.expanduser(str(curr_file_path / group_name / "config.yaml")),
    )
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    return AppGroupScheme.model_validate(data)


# --- 사용 예시 ---

if __name__ == "__main__":
    group_scheme = load_apps("a000_infra")
    for app in group_scheme.apps:
        print(app)
        if app.type == "install-helm":
            helm_spec = AppInstallHelmSpec(**app.specs)
            print(helm_spec)
        elif app.type == "pull-git":
            git_spec = AppPullGitSpec(**app.specs)
            print(git_spec)
        # 필요하면 추가 분기


def get_spec_model(app_type: str):
    """앱 타입에 따라 적절한 Spec 모델 클래스를 반환합니다."""
    spec_model_mapping = {
        "exec": AppExecSpec,
        "install-helm": AppInstallHelmSpec,
        "install-kubectl": AppInstallKubectlSpec,
        "install-shell": AppInstallShellSpec,
        "install-action": AppInstallActionSpec,
        "install-yaml": AppInstallActionSpec,  # install-yaml과 install-action은 같은 스펙 사용
        "install-kustomize": AppInstallKustomizeSpec,
        "render": AppRenderSpec,
        "pull-helm": AppPullHelmSpec,
        "pull-helm-oci": AppPullHelmOciSpec,
        "pull-git": AppPullGitSpec,
        "pull-http": AppPullHttpSpec,
        "copy-app": AppCopySpec,
    }
    return spec_model_mapping.get(app_type)
