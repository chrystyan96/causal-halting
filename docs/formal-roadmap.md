---
layout: page
title: Formal Roadmap
---

# Formal Roadmap

Causal Halting should not grow by claiming more than it proves. The maximum useful theory is not hypercomputation. It is a layered account of prediction-feedback: where it is structural, where it is decidable, where it must be conservative, and where ordinary undecidability remains.

## Two Coordinated Tracks

The practical track accepts real artifacts and returns a checkable diagnosis:

```text
real artifact
-> normalized CHC trace / DesignIR
-> deterministic causal classification
-> repair recommendation
-> proof-obligation verification
-> Markdown/Mermaid report
```

The formal track explains why each practical boundary is legitimate:

```text
CHC-0 -> CHC-1 -> CHC-2 -> CHC-3 -> CHC-4 -> CHC-5 -> CHC-Meta
```

Both tracks keep the same constraint: CHC does not decide the classical Halting Problem. It separates structural prediction-feedback loops from semantic unprovability.

## CHC-0: Finite First-Order Core

Scope:

- first-order CHC definitions;
- no CHC recursion;
- no higher-order code;
- no `eval`;
- finite causal graphs;
- decidable `acyclic_unif`.

Current theorem targets:

- diagonalization is causally ill-typed;
- `Q_e`-style semantic hard cases remain `unproved`;
- `causal_paradox` is stable across proof systems for a fixed calculus.

## CHC-1: Recursion With Effect Summaries

V2.0 operational status: implemented conservatively in the checker.

Each function receives a causal effect summary:

```text
Eff(f) = least_fixed_point(body_effect(f))
```

Remaining theorem work:

- finite summaries exist under stated restrictions;
- summary checking is decidable or explicitly conservative;
- accepted summaries are sound: no detected prediction-feedback path is hidden by recursion;
- incompleteness is acknowledged: some safe programs may be rejected.

## CHC-2: Higher-Order Effects

V2.0 operational status: implemented conservatively in the checker.

Candidate type shape:

```text
f : A -> B ! Eff
```

Remaining theorem work:

- effect composition is sound;
- substitution preserves causal safety;
- higher-order callbacks cannot smuggle observation results into the observed execution.

## V4.0 Formal Status

The Lean track now covers core structural invariants for CHC-0 through CHC-5:

```text
CHC-0  finite graph/reachability core and diagonal rejection
CHC-1  conservative effect-summary status
CHC-2  effect annotation and callback composition
CHC-3  process/session non-interference core
CHC-4  temporal pre-end feedback rule
CHC-5  prediction-confidence irrelevance for causal feedback
```

This is not a mechanized proof of arbitrary termination and not a full mechanization of every parser/adapter. It is the proof track for the core structural rules the tools enforce.

## CHC-3: Processes, Supervisors, And Sessions

V4.0 operational status: implemented as `chc_process_check.py` over stricter structured `ProcessIR`, including process/session/channel/execution/result identity checks and multi-hop route detection.

Goal: model agents, supervisors, workers, monitors, and orchestrators as typed processes.

Separate identities:

```text
process identity
execution identity
result identity
control channel
```

Core non-interference rule:

```text
observation result of E cannot flow into control channel of E before E ends
```

This is where CHC connects most directly to session types and information-flow security.

## CHC-4: Temporal And Distributed Traces

V4.0 operational status: implemented as `chc_temporal_check.py` over temporal JSONL traces with explicit happens-before, span parent links, logical clocks, and safe timestamp ordering.

Goal: reason over observed execution traces rather than only static terms.

Core events:

```text
exec_start
observe
consume
control_exec
exec_end
```

Temporal facts:

- same-run pre-end consumption is invalid;
- post-run audit is valid;
- future-run control is valid;
- ambiguous execution identity returns `insufficient_info`;
- missing end events are treated conservatively.

## CHC-5: Probabilistic And AI Predictions

V4.0 operational status: implemented as `chc_prediction_check.py` over structured `PredictionIR` with explicit prediction scope and confidence ignored for classification.

Goal: generalize `HaltResult` to broader `PredictionResult` values.

Examples:

```text
will_halt
likely_fail
confidence_score
risk_assessment
budget_exhaustion_prediction
```

The causal rule does not require certainty:

```text
prediction_about(E) -> result -> control(E)
```

The problem is the control path, not whether the prediction is binary or perfect.

## CHC-Meta: Boundary Theory

The final theory should characterize:

```text
CausalParadox = structural failure
Unproved       = semantic/proof-theoretic limit
```

Expected properties:

- stronger proof systems can shrink `Unproved`;
- stronger proof systems do not change `CausalParadox` for a fixed calculus;
- undecidability reappears when the calculus becomes expressive enough to encode unrestricted semantic behavior.

## Mechanized Proof Plan

Recommended target: Lean 4.

Order:

1. Formalize CHC-0 syntax, types, and graph generation.
2. Formalize finite reachability and `acyclic_unif`.
3. Prove decidability for finite CHC-0 graphs.
4. Prove the diagonal term is rejected.
5. State the `Q_e` reduction boundary.
6. Prove the boundary theorem.
7. Extend to CHC-1 effect summaries.

V4.0 expands this track under `formal/lean/` from a CHC-0 skeleton into modules for CHC-0/1/2/3/4/5 core invariants. Future work is to mechanize the full parser-to-proof correspondence and richer CHC-1/2 soundness theorems.
