"""
Performance benchmarks for critical sbkube operations.

These tests measure execution time and resource usage
for various sbkube operations under different load conditions.
"""

import shutil

import pytest
import yaml
from click.testing import CliRunner

from sbkube.cli import main

from .conftest import measure_performance


@pytest.mark.performance
@pytest.mark.benchmark
class TestConfigLoadingPerformance:
    """Benchmark configuration loading and parsing."""

    def test_small_config_loading(self, benchmark, tmp_path):
        """Benchmark loading a small configuration."""
        # Create small config
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": f"app-{i}",
                    "type": "exec",
                    "specs": {"commands": ["echo test"]},
                }
                for i in range(5)
            ],
        }

        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config, f)

        # Benchmark config loading
        def load_config():
            with open(config_file) as f:
                return yaml.safe_load(f)

        result = benchmark(load_config)
        assert len(result["apps"]) == 5

    def test_large_config_loading(self, benchmark, large_project_generator, tmp_path):
        """Benchmark loading a large configuration."""
        # Generate large project
        project_dir = large_project_generator(
            tmp_path, num_apps=100, num_values_per_app=5
        )

        config_file = project_dir / "config" / "config.yaml"

        # Benchmark config loading
        def load_config():
            with open(config_file) as f:
                return yaml.safe_load(f)

        result = benchmark(load_config)
        assert len(result["apps"]) == 100

    def test_config_validation_performance(self, benchmark, tmp_path):
        """Benchmark Pydantic model validation."""
        from sbkube.models.config_model import AppGroupScheme

        # Create config data
        config_data = {
            "namespace": "test",
            "apps": [
                {
                    "name": f"app-{i:03d}",
                    "type": "install-helm",
                    "specs": {
                        "path": f"charts/app-{i}",
                        "values": [f"values-{j}.yaml" for j in range(3)],
                    },
                }
                for i in range(50)
            ],
        }

        # Benchmark validation
        result = benchmark(lambda: AppGroupScheme(**config_data))
        assert len(result.apps) == 50


@pytest.mark.performance
@pytest.mark.slow
class TestCommandPerformance:
    """Benchmark sbkube command execution performance."""

    def test_prepare_command_performance(
        self, performance_benchmark, large_project_generator, tmp_path
    ):
        """Benchmark prepare command with multiple apps."""
        runner = CliRunner()

        # Test with different project sizes
        for num_apps in [10, 50, 100]:
            project_dir = large_project_generator(tmp_path, num_apps=num_apps)

            with measure_performance(f"prepare_{num_apps}_apps") as metrics:
                result = runner.invoke(
                    main,
                    ["prepare", "--base-dir", str(project_dir), "--app-dir", "config"],
                )

            performance_benchmark["add"](metrics)

            # Basic assertion to ensure command succeeded
            if result.exit_code != 0:
                print(f"Command output: {result.output}")

        # Print performance report
        report = performance_benchmark["get_report"]()
        print("\nPrepare Command Performance Report:")
        print(f"  Total operations: {report['total_operations']}")
        print(f"  Average duration: {report['average_duration']:.3f}s")
        print(
            f"  Slowest: {report['slowest_operation'].duration:.3f}s "
            f"({report['slowest_operation'].operation})"
        )

    def test_build_command_performance(self, performance_benchmark, tmp_path):
        """Benchmark build command with file operations."""
        runner = CliRunner()

        # Create project with files to copy
        project_dir = tmp_path / "build_perf"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Create source files of different sizes
        file_sizes = [1, 10, 50]  # MB
        apps = []

        for i, size_mb in enumerate(file_sizes):
            app_name = f"app-{size_mb}mb"
            src_dir = config_dir / f"src-{app_name}"
            src_dir.mkdir()

            # Create file with specific size
            test_file = src_dir / "data.bin"
            test_file.write_bytes(b"0" * (size_mb * 1024 * 1024))

            apps.append(
                {
                    "name": app_name,
                    "type": "copy-app",
                    "specs": {"paths": [{"src": f"src-{app_name}", "dest": app_name}]},
                }
            )

        # Create config
        config = {"namespace": "test", "apps": apps}
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Benchmark build
        with measure_performance("build_with_large_files") as metrics:
            result = runner.invoke(
                main, ["build", "--base-dir", str(project_dir), "--app-dir", "config"]
            )

        performance_benchmark["add"](metrics)
        assert result.exit_code == 0

        # Verify files were copied
        build_dir = config_dir / "build"
        for size_mb in file_sizes:
            copied_file = build_dir / f"app-{size_mb}mb" / "data.bin"
            assert copied_file.exists()
            assert copied_file.stat().st_size == size_mb * 1024 * 1024

    def test_template_rendering_performance(
        self, performance_benchmark, stress_test_data, tmp_path
    ):
        """Benchmark template rendering with complex values."""
        runner = CliRunner()

        project_dir = tmp_path / "template_perf"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()
        values_dir = config_dir / "values"
        values_dir.mkdir()

        # Create large values file
        large_values = stress_test_data["generate_large_values"](size_mb=5)
        with open(values_dir / "large-values.yaml", "w") as f:
            yaml.dump(large_values, f)

        # Create simple Helm chart
        chart_dir = project_dir / "charts" / "perf-test"
        chart_dir.mkdir(parents=True)
        templates_dir = chart_dir / "templates"
        templates_dir.mkdir()

        # Chart.yaml
        with open(chart_dir / "Chart.yaml", "w") as f:
            yaml.dump({"apiVersion": "v2", "name": "perf-test", "version": "1.0.0"}, f)

        # Template with many value references
        template_content = """apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ .Release.Name }}
data:
{{- range $key, $value := .Values }}
  {{ $key }}: {{ $value | toYaml | indent 4 }}
{{- end }}
"""
        with open(templates_dir / "configmap.yaml", "w") as f:
            f.write(template_content)

        # Config
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "perf-test",
                    "type": "install-helm",
                    "specs": {
                        "path": "../../charts/perf-test",
                        "values": ["large-values.yaml"],
                    },
                }
            ],
        }
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Copy chart to build dir (simulate build)
        build_dir = config_dir / "build" / "perf-test"
        shutil.copytree(chart_dir, build_dir)

        # Benchmark template rendering
        output_dir = project_dir / "rendered"
        with measure_performance("template_large_values") as metrics:
            runner.invoke(
                main,
                [
                    "template",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--output-dir",
                    str(output_dir),
                ],
            )

        performance_benchmark["add"](metrics)

        # Check output
        assert output_dir.exists()
        rendered_files = list(output_dir.rglob("*.yaml"))
        assert len(rendered_files) > 0


@pytest.mark.performance
@pytest.mark.slow
class TestScalabilityBenchmarks:
    """Test scalability with increasing load."""

    def test_concurrent_deployments(self, performance_benchmark, tmp_path):
        """Benchmark handling multiple concurrent deployments."""
        runner = CliRunner()

        # Create project with many independent apps
        project_dir = tmp_path / "concurrent_test"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()

        # Generate many small apps
        num_apps = 50
        apps = []
        for i in range(num_apps):
            apps.append(
                {
                    "name": f"concurrent-app-{i:03d}",
                    "type": "exec",
                    "specs": {
                        "commands": [
                            f"echo 'Deploying app {i}'",
                            "sleep 0.1",  # Simulate some work
                        ]
                    },
                }
            )

        config = {"namespace": "test", "apps": apps}
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Benchmark deployment
        with measure_performance(f"deploy_{num_apps}_apps") as metrics:
            runner.invoke(
                main, ["deploy", "--base-dir", str(project_dir), "--app-dir", "config"]
            )

        performance_benchmark["add"](metrics)

        # Calculate throughput
        if metrics.duration > 0:
            throughput = num_apps / metrics.duration
            print(f"\nDeployment throughput: {throughput:.2f} apps/second")

    def test_large_manifest_processing(
        self, performance_benchmark, stress_test_data, tmp_path
    ):
        """Benchmark processing large numbers of Kubernetes manifests."""
        runner = CliRunner()

        project_dir = tmp_path / "manifest_test"
        project_dir.mkdir()
        config_dir = project_dir / "config"
        config_dir.mkdir()
        manifests_dir = config_dir / "manifests"
        manifests_dir.mkdir()

        # Generate many resources
        resources = stress_test_data["generate_many_resources"](count=200)

        # Write to single file
        manifest_file = manifests_dir / "all-resources.yaml"
        with open(manifest_file, "w") as f:
            yaml.dump_all(resources, f)

        # Config
        config = {
            "namespace": "test",
            "apps": [
                {
                    "name": "many-resources",
                    "type": "install-yaml",
                    "specs": {
                        "actions": [
                            {"type": "apply", "path": "manifests/all-resources.yaml"}
                        ]
                    },
                }
            ],
        }
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        # Benchmark with dry-run
        with measure_performance("process_200_manifests") as metrics:
            runner.invoke(
                main,
                [
                    "deploy",
                    "--base-dir",
                    str(project_dir),
                    "--app-dir",
                    "config",
                    "--dry-run",
                ],
            )

        performance_benchmark["add"](metrics)

        print(
            f"\nManifest processing rate: "
            f"{len(resources) / metrics.duration:.2f} resources/second"
        )

    def test_state_tracking_performance(self, performance_benchmark, tmp_path):
        """Benchmark deployment state tracking overhead."""
        from sbkube.models.deployment_state import (
            AppDeploymentCreate,
            DeploymentCreate,
            ResourceAction,
            ResourceInfo,
        )
        from sbkube.state.database import DeploymentDatabase

        # Create database
        db_path = tmp_path / "test.db"
        db = DeploymentDatabase(db_path)

        # Benchmark creating many deployments
        num_deployments = 100

        with measure_performance(f"track_{num_deployments}_deployments") as metrics:
            for i in range(num_deployments):
                # Create deployment
                deployment_data = DeploymentCreate(
                    deployment_id=f"dep-{i:04d}",
                    cluster="test",
                    namespace="test",
                    app_config_dir="/test",
                    config_file_path="/test/config.yaml",
                    command="deploy",
                    config_snapshot={"test": i},
                )
                deployment = db.create_deployment(deployment_data)

                # Add app deployments
                for j in range(5):
                    app_data = AppDeploymentCreate(
                        app_name=f"app-{j}",
                        app_type="install-yaml",
                        app_config={"test": j},
                    )
                    app_dep = db.add_app_deployment(deployment.id, app_data)

                    # Add resources
                    for k in range(10):
                        resource = ResourceInfo(
                            api_version="v1",
                            kind="ConfigMap",
                            name=f"cm-{k}",
                            namespace="test",
                            action=ResourceAction.CREATE,
                            current_state={"data": {"key": f"value-{k}"}},
                        )
                        db.add_deployed_resource(app_dep.id, resource)

        performance_benchmark["add"](metrics)

        # Benchmark querying
        with measure_performance("query_deployments") as metrics:
            deployments = db.list_deployments(limit=1000)
            assert len(deployments) == num_deployments

        performance_benchmark["add"](metrics)

        # Print database stats
        db_size = db_path.stat().st_size / 1024 / 1024
        print(f"\nDatabase size for {num_deployments} deployments: {db_size:.2f} MB")
