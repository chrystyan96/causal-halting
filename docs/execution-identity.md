---
layout: page
title: Execution Identity
---

# Execution Identity

Prediction feedback depends on identity. The checker distinguishes:

- `same_execution`: the result controls the execution it observes before that execution ends.
- `future_execution`: the result controls a later execution.
- `resumed_execution`: the result controls a continuation of the same logical execution.
- `retried_execution`: the result controls a retry with a new execution identity.
- `forked_execution`: the result controls a parallel child execution.
- `unknown_identity`: the artifact does not expose enough identity information.

Default policy:

- same execution before end -> `causal_paradox`;
- future execution -> `valid_acyclic`;
- post-run audit -> `valid_acyclic`;
- unknown identity -> `insufficient_info`.

Adapters should preserve original IDs (`trace_id`, `span_id`, `parent_id`, run IDs, task IDs) so a human can audit the boundary.
