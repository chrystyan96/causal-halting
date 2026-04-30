---
layout: page
title: CHC-1 And CHC-2
---

# CHC-1 And CHC-2

V2.0 adds operational support for the next two layers of Causal Halting.

This is still not a halting oracle. The checker only tracks causal prediction-feedback structure.

## CHC-1: Recursive Effect Summaries

CHC-1 supports recursive CHC functions through finite causal effect summaries:

```text
Eff(f) = fixed-point summary of body_effect(f)
```

The implementation computes summaries by monotone iteration over symbolic graph edges. If the summaries stabilize, the checker analyzes `run f(args)` using the converged summary. If they do not stabilize within the configured limit, the result is conservative:

```text
classification: insufficient_info
fixed_point_status: not_converged
```

Example:

```text
Rec(y) = let r = H(Rec,y) in if r then Rec(y) else halt
run Rec(Task)
```

This produces a CHC-1 causal paradox because the recursive summary routes:

```text
E(Rec,Task) -> R(Rec,Task) -> E(Rec,Task)
```

## CHC-2: Higher-Order Effects

CHC-2 supports controlled higher-order calls through explicit effect annotations:

```text
Cb(x) = halt
Apply(cb!Clean,x) = cb(x)
run Apply(Cb,Task)
```

The annotation says that `cb` is a function parameter with an explicit effect. During analysis, callback effects are composed into the caller before `acyclic_unif`.

If the annotation is missing:

```text
Apply(cb,x) = cb(x)
```

the checker returns:

```text
classification: insufficient_info
effect_composition_status: incomplete
```

Callbacks cannot receive `HaltResult` values. This preserves the CHC-0 rule that observation results cannot be hidden inside opaque or higher-order calls.

## Output Fields

V2.0 checker output includes:

```text
chc_level
effect_summaries
fixed_point_status
higher_order_effects
effect_composition_status
```

These fields make the operational path auditable: the user can see whether the result came from CHC-0 direct graph generation, CHC-1 recursive summaries, or CHC-2 higher-order effect composition.
