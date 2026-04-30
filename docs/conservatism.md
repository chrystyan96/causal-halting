---
layout: page
title: Conservatism
---

# Conservatism Profile

The checker reports how strong its result is:

```json
{
  "analysis_profile": "complete_for_chc0"
}
```

Profiles:

- `complete_for_chc0`: finite first-order CHC-0 graph check.
- `conservative_chc1`: recursive effect summaries may reject safe programs.
- `annotation_required_chc2`: higher-order safety depends on explicit effect annotations.
- `trace_identity_limited`: trace/design checks depend on stable execution identity.

Known conservative cases:

- recursive summaries that do not converge;
- missing higher-order effect annotations;
- traces with unknown execution identity;
- structured designs that omit the result consumer.

Known non-claims:

- `valid_acyclic` does not mean the program terminates;
- `valid_acyclic` does not mean the system is safe;
- `causal_paradox` does not mean every part of the program is wrong;
- `unproved` is not a failure, only a semantic boundary.
