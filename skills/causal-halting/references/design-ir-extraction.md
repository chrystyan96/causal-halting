# DesignIR Extraction Contract

Natural language is never classified directly by Causal Halting scripts.

The LLM must interpret prose into `DesignIR`. Deterministic scripts then validate
and classify the `DesignIR`.

## Rule

Do not look for specific words. Ask:

```text
what execution exists?
what execution is observed or predicted?
what result is produced?
what execution consumes that result?
```

Words like `halt`, `loop`, `supervisor`, `monitor`, `prediction`, or `execucao`
are not evidence by themselves. Only structured causal roles in `DesignIR` are
analyzed.

## Schema

```json
{
  "executions": [
    {"id": "run-1", "program": "AgentRun", "input": "task"}
  ],
  "observations": [
    {"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}
  ],
  "controls": [
    {"result": "r-1", "target_exec": "run-1", "action": "change_strategy"}
  ],
  "uncertain": []
}
```

## Ambiguity

If the consumer of an observation result is unclear, do not guess:

```json
{
  "executions": [
    {"id": "run-1", "program": "AgentRun", "input": "task"}
  ],
  "observations": [
    {"id": "obs-1", "observer": "Evaluator", "target_exec": "run-1", "result": "r-1"}
  ],
  "controls": [],
  "uncertain": [
    {
      "field": "controls.target_exec",
      "reason": "The prose says the result is used, but not which execution consumes it."
    }
  ]
}
```

## Multilingual Examples

English:

```text
The active worker receives an evaluator's forecast and revises its own route.
```

DesignIR:

```json
{
  "executions": [
    {"id": "run-1", "program": "Worker", "input": "task"}
  ],
  "observations": [
    {"id": "obs-1", "observer": "Evaluator", "target_exec": "run-1", "result": "r-1"}
  ],
  "controls": [
    {"result": "r-1", "target_exec": "run-1", "action": "revise_route"}
  ],
  "uncertain": []
}
```

Portuguese:

```text
O agente em execucao recebe uma avaliacao sobre sua propria rodada e muda o plano.
```

DesignIR:

```json
{
  "executions": [
    {"id": "run-1", "program": "AgentRun", "input": "task"}
  ],
  "observations": [
    {"id": "obs-1", "observer": "Evaluator", "target_exec": "run-1", "result": "r-1"}
  ],
  "controls": [
    {"result": "r-1", "target_exec": "run-1", "action": "change_plan"}
  ],
  "uncertain": []
}
```

Spanish:

```text
El proceso activo recibe una evaluacion de esa misma ejecucion y cambia su ruta.
```

DesignIR:

```json
{
  "executions": [
    {"id": "run-1", "program": "ActiveProcess", "input": "task"}
  ],
  "observations": [
    {"id": "obs-1", "observer": "Evaluator", "target_exec": "run-1", "result": "r-1"}
  ],
  "controls": [
    {"result": "r-1", "target_exec": "run-1", "action": "change_route"}
  ],
  "uncertain": []
}
```

## Non-Goal

This contract does not expose hidden chain-of-thought. It asks the LLM for an
auditable structured interpretation.
