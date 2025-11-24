"""Tests for manifest_cleaner utility."""

import pytest

from sbkube.utils.manifest_cleaner import clean_manifest_file, clean_manifest_metadata


class TestCleanManifestMetadata:
    """Test clean_manifest_metadata function."""

    def test_clean_managed_fields(self):
        """Test removing metadata.managedFields."""
        manifest = """
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
  managedFields:
    - manager: kubectl
      operation: Update
spec:
  containers:
  - name: nginx
    image: nginx:latest
"""
        result = clean_manifest_metadata(manifest)
        assert "managedFields" not in result
        assert "test-pod" in result
        assert "nginx:latest" in result

    def test_clean_creation_timestamp(self):
        """Test removing metadata.creationTimestamp."""
        manifest = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  creationTimestamp: "2024-01-01T00:00:00Z"
spec:
  selector:
    app: MyApp
  ports:
  - protocol: TCP
    port: 80
"""
        result = clean_manifest_metadata(manifest)
        assert "creationTimestamp" not in result
        assert "my-service" in result

    def test_clean_resource_version(self):
        """Test removing metadata.resourceVersion."""
        manifest = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-config
  resourceVersion: "12345"
data:
  key: value
"""
        result = clean_manifest_metadata(manifest)
        assert "resourceVersion" not in result
        assert "my-config" in result
        assert "key: value" in result

    def test_clean_uid(self):
        """Test removing metadata.uid."""
        manifest = """
apiVersion: v1
kind: Secret
metadata:
  name: my-secret
  uid: 123e4567-e89b-12d3-a456-426614174000
type: Opaque
data:
  password: cGFzc3dvcmQ=
"""
        result = clean_manifest_metadata(manifest)
        assert "uid:" not in result
        assert "my-secret" in result

    def test_clean_generation(self):
        """Test removing metadata.generation."""
        manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx-deployment
  generation: 5
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nginx
  template:
    metadata:
      labels:
        app: nginx
    spec:
      containers:
      - name: nginx
        image: nginx:1.14.2
"""
        result = clean_manifest_metadata(manifest)
        assert "generation:" not in result
        assert "nginx-deployment" in result

    def test_clean_self_link(self):
        """Test removing deprecated metadata.selfLink."""
        manifest = """
apiVersion: v1
kind: Namespace
metadata:
  name: test-namespace
  selfLink: /api/v1/namespaces/test-namespace
spec:
  finalizers:
  - kubernetes
"""
        result = clean_manifest_metadata(manifest)
        assert "selfLink" not in result
        assert "test-namespace" in result

    def test_clean_status_section(self):
        """Test removing entire status section."""
        manifest = """
apiVersion: v1
kind: Pod
metadata:
  name: test-pod
spec:
  containers:
  - name: nginx
    image: nginx:latest
status:
  phase: Running
  conditions:
  - type: Ready
    status: "True"
  containerStatuses:
  - ready: true
    restartCount: 0
"""
        result = clean_manifest_metadata(manifest)
        assert "status:" not in result
        assert "phase:" not in result
        assert "test-pod" in result
        assert "spec:" in result

    def test_clean_all_fields_combined(self):
        """Test removing all server-managed fields at once."""
        manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  namespace: default
  uid: 123e4567-e89b-12d3-a456-426614174000
  resourceVersion: "12345"
  generation: 5
  creationTimestamp: "2024-01-01T00:00:00Z"
  selfLink: /apis/apps/v1/namespaces/default/deployments/app-deployment
  managedFields:
  - manager: kubectl
    operation: Update
    apiVersion: apps/v1
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
status:
  availableReplicas: 3
  readyReplicas: 3
"""
        result = clean_manifest_metadata(manifest)

        # Verify all server-managed fields are removed
        assert "uid:" not in result
        assert "resourceVersion" not in result
        assert "generation:" not in result
        assert "creationTimestamp" not in result
        assert "selfLink" not in result
        assert "managedFields" not in result
        assert "status:" not in result
        assert "availableReplicas" not in result

        # Verify essential fields remain
        assert "app-deployment" in result
        assert "namespace: default" in result
        assert "replicas: 3" in result

    def test_multi_document_yaml(self):
        """Test cleaning multi-document YAML (separated by ---)."""
        manifest = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  managedFields: []
spec:
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-deployment
  resourceVersion: "12345"
spec:
  replicas: 2
"""
        result = clean_manifest_metadata(manifest)
        assert "managedFields" not in result
        assert "resourceVersion" not in result
        assert "my-service" in result
        assert "my-deployment" in result
        assert "---" in result  # Multi-doc separator preserved

    def test_list_kind_resources(self):
        """Test cleaning List kind resources (e.g., ConfigMapList)."""
        manifest = """
apiVersion: v1
kind: List
items:
- apiVersion: v1
  kind: ConfigMap
  metadata:
    name: config1
    managedFields: []
  data:
    key1: value1
- apiVersion: v1
  kind: ConfigMap
  metadata:
    name: config2
    resourceVersion: "12345"
  data:
    key2: value2
"""
        result = clean_manifest_metadata(manifest)
        assert "managedFields" not in result
        assert "resourceVersion" not in result
        assert "config1" in result
        assert "config2" in result

    def test_empty_manifest(self):
        """Test handling empty manifest."""
        result = clean_manifest_metadata("")
        assert result == ""

    def test_invalid_yaml(self):
        """Test handling invalid YAML (should return original)."""
        invalid_yaml = "this is not: yaml: {invalid"
        result = clean_manifest_metadata(invalid_yaml)
        # Should return original on parse failure
        assert result == invalid_yaml

    def test_preserve_custom_metadata(self):
        """Test that custom metadata fields are preserved."""
        manifest = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  namespace: production
  labels:
    app: myapp
    tier: backend
  annotations:
    prometheus.io/scrape: "true"
  managedFields: []
spec:
  type: ClusterIP
"""
        result = clean_manifest_metadata(manifest)

        # Verify custom fields are preserved
        assert "namespace: production" in result
        assert "labels:" in result
        assert "app: myapp" in result
        assert "annotations:" in result
        assert "prometheus.io/scrape" in result

        # Verify server-managed fields are removed
        assert "managedFields" not in result


class TestCleanManifestFile:
    """Test clean_manifest_file function."""

    def test_clean_file_inplace(self, tmp_path):
        """Test cleaning a file in-place."""
        manifest_file = tmp_path / "deployment.yaml"
        content = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nginx
  managedFields: []
spec:
  replicas: 1
"""
        manifest_file.write_text(content, encoding="utf-8")

        clean_manifest_file(str(manifest_file))

        result = manifest_file.read_text(encoding="utf-8")
        assert "managedFields" not in result
        assert "nginx" in result

    def test_clean_file_to_new_file(self, tmp_path):
        """Test cleaning to a new output file."""
        input_file = tmp_path / "input.yaml"
        output_file = tmp_path / "output.yaml"

        content = """
apiVersion: v1
kind: Service
metadata:
  name: my-service
  resourceVersion: "12345"
spec:
  type: ClusterIP
"""
        input_file.write_text(content, encoding="utf-8")

        clean_manifest_file(str(input_file), str(output_file))

        # Verify input unchanged
        assert "resourceVersion" in input_file.read_text(encoding="utf-8")

        # Verify output cleaned
        result = output_file.read_text(encoding="utf-8")
        assert "resourceVersion" not in result
        assert "my-service" in result

    def test_file_not_found(self):
        """Test handling non-existent file."""
        with pytest.raises(FileNotFoundError):
            clean_manifest_file("/nonexistent/file.yaml")
