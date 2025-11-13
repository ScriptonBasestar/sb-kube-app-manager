# Workspace Feature Design Decisions

**Document Type**: Design Review
**Date**: 2025-01-13
**Status**: DESIGN RESOLVED (Ready for Implementation)
**Reviewer**: Claude (Sonnet 4.5)
**Scope**: Option 3 - Design review only (30min-1hour)

---

## Executive Summary

This document resolves the 3 major design issues that blocked workspace feature implementation. The workspace feature adds multi-phase deployment orchestration to SBKube, enabling sequential deployment of infrastructure → data → applications with explicit dependency management.

**Key Outcome**: All design blockers resolved. Feature can proceed to implementation phase.

---

## 1. File Naming Decision

### Question
Should workspace configuration use `workspace.yaml`, `phases.yaml`, `deployment-plan.yaml`, or another name?

### Decision: `workspace.yaml` ✅

### Rationale
1. **Consistency**: Matches existing SBKube naming pattern
   - `sources.yaml`: Cluster and repository targeting
   - `config.yaml`: App group configuration
   - `workspace.yaml`: Multi-phase orchestration

2. **Clarity**: "workspace" clearly indicates top-level orchestration scope
   - Broader than "phases" (which is just one component)
   - More specific than "deployment-plan" (too generic)

3. **Future-proof**: Allows workspace to grow beyond just phases
   - Could add workspace-level hooks
   - Could add workspace-level validation rules
   - Could add workspace-level metadata/tags

### Rejected Alternatives
- `phases.yaml`: Too narrow, implies only phase definitions
- `deployment-plan.yaml`: Too generic, doesn't convey SBKube context
- `orchestration.yaml`: Too technical, less user-friendly

---

## 2. Phase-Level Sources Reference Strategy

### Question
How should each phase reference cluster configuration and repositories?

### Design Issue (from workspace-feature-plan.md)
Initial design only supported single `sources.yaml`, but real-world scenarios require:
- Different phases deploying to different clusters
- Different phases using different Helm/OCI repositories
- Reusable sources configurations across multiple workspaces

### Two Options Analyzed

#### Option A: Override Approach (External Reference)
```yaml
phases:
  p1-infra:
    source: p1-kube/sources.yaml  # Reference external file
    app_groups: [...]
```

**Pros**:
- Clean separation of concerns (orchestration vs targeting)
- Sources files reusable across multiple workspaces
- Each phase can target different cluster/context
- Easier to version control separately

**Cons**:
- More files to manage
- Indirection (must follow reference to see full config)

#### Option B: Inline Approach (Embedded Config)
```yaml
phases:
  p1-infra:
    sources:  # Inline sources config
      kubeconfig: ~/.kube/config
      context: prod-cluster
      helm_repos: [...]
    app_groups: [...]
```

**Pros**:
- Single file contains all configuration
- No external file management
- Easier to see full config at a glance

**Cons**:
- Mixing orchestration logic with targeting config
- Sources config not reusable
- Harder to manage different cluster targets
- Violates separation of concerns

### Decision: Option A (Override Approach) ✅

### Rationale
1. **Separation of Concerns**: Workspace should focus on orchestration (what, when), not targeting (where, how)
2. **Reusability**: Sources files can be shared across multiple workspaces
3. **Flexibility**: Supports both single-cluster and multi-cluster scenarios
4. **Consistency**: Follows existing SBKube architecture pattern

### Implementation Details
```yaml
# workspace.yaml
phases:
  p1-infra:
    description: "Infrastructure layer"
    source: p1-kube/sources.yaml    # Required: path to sources.yaml
    app_groups:
      - a000_network
      - a001_storage
```

```yaml
# p1-kube/sources.yaml (existing format, no changes needed)
kubeconfig: ~/.kube/config
context: production-cluster
helm_repos:
  bitnami:
    url: https://charts.bitnami.com/bitnami
```

### Precedence Rules
When same configuration appears at multiple levels:
1. **App-level** (config.yaml) - Highest priority
2. **Phase-level** (sources.yaml)
3. **Workspace-level** (global section)

---

## 3. Cluster Targeting Complexity

### Question
Should workspace design optimize for single-cluster sequential deployment or multi-cluster scenarios?

### Use Case Analysis

#### 90% Case: Single-Cluster Sequential
```yaml
# All phases deploy to same cluster, different namespaces
phases:
  p1-infra:
    source: sources.yaml  # context: prod-cluster
    app_groups: [...]
  p2-data:
    source: sources.yaml  # context: prod-cluster (same)
    app_groups: [...]
```

**Characteristics**:
- Same cluster, different phases
- Sequential execution (infra → data → app)
- Shared cluster resources
- Simple dependency resolution

#### 10% Case: Multi-Cluster
```yaml
# Different phases target different clusters
phases:
  p1-infra-us:
    source: us-cluster/sources.yaml    # context: us-prod
    app_groups: [...]
  p1-infra-eu:
    source: eu-cluster/sources.yaml    # context: eu-prod
    app_groups: [...]
```

**Characteristics**:
- Different clusters, potentially parallel deployment
- Complex dependency resolution across clusters
- Different kubeconfig/context per phase

### Decision: Single-Cluster Focus for v1.0 ✅

### Rationale
1. **80/20 Rule**: Optimize for 90% use case first
2. **Simplicity**: Easier to understand, document, and support
3. **Incremental Complexity**: Multi-cluster can be added later without breaking changes
4. **Proven Pattern**: Follows SBKube's "Convention over Configuration" philosophy

### Implementation Strategy
**v1.0 (Recommended)**:
- Design workspace for sequential deployment to same cluster
- Each phase can still reference different sources.yaml (allows cluster override if needed)
- Focus on phase dependency resolution (Kahn's algorithm)
- Simple validation: Check all phases accessible from current kubeconfig

**v1.1+ (Future Enhancement)**:
- Add explicit multi-cluster support
- Parallel phase execution across clusters
- Cross-cluster dependency validation
- Advanced state tracking per cluster

### Migration Path
Existing single-cluster approach still works via override:
```yaml
# Single cluster, multiple phases
global:
  kubeconfig: ~/.kube/config
  context: prod-cluster

phases:
  p1-infra:
    source: p1/sources.yaml  # Can override context if needed
  p2-data:
    source: p2/sources.yaml  # Defaults to global context
```

---

## 4. Repository Management Hierarchy

### Question
When Helm/OCI repository defined at multiple levels, which takes precedence?

### Three-Level Configuration

#### Level 1: Workspace Global
```yaml
# workspace.yaml
global:
  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami
```

#### Level 2: Phase Sources
```yaml
# p1-kube/sources.yaml
helm_repos:
  custom-repo:
    url: https://charts.internal.company.com
```

#### Level 3: App Config
```yaml
# p1-kube/config.yaml
apps:
  nginx:
    chart: custom-repo/nginx  # Explicit repo reference
```

### Decision: App > Phase > Workspace (Most Specific Wins) ✅

### Rationale
1. **Consistency**: Follows existing SBKube inheritance pattern
2. **Flexibility**: Allows global defaults with specific overrides
3. **Principle of Least Surprise**: Most specific configuration wins
4. **Explicit Override**: Apps can explicitly reference repositories

### Precedence Order (Highest to Lowest)
1. **App-level explicit chart reference** (`chart: repo/name`)
2. **Phase-level sources.yaml** (`helm_repos` section)
3. **Workspace-level global** (`global.helm_repos`)

### Example Scenario
```yaml
# workspace.yaml
global:
  helm_repos:
    bitnami:
      url: https://charts.bitnami.com/bitnami  # Default

# p1-kube/sources.yaml
helm_repos:
  bitnami:
    url: https://charts.internal.com/bitnami-mirror  # Override for this phase

# p1-kube/config.yaml
apps:
  redis:
    chart: bitnami/redis  # Uses phase-level mirror
  nginx:
    chart: custom/nginx   # Uses app-level explicit reference
```

**Result**:
- `redis` chart: Fetched from `https://charts.internal.com/bitnami-mirror` (phase-level)
- `nginx` chart: Fetched from `custom` repo (must be defined somewhere)

---

## 5. Schema Structure Summary

Based on above decisions, the `workspace.yaml` schema includes:

### Required Fields
- `version`: Schema version (e.g., "1.0")
- `metadata.name`: Workspace identifier
- `phases`: Map of phase definitions
  - `phases.<name>.description`: Human-readable description
  - `phases.<name>.source`: Path to sources.yaml
  - `phases.<name>.app_groups`: List of app group directories
  - `phases.<name>.depends_on`: List of prerequisite phases

### Optional Fields
- `metadata.description`: Workspace description
- `metadata.environment`: Environment label (dev/staging/prod)
- `metadata.tags`: Categorization tags
- `global.kubeconfig`: Default kubeconfig path
- `global.context`: Default kubectl context
- `global.helm_repos`: Default Helm repositories
- `global.oci_registries`: Default OCI registries
- `global.timeout`: Default operation timeout
- `global.on_failure`: Default failure behavior
- `phases.<name>.timeout`: Phase-specific timeout
- `phases.<name>.on_failure`: Phase-specific failure behavior
- `phases.<name>.parallel`: Enable parallel app group deployment
- `phases.<name>.env`: Phase-level environment variables
- `hooks`: Workspace and phase lifecycle hooks
- `validation`: Workspace validation rules

### Full Schema
See: `tmp/workspace-schema-draft.yaml` (348 lines with comprehensive comments)

---

## 6. Backward Compatibility

### No Breaking Changes ✅

**Existing workflows unchanged**:
```bash
# Single-phase deployment (existing)
cd p1-kube/
sbkube apply -c sources.yaml

# Still works exactly the same way
```

**New workspace feature is additive**:
```bash
# Multi-phase deployment (new)
sbkube workspace deploy -f workspace.yaml
```

### Migration Strategy
1. **Optional adoption**: workspace.yaml only needed for multi-phase deployments
2. **Gradual migration**: Convert one phase at a time
3. **Parallel usage**: Can use both old and new approaches simultaneously

### Zero Impact
- No changes to existing `sources.yaml` format
- No changes to existing `config.yaml` format
- No changes to existing CLI commands (apply, deploy, etc.)
- New `workspace` command group is separate

---

## 7. Implementation Recommendations

### Immediate Next Steps (Not in Current Scope)
This design review focused on resolving blockers. Implementation would include:

1. **Phase 1: Core Models** (2-3 hours)
   - Create `sbkube/models/workspace_model.py`
   - Pydantic models: `WorkspaceConfig`, `PhaseConfig`, `PhaseMetadata`
   - Validation: File existence, circular dependencies

2. **Phase 2: CLI Commands** (3-4 hours)
   - `sbkube workspace validate -f workspace.yaml`
   - `sbkube workspace deploy -f workspace.yaml [--phase <name>]`
   - `sbkube workspace status -f workspace.yaml`

3. **Phase 3: Dependency Resolution** (2-3 hours)
   - Implement Kahn's algorithm for topological sorting
   - Implement DFS for circular dependency detection
   - Phase execution order calculation

4. **Phase 4: State Management** (2-3 hours)
   - Workspace-level deployment tracking in SQLite
   - Phase-level status tracking
   - Rollback point creation

### Validation Requirements
- All referenced `sources.yaml` files must exist
- All referenced `app_groups` directories must exist
- No circular dependencies in `depends_on`
- At least one phase defined
- Phase names must be unique

### Testing Strategy
- Unit tests: Pydantic model validation (20+ tests)
- Unit tests: Dependency resolution (10+ tests)
- Integration tests: End-to-end workspace deployment (5+ tests)
- Fixtures: Example workspace.yaml files for common scenarios

---

## 8. Design Review Completion

### All Blockers Resolved ✅

| Issue | Status | Decision |
|-------|--------|----------|
| **Issue #1**: Phase-level sources reference | ✅ Resolved | Override approach (external file reference) |
| **Issue #2**: Cluster targeting complexity | ✅ Resolved | Single-cluster focus for v1.0 |
| **Issue #3**: Repository management hierarchy | ✅ Resolved | App > Phase > Workspace precedence |
| **Issue #4**: File naming | ✅ Resolved | `workspace.yaml` confirmed |

### Deliverables Completed

1. ✅ **workspace-feature-plan.md review**: All 281 lines reviewed and understood
2. ✅ **workspace.yaml schema draft**: 348-line comprehensive schema with comments
3. ✅ **Design decisions document**: This document (current)

### Status Update Recommendation

Update `tasks/plan/workspace-feature-plan.md`:
```yaml
status: DESIGN RESOLVED
next_action: Ready for implementation
blocked_by: null
decisions_finalized:
  - File naming: workspace.yaml
  - Sources reference: Override approach
  - Cluster targeting: Single-cluster v1.0
  - Repository precedence: App > Phase > Workspace
```

---

## 9. Future Enhancements (Out of Scope)

### v1.1+: Multi-Cluster Support
- Parallel phase execution across clusters
- Cross-cluster dependency validation
- Per-cluster rollback management

### v1.2+: Advanced Features
- Conditional phase execution (if/unless)
- Dynamic phase generation (loops, templates)
- External variable substitution
- Workspace composition (import other workspaces)

### v2.0+: Enterprise Features
- Workspace versioning and history
- Approval workflows for phase deployment
- Multi-tenant workspace isolation
- Audit logging and compliance reporting

---

## 10. References

### Primary Documents
- `tasks/plan/workspace-feature-plan.md` (281 lines) - Original design document
- `tmp/workspace-schema-draft.yaml` (348 lines) - Comprehensive schema with examples
- `CLAUDE.md` Section 2.2 - Query Type Routing and context navigation

### Related SBKube Concepts
- `sources.yaml`: Cluster targeting and repository configuration
- `config.yaml`: App group and app definitions
- Phase-based deployment: Existing pattern in SBKube user documentation
- Dependency resolution: App-level dependencies already supported

### Implementation Patterns
- `sbkube/models/config_model.py`: Existing Pydantic model pattern
- `sbkube/models/sources_model.py`: Existing sources schema
- `sbkube/utils/base_command.py`: `EnhancedBaseCommand` pattern for new CLI commands

---

**Document Status**: FINAL
**Review Scope**: Design review only (Option 3)
**Implementation**: Out of scope - blocked issues now resolved
**Next Step**: Update workspace-feature-plan.md status and proceed to implementation when ready
