"""Phase 4 HookApp E2E 테스트.

실제 Kubernetes 클러스터에서 HookApp 배포 테스트.
"""

import pytest

# E2E 테스트는 실제 k3s 클러스터가 필요하므로 skip 마커 추가
pytestmark = pytest.mark.e2e


@pytest.mark.skip(reason="Requires Kubernetes cluster and manual setup")
def test_hook_app_basic_deployment() -> None:
    """기본 HookApp 배포 E2E 테스트."""
    # TODO: 실제 k3s 클러스터에서 테스트
    # 1. examples/hooks-phase4 디렉토리 사용
    # 2. sbkube apply 실행
    # 3. 배포 결과 확인


@pytest.mark.skip(reason="Requires Kubernetes cluster and manual setup")
def test_hook_app_dependency_chain() -> None:
    """HookApp 의존성 체인 E2E 테스트."""
    # TODO: 실제 k3s 클러스터에서 테스트
    # 1. cert-manager → setup-issuers → create-certificates → verify-deployment
    # 2. 각 단계별 배포 순서 확인
    # 3. 의존성이 올바르게 해결되는지 확인


@pytest.mark.skip(reason="Requires Kubernetes cluster and manual setup")
def test_hook_app_validation_phase3() -> None:
    """HookApp Phase 3 기능 (validation) E2E 테스트."""
    # TODO: 실제 k3s 클러스터에서 테스트
    # 1. ClusterIssuer 배포
    # 2. wait_for_ready 검증
    # 3. Certificate 배포
    # 4. validation 통과 확인


@pytest.mark.skip(reason="Requires Kubernetes cluster and manual setup")
def test_hook_app_rollback_phase3() -> None:
    """HookApp Phase 3 기능 (rollback) E2E 테스트."""
    # TODO: 실제 k3s 클러스터에서 테스트
    # 1. 의도적으로 실패하는 HookApp 배포
    # 2. rollback 자동 실행 확인
    # 3. 리소스 정리 확인


@pytest.mark.skip(reason="Requires Kubernetes cluster and manual setup")
def test_hook_app_skip_in_prepare_build_template() -> None:
    """HookApp이 prepare/build/template에서 건너뛰는지 E2E 테스트."""
    # TODO: 실제 명령어 실행 후 출력 확인
    # 1. sbkube prepare → "HookApp does not require prepare" 메시지 확인
    # 2. sbkube build → "HookApp does not require build" 메시지 확인
    # 3. sbkube template → "HookApp does not support template" 메시지 확인
    # 4. sbkube deploy → HookApp 정상 실행 확인


@pytest.mark.skip(reason="Requires Kubernetes cluster and manual setup")
def test_hook_app_dry_run() -> None:
    """HookApp dry-run 모드 E2E 테스트."""
    # TODO: 실제 k3s 클러스터에서 테스트
    # 1. sbkube deploy --dry-run
    # 2. 리소스가 실제로 생성되지 않았는지 확인
    # 3. dry-run 로그 출력 확인


# ============================================================================
# 실제 E2E 테스트 구현 가이드
# ============================================================================

"""
E2E 테스트 구현 시 참고사항:

1. **테스트 환경 설정**:
   ```python
   from testcontainers.k3s import K3sContainer

   @pytest.fixture(scope="module")
   def k3s_cluster():
       with K3sContainer() as k3s:
           kubeconfig = k3s.get_kubeconfig()
           yield kubeconfig
   ```

2. **sbkube 명령어 실행**:
   ```python
   from sbkube.utils.common import run_command

   def test_hook_app_deploy(k3s_cluster):
       cmd = [
           "sbkube", "deploy",
           "--app-dir", "examples/hooks-phase4",
           "--namespace", "cert-manager",
           "--kubeconfig", k3s_cluster,
       ]
       return_code, stdout, stderr = run_command(cmd)
       assert return_code == 0
   ```

3. **Kubernetes 리소스 확인**:
   ```python
   from kubernetes import client, config

   def test_resources_created(k3s_cluster):
       config.load_kube_config(k3s_cluster)
       v1 = client.CoreV1Api()

       # ClusterIssuer 확인 (cert-manager CRD)
       custom_api = client.CustomObjectsApi()
       issuers = custom_api.list_cluster_custom_object(
           group="cert-manager.io",
           version="v1",
           plural="clusterissuers"
       )
       assert len(issuers["items"]) >= 2  # prd, stg
   ```

4. **배포 순서 검증**:
   ```python
   from sbkube.models.config_model import SBKubeConfig
   from sbkube.utils.file_loader import load_config_file

   def test_deployment_order():
       config_data = load_config_file("examples/hooks-phase4/config.yaml")
       config = SBKubeConfig(**config_data)
       order = config.get_deployment_order()

       # 예상 순서: cert-manager → setup-issuers → create-certificates → verify-deployment
       assert order.index("cert-manager") < order.index("setup-issuers")
       assert order.index("setup-issuers") < order.index("create-certificates")
       assert order.index("create-certificates") < order.index("verify-deployment")
   ```

5. **실행 예제** (수동 테스트):
   ```bash
   # Kind 클러스터 생성
   kind create cluster --name sbkube-phase4-test

   # SBKube 실행
   sbkube apply --app-dir examples/hooks-phase4 --namespace cert-manager

   # 결과 확인
   kubectl get clusterissuers
   kubectl get certificates -n default
   kubectl get secrets -n default | grep cert-tls

   # 클러스터 정리
   kind delete cluster --name sbkube-phase4-test
   ```
"""
