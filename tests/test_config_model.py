"""
SBKube v0.3.0 설정 모델 테스트.
"""

import pytest

from sbkube.models.config_model import HelmApp, SBKubeConfig, YamlApp


class TestHelmApp:
    """HelmApp 모델 테스트."""

    def test_valid_helm_app(self):
        """정상적인 Helm 앱 검증."""
        app = HelmApp(
            chart="grafana/grafana",
            version="6.50.0",
            values=["grafana.yaml"],
        )
        assert app.get_repo_name() == "grafana"
        assert app.get_chart_name() == "grafana"

    def test_local_chart(self):
        """로컬 차트 형식 검증."""
        # 로컬 차트는 유효함
        app1 = HelmApp(chart="./charts/grafana")
        assert not app1.is_remote_chart()

        app2 = HelmApp(chart="/absolute/path/to/chart")
        assert not app2.is_remote_chart()

        app3 = HelmApp(chart="grafana")  # 로컬 차트로 간주
        assert not app3.is_remote_chart()


class TestYamlApp:
    """YamlApp 모델 테스트."""

    def test_valid_yaml_app(self):
        """정상적인 YAML 앱 검증."""
        app = YamlApp(
            manifests=["deployment.yaml", "service.yaml"],
            namespace="production",
        )
        assert len(app.manifests) == 2
        assert app.namespace == "production"

    def test_empty_manifests_list(self):
        """빈 manifests 리스트 검증."""
        from sbkube.exceptions import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="manifests cannot be empty"):
            YamlApp(manifests=[])


class TestSBKubeConfig:
    """SBKubeConfig 메인 설정 모델 테스트."""

    def test_valid_config(self):
        """정상적인 설정 검증."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "grafana": {
                    "type": "helm",
                    "chart": "grafana/grafana",
                    "values": ["grafana.yaml"],
                },
                "backend": {
                    "type": "yaml",
                    "manifests": ["deployment.yaml"],
                },
            },
        )
        assert config.namespace == "production"
        assert len(config.apps) == 2

    def test_namespace_inheritance(self):
        """네임스페이스 상속 검증."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "grafana": {
                    "type": "helm",
                    "chart": "grafana/grafana",
                    # namespace 지정 안 함 → 상속
                },
            },
        )
        grafana_app = config.apps["grafana"]
        assert grafana_app.namespace == "production"

    def test_namespace_override(self):
        """네임스페이스 오버라이드 검증."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "grafana": {
                    "type": "helm",
                    "chart": "grafana/grafana",
                    "namespace": "monitoring",  # 오버라이드
                },
            },
        )
        grafana_app = config.apps["grafana"]
        assert grafana_app.namespace == "monitoring"

    def test_deployment_order_simple(self):
        """간단한 배포 순서 검증 (의존성 없음)."""
        config = SBKubeConfig(
            namespace="test",
            apps={
                "grafana": {"type": "helm", "chart": "grafana/grafana"},
                "postgres": {"type": "helm", "chart": "cloudnative-pg/cloudnative-pg"},
            },
        )
        order = config.get_deployment_order()
        assert len(order) == 2
        assert set(order) == {"grafana", "postgres"}

    def test_deployment_order_with_dependencies(self):
        """의존성이 있는 배포 순서 검증."""
        config = SBKubeConfig(
            namespace="test",
            apps={
                "backend": {
                    "type": "helm",
                    "chart": "my/backend",
                    "depends_on": ["grafana", "postgres"],
                },
                "grafana": {"type": "helm", "chart": "grafana/grafana"},
                "postgres": {"type": "helm", "chart": "cloudnative-pg/cloudnative-pg"},
            },
        )
        order = config.get_deployment_order()
        assert len(order) == 3
        # grafana와 postgres가 backend보다 먼저
        backend_idx = order.index("backend")
        grafana_idx = order.index("grafana")
        postgres_idx = order.index("postgres")
        assert grafana_idx < backend_idx
        assert postgres_idx < backend_idx

    def test_circular_dependency_detection(self):
        """순환 의존성 검출 검증."""
        from sbkube.exceptions import ConfigValidationError

        # model_validator에서 초기화 시점에 순환 의존성 검출
        with pytest.raises(ConfigValidationError, match="Circular dependency"):
            SBKubeConfig(
                namespace="test",
                apps={
                    "app1": {
                        "type": "helm",
                        "chart": "my/app1",
                        "depends_on": ["app2"],
                    },
                    "app2": {
                        "type": "helm",
                        "chart": "my/app2",
                        "depends_on": ["app1"],
                    },
                },
            )

    def test_nonexistent_dependency(self):
        """존재하지 않는 앱에 대한 의존성 검증."""
        from sbkube.exceptions import ConfigValidationError

        # model_validator에서 초기화 시점에 존재하지 않는 의존성 검출
        with pytest.raises(ConfigValidationError, match="depends on non-existent app"):
            SBKubeConfig(
                namespace="test",
                apps={
                    "backend": {
                        "type": "helm",
                        "chart": "my/backend",
                        "depends_on": ["nonexistent"],
                    },
                },
            )

    def test_disabled_apps(self):
        """비활성화된 앱 처리 검증."""
        config = SBKubeConfig(
            namespace="test",
            apps={
                "grafana": {"type": "helm", "chart": "grafana/grafana", "enabled": True},
                "postgres": {
                    "type": "helm",
                    "chart": "cloudnative-pg/cloudnative-pg",
                    "enabled": False,
                },
            },
        )
        enabled_apps = config.get_enabled_apps()
        assert len(enabled_apps) == 1
        assert "grafana" in enabled_apps
        assert "postgres" not in enabled_apps

    def test_get_apps_by_type(self):
        """타입별 앱 조회 검증."""
        config = SBKubeConfig(
            namespace="test",
            apps={
                "grafana": {"type": "helm", "chart": "grafana/grafana"},
                "backend": {"type": "yaml", "manifests": ["deployment.yaml"]},
                "postgres": {"type": "helm", "chart": "cloudnative-pg/cloudnative-pg"},
            },
        )
        helm_apps = config.get_apps_by_type("helm")
        assert len(helm_apps) == 2
        assert set(helm_apps.keys()) == {"grafana", "postgres"}

        yaml_apps = config.get_apps_by_type("yaml")
        assert len(yaml_apps) == 1
        assert "backend" in yaml_apps

    def test_deps_field_parsing(self):
        """deps 필드 파싱 검증 (v0.4.10+)."""
        config = SBKubeConfig(
            namespace="harbor",
            deps=["a000_infra_network", "a101_data_rdb", "a100_data_memory"],
            apps={
                "harbor": {
                    "type": "helm",
                    "chart": "harbor/harbor",
                },
            },
        )
        assert len(config.deps) == 3
        assert "a000_infra_network" in config.deps
        assert "a101_data_rdb" in config.deps
        assert "a100_data_memory" in config.deps

    def test_deps_field_optional(self):
        """deps 필드가 없어도 정상 동작 (후방 호환성)."""
        config = SBKubeConfig(
            namespace="production",
            apps={
                "grafana": {
                    "type": "helm",
                    "chart": "grafana/grafana",
                },
            },
        )
        assert config.deps == []  # 기본값 빈 리스트

    def test_deps_field_empty_list(self):
        """deps가 빈 리스트인 경우."""
        config = SBKubeConfig(
            namespace="production",
            deps=[],
            apps={
                "grafana": {
                    "type": "helm",
                    "chart": "grafana/grafana",
                },
            },
        )
        assert config.deps == []
