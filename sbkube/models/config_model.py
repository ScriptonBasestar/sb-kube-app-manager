from pydantic import BaseModel, Field, model_validator
from pathlib import Path
from typing import Optional, Literal, List, Dict, Any
import os
import yaml

# --- 각 spec 정의 ---

class CopyPair(BaseModel):
    src: str
    dest: str

class FileActionSpec(BaseModel):
    type: Literal['apply', 'create', 'delete']
    path: str
    # n: Optional[str] = None

class AppSpecBase(BaseModel):
    pass

class AppExecSpec(AppSpecBase):
    commands: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_commands(self) -> "AppExecSpec":
        if not isinstance(self.commands, list) or not all(isinstance(cmd, str) for cmd in self.commands):
            raise ValueError("commands must be a list of str")
        return self

class AppInstallHelmSpec(AppSpecBase):
    values: List[str] = Field(default_factory=list)

class AppInstallKubectlSpec(AppSpecBase):
    paths: List[str] = Field(default_factory=list)

class AppInstallShellSpec(AppSpecBase):
    commands: List[str] = Field(default_factory=list)

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
    app_type: Literal['install-yaml'] = 'install-yaml'
    actions: List[FileActionSpec] = Field(default_factory=list)

class AppInstallKustomizeSpec(AppSpecBase):
    kustomize_path: str

class AppRenderSpec(AppSpecBase):
    templates: List[str] = Field(default_factory=list)

class AppCopySpec(AppSpecBase):
    paths: List[CopyPair] = Field(default_factory=list)

class AppPullHelmSpec(AppSpecBase):
    repo: str
    chart: str
    dest: Optional[str] = None
    chart_version: Optional[str] = None
    app_version: Optional[str] = None
    removes: List[str] = Field(default_factory=list)
    overrides: List[str] = Field(default_factory=list)

class AppPullHelmOciSpec(AppSpecBase):
    repo: str
    chart: str
    dest: Optional[str] = None
    chart_version: Optional[str] = None
    app_version: Optional[str] = None
    removes: List[str] = Field(default_factory=list)
    overrides: List[str] = Field(default_factory=list)
    registry_url: Optional[str] = None

class AppPullGitSpec(AppSpecBase):
    repo: str
    paths: List[CopyPair] = Field(default_factory=list)

class AppPullHttpSpec(AppSpecBase):
    name: Literal['pull-http'] = 'pull-http'
    url: str
    paths: List[CopyPair] = Field(default_factory=list)

# --- 상위 스키마 ---

class AppInfoScheme(BaseModel):
    name: str
    type: Literal[
        'exec',
        'install-helm', 'install-action', 'install-kustomize',
        'pull-helm', 'pull-helm-oci', 'pull-git', 'pull-http'
    ]
    path: Optional[str] = None
    enabled: bool = False
    namespace: Optional[str] = None
    release_name: Optional[str] = None
    specs: Dict[str, Any] = Field(default_factory=dict)

class AppGroupScheme(BaseModel):
    namespace: str
    deps: List[str] = Field(default_factory=list)
    apps: List[AppInfoScheme] = Field(default_factory=list)

# --- YAML 로더 (pydantic 활용) ---

def load_apps(group_name: str) -> AppGroupScheme:
    curr_file_path = Path(__file__).parent.resolve()
    yaml_path = Path(os.path.expanduser(str(curr_file_path / group_name / "config.yaml")))
    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)
    return AppGroupScheme.model_validate(data)

# --- 사용 예시 ---

if __name__ == '__main__':
    group_scheme = load_apps("a000_infra")
    for app in group_scheme.apps:
        print(app)
        if app.type == 'install-helm':
            helm_spec = AppInstallHelmSpec(**app.specs)
            print(helm_spec)
        elif app.type == 'pull-git':
            git_spec = AppPullGitSpec(**app.specs)
            print(git_spec)
        # 필요하면 추가 분기

def get_spec_model(app_type: str):
    """앱 타입에 따라 적절한 Spec 모델 클래스를 반환합니다."""
    spec_model_mapping = {
        'exec': AppExecSpec,
        'install-helm': AppInstallHelmSpec,
        'install-kubectl': AppInstallKubectlSpec,
        'install-shell': AppInstallShellSpec,
        'install-action': AppInstallActionSpec,
        'install-kustomize': AppInstallKustomizeSpec,
        'render': AppRenderSpec,
        'pull-helm': AppPullHelmSpec,
        'pull-helm-oci': AppPullHelmOciSpec,
        'pull-git': AppPullGitSpec,
        'pull-http': AppPullHttpSpec,
    }
    return spec_model_mapping.get(app_type)

