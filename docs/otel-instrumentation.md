---
layout: page
title: OpenTelemetry Instrumentation
---

The OpenTelemetry adapter is deliberately conservative. It does not infer
causal meaning from span names. It only reads explicit `chc.*` attributes.

## Required Event Types

Every CHC event is represented by a span or span event with:

```text
chc.event.type = exec_start | exec_end | observe | consume
```

## Execution Start

```text
chc.event.type = exec_start
chc.exec.id    = run-1
chc.program    = AgentRun
chc.input      = task-a
```

## Observation

```text
chc.event.type      = observe
chc.observer        = Supervisor
chc.target_exec.id  = run-1
chc.result.id       = r-1
```

This says that `r-1` is a result produced by observing `run-1`.

## Consumption

Unsafe same-run control:

```text
chc.event.type        = consume
chc.result.id         = r-1
chc.consumer_exec.id  = run-1
chc.purpose           = strategy_change
```

Safe external controller:

```text
chc.event.type  = consume
chc.result.id   = r-1
chc.consumer    = Orchestrator
chc.purpose     = stop_or_retry
```

Safe future run:

```text
chc.event.type        = consume
chc.result.id         = r-1
chc.consumer_exec.id  = run-2
chc.purpose           = schedule_retry
```

## Execution End

```text
chc.event.type = exec_end
chc.exec.id    = run-1
chc.status     = halted
```

## Rule Checked

The trace analyzer rejects:

```text
observe(target_exec_id = run-1)
consume(result_id = r-1, consumer_exec_id = run-1)
before exec_end(run-1)
```

as:

```text
causal_paradox
```

It accepts external controllers, later runs, and post-run audit/logging paths as
`valid_acyclic`.
