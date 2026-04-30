---
layout: page
title: CHC-2
---

# CHC-2: Higher-Order Causal Effects

CHC-2 lets functions receive functions only when the callback effect is explicit.

```text
Apply(cb!Clean,x) = cb(x)
```

The checker treats missing annotations as `insufficient_info`, not as `valid_acyclic`.

Effect annotation shape:

```json
{
  "parameter": "cb",
  "callee": "Cb",
  "effect": "Clean",
  "status": "composed"
}
```

Rules:

- Callback effects are composed into the caller graph before `acyclic_unif`.
- `HaltResult` cannot be passed into callbacks.
- Unknown callback effects are rejected conservatively.

Soundness claim: a higher-order call accepted by CHC-2 has no modeled callback path that smuggles a prediction result back into the observed execution.

CHC-2 still does not infer arbitrary effects from code. Annotations are required.
