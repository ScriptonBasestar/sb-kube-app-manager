"""
Performance test fixtures and utilities.

This module provides fixtures for benchmarking and performance testing,
including resource monitoring and test data generation.
"""

import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import psutil
import pytest
import yaml
from faker import Faker


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    operation: str
    duration: float
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_io_read: int = 0
    disk_io_write: int = 0

    @property
    def ops_per_second(self) -> float:
        """Calculate operations per second."""
        return 1.0 / self.duration if self.duration > 0 else 0.0


@dataclass
class ResourceMonitor:
    """Monitor system resources during operations."""

    process: psutil.Process = field(default_factory=lambda: psutil.Process(os.getpid()))
    interval: float = 0.1
    _monitoring: bool = False
    _thread: threading.Thread = None
    _metrics: list[dict[str, float]] = field(default_factory=list)

    def start(self):
        """Start monitoring resources."""
        self._monitoring = True
        self._metrics = []
        self._thread = threading.Thread(target=self._monitor)
        self._thread.daemon = True
        self._thread.start()

    def stop(self) -> dict[str, float]:
        """Stop monitoring and return average metrics."""
        self._monitoring = False
        if self._thread:
            self._thread.join()

        if not self._metrics:
            return {}

        # Calculate averages
        avg_metrics = {
            "cpu_percent": sum(m["cpu_percent"] for m in self._metrics)
            / len(self._metrics),
            "memory_mb": sum(m["memory_mb"] for m in self._metrics)
            / len(self._metrics),
            "peak_memory_mb": max(m["memory_mb"] for m in self._metrics),
        }

        return avg_metrics

    def _monitor(self):
        """Monitor loop running in background thread."""
        while self._monitoring:
            try:
                cpu_percent = self.process.cpu_percent(interval=None)
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                self._metrics.append(
                    {
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb,
                        "timestamp": time.time(),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break

            time.sleep(self.interval)


@contextmanager
def measure_performance(operation: str) -> PerformanceMetrics:
    """
    Context manager to measure performance of an operation.

    Usage:
        with measure_performance("test_operation") as metrics:
            # Do something
        print(f"Took {metrics.duration} seconds")
    """
    monitor = ResourceMonitor()
    start_time = time.perf_counter()

    # Get initial disk I/O
    disk_io_start = psutil.disk_io_counters()

    monitor.start()
    metrics = PerformanceMetrics(operation=operation, duration=0.0)

    yield metrics

    # Stop monitoring and calculate metrics
    end_time = time.perf_counter()
    resource_metrics = monitor.stop()
    disk_io_end = psutil.disk_io_counters()

    metrics.duration = end_time - start_time
    metrics.cpu_percent = resource_metrics.get("cpu_percent", 0.0)
    metrics.memory_mb = resource_metrics.get("peak_memory_mb", 0.0)

    if disk_io_start and disk_io_end:
        metrics.disk_io_read = disk_io_end.read_bytes - disk_io_start.read_bytes
        metrics.disk_io_write = disk_io_end.write_bytes - disk_io_start.write_bytes


@pytest.fixture
def performance_benchmark():
    """
    Fixture for collecting performance benchmarks.

    Returns a collector that can be used to track multiple operations
    and generate a performance report.
    """
    benchmarks = []

    def add_benchmark(metrics: PerformanceMetrics):
        """Add a benchmark result."""
        benchmarks.append(metrics)

    def get_report() -> dict[str, Any]:
        """Generate performance report."""
        if not benchmarks:
            return {}

        total_duration = sum(b.duration for b in benchmarks)
        avg_duration = total_duration / len(benchmarks)

        return {
            "total_operations": len(benchmarks),
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "slowest_operation": max(benchmarks, key=lambda x: x.duration),
            "fastest_operation": min(benchmarks, key=lambda x: x.duration),
            "average_cpu_percent": sum(b.cpu_percent for b in benchmarks)
            / len(benchmarks),
            "peak_memory_mb": max(b.memory_mb for b in benchmarks),
            "total_disk_read_mb": sum(b.disk_io_read for b in benchmarks) / 1024 / 1024,
            "total_disk_write_mb": sum(b.disk_io_write for b in benchmarks)
            / 1024
            / 1024,
        }

    return {"add": add_benchmark, "benchmarks": benchmarks, "get_report": get_report}


@pytest.fixture
def large_project_generator():
    """Generate large project structures for performance testing."""
    faker = Faker()

    def generate_project(
        base_dir: Path,
        num_apps: int = 10,
        num_values_per_app: int = 3,
        num_manifests_per_app: int = 5,
    ) -> Path:
        """
        Generate a large sbkube project for testing.

        Args:
            base_dir: Base directory for project
            num_apps: Number of applications to generate
            num_values_per_app: Number of values files per app
            num_manifests_per_app: Number of manifest files per app

        Returns:
            Path to project directory
        """
        project_dir = base_dir / f"perf_test_{int(time.time())}"
        project_dir.mkdir()

        config_dir = project_dir / "config"
        config_dir.mkdir()
        values_dir = config_dir / "values"
        values_dir.mkdir()

        # Generate sources.yaml
        sources = {
            "cluster": "perf-test-cluster",
            "helm_repos": {
                f"repo-{i}": f"https://example.com/repo-{i}" for i in range(5)
            },
            "git_repos": {
                f"git-{i}": {
                    "url": f"https://github.com/test/repo-{i}.git",
                    "branch": "main",
                }
                for i in range(3)
            },
        }
        with open(project_dir / "sources.yaml", "w") as f:
            yaml.dump(sources, f)

        # Generate apps
        apps = []
        for i in range(num_apps):
            app_name = f"app-{i:03d}"
            app_type = faker.random_element(
                ["install-helm", "install-yaml", "exec", "copy-app"]
            )

            # Generate values files
            for j in range(num_values_per_app):
                values = {
                    "replicaCount": faker.random_int(1, 10),
                    "image": {
                        "repository": faker.word(),
                        "tag": faker.numerify("v#.#.#"),
                    },
                    "resources": {
                        "limits": {
                            "memory": f"{faker.random_int(128, 1024)}Mi",
                            "cpu": f"{faker.random_int(100, 2000)}m",
                        }
                    },
                    "config": {
                        faker.word(): faker.sentence()
                        for _ in range(faker.random_int(5, 20))
                    },
                }
                values_file = values_dir / f"{app_name}-{j}.yaml"
                with open(values_file, "w") as f:
                    yaml.dump(values, f)

            # Create app config based on type
            if app_type == "install-helm":
                specs = {
                    "path": f"charts/{app_name}",
                    "values": [
                        f"{app_name}-{j}.yaml" for j in range(num_values_per_app)
                    ],
                }
            elif app_type == "install-yaml":
                # Generate manifests
                manifests_dir = config_dir / "manifests" / app_name
                manifests_dir.mkdir(parents=True)

                actions = []
                for j in range(num_manifests_per_app):
                    manifest = {
                        "apiVersion": "v1",
                        "kind": faker.random_element(
                            ["ConfigMap", "Secret", "Service"]
                        ),
                        "metadata": {
                            "name": f"{app_name}-{j}",
                            "labels": {
                                faker.word(): faker.word()
                                for _ in range(faker.random_int(3, 10))
                            },
                        },
                        "data": {
                            faker.word(): faker.sentence()
                            for _ in range(faker.random_int(5, 20))
                        },
                    }
                    manifest_file = manifests_dir / f"manifest-{j}.yaml"
                    with open(manifest_file, "w") as f:
                        yaml.dump(manifest, f)

                    actions.append(
                        {
                            "type": "apply",
                            "path": f"manifests/{app_name}/manifest-{j}.yaml",
                        }
                    )

                specs = {"actions": actions}
            elif app_type == "exec":
                specs = {
                    "commands": [
                        f"echo 'Processing {app_name} step {j}'"
                        for j in range(faker.random_int(1, 5))
                    ]
                }
            else:  # copy-app
                specs = {
                    "paths": [{"src": f"source/{app_name}", "dest": f"dest/{app_name}"}]
                }

            apps.append(
                {"name": app_name, "type": app_type, "enabled": True, "specs": specs}
            )

        # Generate config.yaml
        config = {"namespace": "perf-test", "deps": [], "apps": apps}
        with open(config_dir / "config.yaml", "w") as f:
            yaml.dump(config, f)

        return project_dir

    return generate_project


@pytest.fixture
def stress_test_data():
    """Generate data for stress testing."""

    def generate_large_values(size_mb: int = 1) -> dict[str, Any]:
        """Generate large values file for testing."""
        # Calculate approximate size per entry
        entry_size = 100  # bytes
        num_entries = (size_mb * 1024 * 1024) // entry_size

        faker = Faker()
        return {
            f"key_{i}": {
                "value": faker.text(max_nb_chars=50),
                "description": faker.sentence(),
                "enabled": faker.boolean(),
            }
            for i in range(num_entries)
        }

    def generate_many_resources(count: int = 100) -> list[dict[str, Any]]:
        """Generate many Kubernetes resources."""
        faker = Faker()
        resources = []

        for i in range(count):
            resource = {
                "apiVersion": "v1",
                "kind": faker.random_element(["ConfigMap", "Secret", "Service"]),
                "metadata": {
                    "name": f"resource-{i:04d}",
                    "labels": {
                        "app": f"stress-test-{i // 10}",
                        "component": faker.word(),
                        "version": faker.numerify("v#.#.#"),
                    },
                    "annotations": {
                        f"annotation-{j}": faker.sentence()
                        for j in range(faker.random_int(1, 5))
                    },
                },
                "data": {
                    f"key-{j}": faker.text(max_nb_chars=100)
                    for j in range(faker.random_int(5, 20))
                },
            }
            resources.append(resource)

        return resources

    return {
        "generate_large_values": generate_large_values,
        "generate_many_resources": generate_many_resources,
    }
