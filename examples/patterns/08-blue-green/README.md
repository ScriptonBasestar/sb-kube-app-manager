# Blue-Green Deployment Pattern

**Instant traffic switching between two identical production environments with zero-downtime and immediate rollback**

## 📋 Overview

This example demonstrates how to use SBKube to implement a blue-green deployment strategy. Blue-green deployments maintain two identical production environments, allowing instant traffic switching and immediate rollback if issues occur.

Key benefits:
- **Zero downtime** - Seamless traffic switch between environments
- **Instant rollback** - Immediately revert to previous version if needed
- **Full testing** - Validate new version in production-like environment before switch
- **Risk reduction** - New version fully deployed and tested before receiving traffic
- **Simple operation** - Single command to switch traffic

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            Blue-Green Deployment Strategy                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Initial State: Blue Active                                 │
│  ┌──────────────┐              ┌──────────────┐           │
│  │ Blue (v1.0)  │ ◄── Traffic  │ Green (v2.0) │           │
│  │ 3 pods       │              │ 1 pod (idle) │           │
│  │ ACTIVE       │              │ IDLE         │           │
│  └──────────────┘              └──────────────┘           │
│         ▲                                                   │
│         │                                                   │
│   [ Load Balancer ]                                        │
│                                                             │
│  After Switch: Green Active                                 │
│  ┌──────────────┐              ┌──────────────┐           │
│  │ Blue (v1.0)  │              │ Green (v2.0) │ ◄── Traffic│
│  │ 1 pod (idle) │              │ 3 pods       │           │
│  │ IDLE         │              │ ACTIVE       │           │
│  └──────────────┘              └──────────────┘           │
│                                        ▲                     │
│                                        │                     │
│                                  [ Load Balancer ]          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Directory Structure

```
08-blue-green/
├── sbkube.yaml                # Cluster connection config
├── config-blue-active.yaml     # Blue active, green idle
├── config-green-active.yaml    # Green active, blue idle
├── values/
│   ├── backend-blue.yaml       # Blue active values (3 pods)
│   ├── backend-blue-idle.yaml  # Blue idle values (1 pod)
│   ├── backend-green.yaml      # Green active values (3 pods)
│   └── backend-green-idle.yaml # Green idle values (1 pod)
├── manifests/
│   ├── service-blue.yaml       # Service pointing to blue
│   └── service-green.yaml      # Service pointing to green
├── deploy-bluegreen.sh         # Deployment script
├── switch.sh                   # Traffic switching script
└── README.md                   # This file
```

## 🎯 Key Concepts

### 1. Two Identical Environments

Maintain two complete production environments:
- **Blue**: Current production version (v1.0.0)
- **Green**: New version being deployed (v2.0.0)

### 2. Service Selector Switching

Traffic routing controlled by Kubernetes Service selector:

**Blue active**:
```yaml
selector:
  environment: blue
  status: active
```

**Green active**:
```yaml
selector:
  environment: green
  status: active
```

### 3. Active vs Idle States

**Active environment**: Full resources (3 pods, higher CPU/memory)
**Idle environment**: Reduced resources (1 pod, lower CPU/memory)

This optimizes cost while keeping both environments ready.

### 4. Instant Traffic Switch

Switch traffic by updating Service selector:
```bash
./switch.sh green  # Switch to green
./switch.sh blue   # Rollback to blue
```

## 🚀 Quick Start

### Prerequisites

- Kubernetes cluster (k3s, minikube, or cloud provider)
- kubectl configured with cluster access
- helm 3+ installed
- SBKube v0.5.0+ installed

### Step 1: Deploy Initial State (Blue Active)

Start with blue environment active:

```bash
# Make scripts executable
chmod +x deploy-bluegreen.sh switch.sh

# Deploy both environments (blue active, green idle)
./deploy-bluegreen.sh blue-active

# Verify deployment
kubectl get pods -n bluegreen-demo -l app=backend --show-labels
```

**Expected output**:
```
NAME                            READY   LABELS
backend-blue-xxx (3 pods)       1/1     environment=blue,status=active
backend-green-xxx (1 pod)       1/1     environment=green,status=idle
```

### Step 2: Test Blue Environment

Verify blue environment is receiving traffic:

```bash
# Get Service external IP
kubectl get service backend -n bluegreen-demo

# Test endpoint
curl http://<EXTERNAL-IP>

# Monitor blue pods
kubectl logs -n bluegreen-demo -l environment=blue,status=active --tail=50 -f
```

### Step 3: Deploy New Version to Green

Deploy new version (v2.0.0) to green environment:

```bash
# Green environment is already deployed (idle state)
# Verify green pods are running
kubectl get pods -n bluegreen-demo -l environment=green

# Test green environment directly (via pod port-forward)
kubectl port-forward -n bluegreen-demo \
  $(kubectl get pod -n bluegreen-demo -l environment=green -o jsonpath='{.items[0].metadata.name}') \
  8080:8080

# In another terminal, test:
curl http://localhost:8080
```

### Step 4: Switch Traffic to Green

After validating green environment:

```bash
# Switch traffic to green
./switch.sh green

# Verify service is now pointing to green
kubectl get service backend -n bluegreen-demo -o yaml | grep -A3 selector

# Monitor green pods receiving traffic
kubectl logs -n bluegreen-demo -l environment=green,status=active --tail=50 -f
```

### Step 5: Scale Up Green (Recommended)

After switch, scale green to full production capacity:

```bash
# Apply green-active config (scales green to 3 pods)
./deploy-bluegreen.sh green-active

# Verify scaling
kubectl get pods -n bluegreen-demo -l environment=green
# Should show 3 pods
```

### Step 6: Monitor and Rollback if Needed

Monitor green environment:

```bash
# Monitor pods
watch kubectl get pods -n bluegreen-demo -l environment=green

# Check logs for errors
kubectl logs -n bluegreen-demo -l environment=green --tail=100

# If issues detected, immediately rollback:
./switch.sh blue
```

## 🔧 Advanced Usage

### Gradual Confidence Building

Test green before full production traffic:

```bash
# 1. Deploy green (idle)
./deploy-bluegreen.sh blue-active

# 2. Port-forward to test green directly
kubectl port-forward -n bluegreen-demo svc/backend-green 8080:80
curl http://localhost:8080

# 3. Run smoke tests against green
# (your test suite here)

# 4. If tests pass, switch traffic
./switch.sh green

# 5. Scale up green
./deploy-bluegreen.sh green-active
```

### Canary Testing Before Switch

Combine with ingress-based canary:

```yaml
# ingress-canary.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: backend-canary
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"  # 10% to green
spec:
  rules:
    - host: app.example.com
      http:
        paths:
          - path: /
            backend:
              service:
                name: backend-green
                port:
                  number: 80
```

### Database Migration Handling

For deployments with schema changes:

```bash
# 1. Deploy compatible blue version (supports both old/new schema)
./deploy-bluegreen.sh blue-active

# 2. Run database migration
kubectl exec -n bluegreen-demo deployment/backend-blue -- \
  /app/migrate.sh

# 3. Deploy green with new code
./deploy-bluegreen.sh blue-active  # Green is idle, blue still active

# 4. Validate green with new schema
# (test green directly)

# 5. Switch traffic
./switch.sh green

# 6. Scale up green
./deploy-bluegreen.sh green-active
```

### CI/CD Integration

**GitHub Actions example**:

```yaml
name: Blue-Green Deployment

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Determine inactive environment
        id: env
        run: |
          ACTIVE=$(kubectl get service backend -n bluegreen-demo \
            -o jsonpath='{.spec.selector.environment}')
          if [[ "$ACTIVE" == "blue" ]]; then
            echo "inactive=green" >> $GITHUB_OUTPUT
          else
            echo "inactive=blue" >> $GITHUB_OUTPUT
          fi

      - name: Deploy to inactive environment
        run: |
          cd examples/patterns/08-blue-green
          if [[ "${{ steps.env.outputs.inactive }}" == "green" ]]; then
            ./deploy-bluegreen.sh blue-active  # Updates green (idle)
          else
            ./deploy-bluegreen.sh green-active # Updates blue (idle)
          fi

      - name: Run tests against inactive environment
        run: |
          # Test inactive environment
          kubectl port-forward -n bluegreen-demo \
            svc/backend-${{ steps.env.outputs.inactive }} 8080:80 &
          sleep 5
          curl http://localhost:8080/health
          # Run full test suite
          npm test

      - name: Switch traffic
        run: |
          cd examples/patterns/08-blue-green
          ./switch.sh ${{ steps.env.outputs.inactive }}

      - name: Scale up new active environment
        run: |
          cd examples/patterns/08-blue-green
          if [[ "${{ steps.env.outputs.inactive }}" == "green" ]]; then
            ./deploy-bluegreen.sh green-active
          else
            ./deploy-bluegreen.sh blue-active
          fi
```

## 📊 Comparison: Blue-Green vs Canary

| Aspect | Blue-Green | Canary |
|--------|------------|--------|
| **Traffic Switch** | Instant (all at once) | Gradual (10% → 50% → 100%) |
| **Resource Usage** | 2x environment (both running) | 1.1-1.5x (partial overlap) |
| **Rollback Speed** | Instant (single command) | Requires redeployment |
| **Risk Level** | Medium (all traffic switches) | Low (gradual validation) |
| **Complexity** | Low (simple switch) | Medium (traffic management) |
| **Best For** | Stable releases, quick rollback | Uncertain releases, gradual validation |
| **Cost** | Higher (2 full environments) | Lower (partial overlap) |

## 🐛 Troubleshooting

### Issue: Service Not Switching

**Problem**: `./switch.sh green` doesn't change traffic

**Solution**: Verify Service and pod labels match:

```bash
# Check Service selector
kubectl get service backend -n bluegreen-demo -o yaml | grep -A3 selector

# Check green pod labels
kubectl get pods -n bluegreen-demo -l environment=green --show-labels

# Ensure status=active label exists on green pods
```

### Issue: Both Environments Receiving Traffic

**Problem**: Traffic splitting between blue and green

**Solution**: Ensure only one Service exists:

```bash
# Check for multiple Services
kubectl get services -n bluegreen-demo

# Delete duplicate if exists
kubectl delete service backend-duplicate -n bluegreen-demo

# Reapply correct Service
./switch.sh <target-environment>
```

### Issue: Idle Environment Not Scaled Down

**Problem**: Both environments running at full scale

**Solution**: Apply correct config for active/idle states:

```bash
# If green is active, use:
./deploy-bluegreen.sh green-active  # Green: 3 pods, Blue: 1 pod

# If blue is active, use:
./deploy-bluegreen.sh blue-active   # Blue: 3 pods, Green: 1 pod
```

## 📝 Best Practices

### 1. Test Before Switch

Always validate inactive environment:

```bash
# Port-forward to test
kubectl port-forward -n bluegreen-demo svc/backend-green 8080:80

# Run tests
curl http://localhost:8080/health
# Run full integration tests
```

### 2. Monitor After Switch

Watch for issues immediately after switch:

```bash
# Monitor logs
kubectl logs -n bluegreen-demo -l status=active --tail=100 -f

# Watch for pod restarts
watch kubectl get pods -n bluegreen-demo

# Check error rates
# (Prometheus metrics)
```

### 3. Keep Previous Version Ready

Don't delete inactive environment:

```
✅ Green active (v2.0.0), blue idle (v1.0.0) - Ready for rollback
❌ Green active (v2.0.0), blue deleted - No rollback option
```

### 4. Automate Health Checks

Pre-switch validation:

```bash
# Health check script
if curl -f http://backend-green/health; then
  ./switch.sh green
else
  echo "Health check failed, not switching"
  exit 1
fi
```

### 5. Document Rollback Process

Keep rollback instructions accessible:

```bash
# Create runbook
cat > ROLLBACK.md <<EOF
# Immediate Rollback
./switch.sh blue

# Check rollback success
kubectl get service backend -n bluegreen-demo -o yaml | grep environment
EOF
```

## 🔗 Related Examples

- **[07-canary-deployment](../07-canary-deployment/)** - Canary deployment with gradual rollout
- **[06-environment-configs](../06-environment-configs/)** - Environment-based configuration
- **[05-multi-cluster](../05-multi-cluster/)** - Multi-cluster deployment
- **[03-monitoring-stack](../../use-cases/03-monitoring-stack/)** - Monitoring with Prometheus

## 📚 Additional Resources

- [SBKube Configuration Schema](../../../docs/03-configuration/config-schema.md)
- [Blue-Green Deployments (Martin Fowler)](https://martinfowler.com/bliki/BlueGreenDeployment.html)
- [Kubernetes Deployment Strategies](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#strategy)
- [Zero-Downtime Deployments](https://www.redhat.com/en/topics/devops/what-is-zero-downtime-deployment)

## 🎯 Summary

This example demonstrates:

- ✅ Blue-green deployment with two identical environments
- ✅ Instant traffic switching via Service selector
- ✅ Immediate rollback capability
- ✅ Active/idle resource optimization
- ✅ Zero-downtime deployments
- ✅ Pre-production validation in green environment
- ✅ Automated deployment and switch scripts

**Key Takeaway**: Blue-green deployments with SBKube provide instant traffic switching and immediate rollback capabilities, ideal for stable releases where quick rollback is more important than gradual validation.
