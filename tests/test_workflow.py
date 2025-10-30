"""
SBKube v0.3.0 통합 워크플로우 테스트.

prepare → build → template → deploy 전체 워크플로우를 검증합니다.
"""

import yaml

from sbkube.commands.build import build_helm_app
from sbkube.models.config_model import HelmApp, SBKubeConfig


class TestWorkflowV3:
    """v0.3.0 워크플로우 통합 테스트."""

    def test_full_workflow_with_overrides(self, tmp_path):
        """
        전체 워크플로우 테스트: prepare → build → (deploy 제외).

        overrides가 올바르게 적용되는지 검증합니다.
        """
        # 1. 디렉토리 구조 생성
        charts_dir = tmp_path / "charts"
        build_dir = tmp_path / "build"
        app_config_dir = tmp_path / "config"
        overrides_dir = app_config_dir / "overrides" / "redis"

        charts_dir.mkdir(parents=True, exist_ok=True)
        app_config_dir.mkdir(parents=True, exist_ok=True)
        overrides_dir.mkdir(parents=True, exist_ok=True)

        # 2. sources.yaml 생성
        sources_file = tmp_path / "sources.yaml"
        sources_file.write_text(
            yaml.dump(
                {
                    "helm": {
                        "bitnami": "https://charts.bitnami.com/bitnami",
                    }
                }
            )
        )

        # 3. Mock chart (prepare 시뮬레이션)
        # 실제로는 helm pull을 실행하지만, 테스트에서는 미리 차트를 생성
        mock_chart_dir = charts_dir / "redis" / "redis"
        mock_chart_dir.mkdir(parents=True, exist_ok=True)
        (mock_chart_dir / "Chart.yaml").write_text("name: redis\nversion: 17.13.2")
        (mock_chart_dir / "values.yaml").write_text(
            "replicaCount: 1\nimage:\n  tag: 7.0"
        )
        (mock_chart_dir / "templates").mkdir(exist_ok=True)
        (mock_chart_dir / "templates" / "deployment.yaml").write_text(
            "kind: Deployment\nmetadata:\n  name: redis"
        )
        (mock_chart_dir / "README.md").write_text("# Redis Chart")

        # 4. Overrides 파일 생성
        (overrides_dir / "values.yaml").write_text(
            "replicaCount: 3\nimage:\n  tag: 7.2"
        )

        # 5. HelmApp 설정
        app = HelmApp(
            chart="bitnami/redis",
            version="17.13.2",
            overrides=["values.yaml"],
            removes=["README.md"],
        )

        # 6. Build 실행 (overrides/removes 적용)
        success = build_helm_app(
            app_name="redis",
            app=app,
            base_dir=tmp_path,
            charts_dir=charts_dir,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
        )

        assert success, "Build should succeed"

        # 7. 검증: build 디렉토리 생성
        assert (build_dir / "redis").exists()
        assert (build_dir / "redis" / "Chart.yaml").exists()

        # 8. 검증: overrides 적용됨
        values_content = (build_dir / "redis" / "values.yaml").read_text()
        assert "replicaCount: 3" in values_content
        assert "tag: 7.2" in values_content

        # 9. 검증: removes 적용됨
        assert not (build_dir / "redis" / "README.md").exists()

        # 10. 검증: 원본 차트는 변경되지 않음
        original_values = (mock_chart_dir / "values.yaml").read_text()
        assert "replicaCount: 1" in original_values
        assert (mock_chart_dir / "README.md").exists()

    def test_config_v3_dependency_resolution(self, tmp_path):
        """
        의존성 해결 테스트.

        depends_on 필드가 올바르게 처리되는지 검증합니다.
        """
        # config.yaml 생성
        config_file = tmp_path / "config.yaml"
        config_data = {
            "namespace": "test",
            "apps": {
                "database": {
                    "type": "helm",
                    "chart": "bitnami/postgresql",
                },
                "cache": {
                    "type": "helm",
                    "chart": "bitnami/redis",
                    "depends_on": ["database"],
                },
                "app": {
                    "type": "helm",
                    "chart": "myapp/backend",
                    "depends_on": ["database", "cache"],
                },
            },
        }
        config_file.write_text(yaml.dump(config_data))

        # 설정 로드
        config = SBKubeConfig(**config_data)

        # 의존성 순서 확인
        deployment_order = config.get_deployment_order()

        assert deployment_order[0] == "database", "database should be first"
        assert deployment_order[1] == "cache", (
            "cache should be second (depends on database)"
        )
        assert deployment_order[2] == "app", (
            "app should be last (depends on database, cache)"
        )

    def test_local_chart_workflow(self, tmp_path):
        """
        로컬 차트 워크플로우 테스트.

        로컬 차트도 overrides/removes가 올바르게 적용되는지 검증합니다.
        """
        # 1. 로컬 차트 생성
        local_chart_dir = tmp_path / "my-chart"
        local_chart_dir.mkdir(exist_ok=True)
        (local_chart_dir / "Chart.yaml").write_text("name: my-chart\nversion: 1.0.0")
        (local_chart_dir / "values.yaml").write_text("enabled: true\nport: 8080")
        (local_chart_dir / "templates").mkdir(exist_ok=True)
        (local_chart_dir / "templates" / "deployment.yaml").write_text(
            "kind: Deployment"
        )
        (local_chart_dir / "LICENSE").write_text("MIT License")

        # 2. Overrides 디렉토리
        overrides_dir = tmp_path / "overrides" / "my-app"
        overrides_dir.mkdir(parents=True, exist_ok=True)
        (overrides_dir / "values.yaml").write_text("enabled: false\nport: 9000")

        # 3. HelmApp 설정 (로컬 차트)
        app = HelmApp(
            chart="./my-chart",
            overrides=["values.yaml"],
            removes=["LICENSE"],
        )

        # 4. Build 실행
        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",  # 사용 안 됨
            build_dir=build_dir,
            app_config_dir=tmp_path,
        )

        assert success, "Build should succeed"

        # 5. 검증: overrides 적용
        values_content = (build_dir / "my-app" / "values.yaml").read_text()
        assert "enabled: false" in values_content
        assert "port: 9000" in values_content

        # 6. 검증: removes 적용
        assert not (build_dir / "my-app" / "LICENSE").exists()

        # 7. 검증: 원본 차트는 변경되지 않음
        original_values = (local_chart_dir / "values.yaml").read_text()
        assert "enabled: true" in original_values
        assert (local_chart_dir / "LICENSE").exists()

    def test_http_app_workflow(self, tmp_path):
        """
        HttpApp 워크플로우 테스트.

        HTTP 다운로드 → build 단계를 검증합니다.
        """
        from sbkube.models.config_model import HttpApp

        # 1. Mock 다운로드 파일 생성 (prepare 시뮬레이션)
        app_config_dir = tmp_path / "config"
        app_config_dir.mkdir(exist_ok=True)
        downloaded_file = app_config_dir / "downloaded.yaml"
        downloaded_file.write_text("apiVersion: v1\nkind: ConfigMap")

        # 2. HttpApp 설정
        app = HttpApp(
            url="https://example.com/file.yaml",
            dest="downloaded.yaml",
        )

        # 3. Build 실행
        from sbkube.commands.build import build_http_app

        build_dir = tmp_path / "build"
        success = build_http_app(
            app_name="my-http-app",
            app=app,
            base_dir=tmp_path,
            build_dir=build_dir,
            app_config_dir=app_config_dir,
        )

        assert success, "Build should succeed"

        # 4. 검증: build 디렉토리에 파일 복사됨
        assert (build_dir / "my-http-app" / "downloaded.yaml").exists()

        content = (build_dir / "my-http-app" / "downloaded.yaml").read_text()
        assert "kind: ConfigMap" in content
