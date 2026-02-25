# LLM-Friendly Output Formats Example

**SBKube v0.7.0+** introduces LLM-friendly output formats designed for AI agents, automation, and CI/CD integration. This example demonstrates all supported output formats and their use cases.

## 📋 Overview

This example demonstrates:
- Four output formats: `human`, `llm`, `json`, `yaml`
- Token reduction (80-90% for LLM format)
- AI/LLM agent integration patterns
- CI/CD pipeline integration
- Parsing examples with jq and yq

## 🎯 Supported Output Formats

### 1. `human` (Default)

Rich console output for interactive terminal usage.

**Features:**
- Colors, tables, progress bars
- Detailed log messages
- Maximum readability
- Visual feedback

**Best For:**
- Direct terminal usage
- Manual deployment
- Development and debugging
- Human operators

### 2. `llm` (LLM-Optimized)

Token-optimized structured text output for AI agents.

**Features:**
- 80-90% token reduction vs human format
- KEY: VALUE structure
- Minimal decorative elements
- Parseable, consistent format
- Context-aware summaries

**Best For:**
- Claude Code, ChatGPT integration
- AI-driven workflows
- Token-conscious automation
- LLM agent processing

### 3. `json`

Structured JSON output for machine parsing.

**Features:**
- Complete structured data
- Machine-readable
- Programming-friendly
- Standard format

**Best For:**
- Script integration
- CI/CD pipelines
- API responses
- Data processing

### 4. `yaml`

YAML format output (requires PyYAML).

**Features:**
- Human-readable structured data
- Configuration file style
- Comment support
- GitOps friendly

**Best For:**
- Configuration generation
- Documentation
- GitOps workflows
- Human and machine readable

## 📁 File Structure

```
06-llm-output-formats/
├── sbkube.yaml          # Simple Redis deployment
├── sbkube.yaml         # Cluster and Helm repo config
├── redis-values.yaml    # Minimal Redis configuration
└── README.md            # This file
```

## 🚀 Usage Examples

### Basic Usage

**IMPORTANT:** `--format` is a global option and must appear **before** the subcommand.

```bash
# ✅ Correct Usage (global option before subcommand)
sbkube --format llm apply --app-dir examples/advanced-features/06-llm-output-formats
sbkube --format json status --app-dir examples/advanced-features/06-llm-output-formats
sbkube --format yaml deploy --app-dir examples/advanced-features/06-llm-output-formats

# ❌ Wrong Usage (will fail)
sbkube apply --format llm  # Error: No such option: --format
```

### Environment Variable

Set format for entire session:

```bash
# Apply to all commands in session
export SBKUBE_OUTPUT_FORMAT=llm

sbkube apply --app-dir examples/advanced-features/06-llm-output-formats
sbkube status --app-dir examples/advanced-features/06-llm-output-formats

# One-time override
SBKUBE_OUTPUT_FORMAT=json sbkube apply --app-dir examples/advanced-features/06-llm-output-formats
```

### Priority Order

```
CLI option (--format) > Environment variable > Default (human)
```

**Example:**

```bash
export SBKUBE_OUTPUT_FORMAT=json

# CLI option takes precedence
sbkube --format llm apply  # Uses llm (CLI wins)
sbkube status              # Uses json (environment variable)
```

## 📊 Output Comparison

### Deployment Success

#### human Format

```
╭──────────────────────────────────────────────────────────╮
│  🚀 SBKube Deployment Summary                            │
├──────────────────────────────────────────────────────────┤
│  Status: ✅ Success                                      │
│  Charts Deployed: 1                                      │
│  Total Duration: 8.3s                                    │
│  Working Dir: /path/to/.sbkube                           │
╰──────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┓
┃ Application ┃ Namespace ┃ Status   ┃ Version ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━┩
│ redis-demo  │ llm-demo  │ RUNNING  │ 18.0.0  │
└─────────────┴───────────┴──────────┴─────────┘

[12:34:56] INFO     Preparing Helm charts...
[12:34:57] INFO     Downloaded chart: redis from bitnami
[12:34:58] INFO     Building manifests...
[12:34:59] INFO     Templating charts...
[12:35:00] INFO     Deploying to Kubernetes...
[12:35:04] SUCCESS  Deployment completed!
```

**Tokens:** ~400-600 tokens

#### llm Format

```
STATUS: success ✅
DEPLOYED: 1 chart in 8.3s

APPLICATIONS:
- redis-demo (llm-demo): RUNNING v18.0.0

NEXT STEPS:
kubectl get pods -n llm-demo
kubectl logs -n llm-demo -l app.kubernetes.io/name=redis

ERRORS: none
```

**Tokens:** ~60-80 tokens (**85% reduction**)

#### json Format

```json
{
  "status": "success",
  "summary": {
    "charts_deployed": 1,
    "duration_seconds": 8.3,
    "timestamp": "2025-01-23T12:35:04Z"
  },
  "applications": [
    {
      "name": "redis-demo",
      "namespace": "llm-demo",
      "status": "running",
      "version": "18.0.0",
      "chart": "bitnami/redis"
    }
  ],
  "next_steps": [
    "kubectl get pods -n llm-demo",
    "kubectl logs -n llm-demo -l app.kubernetes.io/name=redis"
  ],
  "errors": []
}
```

**Tokens:** ~120-150 tokens (structured, parseable)

#### yaml Format

```yaml
status: success
summary:
  charts_deployed: 1
  duration_seconds: 8.3
  timestamp: '2025-01-23T12:35:04Z'
applications:
  - name: redis-demo
    namespace: llm-demo
    status: running
    version: 18.0.0
    chart: bitnami/redis
next_steps:
  - kubectl get pods -n llm-demo
  - kubectl logs -n llm-demo -l app.kubernetes.io/name=redis
errors: []
```

**Tokens:** ~100-130 tokens (human-readable structured)

### Deployment Failure

#### llm Format

```
STATUS: failed ❌
DEPLOYED: 0 charts in 3.2s

APPLICATIONS:
- redis-demo (llm-demo): FAILED

ERRORS:
- redis-demo: ImagePullBackOff (container image not found)
- redis-demo: CrashLoopBackOff (pod restarting)

NEXT STEPS:
kubectl describe pod redis-demo -n llm-demo
kubectl logs redis-demo -n llm-demo
kubectl get events -n llm-demo
```

**Tokens:** ~80-100 tokens

## 🤖 AI/LLM Agent Integration

### Claude Code Integration

```python
import subprocess
import os

# Set LLM format for session
os.environ["SBKUBE_OUTPUT_FORMAT"] = "llm"

# Deploy application
result = subprocess.run(
    ["sbkube", "apply", "--app-dir", "examples/advanced-features/06-llm-output-formats"],
    capture_output=True,
    text=True
)

# Parse simple text output
if "STATUS: success" in result.stdout:
    print("✅ Deployment successful!")

    # Extract application status
    for line in result.stdout.split('\n'):
        if line.startswith('- redis-demo'):
            print(f"Redis status: {line}")
else:
    print("❌ Deployment failed")

    # Extract errors
    in_errors = False
    for line in result.stdout.split('\n'):
        if line.startswith('ERRORS:'):
            in_errors = True
        elif in_errors and line.startswith('- '):
            print(f"Error: {line[2:]}")
```

### ChatGPT Code Interpreter

```python
import subprocess
import json

# Use JSON format for structured parsing
result = subprocess.run(
    ["sbkube", "--format", "json", "status", "--app-dir", "examples/advanced-features/06-llm-output-formats"],
    capture_output=True,
    text=True
)

# Parse JSON output
try:
    data = json.loads(result.stdout)

    print(f"Status: {data['status']}")
    print(f"Deployed: {data['summary']['charts_deployed']} charts")

    for app in data["applications"]:
        print(f"- {app['name']}: {app['status']} (v{app['version']})")

    if data["errors"]:
        print("\nErrors:")
        for error in data["errors"]:
            print(f"- {error}")

except json.JSONDecodeError as e:
    print(f"Failed to parse JSON: {e}")
```

### Environment Variable Approach (Recommended)

```python
import os
import subprocess

# Set format once for entire session
os.environ["SBKUBE_OUTPUT_FORMAT"] = "llm"

# All subsequent commands use LLM format automatically
subprocess.run(["sbkube", "apply", "--app-dir", "examples/advanced-features/06-llm-output-formats"])
subprocess.run(["sbkube", "status", "--app-dir", "examples/advanced-features/06-llm-output-formats"])
subprocess.run(["sbkube", "validate", "examples/advanced-features/06-llm-output-formats/sbkube.yaml"])
```

## 🔧 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy with SBKube

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup SBKube
        run: |
          uv tool install sbkube

      - name: Deploy with JSON output
        run: |
          sbkube --format json apply --app-dir examples/advanced-features/06-llm-output-formats > deploy-result.json

      - name: Parse deployment result
        run: |
          STATUS=$(jq -r '.status' deploy-result.json)
          if [ "$STATUS" = "success" ]; then
            echo "✅ Deployment successful"
          else
            echo "❌ Deployment failed"
            jq -r '.errors[]' deploy-result.json
            exit 1
          fi

      - name: Upload deployment report
        uses: actions/upload-artifact@v4
        with:
          name: deployment-report
          path: deploy-result.json
```

### GitLab CI

```yaml
# .gitlab-ci.yml
deploy:
  stage: deploy
  image: python:3.14-slim
  script:
    - uv tool install sbkube

    # Deploy with JSON output
    - sbkube --format json apply --app-dir examples/advanced-features/06-llm-output-formats > deploy-result.json

    # Check status
    - |
      if jq -e '.status == "success"' deploy-result.json > /dev/null; then
        echo "✅ Deployment successful"
      else
        echo "❌ Deployment failed"
        jq -r '.errors[]' deploy-result.json
        exit 1
      fi

  artifacts:
    paths:
      - deploy-result.json
    reports:
      dotenv: deploy-result.json
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any

    environment {
        SBKUBE_OUTPUT_FORMAT = 'json'
    }

    stages {
        stage('Deploy') {
            steps {
                sh '''
                    sbkube apply --app-dir examples/advanced-features/06-llm-output-formats > deploy-result.json
                '''
            }
        }

        stage('Verify') {
            steps {
                script {
                    def result = readJSON file: 'deploy-result.json'

                    if (result.status == 'success') {
                        echo "✅ Deployment successful: ${result.summary.charts_deployed} charts deployed"
                    } else {
                        error("❌ Deployment failed: ${result.errors}")
                    }
                }
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: 'deploy-result.json'
        }
    }
}
```

## 📊 Parsing Examples

### jq (JSON Query)

```bash
# Get deployment status
sbkube --format json status --app-dir examples/advanced-features/06-llm-output-formats | jq -r '.status'

# List all applications
sbkube --format json status --app-dir examples/advanced-features/06-llm-output-formats | jq -r '.applications[].name'

# Get failed applications
sbkube --format json status --app-dir examples/advanced-features/06-llm-output-formats | jq -r '.applications[] | select(.status == "failed") | .name'

# Extract errors
sbkube --format json apply --app-dir examples/advanced-features/06-llm-output-formats | jq -r '.errors[]'

# Pretty print with colors
sbkube --format json status --app-dir examples/advanced-features/06-llm-output-formats | jq '.'

# Count deployed charts
sbkube --format json status --app-dir examples/advanced-features/06-llm-output-formats | jq -r '.summary.charts_deployed'

# Get deployment duration
sbkube --format json apply --app-dir examples/advanced-features/06-llm-output-formats | jq -r '.summary.duration_seconds'
```

### yq (YAML Query)

```bash
# Install yq if needed
uv tool install yq

# Get deployment status
sbkube --format yaml status --app-dir examples/advanced-features/06-llm-output-formats | yq '.status'

# List applications
sbkube --format yaml status --app-dir examples/advanced-features/06-llm-output-formats | yq '.applications[].name'

# Get specific application status
sbkube --format yaml status --app-dir examples/advanced-features/06-llm-output-formats | yq '.applications[] | select(.name == "redis-demo") | .status'

# Convert YAML to JSON
sbkube --format yaml status --app-dir examples/advanced-features/06-llm-output-formats | yq -o json '.'
```

### grep (Simple Text Parsing)

For LLM format, simple grep is often sufficient:

```bash
# Check if deployment succeeded
sbkube --format llm apply --app-dir examples/advanced-features/06-llm-output-formats | grep "STATUS: success"

# Get application status
sbkube --format llm status --app-dir examples/advanced-features/06-llm-output-formats | grep "^- "

# Extract errors
sbkube --format llm apply --app-dir examples/advanced-features/06-llm-output-formats | grep "^- " | grep "FAILED\|ERROR"

# Get next steps
sbkube --format llm apply --app-dir examples/advanced-features/06-llm-output-formats | sed -n '/NEXT STEPS:/,/^$/p'
```

## 📈 Token Reduction Benchmarks

Comparison of token usage across formats:

| Operation | human | llm | json | yaml | Reduction (vs human) |
|-----------|-------|-----|------|------|----------------------|
| **Simple deploy (1 app)** | 400-600 | 60-80 | 120-150 | 100-130 | 85-90% |
| **Medium deploy (5 apps)** | 1200-1500 | 150-200 | 300-400 | 250-350 | 85-87% |
| **Large deploy (10 apps)** | 2500-3000 | 250-350 | 500-700 | 400-600 | 88-90% |
| **Status check** | 300-500 | 50-80 | 100-150 | 80-120 | 80-85% |
| **Error report** | 800-1200 | 120-180 | 200-300 | 150-250 | 80-85% |

**Key Insights:**
- LLM format provides **80-90% token reduction** for all operations
- JSON format balances structure with token efficiency (~70-75% reduction)
- YAML format is similar to JSON but more human-readable
- Token savings scale with operation complexity

## 🔍 Validation

Validate the configuration before deployment:

```bash
# Validate with default (human) output
uv run sbkube validate -f sbkube.yaml examples/advanced-features/06-llm-output-formats/sbkube.yaml

# Validate with LLM output
uv run sbkube --format llm validate examples/advanced-features/06-llm-output-formats/sbkube.yaml

# Validate with JSON output
uv run sbkube --format json validate examples/advanced-features/06-llm-output-formats/sbkube.yaml
```

Expected output (LLM format):

```
VALIDATION: passed ✅

CONFIG: examples/advanced-features/06-llm-output-formats/sbkube.yaml
NAMESPACE: llm-demo
APPS: 1

CHECKS:
- sbkube.yaml: valid YAML ✅
- sbkube.yaml: found ✅
- redis-values.yaml: found ✅
- modern format (v0.5.0+): ✅
- app names: valid ✅

WARNINGS: none
ERRORS: none
```

## 🚀 Deployment

### Full Workflow (All Formats)

```bash
# 1. Validate (human format for development)
uv run sbkube validate -f sbkube.yaml examples/advanced-features/06-llm-output-formats/sbkube.yaml

# 2. Dry run (LLM format for quick check)
uv run sbkube --format llm apply --app-dir examples/advanced-features/06-llm-output-formats --dry-run

# 3. Deploy (JSON format for CI/CD)
uv run sbkube --format json apply --app-dir examples/advanced-features/06-llm-output-formats > deploy-result.json

# 4. Verify (LLM format for monitoring)
uv run sbkube --format llm status --app-dir examples/advanced-features/06-llm-output-formats

# 5. Check pods (YAML format for documentation)
uv run sbkube --format yaml status --app-dir examples/advanced-features/06-llm-output-formats > deployment-status.yaml
```

### Cleanup

```bash
# Delete with human output (default)
uv run sbkube delete --app-dir examples/advanced-features/06-llm-output-formats

# Delete with LLM output
uv run sbkube --format llm delete --app-dir examples/advanced-features/06-llm-output-formats

# Delete with JSON output for automation
uv run sbkube --format json delete --app-dir examples/advanced-features/06-llm-output-formats
```

## 💡 Best Practices

### When to Use Each Format

**human (default)**:
- ✅ Interactive terminal sessions
- ✅ Manual deployment and debugging
- ✅ Development and testing
- ✅ Learning and exploration
- ❌ Automation and scripting

**llm (token-optimized)**:
- ✅ Claude Code / ChatGPT integration
- ✅ AI-driven workflows
- ✅ Token-conscious environments
- ✅ Quick status checks in LLM context
- ❌ Complex data processing

**json (structured)**:
- ✅ CI/CD pipeline integration
- ✅ Script automation
- ✅ Data processing and analytics
- ✅ API responses
- ✅ Complex parsing requirements
- ❌ Quick visual inspection

**yaml (human + machine)**:
- ✅ Configuration file generation
- ✅ GitOps workflows
- ✅ Documentation
- ✅ Human-readable reports
- ❌ High-frequency automation

### Environment Variable Strategy

```bash
# Development: human format (default)
# No environment variable needed

# AI Agent: LLM format
export SBKUBE_OUTPUT_FORMAT=llm

# CI/CD: JSON format
export SBKUBE_OUTPUT_FORMAT=json

# Documentation: YAML format
export SBKUBE_OUTPUT_FORMAT=yaml
```

### Error Handling

```bash
# Capture both stdout and stderr
sbkube --format json apply --app-dir examples/advanced-features/06-llm-output-formats > result.json 2> errors.log

# Check exit code
if sbkube --format llm apply --app-dir examples/advanced-features/06-llm-output-formats | grep -q "STATUS: success"; then
    echo "Deployment succeeded"
else
    echo "Deployment failed"
    exit 1
fi

# Parse JSON errors
sbkube --format json apply --app-dir examples/advanced-features/06-llm-output-formats | jq -e '.status == "success"' || {
    echo "Errors:"
    jq -r '.errors[]' result.json
    exit 1
}
```

## 🐛 Troubleshooting

### Format Not Working

**Issue**: `--format` option not recognized

**Solution**: Ensure `--format` is placed **before** the subcommand (global option)

```bash
# ✅ Correct
sbkube --format llm apply

# ❌ Wrong
sbkube apply --format llm  # Error!
```

### YAML Format Fails

**Issue**: `YAML format requires PyYAML`

**Solution**: Install PyYAML

```bash
uv add pyyaml
```

### Environment Variable Not Working

**Issue**: Format not applied

**Solution**: Check variable name (case-sensitive)

```bash
# ✅ Correct
export SBKUBE_OUTPUT_FORMAT=llm

# ❌ Wrong (lowercase)
export sbkube_output_format=llm
```

### JSON Parsing Fails

**Issue**: `jq: parse error`

**Solution**: Check if output contains error messages mixed with JSON

```bash
# Redirect stderr to avoid mixing
sbkube --format json apply 2>/dev/null | jq '.'
```

## 🔗 Related Documentation

- [LLM-Friendly Output Guide](../../../docs/02-features/llm-friendly-output.md) - Complete feature documentation
- [Commands Reference](../../../docs/02-features/commands.md) - All SBKube commands
- [OutputFormatter Implementation](../../../sbkube/utils/output_formatter.py) - Source code

## 📝 Notes

1. **v0.7.0+ Feature**: Output formats are only available in SBKube v0.7.0 and later
2. **Default Behavior**: Without `--format` or environment variable, `human` format is used
3. **Global Option**: `--format` must appear before subcommands (e.g., `sbkube --format llm apply`)
4. **Token Savings**: LLM format provides 80-90% token reduction compared to human format
5. **PyYAML Required**: YAML format requires `pyyaml` package to be installed

## ⚠️ Important Notes

- **LLM format is designed for AI agents**, not for human reading
- **JSON format is best for CI/CD**, providing structured, parseable output
- **YAML format balances readability and structure**, ideal for documentation
- **Always validate** before deploying in production environments
- **Token savings scale** with operation complexity (more apps = more savings)

## 📊 Summary

| Format | Best For | Token Efficiency | Parsing | Readability |
|--------|----------|------------------|---------|-------------|
| **human** | Terminal usage | Low (baseline) | Hard | Excellent |
| **llm** | AI agents | Excellent (80-90%) | Easy | Good |
| **json** | CI/CD, scripts | Good (70-75%) | Very Easy | Fair |
| **yaml** | GitOps, docs | Good (70-75%) | Easy | Good |

**Recommendation**: Use `llm` format for AI-driven workflows, `json` for automation, and `human` for interactive sessions.
