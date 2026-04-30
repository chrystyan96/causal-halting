---
layout: page
title: CHC-0 Technical Overview
---

# CHC-0 Technical Overview

CHC-0 is the first, deliberately small version of the Causal Halting Calculus.

Its goal is not to make every halting question decidable. Its goal is to isolate one structural pattern:

```text
prediction about an execution -> result -> control of that same execution
```

## Roles

CHC-0 separates four roles that the classical diagonal argument freely collapses:

```text
Code        inert program description
Exec        live execution event
H           halting observation operator
HaltResult  causal token produced by H
```

The key restriction:

```text
HaltResult is not ordinary data.
```

It cannot be passed into opaque code, treated as a normal value, or hidden inside another function. It can only be discarded or eliminated by a dedicated halting branch.

## Causal Graph

The checker builds a symbolic graph with two node types:

```text
E(p,a)   execution of program p on argument a
R(p,a)   result of observing E(p,a)
```

Observation adds:

```text
E(p,a) -> R(p,a)
```

Branching on the result inside the current execution adds:

```text
R(p,a) -> E(current)
```

The forbidden shape is:

```text
E(p,a) -> R(p,a) -> E(p,a)
```

## Why Unification Matters

The graph can be symbolic.

For example:

```text
E(y,y) -> R(y,y)
R(y,y) -> E(D,y)
```

There is no literal syntactic cycle. But the path:

```text
E(y,y) ->+ E(D,y)
```

becomes a cycle under:

```text
y = D
```

So CHC-0 checks whether any reachable pair of `E` nodes has labels that are first-order unifiable.

## Classification

CHC-0 uses two main outcomes:

```text
causal_paradox  unifiable prediction-feedback cycle exists
unproved        no causal paradox, but halting status is not proven
```

This is the point of the framework. It separates a structural feedback problem from ordinary semantic difficulty.

## Diagonalization

The classical diagonal program has this form:

```text
D(y) =
  if H(y,y) then loop else halt
```

Running `D(D)` creates:

```text
E(D,D) -> R(D,D) -> E(D,D)
```

CHC-0 rejects this as a causal type error.

That does not refute Turing. It says that the classical diagonal construction requires a prediction-feedback loop, and this calculus refuses that loop as a valid construction.

## Semantic Undecidability Still Survives

Now consider an H-free object-language program:

```text
Q_e() =
  simulate e(e)
  if e(e) halts, halt
  else diverge
```

`Q_e` produces no CHC-0 halting observation, so its causal graph is empty. It is causally valid.

But deciding `Q_e` for all `e` would decide the classical Halting Problem.

So the hard semantic cases remain:

```text
D(D)  -> causal_paradox
Q_e   -> valid_acyclic but unproved
```

## Checker

The repository includes a small Python checker:

```powershell
python scripts/chc_check.py examples/diagonal.graph
python scripts/chc_check.py examples/qe-valid-acyclic.chc
```

The portable skill package also includes the checker:

```powershell
cd skills\causal-halting
python scripts\chc_check.py examples\diagonal.graph
```

## Full Reference

The full formal note is in the repository:

[causal-halting-calculus.md](https://github.com/chrystyan96/causal-halting/blob/master/skills/causal-halting/references/causal-halting-calculus.md)
