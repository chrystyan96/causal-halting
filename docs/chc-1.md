---
layout: page
title: CHC-1
---

# CHC-1: Recursion With Effect Summaries

CHC-1 extends CHC-0 with recursive CHC functions. It does not inline recursion forever. It computes finite causal effect summaries and uses those summaries during `RUN`.

```text
Eff(f) = fixed point of body_effect(f)
```

V3.0 exposes summaries as structured metadata:

```json
{
  "summary_id": "Eff(Rec)",
  "function": "Rec",
  "edges": ["E(Rec,y) -> R(Rec,y)"],
  "status": "converged_exact",
  "iteration_count": 2,
  "max_iterations": 32,
  "widening_applied": false,
  "conservative_reason": null
}
```

Statuses:

- `converged_exact`: summary stabilized without widening.
- `converged_conservative`: reserved for future widening-based summaries.
- `not_converged`: checker returns `insufficient_info`.
- `not_needed`: non-recursive CHC-0 behavior.

Soundness claim: accepted CHC-1 summaries do not hide a detected prediction-feedback edge. Incompleteness is explicit: some safe recursive programs may be rejected as `insufficient_info`.

CHC-1 still does not prove arbitrary recursive termination.
