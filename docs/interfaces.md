---
layout: page
title: Interfaces
---

# Stable Interfaces

Causal Halting is useful only if the artifacts are inspectable. The project keeps natural-language interpretation outside deterministic scripts and moves all verification through explicit structured interfaces.

## Current Interfaces

### Mini-CHC v2

Used for executable CHC source checks.

Supported operational layers:

```text
CHC-0: halt, loop, H(p,a), let, HaltResult branch, data branch, L0 call, CHC call
CHC-1: recursive CHC functions through fixed-point effect summaries
CHC-2: higher-order function parameters with explicit effect annotations
```

The checker emits:

```text
chc_level
effect_summaries
fixed_point_status
higher_order_effects
effect_composition_status
analysis_profile
capability_boundary
validity_scope
identity_resolution
formal_status
theorem_coverage
```

`insufficient_info` is used when a recursive summary does not converge or a higher-order effect is not explicit.

### DesignIR v1.x

Used when an LLM or a human extracts causal structure from a design.

Required roles:

```text
executions
observations
controls
uncertain
semantic_evidence
```

The script classifies only this structured artifact. It does not read prose.

### CHC Trace JSONL

Used for runtime traces and adapter output.

Core events:

```text
exec_start
observe
consume
control_exec
exec_end
```

Optional audit metadata:

```text
event_source
timestamp
span_id
parent_id
confidence
execution_identity_relation
```

### Repair JSON

Used to turn a finding into a proposed architecture boundary.

It contains:

```text
classification
repair_status
repair_graph
recommendations
proof_obligations
```

### Proof Obligation JSON

Used by `verify-repair`.

Current obligation names:

```text
result_not_consumed_by_observed_execution_before_end
external_controller_consumes_result
future_run_consumes_result
audit_only_after_end
```

Older v1 names are still accepted for compatibility.

### Markdown/Mermaid Report

Used for human review in PRs and architecture documents.

Every report must state that CHC does not solve classical halting.

## Future Interfaces

V4.0 treats these structured interfaces as first-class analyzer inputs:

```text
ProcessIR
TemporalTraceIR
ProofCertificate
PredictionIR
IdentityResolutionReport
ValidityScope
TheoremCoverage
```

JSON schemas are maintained under `schemas/`:

```text
design-ir.schema.json
effect-summary.schema.json
effect-annotation.schema.json
process-ir.schema.json
temporal-trace.schema.json
prediction-result.schema.json
repair-certificate.schema.json
identity-resolution.schema.json
validity-scope.schema.json
theorem-coverage.schema.json
```

The rule remains fixed: scripts verify structured causal artifacts; they do not classify natural language.

## Validity Scope

All analyzer outputs must include:

```json
{
  "validity_scope": "no_modeled_prediction_feedback_only"
}
```

This field is deliberately narrow. It means the modeled artifact did not expose a prediction-feedback cycle. It does not prove termination, correctness, semantic safety, or completeness of the trace/IR.

## Identity Resolution

Production results are only useful when execution/result/control identities are explicit. The shared identity report is:

```json
{
  "resolved": [],
  "ambiguous": [],
  "missing": [],
  "conflicts": [],
  "assumptions": []
}
```

For production-style analyzers, ambiguous, missing, or conflicting identity evidence must produce `insufficient_info`, not `valid_acyclic`.
