# Causal Halting Skill

A self-contained Agent Skill for analyzing prediction-feedback loops in halting-style reasoning.

This package is the portable skill distribution for `causal-halting`. It is suitable for installation through `openai/skills`, direct GitHub skill install, and `npx skills`.

## What It Does

The skill applies Causal Halting Calculus (CHC-0) as an analysis method.

It separates two failure modes:

```text
causal_paradox  structural prediction-feedback cycle
unproved        causally valid behavior whose halting status is not proven
```

It does not solve the classical Halting Problem. It detects the narrower pattern where a prediction or observation about an execution can control that same execution:

```text
Exec(P, X) -> HaltResult(P, X) -> Exec(P, X)
```

## Contents

```text
causal-halting/
  SKILL.md
  README.md
  LICENSE.txt
  agents/
    openai.yaml
  references/
    causal-halting-calculus.md
  scripts/
    chc_check.py
    chc_design_analyze.py
    chc_design_schema.py
    chc_trace_check.py
    chc_repair.py
    chc_workflow_adapter.py
    chc_verify_repair.py
  examples/
    diagonal.chc
    diagonal.graph
    future-run.trace.jsonl
    generic-workflow.json
    post-end-audit.trace.jsonl
    qe-valid-acyclic.chc
    safe-supervisor.graph
    self-prediction.analysis.json
    self-prediction.trace.jsonl
```

## Install

### Codex Skill Installer

```text
$skill-installer install https://github.com/chrystyan96/causal-halting/tree/master/skills/causal-halting
```

Restart Codex after installing a new skill.

### npx skills

```powershell
npx skills add https://github.com/chrystyan96/causal-halting/tree/master/skills/causal-halting -a codex -g
```

For local testing from the repository root:

```powershell
npx skills add .\skills\causal-halting -a codex -g
```

## Use

Ask the agent to analyze designs involving halting, self-reference, prediction feedback, or AI agent loops:

```text
Use causal-halting to analyze this agent design:
The agent asks a monitor whether the current run will halt,
then decides whether to continue based on the monitor result.
```

Expected response shape:

```text
Core claim:
CHC roles:
Causal graph:
acyclic_unif result:
Classification:
Limits:
```

## Checker

The bundled checker uses Python standard library only.

Run from this skill directory:

```powershell
python scripts/chc_check.py examples/diagonal.graph
python scripts/chc_check.py --format json examples/diagonal.chc
python scripts/chc_check.py examples/qe-valid-acyclic.chc
python scripts/chc_check.py examples/safe-supervisor.graph
python scripts/chc_design_analyze.py "The current execution changes strategy when a supervisor predicts it will not finish."
python scripts/chc_trace_check.py examples/self-prediction.trace.jsonl
python scripts/chc_repair.py examples/self-prediction.analysis.json
python scripts/chc_workflow_adapter.py examples/generic-workflow.json
python scripts/chc_verify_repair.py examples/self-prediction.trace.jsonl examples/future-run.trace.jsonl
```

Checker classifications:

```text
causal_paradox  unifiable prediction-feedback cycle found
valid_acyclic   no CHC-0 causal paradox detected
parse_error     unsupported or invalid checker input
```

`semantic_status` may be:

```text
unproved        causally valid, but arbitrary halting remains undecidable
not_analyzed    semantic halting status was not analyzed
```

## Examples

### Diagonal

```text
D(y) = if H(y,y) then loop else halt
run D(D)
```

Expected:

```text
classification: causal_paradox
```

The program asks for a halting observation about its own current execution and then branches on that result.

### Q_e

```text
Q_e() = simulate e(e); if e(e) halts then halt else diverge
run Q_e()
```

Expected:

```text
classification: valid_acyclic
semantic_status: unproved
```

`Q_e` is H-free, so it has no CHC-0 causal paradox. It remains semantically hard because deciding it for all `e` would decide classical halting.

### Safe Supervisor

```text
E(TaskA,input) -> R(TaskA,input)
R(TaskA,input) -> E(Supervisor,input)
```

Expected:

```text
classification: valid_acyclic
```

The supervisor observes a separate worker. The result does not feed back into the observed worker execution.

## Design, Trace, And Repair Workflows

The portable skill also includes the v1.5 analysis scripts:

```text
chc_design_analyze.py  infer DesignIR from text or analyze explicit DesignIR JSON
chc_design_schema.py   validate design-analysis JSON
chc_trace_check.py     deterministically analyze JSONL execution traces
chc_repair.py          generate repair reports and proof obligations
chc_workflow_adapter.py convert generic workflow JSON to CHC trace JSONL
chc_verify_repair.py   verify before/after trace repair
```

Trace schema:

```json
{"type":"exec_start","exec_id":"run-1","program":"AgentRun","input":"task-a"}
{"type":"observe","observer":"Supervisor","target_exec_id":"run-1","result_id":"r-1"}
{"type":"consume","result_id":"r-1","consumer_exec_id":"run-1","purpose":"strategy_change"}
{"type":"exec_end","exec_id":"run-1","status":"halted"}
```

Repair reports move same-run prediction feedback to a separate orchestrator/future-run boundary and emit the proof obligation that the observed execution must not consume its own prediction result before it ends.

## Limits

- Does not solve the classical Halting Problem.
- Does not prove arbitrary termination or divergence.
- Checks explicit CHC-0 graph DSL and mini-CHC artifacts only.
- Infers `DesignIR` conservatively from text; deterministic classification starts from `DesignIR`.
- Deterministically checks traces only when they follow the documented JSONL schema.
- Converts only the documented generic workflow JSON format; framework adapters are future work.
- Produces causal refactoring guidance, not arbitrary code patches.
- Treats semantic undecidability as `unproved`, not as `causal_paradox`.
- Does not include the full Codex plugin hook or `/causal-halting` slash command. Those live in the full plugin repository.

## License

Apache-2.0. See `LICENSE.txt`.
