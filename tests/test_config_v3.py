"""
SBKube v0.3.0 설정 모델 테스트.
"""

import pytest
from pydantic import ValidationError

from sbkube.models.config_v3 import HelmApp, SBKubeConfigV3, YamlApp


class TestHelmApp:
    """HelmApp 모델 테스트."""

    def test_valid_helm_app(self):
        """정상적인 Helm 앱 검증."""
        app = HelmApp(
            chart="bitnami/redis",
            version="17.13.2",
            values=["redis.yaml"],
        )
        assert app.get_repo_name() == "bitnami"
        assert app.get_chart_name() == "redis"

    def test_local_chart(self):
        """로컬 차트 형식 검증."""
        # 로컬 차트는 유효함
        app1 = HelmApp(chart="./charts/redis")
        assert not app1.is_remote_chart()

        app2 = HelmApp(chart="/absolute/path/to/chart")
        assert not app2.is_remote_chart()

        app3 = HelmApp(chart="redis")  # 로컬 차트로 간주
        assert not app3.is_remote_chart()


class TestYamlApp:
    """YamlApp 모델 테스트."""

    def test_valid_yaml_app(self):
        """정상적인 YAML 앱 검증."""
        app = YamlApp(
            files=["deployment.yaml", "service.yaml"],
            namespace="production",
        )
        assert len(app.files) == 2
        assert app.namespace == "production"

    def test_empty_files_list(self):
        """빈 files 리스트 검증."""
        from sbkube.exceptions import ConfigValidationError

        with pytest.raises(ConfigValidationError, match="files cannot be empty"):
            YamlApp(files=[])


class TestSBKubeConfigV3:
    """SBKubeConfigV3 메인 설정 모델 테스트."""

    def test_valid_config(self):
        """정상적인 설정 검증."""
        config = SBKubeConfigV3(
            namespace="production",
            apps={
                "redis": {
                    "type": "helm",
                    "chart": "bitnami/redis",
                    "values": ["redis.yaml"],
                },
                "backend": {
                    "type": "yaml",
                    "files": ["deployment.yaml"],
                },
            },
        )
        assert config.namespace == "production"
        assert len(config.apps) == 2

    def test_namespace_inheritance(self):
        """네임스페이스 상속 검증."""
        config = SBKubeConfigV3(
            namespace="production",
            apps={
                "redis": {
                    "type": "helm",
                    "chart": "bitnami/redis",
                    # namespace 지정 안 함 → 상속
                },
            },
        )
        redis_app = config.apps["redis"]
        assert redis_app.namespace == "production"

    def test_namespace_override(self):
        """네임스페이스 오버라이드 검증."""
        config = SBKubeConfigV3(
            namespace="production",
            apps={
                "redis": {
                    "type": "helm",
                    "chart": "bitnami/redis",
                    "namespace": "cache",  # 오버라이드
                },
            },
        )
        redis_app = config.apps["redis"]
        assert redis_app.namespace == "cache"

    def test_deployment_order_simple(self):
        """간단한 배포 순서 검증 (의존성 없음)."""
        config = SBKubeConfigV3(
            namespace="test",
            apps={
                "redis": {"type": "helm", "chart": "bitnami/redis"},
                "postgres": {"type": "helm", "chart": "bitnami/postgresql"},
            },
        )
        order = config.get_deployment_order()
        assert len(order) == 2
        assert set(order) == {"redis", "postgres"}

    def test_deployment_order_with_dependencies(self):
        """의존성이 있는 배포 순서 검증."""
        config = SBKubeConfigV3(
            namespace="test",
            apps={
                "backend": {
                    "type": "helm",
                    "chart": "my/backend",
                    "depends_on": ["redis", "postgres"],
                },
                "redis": {"type": "helm", "chart": "bitnami/redis"},
                "postgres": {"type": "helm", "chart": "bitnami/postgresql"},
            },
        )
        order = config.get_deployment_order()
        assert len(order) == 3
        # redis와 postgres가 backend보다 먼저
        backend_idx = order.index("backend")
        redis_idx = order.index("redis")
        postgres_idx = order.index("postgres")
        assert redis_idx < backend_idx
        assert postgres_idx < backend_idx

    def test_circular_dependency_detection(self):
        """순환 의존성 검출 검증."""
        from sbkube.exceptions import ConfigValidationError

        # model_validator에서 초기화 시점에 순환 의존성 검출
        with pytest.raises(ConfigValidationError, match="Circular dependency"):
            SBKubeConfigV3(
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
            SBKubeConfigV3(
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
        config = SBKubeConfigV3(
            namespace="test",
            apps={
                "redis": {"type": "helm", "chart": "bitnami/redis", "enabled": True},
                "postgres": {"type": "helm", "chart": "bitnami/postgresql", "enabled": False},
            },
        )
        enabled_apps = config.get_enabled_apps()
        assert len(enabled_apps) == 1
        assert "redis" in enabled_apps
        assert "postgres" not in enabled_apps

    def test_get_apps_by_type(self):
        """타입별 앱 조회 검증."""
        config = SBKubeConfigV3(
            namespace="test",
            apps={
                "redis": {"type": "helm", "chart": "bitnami/redis"},
                "backend": {"type": "yaml", "files": ["deployment.yaml"]},
                "postgres": {"type": "helm", "chart": "bitnami/postgresql"},
            },
        )
        helm_apps = config.get_apps_by_type("helm")
        assert len(helm_apps) == 2
        assert set(helm_apps.keys()) == {"redis", "postgres"}

        yaml_apps = config.get_apps_by_type("yaml")
        assert len(yaml_apps) == 1
        assert "backend" in yaml_apps
