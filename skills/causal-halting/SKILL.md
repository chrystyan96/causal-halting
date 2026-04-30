---
name: causal-halting
description: Analyze halting-problem variants, Turing diagonalization, self-reference, prediction-feedback loops, AI agent termination, workflow self-evaluation, and systems that ask whether their own current execution will halt. Use this skill when the task involves Causal Halting Calculus (CHC-0), causal paradox vs semantic unprovability, halting predictors, or designing/reviewing systems that separate observation, execution, and feedback.
---

# Causal Halting

Use this skill to apply the Causal Halting Calculus (CHC-0) as an analysis method. CHC-0 does not solve the classical Halting Problem. It separates two failure modes: structural prediction-feedback cycles (`causal_paradox`) and ordinary semantic undecidability (`unproved`).

## Workflow

1. State the exact claim being analyzed.
   - Distinguish "decide all halting" from "detect prediction-feedback loops."
   - Do not claim CHC-0 removes undecidability.

2. Identify the CHC roles.
   - `Code`: inert program description.
   - `Exec`: live execution event.
   - `H`: halting observation operator.
   - `HaltResult`: causal token produced by `H`, not ordinary data.

3. Enforce CHC-0 restrictions before reasoning.
   - No `eval`.
   - No runtime code generation.
   - No higher-order code.
   - No recursion in CHC-defined code.
   - CHC calls are fully inlined over an acyclic call graph.
   - L0 programs are opaque, H-free, and may be Turing-complete.
   - `HaltResult` is not `Val`.
   - `HaltResult` cannot enter L0 or cross CHC function boundaries.
   - `HaltResult` can only be discarded or eliminated by `H-BRANCH`.

4. Build the symbolic causal graph.
   - Observation `H(p,a)` adds `E(p,a) -> R(p,a)`.
   - Branching on `HaltResult(p,a)` inside current execution `e` adds `R(p,a) -> e`.
   - Branching on ordinary `Bool` adds no causal edge.
   - L0 calls add no causal edge.
   - CHC calls inline their body and accumulate edges.

5. Check `acyclic_unif`.
   - Look for a nonempty path `E(s,t) ->+ E(u,v)`.
   - If `(s,t)` and `(u,v)` unify under first-order unification, classify as `causal_paradox`.
   - Use unification, not enumeration of concrete substitutions.

6. Classify the result.
   - `causal_paradox`: a unifiable prediction-feedback cycle exists.
   - `unproved`: no causal paradox, but termination/divergence is not proven.
   - `proved_halts` or `proved_diverges`: only if an explicit proof, restricted analysis, or trusted verifier establishes it.

7. Explain the boundary.
   - `causal_paradox` is type-system intrinsic and stable across proof systems.
   - `unproved` is proof-system relative and can shrink under stronger sound provers.

## Canonical Examples

Diagonal program:

```text
D(y) =
  let r = H(y,y) in
  if r then loop else halt
```

Graph:

```text
E(y,y) -> R(y,y) -> E(D,y)
```

The path `E(y,y) ->+ E(D,y)` becomes a cycle under unifier `y |-> D`. Therefore `D(D)` is a `causal_paradox`.

Semantic hard case:

```text
Q_e() =
  simulate e(e)
  if e(e) halts, halt
  else diverge
```

`Q_e` is H-free L0 code, so it generates no causal graph edges. It is causally valid, but deciding it for all `e` would decide the classical Halting Problem. Therefore it belongs to `unproved` in general.

## Output Pattern

When responding, prefer this structure:

```text
Core claim:
CHC roles:
Causal graph:
acyclic_unif result:
Classification:
Limits:
```

Keep the distinction sharp:

```text
CHC-0 rejects diagonal prediction feedback.
CHC-0 does not decide all halting questions.
```

## Reference

For formal rules, theorem statements, and the current paper draft, read:

```text
references/causal-halting-calculus.md
```
