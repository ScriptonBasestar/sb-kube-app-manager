"""SBKube 차트 커스터마이징 통합 테스트.

overrides와 removes 기능의 실전 시나리오를 검증합니다.
"""

import pytest

from sbkube.commands.build import build_helm_app
from sbkube.models.config_model import HelmApp
from sbkube.utils.output_manager import OutputManager


@pytest.fixture
def output_manager():
    """OutputManager fixture for tests."""
    return OutputManager(format_type="human")


class TestChartCustomization:
    """차트 커스터마이징 통합 테스트."""

    def test_overrides_and_removes_combined(self, tmp_path, output_manager):
        """overrides와 removes를 동시에 사용하는 시나리오."""
        # 테스트 차트 생성
        chart_dir = tmp_path / "charts" / "grafana" / "grafana"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: grafana\nversion: 6.50.0")
        (chart_dir / "values.yaml").write_text("replicaCount: 1")
        (chart_dir / "README.md").write_text("# Grafana Chart")
        (chart_dir / "LICENSE").write_text("Apache 2.0")

        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("kind: Deployment")
        (templates_dir / "service.yaml").write_text("kind: Service")
        (templates_dir / "ingress.yaml").write_text("kind: Ingress")
        (templates_dir / "NOTES.txt").write_text("Installation notes")

        # Overrides 디렉토리 - 일부 파일 교체
        overrides_dir = tmp_path / "overrides" / "grafana"
        overrides_dir.mkdir(parents=True)
        (overrides_dir / "values.yaml").write_text(
            "replicaCount: 3\nimage: custom/grafana"
        )
        (overrides_dir / "templates").mkdir()
        (overrides_dir / "templates" / "deployment.yaml").write_text(
            "kind: Deployment\nmetadata:\n  labels:\n    custom: override"
        )

        # HelmApp 설정 - overrides + removes
        app = HelmApp(
            chart="grafana/grafana",
            version="6.50.0",
            overrides=["values.yaml", "templates/deployment.yaml"],
            removes=["README.md", "LICENSE", "templates/NOTES.txt"],
        )

        # 빌드 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="grafana",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success

        # 검증: Overrides 적용 확인
        assert (
            build_dir / "grafana" / "values.yaml"
        ).read_text() == "replicaCount: 3\nimage: custom/grafana"
        assert (
            "custom: override"
            in (build_dir / "grafana" / "templates" / "deployment.yaml").read_text()
        )

        # 검증: Removes 적용 확인
        assert not (build_dir / "grafana" / "README.md").exists()
        assert not (build_dir / "grafana" / "LICENSE").exists()
        assert not (build_dir / "grafana" / "templates" / "NOTES.txt").exists()

        # 검증: 다른 파일은 유지
        assert (build_dir / "grafana" / "Chart.yaml").exists()
        assert (build_dir / "grafana" / "templates" / "service.yaml").exists()
        assert (build_dir / "grafana" / "templates" / "ingress.yaml").exists()

    def test_override_entire_templates_directory(self, tmp_path, output_manager):
        """Templates 디렉토리 전체를 교체하는 시나리오."""
        # 원본 차트
        chart_dir = tmp_path / "charts" / "myapp" / "myapp"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: myapp\nversion: 1.0.0")

        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("kind: Deployment\nspec: {}")
        (templates_dir / "service.yaml").write_text("kind: Service")
        (templates_dir / "configmap.yaml").write_text("kind: ConfigMap")

        # Overrides - 완전히 새로운 템플릿 세트
        overrides_dir = tmp_path / "overrides" / "myapp"
        (overrides_dir / "templates").mkdir(parents=True)
        (overrides_dir / "templates" / "statefulset.yaml").write_text(
            "kind: StatefulSet"
        )
        (overrides_dir / "templates" / "service.yaml").write_text(
            "kind: Service\nmetadata:\n  name: custom-svc"
        )
        (overrides_dir / "templates" / "pvc.yaml").write_text(
            "kind: PersistentVolumeClaim"
        )

        # HelmApp - templates/* 패턴 사용 (glob은 재귀적이지 않음)
        app = HelmApp(
            chart="myapp/myapp",
            version="1.0.0",
            overrides=["templates/*.yaml"],
        )

        # 빌드 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="myapp",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success

        # 검증: 새 템플릿들이 추가됨
        assert (build_dir / "myapp" / "templates" / "statefulset.yaml").exists()
        assert (build_dir / "myapp" / "templates" / "pvc.yaml").exists()

        # 검증: 기존 service.yaml은 교체됨
        service_content = (
            build_dir / "myapp" / "templates" / "service.yaml"
        ).read_text()
        assert "custom-svc" in service_content

        # 검증: 원본의 deployment.yaml, configmap.yaml은 유지 (overrides에 없으므로)
        assert (build_dir / "myapp" / "templates" / "deployment.yaml").exists()
        assert (build_dir / "myapp" / "templates" / "configmap.yaml").exists()

    def test_remove_specific_files(self, tmp_path, output_manager):
        """특정 파일들을 명시적으로 삭제."""
        # 테스트 차트
        chart_dir = tmp_path / "charts" / "app" / "app"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: app")

        # 여러 불필요한 파일 생성
        (chart_dir / "README.md").write_text("readme")
        (chart_dir / "LICENSE").write_text("license")
        (chart_dir / "CONTRIBUTING.md").write_text("contributing")
        (chart_dir / "CHANGELOG.md").write_text("changelog")

        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("kind: Deployment")
        (templates_dir / "NOTES.txt").write_text("notes")
        (templates_dir / "HELPERS.tpl").write_text("helpers")

        # HelmApp - 명시적 경로로 삭제 (removes는 glob 미지원)
        app = HelmApp(
            chart="app/app",
            removes=[
                "README.md",
                "CONTRIBUTING.md",
                "CHANGELOG.md",
                "LICENSE",
                "templates/NOTES.txt",
            ],
        )

        # 빌드 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="app",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success

        # 검증: 명시된 파일들이 삭제됨
        assert not (build_dir / "app" / "README.md").exists()
        assert not (build_dir / "app" / "CONTRIBUTING.md").exists()
        assert not (build_dir / "app" / "CHANGELOG.md").exists()
        assert not (build_dir / "app" / "LICENSE").exists()
        assert not (build_dir / "app" / "templates" / "NOTES.txt").exists()

        # 검증: 다른 파일은 유지
        assert (build_dir / "app" / "Chart.yaml").exists()
        assert (build_dir / "app" / "templates" / "deployment.yaml").exists()
        assert (build_dir / "app" / "templates" / "HELPERS.tpl").exists()

    def test_security_hardening_scenario(self, tmp_path, output_manager):
        """보안 강화 시나리오: 기본 차트에 보안 설정 추가."""
        # 기본 차트 (보안 설정 없음)
        chart_dir = tmp_path / "charts" / "webapp" / "webapp"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: webapp\nversion: 1.0.0")

        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: webapp
        image: nginx:latest
""")

        # Overrides - 보안 강화된 deployment
        overrides_dir = tmp_path / "overrides" / "webapp"
        (overrides_dir / "templates").mkdir(parents=True)
        (overrides_dir / "templates" / "deployment.yaml").write_text("""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webapp
spec:
  replicas: 1
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
        fsGroup: 65534
      containers:
      - name: webapp
        image: nginx:1.21-alpine
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop: [ALL]
""")

        # HelmApp
        app = HelmApp(
            chart="webapp/webapp",
            version="1.0.0",
            overrides=["templates/deployment.yaml"],
        )

        # 빌드 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="webapp",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success

        # 검증: 보안 설정 적용 확인
        deployment_content = (
            build_dir / "webapp" / "templates" / "deployment.yaml"
        ).read_text()
        assert "runAsNonRoot: true" in deployment_content
        assert "allowPrivilegeEscalation: false" in deployment_content
        assert "readOnlyRootFilesystem: true" in deployment_content
        assert "nginx:1.21-alpine" in deployment_content

    def test_multi_tenant_scenario(self, tmp_path, output_manager):
        """멀티 테넌트 시나리오: 테넌트별 설정 파일 교체."""
        # 기본 차트
        chart_dir = tmp_path / "charts" / "saas-app" / "saas-app"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: saas-app")
        (chart_dir / "values.yaml").write_text("""
tenant: default
resources:
  limits:
    cpu: 100m
    memory: 128Mi
""")

        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("kind: Deployment")
        (templates_dir / "configmap.yaml").write_text("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  tier: free
""")

        # Overrides - 프리미엄 테넌트 설정
        overrides_dir = tmp_path / "overrides" / "saas-app-premium"
        overrides_dir.mkdir(parents=True)
        (overrides_dir / "values.yaml").write_text("""
tenant: premium-customer
resources:
  limits:
    cpu: 2000m
    memory: 4Gi
""")
        (overrides_dir / "templates").mkdir()
        (overrides_dir / "templates" / "configmap.yaml").write_text("""
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  tier: premium
  features: all-enabled
  sla: 99.99
""")

        # HelmApp
        app = HelmApp(
            chart="saas-app/saas-app",
            overrides=["values.yaml", "templates/configmap.yaml"],
        )

        # 빌드 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="saas-app-premium",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success

        # 검증: 프리미엄 설정 적용
        values_content = (build_dir / "saas-app-premium" / "values.yaml").read_text()
        assert "tenant: premium-customer" in values_content
        assert "cpu: 2000m" in values_content
        assert "memory: 4Gi" in values_content

        configmap_content = (
            build_dir / "saas-app-premium" / "templates" / "configmap.yaml"
        ).read_text()
        assert "tier: premium" in configmap_content
        assert "features: all-enabled" in configmap_content
        assert "sla: 99.99" in configmap_content

    def test_cleanup_unnecessary_files(self, tmp_path, output_manager):
        """불필요한 파일 제거 시나리오."""
        # 차트에 많은 불필요한 파일들이 있는 경우
        chart_dir = tmp_path / "charts" / "bloated-chart" / "bloated-chart"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: bloated-chart")
        (chart_dir / "values.yaml").write_text("enabled: true")

        # 불필요한 문서/예제 파일들
        (chart_dir / "README.md").write_text("readme")
        (chart_dir / "CHANGELOG.md").write_text("changelog")
        (chart_dir / "LICENSE").write_text("license")
        (chart_dir / "OWNERS").write_text("owners")
        (chart_dir / "SECURITY.md").write_text("security")
        (chart_dir / "values.schema.json").write_text("{}")

        (chart_dir / "ci").mkdir()
        (chart_dir / "ci" / "values-test.yaml").write_text("test: true")
        (chart_dir / "ci" / "values-dev.yaml").write_text("dev: true")

        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("kind: Deployment")
        (templates_dir / "service.yaml").write_text("kind: Service")
        (templates_dir / "NOTES.txt").write_text("notes")
        (templates_dir / "tests").mkdir()
        (templates_dir / "tests" / "test-connection.yaml").write_text("kind: Pod")

        # HelmApp - 프로덕션 배포용으로 최소화 (removes는 명시적 경로만 지원)
        app = HelmApp(
            chart="bloated-chart/bloated-chart",
            removes=[
                "README.md",
                "CHANGELOG.md",
                "SECURITY.md",
                "LICENSE",
                "OWNERS",
                "values.schema.json",
                "ci/",  # 디렉토리
                "templates/NOTES.txt",
                "templates/tests/",  # 디렉토리
            ],
        )

        # 빌드 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="bloated-chart",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success

        # 검증: 불필요한 파일들 제거
        assert not (build_dir / "bloated-chart" / "README.md").exists()
        assert not (build_dir / "bloated-chart" / "CHANGELOG.md").exists()
        assert not (build_dir / "bloated-chart" / "LICENSE").exists()
        assert not (build_dir / "bloated-chart" / "OWNERS").exists()
        assert not (build_dir / "bloated-chart" / "SECURITY.md").exists()
        assert not (build_dir / "bloated-chart" / "values.schema.json").exists()
        assert not (build_dir / "bloated-chart" / "ci").exists()
        assert not (build_dir / "bloated-chart" / "templates" / "NOTES.txt").exists()
        assert not (build_dir / "bloated-chart" / "templates" / "tests").exists()

        # 검증: 필수 파일은 유지
        assert (build_dir / "bloated-chart" / "Chart.yaml").exists()
        assert (build_dir / "bloated-chart" / "values.yaml").exists()
        assert (build_dir / "bloated-chart" / "templates" / "deployment.yaml").exists()
        assert (build_dir / "bloated-chart" / "templates" / "service.yaml").exists()

    def test_no_customization(self, tmp_path, output_manager):
        """커스터마이징 없이 빌드 (순수 복사)."""
        # 차트 생성
        chart_dir = tmp_path / "charts" / "vanilla" / "vanilla"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: vanilla\nversion: 1.0.0")
        (chart_dir / "values.yaml").write_text("replicas: 1")
        (chart_dir / "README.md").write_text("readme")

        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()
        (templates_dir / "deployment.yaml").write_text("kind: Deployment")

        # HelmApp - overrides/removes 없음
        app = HelmApp(
            chart="vanilla/vanilla",
            version="1.0.0",
        )

        # 빌드 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="vanilla",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
            output=output_manager,
        )

        assert success

        # 검증: 모든 파일이 그대로 복사됨
        assert (build_dir / "vanilla" / "Chart.yaml").exists()
        assert (build_dir / "vanilla" / "values.yaml").exists()
        assert (build_dir / "vanilla" / "README.md").exists()
        assert (build_dir / "vanilla" / "templates" / "deployment.yaml").exists()

        # 검증: 내용도 동일
        assert (
            build_dir / "vanilla" / "Chart.yaml"
        ).read_text() == "name: vanilla\nversion: 1.0.0"
        assert (build_dir / "vanilla" / "values.yaml").read_text() == "replicas: 1"
