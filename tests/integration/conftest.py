"""
Integration test fixtures and utilities.

This module provides fixtures for setting up test environments
including Kubernetes clusters, Helm repositories, and Git servers.
"""

import os
import shutil
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import pytest
import yaml

# Only import if available
try:
    from kubernetes import client, config
    from testcontainers.k3s import K3sContainer

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


@pytest.fixture(scope="session")
def k8s_cluster():
    """
    Provide a K3s Kubernetes cluster for testing.

    This fixture creates a K3s container that runs for the entire test session.
    Tests marked with @pytest.mark.requires_k8s will use this cluster.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available, skipping K8s integration tests")

    with K3sContainer() as k3s:
        # Wait for cluster to be ready
        k3s.wait_for_logs("k3s is up and running", timeout=60)

        # Get kubeconfig
        kubeconfig_str = k3s.exec("cat /etc/rancher/k3s/k3s.yaml").output.decode()

        # Write kubeconfig to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            # Update server URL to use container's exposed port
            kubeconfig_data = yaml.safe_load(kubeconfig_str)
            kubeconfig_data["clusters"][0]["cluster"][
                "server"
            ] = k3s.get_connection_url()
            yaml.dump(kubeconfig_data, f)
            kubeconfig_path = f.name

        yield {
            "container": k3s,
            "kubeconfig": kubeconfig_path,
            "api_url": k3s.get_connection_url(),
        }

        # Cleanup
        os.unlink(kubeconfig_path)


@pytest.fixture(scope="function")
def k8s_namespace(k8s_cluster):
    """
    Create a unique namespace for each test.

    This ensures test isolation and easy cleanup.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    # Load kubeconfig
    config.load_kube_config(config_file=k8s_cluster["kubeconfig"])
    v1 = client.CoreV1Api()

    # Create unique namespace
    namespace_name = f"test-{int(time.time())}"
    namespace = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace_name))
    v1.create_namespace(namespace)

    yield namespace_name

    # Cleanup
    v1.delete_namespace(namespace_name)


@pytest.fixture(scope="session")
def helm_binary():
    """
    Ensure Helm binary is available and return its path.
    """
    helm_path = shutil.which("helm")
    if not helm_path:
        pytest.skip("Helm not found in PATH")

    # Check Helm version
    result = subprocess.run(
        [helm_path, "version", "--short"], capture_output=True, text=True
    )
    if result.returncode != 0:
        pytest.skip(f"Helm version check failed: {result.stderr}")

    return helm_path


@pytest.fixture(scope="function")
def helm_repo_server():
    """
    Start a local Helm repository server for testing.

    This uses Python's built-in HTTP server to serve charts.
    """
    repo_dir = tempfile.mkdtemp()
    charts_dir = Path(repo_dir) / "charts"
    charts_dir.mkdir()

    # Create a simple test chart
    test_chart_dir = charts_dir / "test-chart"
    test_chart_dir.mkdir()

    # Chart.yaml
    chart_yaml = {
        "apiVersion": "v2",
        "name": "test-chart",
        "version": "1.0.0",
        "description": "A test Helm chart",
    }
    with open(test_chart_dir / "Chart.yaml", "w") as f:
        yaml.dump(chart_yaml, f)

    # values.yaml
    values_yaml = {"replicaCount": 1, "image": {"repository": "nginx", "tag": "latest"}}
    with open(test_chart_dir / "values.yaml", "w") as f:
        yaml.dump(values_yaml, f)

    # Create templates directory
    templates_dir = test_chart_dir / "templates"
    templates_dir.mkdir()

    # deployment.yaml template
    deployment_template = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Release.Name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Release.Name }}
  template:
    metadata:
      labels:
        app: {{ .Release.Name }}
    spec:
      containers:
      - name: nginx
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
"""
    with open(templates_dir / "deployment.yaml", "w") as f:
        f.write(deployment_template)

    # Package the chart
    subprocess.run(
        ["helm", "package", str(test_chart_dir), "-d", str(charts_dir)], check=True
    )

    # Generate index
    subprocess.run(["helm", "repo", "index", str(charts_dir)], check=True)

    # Start HTTP server
    import http.server
    import threading

    port = 8879  # Random port
    handler = http.server.SimpleHTTPRequestHandler

    def serve():
        os.chdir(charts_dir)
        with http.server.HTTPServer(("", port), handler) as httpd:
            httpd.serve_forever()

    server_thread = threading.Thread(target=serve, daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(1)

    yield {
        "url": f"http://localhost:{port}",
        "charts_dir": charts_dir,
        "charts": ["test-chart"],
    }

    # Cleanup
    shutil.rmtree(repo_dir)


@pytest.fixture(scope="function")
def git_repo():
    """
    Create a temporary Git repository for testing.
    """
    repo_dir = tempfile.mkdtemp()

    # Initialize repo
    subprocess.run(["git", "init"], cwd=repo_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True
    )

    # Add some test files
    test_file = Path(repo_dir) / "test.yaml"
    test_file.write_text("test: data\n")

    # Create a chart directory
    chart_dir = Path(repo_dir) / "charts" / "app"
    chart_dir.mkdir(parents=True)

    # Add Chart.yaml
    chart_yaml = {"apiVersion": "v2", "name": "app", "version": "1.0.0"}
    with open(chart_dir / "Chart.yaml", "w") as f:
        yaml.dump(chart_yaml, f)

    # Commit
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True)

    yield repo_dir

    # Cleanup
    shutil.rmtree(repo_dir)


@pytest.fixture
def sbkube_project(tmp_path):
    """
    Create a complete sbkube project structure for integration testing.
    """
    # Create directory structure
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    config_dir = project_dir / "config"
    config_dir.mkdir()

    values_dir = config_dir / "values"
    values_dir.mkdir()

    charts_dir = project_dir / "charts"
    charts_dir.mkdir()

    # Create sources.yaml
    sources = {
        "cluster": "test-cluster",
        "kubeconfig": "~/.kube/config",
        "helm_repos": {
            "bitnami": "https://charts.bitnami.com/bitnami",
            "stable": "https://charts.helm.sh/stable",
        },
        "git_repos": {
            "test-repo": {"url": "https://github.com/test/repo.git", "branch": "main"}
        },
    }
    with open(project_dir / "sources.yaml", "w") as f:
        yaml.dump(sources, f)

    # Create config.yaml
    config = {
        "namespace": "test-namespace",
        "apps": [
            {
                "name": "redis",
                "type": "pull-helm",
                "specs": {
                    "repo": "bitnami",
                    "chart": "redis",
                    "chart_version": "17.0.0",
                },
            },
            {
                "name": "redis",
                "type": "install-helm",
                "enabled": True,
                "specs": {"path": "redis", "values": ["redis-values.yaml"]},
            },
        ],
    }
    with open(config_dir / "config.yaml", "w") as f:
        yaml.dump(config, f)

    # Create values file
    redis_values = {
        "auth": {"enabled": False},
        "master": {"persistence": {"enabled": False}},
    }
    with open(values_dir / "redis-values.yaml", "w") as f:
        yaml.dump(redis_values, f)

    return project_dir


@contextmanager
def timer():
    """
    Context manager for timing operations.

    Usage:
        with timer() as t:
            # Do something
        print(f"Took {t.elapsed} seconds")
    """

    class Timer:
        def __init__(self):
            self.start = None
            self.end = None
            self.elapsed = None

    t = Timer()
    t.start = time.time()

    yield t

    t.end = time.time()
    t.elapsed = t.end - t.start


@pytest.fixture
def performance_tracker():
    """
    Track performance metrics during tests.
    """
    metrics = {"operations": [], "memory_usage": [], "cpu_usage": []}

    def track_operation(name: str, duration: float, **kwargs):
        """Track an operation's performance."""
        metrics["operations"].append(
            {"name": name, "duration": duration, "timestamp": time.time(), **kwargs}
        )

    def get_summary():
        """Get performance summary."""
        if not metrics["operations"]:
            return {}

        total_duration = sum(op["duration"] for op in metrics["operations"])
        avg_duration = total_duration / len(metrics["operations"])

        return {
            "total_operations": len(metrics["operations"]),
            "total_duration": total_duration,
            "average_duration": avg_duration,
            "slowest_operation": (
                max(metrics["operations"], key=lambda x: x["duration"])
                if metrics["operations"]
                else None
            ),
        }

    metrics["track_operation"] = track_operation
    metrics["get_summary"] = get_summary

    return metrics


@pytest.fixture
def mock_external_services(monkeypatch):
    """
    Mock external service calls for isolated testing.
    """
    mocks = {}

    # Mock subprocess calls
    original_run = subprocess.run

    def mock_run(cmd, *args, **kwargs):
        cmd_str = " ".join(cmd) if isinstance(cmd, list) else cmd

        # Track the call
        if "subprocess_calls" not in mocks:
            mocks["subprocess_calls"] = []
        mocks["subprocess_calls"].append(
            {"command": cmd_str, "args": args, "kwargs": kwargs}
        )

        # Return mock responses for known commands
        if "helm" in cmd_str:
            if "version" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, "v3.12.0", "")
            elif "list" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, "[]", "")

        if "kubectl" in cmd_str:
            if "version" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, "v1.28.0", "")
            elif "get" in cmd_str:
                return subprocess.CompletedProcess(cmd, 0, "{}", "")

        # Default to original for unhandled commands
        return original_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    return mocks
