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

## V3.0 Operational Core

The v3.0 package supports five operational layers:

```text
CHC-0  finite first-order graph generation
CHC-1  recursive causal effect summaries
CHC-2  higher-order calls with explicit effect annotations
CHC-3  process/session non-interference
CHC-4  temporal/distributed trace order
CHC-5  probabilistic PredictionResult feedback
```

If recursion summaries do not converge or higher-order effects are missing, the checker returns `insufficient_info` instead of accepting an unsafe program.
If process identity, temporal order, or prediction target identity is unclear, the structured analyzers also return `insufficient_info`.

## Practical Verification Pipeline

The current plugin is no longer only a prompt-level warning label. The useful
path is:

```text
LLM extracts DesignIR
-> deterministic verifier classifies it
-> trace adapters map real events into CHC events
-> repair emits proof obligations
-> before/after traces verify the boundary
-> repair certificate records evidence
-> Markdown/Mermaid report explains the result
```

The practical commands are:

```text
analyze-design   check explicit DesignIR v1.0
analyze-trace    check JSONL execution events
adapt-otel       convert annotated OpenTelemetry JSON
adapt-langgraph  convert structured LangGraph-style JSON
adapt-temporal-airflow convert structured Temporal/Airflow-style JSON
repair           propose a safer orchestration boundary
verify-repair    check before/after traces and proof obligations
certificate      emit machine-readable repair certificate
process-check    CHC-3 ProcessIR
temporal-check   CHC-4 temporal trace JSONL
prediction-check CHC-5 PredictionIR
report           render Markdown/Mermaid output
```

The proof obligation is simple:

```text
A prediction result about an execution must not be consumed by that same
execution before it ends.
```

## No Lexical Analysis

Natural-language designs are not classified by scripts. The LLM must convert
prose into `DesignIR`; deterministic tools then analyze only that structured
artifact. This keeps the method language-independent and avoids trusting
keywords as evidence.

## Case Studies

The repository includes small cases for the three useful boundaries:

```text
self-feedback       causal_paradox
external controller valid_acyclic
post-run audit      valid_acyclic
```

See [case studies](./case-studies.md).

## Project Links

- Repository: [github.com/chrystyan96/causal-halting](https://github.com/chrystyan96/causal-halting)
- Technical note: [CHC-0 technical overview](./chc-0.md)
- CHC-1/2: [recursive summaries and higher-order effects](./chc-1-2.md)
- CHC-1: [effect summaries](./chc-1.md)
- CHC-2: [higher-order effects](./chc-2.md)
- Conservatism: [what the checker rejects conservatively](./conservatism.md)
- Execution identity: [same, future, resumed, retried, forked, unknown](./execution-identity.md)
- Misuse guide: [what `valid_acyclic` does not mean](./misuse.md)
- Case studies: [practical architecture cases](./case-studies.md)
- Interfaces: [structured artifacts and schemas](./interfaces.md)
- Formal roadmap: [CHC theory layers](./formal-roadmap.md)
- Evaluation notes: [measuring answer quality](./evaluation.md)
- OpenTelemetry guide: [explicit CHC trace attributes](./otel-instrumentation.md)
- Publication status: [submissions and links](./publication.md)
- OpenAI Skills PR: [openai/skills#380](https://github.com/openai/skills/pull/380)

## One Sentence

Classical diagonalization relies on unrestricted prediction feedback; Causal Halting makes that feedback explicit, rejects it structurally, and leaves ordinary undecidability intact.
