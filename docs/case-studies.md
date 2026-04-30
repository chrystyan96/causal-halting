---
layout: page
title: Case Studies
---

These are small architecture cases for testing whether Causal Halting is doing
useful work. They are not proofs about arbitrary termination. They are checks
for one boundary:

```text
observation about a run -> result -> control of that same run
```

## Case 1: Current-Run Self-Feedback

A worker receives an evaluator result about the active attempt and immediately
changes its own route.

DesignIR:

```text
E(Worker,task) -> R(Worker,task) -> E(Worker,task)
```

Classification:

```text
causal_paradox
```

Repair:

```text
send the result to an external orchestrator
let the orchestrator stop, restart, or schedule a later run
do not let the active run consume its own prediction result before it ends
```

## Case 2: External Orchestrator

The worker emits progress. An evaluator observes it. The evaluator result goes
to an orchestrator, and the orchestrator schedules a new attempt.

Design shape:

```text
E(Worker,task) -> R(Worker,task) -> External(Orchestrator)
External(Orchestrator) -> E(Worker,retry)
```

Classification:

```text
valid_acyclic
```

The key difference is that the observed run does not consume the result about
itself.

## Case 3: Post-Run Audit

A monitor observes a run and stores a result. The result is consumed only after
the run has ended, for audit or reporting.

Trace shape:

```text
exec_start(run-1)
observe(run-1) -> r-1
exec_end(run-1)
consume(r-1, run-1, audit_only)
```

Classification:

```text
valid_acyclic
```

This is safe because the result does not control the current execution before
that execution ends.

## Pipeline Demo

The practical workflow is:

```text
DesignIR -> analyze-design -> repair -> verify-repair -> report
```

Commands:

```powershell
python scripts/chc_design_analyze.py examples/self-prediction.design-ir.json --format json
python scripts/chc_repair.py examples/self-prediction.analysis.json --format json
python scripts/chc_verify_repair.py examples/self-prediction.trace.jsonl examples/future-run.trace.jsonl --repair examples/self-prediction.analysis.json
python scripts/chc_report.py examples/self-prediction.analysis.json
```

For trace adapters:

```powershell
python scripts/chc_otel_adapter.py examples/otel-self-prediction.json
python scripts/chc_langgraph_adapter.py examples/langgraph-future-run.json
```

For corpus checks:

```powershell
python scripts/chc_eval_design_ir.py examples/design-ir-corpus
```
