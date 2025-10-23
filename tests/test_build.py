"""
SBKube v0.3.0 build 명령어 테스트.
"""



from sbkube.models.config_model import HelmApp


class TestBuildV3:
    """build_v3.py 테스트."""

    def test_helm_app_with_overrides(self, tmp_path):
        """Overrides가 있는 Helm 앱 빌드 검증."""
        # 테스트 디렉토리 구조 생성
        charts_dir = tmp_path / "charts" / "redis" / "redis"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: redis\nversion: 1.0.0")
        (charts_dir / "values.yaml").write_text("replicaCount: 1")
        (charts_dir / "templates").mkdir()
        (charts_dir / "templates" / "deployment.yaml").write_text("kind: Deployment")

        # Overrides 디렉토리
        overrides_dir = tmp_path / "overrides" / "redis"
        overrides_dir.mkdir(parents=True)
        (overrides_dir / "values.yaml").write_text("replicaCount: 3")  # 오버라이드

        # HelmApp 설정
        app = HelmApp(
            chart="bitnami/redis",
            version="17.13.2",
            overrides=["values.yaml"],
        )

        # build 디렉토리
        build_dir = tmp_path / "build"

        # 빌드 실행 (모의)
        from sbkube.commands.build import build_helm_app

        success = build_helm_app(
            app_name="redis",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
        )

        assert success
        assert (build_dir / "redis" / "Chart.yaml").exists()
        assert (build_dir / "redis" / "values.yaml").read_text() == "replicaCount: 3"

    def test_helm_app_with_removes(self, tmp_path):
        """Removes가 있는 Helm 앱 빌드 검증."""
        # 테스트 디렉토리 구조 생성
        charts_dir = tmp_path / "charts" / "redis" / "redis"
        charts_dir.mkdir(parents=True)
        (charts_dir / "Chart.yaml").write_text("name: redis")
        (charts_dir / "README.md").write_text("# Redis Chart")  # 제거 대상
        (charts_dir / "templates").mkdir()
        (charts_dir / "templates" / "deployment.yaml").write_text("kind: Deployment")

        # HelmApp 설정
        app = HelmApp(
            chart="bitnami/redis",
            version="17.13.2",
            removes=["README.md"],
        )

        # build 디렉토리
        build_dir = tmp_path / "build"

        # 빌드 실행
        from sbkube.commands.build import build_helm_app

        success = build_helm_app(
            app_name="redis",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
        )

        assert success
        assert (build_dir / "redis" / "Chart.yaml").exists()
        assert not (build_dir / "redis" / "README.md").exists()

    def test_local_chart_build(self, tmp_path):
        """로컬 차트 빌드 검증."""
        # 로컬 차트 생성
        local_chart_dir = tmp_path / "my-chart"
        local_chart_dir.mkdir()
        (local_chart_dir / "Chart.yaml").write_text("name: my-chart")
        (local_chart_dir / "values.yaml").write_text("enabled: true")

        # HelmApp 설정 (로컬 차트)
        app = HelmApp(
            chart="./my-chart",
            overrides=["values.yaml"],
        )

        # Overrides 디렉토리
        overrides_dir = tmp_path / "overrides" / "my-app"
        overrides_dir.mkdir(parents=True)
        (overrides_dir / "values.yaml").write_text("enabled: false")

        # build 디렉토리
        build_dir = tmp_path / "build"

        # 빌드 실행
        from sbkube.commands.build import build_helm_app

        success = build_helm_app(
            app_name="my-app",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
        )

        assert success
        assert (build_dir / "my-app" / "Chart.yaml").exists()
        assert (build_dir / "my-app" / "values.yaml").read_text() == "enabled: false"
