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

    def test_helm_app_with_glob_patterns(self, tmp_path):
        """Glob 패턴을 사용한 Overrides 테스트."""
        # 테스트 차트 생성
        chart_dir = tmp_path / "charts" / "nginx" / "nginx"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: nginx\nversion: 1.0.0")
        (chart_dir / "templates").mkdir()
        (chart_dir / "templates" / "deployment.yaml").write_text("kind: Deployment")
        (chart_dir / "templates" / "service.yaml").write_text("kind: Service")

        # Overrides 디렉토리 - 여러 파일 생성
        overrides_dir = tmp_path / "overrides" / "nginx"
        (overrides_dir / "templates").mkdir(parents=True)
        (overrides_dir / "templates" / "configmap.yaml").write_text("kind: ConfigMap")
        (overrides_dir / "templates" / "secret.yaml").write_text("kind: Secret")
        (overrides_dir / "files").mkdir(parents=True)
        (overrides_dir / "files" / "config.txt").write_text("config content")
        (overrides_dir / "files" / "data.json").write_text('{"key": "value"}')

        # HelmApp 설정 - Glob 패턴 사용
        app = HelmApp(
            chart="bitnami/nginx",
            version="15.0.0",
            overrides=[
                "templates/*.yaml",  # 모든 YAML 템플릿
                "files/*",  # 모든 파일
            ],
        )

        # 빌드 실행
        from sbkube.commands.build import build_helm_app

        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="nginx",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
        )

        assert success

        # Glob 패턴으로 복사된 파일들 확인
        assert (build_dir / "nginx" / "templates" / "configmap.yaml").exists()
        assert (build_dir / "nginx" / "templates" / "secret.yaml").exists()
        assert (build_dir / "nginx" / "files" / "config.txt").exists()
        assert (build_dir / "nginx" / "files" / "data.json").exists()

        # 내용 확인
        assert (
            build_dir / "nginx" / "templates" / "configmap.yaml"
        ).read_text() == "kind: ConfigMap"
        assert (
            build_dir / "nginx" / "files" / "config.txt"
        ).read_text() == "config content"

    def test_helm_app_with_mixed_patterns(self, tmp_path):
        """Glob 패턴과 명시적 파일을 혼합 사용."""
        # 테스트 차트 생성
        chart_dir = tmp_path / "charts" / "app" / "app"
        chart_dir.mkdir(parents=True)
        (chart_dir / "Chart.yaml").write_text("name: app\nversion: 1.0.0")
        (chart_dir / "templates").mkdir()

        # Overrides 디렉토리
        overrides_dir = tmp_path / "overrides" / "app"
        (overrides_dir / "templates").mkdir(parents=True)
        (overrides_dir / "templates" / "deployment.yaml").write_text("kind: Deployment")
        (overrides_dir / "templates" / "service.yaml").write_text("kind: Service")
        (overrides_dir / "Chart.yaml").write_text(
            "name: app\nversion: 2.0.0"
        )  # 차트 메타데이터 교체

        # HelmApp 설정 - 혼합 사용
        app = HelmApp(
            chart="my/app",
            overrides=[
                "Chart.yaml",  # 명시적 파일
                "templates/*.yaml",  # Glob 패턴
            ],
        )

        # 빌드 실행
        from sbkube.commands.build import build_helm_app

        build_dir = tmp_path / "build"
        success = build_helm_app(
            app_name="app",
            app=app,
            base_dir=tmp_path,
            charts_dir=tmp_path / "charts",
            build_dir=build_dir,
            app_config_dir=tmp_path,
        )

        assert success

        # 혼합 패턴 결과 확인
        assert (
            build_dir / "app" / "Chart.yaml"
        ).read_text() == "name: app\nversion: 2.0.0"
        assert (build_dir / "app" / "templates" / "deployment.yaml").exists()
        assert (build_dir / "app" / "templates" / "service.yaml").exists()
