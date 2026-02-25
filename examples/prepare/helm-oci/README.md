# OCI Registry Example

This example demonstrates how to use Helm charts from OCI (Open Container Initiative) registries with SBKube.

## What is OCI Registry?

OCI registries are container registries that also support Helm charts. Unlike traditional Helm repositories, OCI registries:
- Don't require `helm repo add` command
- Use `oci://` protocol
- Store charts alongside container images

## Configuration

### sbkube.yaml

```yaml
oci_registries:
  browserless:
    registry: oci://tccr.io/truecharts
  gabe565:
    registry: oci://ghcr.io/gabe565/charts
```

### sbkube.yaml

```yaml
apps:
  browserless:
    type: helm
    repo: browserless  # OCI registry name from sbkube.yaml
    chart: browserless-chrome  # Chart name only (not repo/chart)
    version: "1.0.0"
```

**Important**: Unlike traditional Helm repos, you specify:
- `repo:` - OCI registry name (as defined in sbkube.yaml)
- `chart:` - Chart name only (without registry prefix)

## Usage

```bash
# Prepare: Pull charts from OCI registries
sbkube prepare --app-dir examples/prepare/helm-oci

# Verify charts were downloaded
ls -la charts/
```

## Common OCI Registries

- **TrueCharts**: `oci://tccr.io/truecharts`
- **GitHub Container Registry**: `oci://ghcr.io/`
- **Docker Hub**: `oci://registry-1.docker.io/`
- **GitLab Container Registry**: `oci://registry.gitlab.com/`

## Troubleshooting

### Authentication Required

Some OCI registries require authentication:

```yaml
oci_registries:
  private-registry:
    registry: oci://my-registry.com/charts
    username: myuser
    password: mypass
```

Note: Authentication support is currently limited. For private registries, use `helm registry login` manually:

```bash
echo $PASSWORD | helm registry login oci://my-registry.com -u $USERNAME --password-stdin
```

### Chart Not Found

If you get "chart not found" error:
1. Verify the chart name is correct
2. Check if the registry URL includes the correct path
3. Ensure you have access to the registry

## References

- [Helm OCI Support](https://helm.sh/docs/topics/registries/)
- [TrueCharts Catalog](https://truecharts.org/)
- [OCI Distribution Spec](https://github.com/opencontainers/distribution-spec)
