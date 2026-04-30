---
layout: page
title: Causal Halting
---

**Causal Halting is a small framework for detecting prediction-feedback loops in halting-style reasoning and AI agent designs.**

It does not solve the classical Halting Problem. It asks a narrower question:

```text
What happens when a system consumes a prediction about its own current execution
and uses that prediction to control that same execution?
```

That shape appears in AI agents, supervisors, monitors, retry loops, self-evaluation systems, and workflow controllers.

## The Core Pattern

The unsafe pattern is:

```text
Exec(P, X) -> HaltResult(P, X) -> Exec(P, X)
```

In plain language:

```text
current execution -> prediction about that execution -> control of that same execution
```

Causal Halting calls this a structural prediction-feedback cycle.

## The Separation

Causal Halting separates two cases that are easy to confuse:

```text
causal_paradox  structural prediction-feedback cycle
unproved        causally valid behavior whose halting status is not proven
```

The first is a graph/property problem. The second is the ordinary semantic difficulty behind the classical Halting Problem.

## Why This Matters For AI Agents

An external supervisor observing an agent is fine.

An orchestrator deciding whether to start a later retry is fine.

A system inspecting logs after a run completes is fine.

The risky design is different:

```text
the current run asks whether this same current run will finish
and then changes itself because of the answer
```

Causal Halting gives a way to notice that boundary before it becomes an architectural habit.

## Beyond A Warning Label

The current plugin adds three practical workflows:

```text
analyze-design  infer a CHC graph from an agent/workflow design
analyze-trace   deterministically check JSONL execution events
repair          convert same-run feedback into an orchestrator/future-run boundary
```

This moves the project from architectural hygiene toward causal verification:

```text
infer graph -> classify feedback -> propose repair -> state proof obligation
```

The proof obligation is simple:

```text
A prediction result about an execution must not be consumed by that same
execution before it ends.
```

## Project Links

- Repository: [github.com/chrystyan96/causal-halting](https://github.com/chrystyan96/causal-halting)
- Technical note: [CHC-0 technical overview](./chc-0.md)
- Evaluation notes: [measuring answer quality](./evaluation.md)
- Publication status: [submissions and links](./publication.md)
- OpenAI Skills PR: [openai/skills#380](https://github.com/openai/skills/pull/380)

## One Sentence

Classical diagonalization relies on unrestricted prediction feedback; Causal Halting makes that feedback explicit, rejects it structurally, and leaves ordinary undecidability intact.
