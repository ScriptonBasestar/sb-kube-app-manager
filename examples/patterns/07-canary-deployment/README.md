# Canary Deployment Pattern

**Progressive rollout with gradual traffic shifting: stable → 10% → 50% → 100% promotion**

## 📋 Overview

This example demonstrates how to use SBKube to implement a canary deployment strategy with progressive traffic shifting. Canary deployments reduce risk by gradually rolling out new versions to a small subset of users before full deployment.

Key benefits:
- **Risk mitigation** - Test new versions with small user percentage first
- **Rapid rollback** - Quick revert to stable if issues detected
- **Gradual validation** - Monitor metrics at each phase
- **Zero downtime** - Seamless transition between versions
- **A/B testing** - Compare performance of stable vs canary

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Canary Deployment Phases                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Phase 0: Stable Only (100% stable)                        │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Stable v1.0.0: █████████████ (10 pods)           │     │
│  └──────────────────────────────────────────────────┘     │
│                         ↓                                   │
│  Phase 1: Canary 10% (90% stable, 10% canary)             │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Stable v1.0.0:  █████████ (9 pods)               │     │
│  │ Canary v2.0.0:  █ (1 pod)                        │     │
│  └──────────────────────────────────────────────────┘     │
│                         ↓                                   │
│  Phase 2: Canary 50% (50% stable, 50% canary)             │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Stable v1.0.0:  █████ (5 pods)                   │     │
│  │ Canary v2.0.0:  █████ (5 pods)                   │     │
│  └──────────────────────────────────────────────────┘     │
│                         ↓                                   │
│  Phase 3: Promote (100% new version)                       │
│  ┌──────────────────────────────────────────────────┐     │
│  │ Stable v2.0.0: █████████████ (10 pods)           │     │
│  └──────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
07-canary-deployment/
├── sources.yaml                    # Cluster connection config
├── config-stable.yaml              # Stable version only (100% stable)
├── config-canary-10.yaml           # Canary at 10% traffic
├── config-canary-50.yaml           # Canary at 50% traffic
├── config-promote.yaml             # Promote canary to stable (100%)
├── values/
│   ├── backend-stable.yaml         # Stable version values (9 pods)
│   ├── backend-canary-10.yaml      # Canary at 10% (1 pod)
│   ├── backend-canary-50.yaml      # Canary at 50% (5 pods)
│   └── backend-promoted.yaml       # Promoted version (10 pods)
├── manifests/
│   ├── service.yaml                # Service (shared by stable + canary)
│   └── servicemonitor.yaml         # Prometheus monitoring
├── deploy-canary.sh                # Deployment automation script
└── README.md                       # This file
```

## 🎯 Key Concepts

### 1. Progressive Traffic Shifting

Traffic gradually shifts from stable to canary:

```
Stable: 100% → 90% → 50% → 0%
Canary:   0% → 10% → 50% → 100%
```

Controlled by pod replica counts:
- **10% canary**: 1 canary pod + 9 stable pods = 10% traffic
- **50% canary**: 5 canary pods + 5 stable pods = 50% traffic

### 2. Shared Service

Single Kubernetes Service selects both stable and canary pods:

```yaml
selector:
  app: backend  # Matches both stable and canary pods
```

Kubernetes Service load-balances traffic across all matching pods.

### 3. Pod Labels for Tracking

Different labels distinguish stable vs canary:

```yaml
# Stable pods
podLabels:
  version: stable
  track: stable

# Canary pods
podLabels:
  version: canary
  track: canary
```

### 4. Monitoring Integration

ServiceMonitor enables Prometheus metrics collection:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: backend-canary
spec:
  selector:
    matchLabels:
      app: backend
```

Track metrics by version: error rate, latency, throughput.

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (k3s, minikube, or cloud provider)
- kubectl configured with cluster access
- helm 3+ installed
- SBKube v0.5.0+ installed
- **(Optional) Prometheus + Grafana** for metrics monitoring

### Phase 0: Deploy Stable Version

Start with stable version running:

```bash
# Make deployment script executable
chmod +x deploy-canary.sh

# Deploy stable version (100% stable traffic)
./deploy-canary.sh stable

# Verify deployment
kubectl get pods -n canary-demo -l app=backend
```

**Expected output**:
```
NAME                              READY   STATUS    RESTARTS   AGE
backend-stable-7d8f5c9b-xxxxx     1/1     Running   0          30s
(... 9 more stable pods)
```

### Phase 1: Deploy Canary at 10%

Deploy canary with 10% traffic:

```bash
# Deploy canary version (10% canary, 90% stable)
./deploy-canary.sh 10

# Verify pod distribution
kubectl get pods -n canary-demo -l app=backend --show-labels
```

**Expected output**:
```
NAME                              READY   LABELS
backend-stable-xxx (9 pods)       1/1     version=stable,track=stable
backend-canary-xxx (1 pod)        1/1     version=canary,track=canary
```

**Monitor Phase 1**:
```bash
# Watch pod status
watch kubectl get pods -n canary-demo -l app=backend

# Check logs for canary pods
kubectl logs -n canary-demo -l version=canary --tail=100 -f

# Monitor error rates (if Prometheus available)
# Query: rate(http_requests_total{job="backend",status=~"5.."}[5m])
```

**Decision Point**:
- ✅ **No issues** → Proceed to Phase 2 (50%)
- ❌ **Issues detected** → Rollback to stable: `./deploy-canary.sh stable`

### Phase 2: Increase Canary to 50%

If Phase 1 is successful:

```bash
# Increase canary to 50% (5 stable + 5 canary)
./deploy-canary.sh 50

# Verify pod distribution
kubectl get pods -n canary-demo -l app=backend --show-labels
```

**Expected output**:
```
NAME                              READY   LABELS
backend-stable-xxx (5 pods)       1/1     version=stable,track=stable
backend-canary-xxx (5 pods)        1/1     version=canary,track=canary
```

**Monitor Phase 2**:
```bash
# Monitor for 15-30 minutes at 50% traffic
watch kubectl get pods -n canary-demo

# Compare metrics: stable vs canary
# - Error rates
# - Latency (p50, p95, p99)
# - CPU/Memory usage
```

**Decision Point**:
- ✅ **Metrics look good** → Promote canary to stable
- ⚠️ **Minor issues** → Stay at 50%, investigate
- ❌ **Major issues** → Rollback: `./deploy-canary.sh 10` or `./deploy-canary.sh stable`

### Phase 3: Promote Canary to Stable

If Phase 2 is successful, promote canary:

```bash
# Promote canary to stable (100% new version)
./deploy-canary.sh promote

# Verify deployment
kubectl get pods -n canary-demo -l app=backend
```

**Expected output**:
```
NAME                              READY   STATUS    RESTARTS   AGE
backend-stable-xxx (10 pods)      1/1     Running   0          30s
# All pods now running v2.0.0 (promoted canary)
```

**Post-Promotion**:
- Monitor for 24 hours
- Canary deployment successful!
- Next canary cycle starts with this version as new stable

## 🔧 Advanced Usage

### Manual Canary Control

Deploy specific phases manually:

```bash
# Deploy stable only
sbkube apply --app-dir . --config config-stable.yaml

# Deploy canary at 10%
sbkube apply --app-dir . --config config-canary-10.yaml

# Deploy canary at 50%
sbkube apply --app-dir . --config config-canary-50.yaml

# Promote to stable
sbkube apply --app-dir . --config config-promote.yaml
```

### Custom Traffic Percentages

Adjust replica counts for different traffic splits:

**25% canary**:
```yaml
# config-canary-25.yaml
backend-stable:
  replicaCount: 6  # 75% traffic
backend-canary:
  replicaCount: 2  # 25% traffic
```

**75% canary**:
```yaml
# config-canary-75.yaml
backend-stable:
  replicaCount: 2  # 25% traffic
backend-canary:
  replicaCount: 6  # 75% traffic
```

### Automated Canary with Flagger

For fully automated canary with metric analysis:

```yaml
# flagger-canary.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: backend
  namespace: canary-demo
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  service:
    port: 80
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
      - name: request-duration
        thresholdRange:
          max: 500
```

### CI/CD Integration

**GitHub Actions example**:

```yaml
name: Canary Deployment

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  canary:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Phase 1 - Deploy Canary 10%
        run: |
          cd examples/patterns/07-canary-deployment
          ./deploy-canary.sh 10

      - name: Wait and Monitor
        run: |
          sleep 300  # Wait 5 minutes
          # Check error rates from Prometheus
          ERROR_RATE=$(curl -s 'http://prometheus/api/v1/query?query=rate(http_errors[5m])' | jq '.data.result[0].value[1]')
          if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
            echo "Error rate too high, rolling back"
            ./deploy-canary.sh stable
            exit 1
          fi

      - name: Phase 2 - Increase to 50%
        run: ./deploy-canary.sh 50

      - name: Wait and Monitor
        run: |
          sleep 600  # Wait 10 minutes
          # Additional monitoring checks

      - name: Phase 3 - Promote Canary
        run: ./deploy-canary.sh promote
```

### Rollback Strategy

Quick rollback at any phase:

```bash
# Immediate rollback to stable (removes canary)
./deploy-canary.sh stable

# Or manually
sbkube apply --app-dir . --config config-stable.yaml

# Verify rollback
kubectl get pods -n canary-demo -l app=backend
# Should show only stable pods
```

## 📊 Monitoring and Validation

### Key Metrics to Monitor

Track these metrics per version (stable vs canary):

| Metric | Threshold | Action if Exceeded |
|--------|-----------|-------------------|
| **Error Rate** | < 1% | Rollback immediately |
| **P95 Latency** | < 500ms | Investigate, consider rollback |
| **P99 Latency** | < 1000ms | Investigate |
| **CPU Usage** | < 80% | Monitor, may need more resources |
| **Memory Usage** | < 80% | Monitor for memory leaks |
| **Request Rate** | Expected traffic split | Verify load balancing |

### Prometheus Queries

**Error rate by version**:
```promql
rate(http_requests_total{app="backend",status=~"5..",version="canary"}[5m])
vs
rate(http_requests_total{app="backend",status=~"5..",version="stable"}[5m])
```

**Latency by version**:
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{app="backend",version="canary"}[5m]))
vs
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{app="backend",version="stable"}[5m]))
```

**Traffic distribution**:
```promql
sum(rate(http_requests_total{app="backend",version="canary"}[1m])) /
sum(rate(http_requests_total{app="backend"}[1m])) * 100
```

### Health Checks

Monitor pod health:

```bash
# Check pod status
kubectl get pods -n canary-demo -l app=backend

# Check pod events
kubectl get events -n canary-demo --sort-by='.lastTimestamp'

# Check canary pod logs
kubectl logs -n canary-demo -l version=canary --tail=100

# Check stable pod logs
kubectl logs -n canary-demo -l version=stable --tail=100
```

## 🐛 Troubleshooting

### Issue: Traffic Not Split Correctly

**Problem**: All traffic going to stable, no traffic to canary

**Solution**: Verify Service selector matches both pod labels:

```bash
# Check Service selector
kubectl get service backend -n canary-demo -o yaml | grep -A2 selector

# Check pod labels
kubectl get pods -n canary-demo -l app=backend --show-labels
```

Ensure both stable and canary pods have `app=backend` label.

### Issue: Canary Pods Crashing

**Problem**: Canary pods in CrashLoopBackOff

**Solution**: Check logs and describe pod:

```bash
# Check logs
kubectl logs -n canary-demo -l version=canary --tail=100

# Describe pod
kubectl describe pod -n canary-demo -l version=canary

# Common causes:
# - Missing environment variables
# - Resource limits too low
# - Application bugs in new version
```

### Issue: Metrics Not Available

**Problem**: Cannot see canary metrics in Prometheus

**Solution**: Verify ServiceMonitor and scraping:

```bash
# Check ServiceMonitor
kubectl get servicemonitor -n canary-demo backend-canary -o yaml

# Check if Prometheus is scraping
# Prometheus UI → Status → Targets
# Look for "backend-canary" target

# Verify pod annotations
kubectl get pods -n canary-demo -l version=canary -o yaml | grep -A2 annotations
```

### Issue: Rollback Not Working

**Problem**: Rollback command not removing canary

**Solution**: Manually disable canary app:

```bash
# Option 1: Use stable config (canary not defined)
sbkube apply --app-dir . --config config-stable.yaml

# Option 2: Edit config and set enabled: false
vim config-canary-50.yaml  # Set backend-canary.enabled: false
sbkube apply --app-dir . --config config-canary-50.yaml

# Option 3: Delete canary pods manually
kubectl delete deployment -n canary-demo -l version=canary
```

## 📝 Best Practices

### 1. Start with Small Canary Percentage

Begin with 5-10% canary traffic:

```bash
# Conservative approach
./deploy-canary.sh 10  # Start small
# Monitor for 30 minutes
./deploy-canary.sh 50  # Increase gradually
```

### 2. Monitor Each Phase

Don't rush through phases:

- **10% phase**: Monitor for 15-30 minutes
- **50% phase**: Monitor for 30-60 minutes
- **100% promotion**: Monitor for 24 hours

### 3. Define Clear Rollback Criteria

Set thresholds before deployment:

```
Automatic rollback if:
- Error rate > 1%
- P95 latency > 2x stable
- Pod crash rate > 5%
```

### 4. Use Feature Flags

Combine canary with feature flags for fine-grained control:

```yaml
env:
  - name: FEATURE_NEW_API
    value: "true"  # Only for canary
```

### 5. Test in Staging First

Always test canary process in staging:

```bash
# Test full canary cycle in staging
./deploy-canary.sh 10
# ... monitor ...
./deploy-canary.sh 50
# ... monitor ...
./deploy-canary.sh promote
```

### 6. Document Rollback Process

Keep rollback instructions accessible:

```bash
# Save in runbook
echo "./deploy-canary.sh stable" > ROLLBACK.txt
```

## 🔗 Related Examples

- **[08-blue-green](../08-blue-green/)** - Blue-green deployment pattern
- **[06-environment-configs](../06-environment-configs/)** - Environment-based configuration
- **[05-multi-cluster](../05-multi-cluster/)** - Multi-cluster deployment
- **[03-monitoring-stack](../../use-cases/03-monitoring-stack/)** - Prometheus + Grafana

## 📚 Additional Resources

- [SBKube Configuration Schema](../../../docs/03-configuration/config-schema.md)
- [Helm Chart Customization](../../../docs/03-configuration/chart-customization.md)
- [Kubernetes Canary Deployments](https://kubernetes.io/docs/concepts/cluster-administration/manage-deployment/#canary-deployments)
- [Flagger - Progressive Delivery Operator](https://flagger.app/)
- [Progressive Delivery Best Practices](https://www.weave.works/blog/progressive-delivery)

## 🎯 Summary

This example demonstrates:

- ✅ Progressive canary deployment (0% → 10% → 50% → 100%)
- ✅ Pod replica-based traffic splitting
- ✅ Shared Service for stable + canary
- ✅ Monitoring integration with Prometheus
- ✅ Automated deployment script with phase management
- ✅ Quick rollback capability at any phase
- ✅ Gradual validation with clear decision points

**Key Takeaway**: Canary deployments with SBKube reduce deployment risk by gradually validating new versions with real production traffic before full rollout, enabling quick rollback if issues are detected.
