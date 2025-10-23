# HTTP Example

This example demonstrates deploying Kubernetes manifests downloaded from HTTP(S) URLs.

## Use Cases

- **Public Manifests**: Download official Kubernetes examples or third-party manifests
- **CI/CD Pipelines**: Pull manifests from artifact servers or S3 buckets
- **Version Pinning**: Use specific URLs with version tags
- **Quick Testing**: Try out manifests without cloning repositories

## Files

- `config.yaml` - HTTP application definitions

## Quick Start

```bash
# Prepare: Download files from URLs
sbkube prepare --app-dir examples/deploy/http-example

# Build: Organize downloaded files
sbkube build --app-dir examples/deploy/http-example

# Deploy: Apply to cluster
sbkube deploy --app-dir examples/deploy/http-example --namespace http-demo

# Or use unified command
sbkube apply --app-dir examples/deploy/http-example
```

## Configuration

### Basic HTTP Download
```yaml
nginx-deployment:
  type: http
  url: https://raw.githubusercontent.com/kubernetes/website/main/content/en/examples/application/deployment.yaml
  dest: nginx-deployment.yaml
```

### With Namespace Override
```yaml
cert-manager:
  type: http
  url: https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
  dest: cert-manager.yaml
  namespace: cert-manager    # Override global namespace
```

### With Dependencies
```yaml
app-b:
  type: http
  url: https://example.com/app-b.yaml
  dest: app-b.yaml
  depends_on:
    - app-a                  # Deploy after app-a
```

## Notes

- URLs must be publicly accessible or require authentication (basic auth supported via sources.yaml)
- Downloaded files are cached in the app-dir during prepare phase
- Files are validated during build phase
- Use `dest` to organize files in subdirectories (e.g., `config/my-file.yaml`)

## Security Considerations

- Always verify the source of downloaded manifests
- Use HTTPS URLs whenever possible
- Pin to specific versions using tagged URLs
- Review downloaded content before deploying to production

## See Also

- [yaml-example](../yaml-example/) - Deploy YAML manifests from local files
- [action-example](../action-example/) - Execute kubectl actions
- [basic](../../basic/) - Helm chart deployment
