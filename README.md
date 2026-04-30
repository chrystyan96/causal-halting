# Causal Halting

A Codex skill, low-cost prompt guard, operational CHC-0/CHC-1/CHC-2 checker, CHC-3 process/session analyzer, CHC-4 temporal trace analyzer, CHC-5 probabilistic prediction analyzer, DesignIR verifier, trace analyzer, repair certificates, and report workflow for detecting prediction-feedback loops in halting-style reasoning and agent architectures.

`causal-halting` packages four things:

1. a Codex skill for applying Causal Halting Calculus (CHC-0/1/2);
2. a formal reference note for the CHC-0 rules and theorem boundary;
3. a Python checker for graph DSL and Mini-CHC v2 programs with recursion summaries and higher-order effects;
4. a DesignIR verifier and trace analyzer for agent/workflow systems;
5. a causal repair workflow that proposes safer execution boundaries;
6. a low-cost background prompt guard that lets the main LLM detect CHC-0 cases from causal structure, not keyword matching.
7. CHC-3/4/5 structured analyzers for process/session flows, temporal traces, and probabilistic PredictionResult feedback.

The project is a research tool. It does not solve the classical Halting Problem. It gives a concrete way to separate two different failure modes that are often conflated:

```text
causal_paradox  structural prediction-feedback cycle
unproved        causally valid behavior whose halting status is not proven
```

## What This Tries To Solve

The classical Halting Problem says there is no Turing-computable total procedure that decides, for every program and input, whether the program halts.

The usual proof builds a diagonal program:

```text
D(y) =
  if H(y,y) says "halts" then loop
  else halt
```

Then it asks what happens when `D` is run on itself:

```text
run D(D)
```

The contradiction appears because the predicted execution is allowed to consume the prediction about itself and invert it.

This project targets that narrower structural pattern:

```text
Exec(P, X) -> HaltResult(P, X) -> Exec(P, X)
```

The first edge means a halting observation depends on an execution. The second means the observation result controls that same execution. CHC-0 rejects that loop as a causal type error.

## What This Does Not Claim

This project does not:

- solve the classical Halting Problem;
- prove arbitrary program termination;
- prove arbitrary program divergence;
- implement hypercomputation;
- make quantum, analog, or transfinite computation claims;
- classify all self-reference as invalid.

## What `valid_acyclic` Does Not Mean

`valid_acyclic` only means no modeled prediction-feedback cycle was detected in the structured artifact. It does not mean:

- the program terminates;
- the system is safe;
- the agent is correct;
- the trace is complete;
- the classical Halting Problem has been solved.

Likewise, `causal_paradox` means a modeled prediction/control loop exists. It is not a claim that the entire program is unsafe. `unproved` is not a failure; it is the ordinary semantic boundary.

It makes a narrower claim:

```text
Classical diagonalization relies on unrestricted prediction feedback.
CHC makes that feedback explicit as a causal graph.
The diagonal loop becomes a structural type error.
Ordinary semantic undecidability remains.
```

## How CHC Works

CHC-0 separates roles that the classical argument freely collapses:

```text
Code        inert program description
Exec        live execution event
H           halting observation operator
HaltResult  causal token produced by H
```

The key rule:

```text
HaltResult is not ordinary data.
```

It cannot be passed into opaque code, treated as a normal value, or hidden inside another function. It can only be discarded or used by a dedicated halting branch.

The checker builds a causal graph:

```text
H(p,a)                         adds E(p,a) -> R(p,a)
branching on HaltResult(p,a)   adds R(p,a) -> Exec(current)
ordinary boolean branch        adds no causal edge
opaque H-free code             adds no causal edge
```

Then it checks `acyclic_unif`:

```text
No nonempty path E(s,t) ->+ E(u,v)
where (s,t) and (u,v) unify under first-order unification.
```

Unification matters because code values range over infinitely many programs. Instead of enumerating substitutions, the checker asks whether any substitution could turn a symbolic feedback path into a cycle.

## Repository Layout

```text
causal-halting/
  README.md
  LICENSE.txt
  .codex-plugin/
    plugin.json
  commands/
    causal-halting.md
  docs/
    evaluation.md
  submissions/
    openai-skills-experimental-pr.md
    codex-plugin-official-proposal.md
    codex-plugin-official-request.md
  evals/
    prompts.jsonl
    baseline-responses.jsonl
    guarded-responses.jsonl
    expected-behavior.md
    compare-template.md
  hooks/
    hooks.json
  skills/
    causal-halting/
      SKILL.md
      README.md
      LICENSE.txt
      agents/
        openai.yaml
      examples/
        diagonal.chc
        diagonal.graph
        chc1-recursive-feedback.chc
        chc2-higher-order-safe.chc
        future-run.trace.jsonl
        generic-workflow.json
        langgraph-future-run.json
        otel-self-prediction.json
        temporal-airflow-indirect-feedback.json
        post-end-audit.trace.jsonl
        qe-valid-acyclic.chc
        safe-supervisor.graph
        self-prediction.analysis.json
        self-prediction.design-ir.json
        self-prediction.trace.jsonl
        design-ir-corpus/
      references/
        causal-halting-calculus.md
        chc-1-2-operational.md
        design-ir-extraction.md
      scripts/
        chc_check.py
        chc_design_analyze.py
        chc_design_schema.py
        chc_repair.py
        chc_report.py
        chc_eval_design_ir.py
        chc_trace_check.py
        chc_verify_repair.py
        chc_workflow_adapter.py
        chc_otel_adapter.py
        chc_langgraph_adapter.py
        chc_temporal_airflow_adapter.py
  scripts/
    chc_check.py
    chc_design_analyze.py
    chc_design_schema.py
    chc_repair.py
    chc_report.py
    chc_eval_design_ir.py
    chc_session_guard.py
    chc_trace_check.py
    chc_verify_repair.py
    chc_workflow_adapter.py
    chc_otel_adapter.py
    chc_langgraph_adapter.py
    chc_temporal_airflow_adapter.py
    evaluate_responses.py
  examples/
    diagonal.chc
    diagonal.graph
    chc1-recursive-feedback.chc
    chc2-higher-order-safe.chc
    future-run.trace.jsonl
    generic-workflow.json
    langgraph-future-run.json
    otel-self-prediction.json
    temporal-airflow-indirect-feedback.json
    post-end-audit.trace.jsonl
    qe-valid-acyclic.chc
    safe-supervisor.graph
    self-prediction.analysis.json
    self-prediction.design-ir.json
    self-prediction.trace.jsonl
    design-ir-corpus/
  tests/
    test_chc_check.py
    test_chc_design_trace_repair.py
    test_chc_session_guard.py
```

## Installation

### Install The Codex Skill From GitHub

The skill directory is self-contained for direct installation by URL:

```text
$skill-installer install https://github.com/chrystyan96/causal-halting/tree/master/skills/causal-halting
```

Restart Codex after installing a new skill.

### Install With npx skills

The same self-contained skill can be installed with `npx skills`:

```powershell
npx skills add https://github.com/chrystyan96/causal-halting/tree/master/skills/causal-halting -a codex -g
```

For local testing:

```powershell
npx skills add .\skills\causal-halting -a codex -g
```

Important distinction:

```text
skills/causal-halting/ is portable and self-contained.
It includes SKILL.md, references, examples, checker scripts, design/trace analysis scripts, repair script, and license.

The repository root is the full Codex plugin.
It adds hooks, /causal-halting commands, evaluation fixtures, and plugin metadata.
```

### Use The Checker Locally

The checker uses Python standard library only.

```powershell
cd causal-halting
python scripts/chc_check.py examples/diagonal.chc
python scripts/chc_check.py --format json examples/diagonal.graph
python scripts/chc_design_analyze.py examples/self-prediction.design-ir.json
python scripts/chc_trace_check.py examples/self-prediction.trace.jsonl
python scripts/chc_repair.py examples/self-prediction.analysis.json
python scripts/chc_workflow_adapter.py examples/generic-workflow.json
python scripts/chc_otel_adapter.py examples/otel-self-prediction.json
python scripts/chc_langgraph_adapter.py examples/langgraph-future-run.json
python scripts/chc_temporal_airflow_adapter.py examples/temporal-airflow-indirect-feedback.json
python scripts/chc_verify_repair.py examples/self-prediction.trace.jsonl examples/future-run.trace.jsonl
python scripts/chc_report.py examples/self-prediction.analysis.json
python scripts/chc_eval_design_ir.py examples/design-ir-corpus
```

The portable skill package also includes the checker:

```powershell
cd skills\causal-halting
python scripts\chc_check.py examples\diagonal.chc
python scripts\chc_check.py --format json examples\diagonal.graph
python scripts\chc_design_analyze.py examples\self-prediction.design-ir.json
python scripts\chc_trace_check.py examples\self-prediction.trace.jsonl
python scripts\chc_repair.py examples\self-prediction.analysis.json
python scripts\chc_workflow_adapter.py examples\generic-workflow.json
python scripts\chc_otel_adapter.py examples\otel-self-prediction.json
python scripts\chc_langgraph_adapter.py examples\langgraph-future-run.json
python scripts\chc_temporal_airflow_adapter.py examples\temporal-airflow-indirect-feedback.json
python scripts\chc_verify_repair.py examples\self-prediction.trace.jsonl examples\future-run.trace.jsonl
python scripts\chc_report.py examples\self-prediction.analysis.json
python scripts\chc_eval_design_ir.py examples\design-ir-corpus
```

## Checker Input Formats

### Graph DSL

Use explicit `E` and `R` nodes:

```text
E(y,y) -> R(y,y)
R(y,y) -> E(D,y)
```

Edges can also be chained:

```text
E(D,D) -> R(D,D) -> E(D,D)
```

### Mini-CHC v2 Syntax

The mini parser supports CHC-0 rules:

```text
D(y) = if H(y,y) then loop else halt
run D(D)
```

It also supports explicit L0 calls, CHC-1 recursion summaries, and CHC-2 higher-order effect annotations:

```text
l0 Simulate
Q_e() = simulate e(e); if e(e) halts then halt else diverge
run Q_e()

Rec(y) = let r = H(Rec,y) in if r then Rec(y) else halt
run Rec(Task)

Cb(x) = halt
Apply(cb!Clean,x) = cb(x)
run Apply(Cb,Task)
```

Unsupported language forms return `parse_error` or conservative `insufficient_info` rather than being guessed.

## Checker Output

Human-readable output:

```text
classification: causal_paradox
semantic_status: not_analyzed
explanation: Found a nonempty E-to-E path whose endpoint labels unify, so the graph contains prediction feedback.
graph:
  E(D,D) -> R(D,D)
  R(D,D) -> E(D,D)
unifier:
  y = D
```

JSON output:

```json
{
  "classification": "causal_paradox",
  "graph": [
    "E(y,y) -> R(y,y)",
    "R(y,y) -> E(D,y)"
  ],
  "reachable_e_pairs": [
    {
      "source": "E(y,y)",
      "target": "E(D,y)",
      "path": ["E(y,y)", "R(y,y)", "E(D,y)"],
      "unifier": {"y": "D"}
    }
  ],
  "unifier": {"y": "D"},
  "semantic_status": "not_analyzed",
  "explanation": "Found a nonempty E-to-E path whose endpoint labels unify, so the graph contains prediction feedback."
}
```

Fields:

- `classification`: `causal_paradox`, `valid_acyclic`, `insufficient_info`, or `parse_error`.
- `graph`: generated or parsed causal graph edges.
- `reachable_e_pairs`: E-node pairs connected by a nonempty path.
- `unifier`: first unifier proving a causal paradox, or `null`.
- `semantic_status`: `unproved` or `not_analyzed`.
- `chc_level`: `CHC-0`, `CHC-1`, or `CHC-2`.
- `effect_summaries`: CHC-1 fixed-point causal summaries.
- `higher_order_effects`: CHC-2 callback/effect composition records.
- `explanation`: short human-readable reason.

## Real Examples

### 1. Diagonalization

Input:

```text
D(y) = if H(y,y) then loop else halt
run D(D)
```

Generated graph:

```text
E(D,D) -> R(D,D)
R(D,D) -> E(D,D)
```

Result:

```json
{
  "classification": "causal_paradox",
  "unifier": {},
  "semantic_status": "not_analyzed"
}
```

The program asks for a halting observation about its own current execution, then branches on that result. CHC-0 rejects this as prediction feedback.

### 2. Symbolic Diagonal Shape

Input:

```text
E(y,y) -> R(y,y)
R(y,y) -> E(D,y)
```

Result:

```json
{
  "classification": "causal_paradox",
  "unifier": {"y": "D"}
}
```

The graph has no literal syntactic cycle, but it has a unifiable feedback path. Under substitution `y = D`, the path becomes:

```text
E(D,D) -> R(D,D) -> E(D,D)
```

### 3. Semantic Undecidability Still Survives

Input:

```text
Q_e() = simulate e(e); if e(e) halts then halt else diverge
run Q_e()
```

Result:

```json
{
  "classification": "valid_acyclic",
  "semantic_status": "unproved"
}
```

`Q_e` is H-free L0 code. It contains no CHC halting observation and produces no causal graph edges. It is causally valid, but deciding it for all `e` would decide the classical Halting Problem.

This is the key separation:

```text
D(D)  -> causal_paradox
Q_e   -> valid_acyclic but unproved
```

### 4. CHC-1 Recursive Summary

Input:

```text
Rec(y) = let r = H(Rec,y) in if r then Rec(y) else halt
run Rec(Task)
```

Result:

```json
{
  "classification": "causal_paradox",
  "chc_level": "CHC-1",
  "fixed_point_status": "converged"
}
```

The checker computes a finite effect summary for the recursive definition and detects that the summary feeds the result of observing `Rec(Task)` back into `Rec(Task)`.

### 5. CHC-2 Higher-Order Effect

Input:

```text
Cb(x) = halt
Apply(cb!Clean,x) = cb(x)
run Apply(Cb,Task)
```

Result:

```json
{
  "classification": "valid_acyclic",
  "chc_level": "CHC-2",
  "effect_composition_status": "complete"
}
```

The `cb!Clean` annotation makes the callback effect explicit. Missing annotations return `insufficient_info`; callbacks cannot receive `HaltResult` values.

### 6. Valid Supervisor-Worker Agent

Input:

```text
E(TaskA,input) -> R(TaskA,input)
R(TaskA,input) -> E(Supervisor,input)
```

Result:

```json
{
  "classification": "valid_acyclic",
  "unifier": null
}
```

A supervisor can observe a separate worker and use the result to schedule future work. The result does not feed back into the observed worker execution.

### 7. Invalid Current-Run Self-Prediction

Input:

```text
E(AgentRun,input) -> R(AgentRun,input)
R(AgentRun,input) -> E(AgentRun,input)
```

Result:

```json
{
  "classification": "causal_paradox"
}
```

The run asks whether this same run halts and then uses the answer to control itself.

## From Hygiene To Verification

Version 3.0 extends the project beyond a prompt-level warning label. It keeps the operational CHC-0/1/2 checker and adds CHC-3/4/5 structured analysis plus an explicit causal verification pipeline:

```text
/causal-halting analyze-design <design-ir-json-file>
/causal-halting analyze-trace <jsonl-file>
/causal-halting repair <analysis-json>
/causal-halting adapt-workflow <workflow-json>
/causal-halting adapt-otel <otel-json>
/causal-halting adapt-langgraph <langgraph-json>
/causal-halting adapt-temporal-airflow <temporal-airflow-json>
/causal-halting eval-design-ir <corpus-dir>
/causal-halting verify-repair <trace-before> <trace-after> [repair-json]
/causal-halting report <analysis-or-repair-json>
```

The intent is to move from:

```text
"remember to be careful with agent loops"
```

to:

```text
LLM extracts DesignIR -> deterministic classification -> trace verification -> repair obligations -> before/after proof check -> Markdown/Mermaid report
```

### Design Analysis

Use `analyze-design` only with explicit `DesignIR` JSON:

```powershell
python scripts/chc_design_analyze.py examples/self-prediction.design-ir.json
```

Natural language must be interpreted by the LLM into `DesignIR` before this script runs. If prose is passed directly to the script, it returns `needs_design_ir`.

Example output:

```json
{
  "classification": "causal_paradox",
  "inferred_graph": [
    "E(AgentRun,input) -> R(AgentRun,input)",
    "R(AgentRun,input) -> E(AgentRun,input)"
  ],
  "uncertain_edges": [],
  "repair": [
    "Move the prediction result to an external orchestrator or controller."
  ]
}
```

If the design mentions observation but does not say where the result flows, the analyzer returns `insufficient_info` instead of guessing.

The hard boundary:

```text
Natural language -> LLM semantic interpretation -> DesignIR
DesignIR -> deterministic classification
```

Minimal `DesignIR`:

```json
{
  "design_ir_version": "1.0",
  "executions": [
    {"id": "run-1", "program": "AgentRun", "input": "task"}
  ],
  "observations": [
    {"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}
  ],
  "controls": [
    {
      "id": "ctrl-1",
      "result": "r-1",
      "target_exec": "run-1",
      "timing": "during_observed_execution",
      "action": "change_strategy"
    }
  ],
  "semantic_evidence": [
    {"source": "user description", "claim": "The supervisor result changes the same active run."}
  ],
  "uncertain": []
}
```

Allowed `timing` values:

```text
during_observed_execution
after_observed_execution
future_execution
external_controller
unknown
```

`semantic_evidence` makes the LLM extraction auditable. It is not the proof. The script still determines the classification from structured causal roles.

### No Lexical Analysis

The project intentionally avoids keyword classifiers for design analysis. Words like `halt`, `loop`, `supervisor`, `monitor`, `prediction`, or `execucao` are not trusted as evidence.

Only structured causal roles in `DesignIR` are analyzed:

```text
execution exists
observation targets an execution
observation produces a result
control consumes that result
consumer is same execution, future execution, external controller, or unknown
```

This is what makes the design path language-independent. The LLM handles semantic interpretation; the verifier does not inspect natural-language words.

### Trace Analysis

Use `analyze-trace` when the input is an execution/event trace. The deterministic JSONL schema is:

```json
{"type":"exec_start","exec_id":"run-1","program":"AgentRun","input":"task-a"}
{"type":"observe","observer":"Supervisor","target_exec_id":"run-1","result_id":"r-1"}
{"type":"consume","result_id":"r-1","consumer_exec_id":"run-1","purpose":"strategy_change"}
{"type":"exec_end","exec_id":"run-1","status":"halted"}
```

Run:

```powershell
python scripts/chc_trace_check.py examples/self-prediction.trace.jsonl
```

The trace is a `causal_paradox` when a result produced by observing `run-1` is consumed by `run-1` before `run-1` ends. It is `valid_acyclic` when that result is consumed by a different run, a future run, an external controller, or only for audit/logging after completion.

### Workflow Adapter

Use `adapt-workflow` for a generic workflow JSON file:

```powershell
python scripts/chc_workflow_adapter.py examples/generic-workflow.json
```

This converts:

```text
executions + observations + controls
```

into trace events that can be passed to `chc_trace_check.py`.

### OpenTelemetry, LangGraph, And Temporal/Airflow Adapters

Use `adapt-otel` when production traces already carry explicit `chc.*` attributes:

```powershell
python scripts/chc_otel_adapter.py examples/otel-self-prediction.json
```

Supported OpenTelemetry attributes:

```text
chc.event.type        exec_start | exec_end | observe | consume | control_exec
chc.exec.id
chc.program
chc.input
chc.target_exec.id
chc.result.id
chc.consumer_exec.id
chc.consumer
chc.controlled_exec.id
chc.controller_exec.id
chc.controller
chc.action
chc.purpose
chc.status
chc.event.source
chc.timestamp
chc.span.id
chc.parent.id
chc.confidence
```

Use `adapt-langgraph` for structured LangGraph-style run JSON:

```powershell
python scripts/chc_langgraph_adapter.py examples/langgraph-future-run.json
```

Use `adapt-temporal-airflow` for structured Temporal/Airflow-style run JSON:

```powershell
python scripts/chc_temporal_airflow_adapter.py examples/temporal-airflow-indirect-feedback.json
```

These adapters are deterministic. They preserve original IDs and optional audit metadata such as `event_source`, `timestamp`, `span_id`, `parent_id`, and `confidence`. They do not infer causal meaning from span names, node names, DAG labels, edge labels, or prose.

### Repair Reports

Use `repair` after a design or trace analysis reports `causal_paradox`:

```powershell
python scripts/chc_repair.py examples/self-prediction.analysis.json
```

The repair engine emits a before/after causal boundary:

```text
Problem:
  E(AgentRun,input) -> R(AgentRun,input) -> E(AgentRun,input)

Repair:
  E(AgentRun,input) -> R(AgentRun,input) -> E(Orchestrator,input)
  E(Orchestrator,input) -> E(NextAgentRun,input)

Proof obligation:
  R(AgentRun,input) must not be consumed by AgentRun before AgentRun ends.
```

This still does not prove arbitrary termination. The gain is narrower and practical: it turns self-prediction loops into explicit architecture boundaries that can be reviewed and tested.

### Repair Verification

Use `verify-repair` to compare before/after traces:

```powershell
python scripts/chc_verify_repair.py examples/self-prediction.trace.jsonl examples/future-run.trace.jsonl
```

Expected result:

```text
before_classification: causal_paradox
after_classification: valid_acyclic
verification: passed
```

This makes the repair testable: the after trace must no longer contain same-execution pre-end consumption of its own prediction result. If a repair JSON is provided, `verify-repair` also checks each listed proof obligation.

### Markdown And Mermaid Reports

Use `report` to render an analysis, repair, or verification JSON for PRs and architecture review:

```powershell
python scripts/chc_report.py examples/self-prediction.analysis.json
```

The report includes the classification, explanation, causal graph, repair graph when available, and proof obligations.

### DesignIR Corpus Evaluation

Use `eval-design-ir` to validate extraction fixtures without parsing prose:

```powershell
python scripts/chc_eval_design_ir.py examples/design-ir-corpus
python scripts/chc_eval_suite.py examples/design-ir-corpus
python scripts/chc_certificate.py examples/self-prediction.trace.jsonl examples/future-run.trace.jsonl --repair examples/self-prediction.analysis.json
python scripts/chc_process_check.py examples/process-self-feedback.process-ir.json
python scripts/chc_temporal_check.py examples/temporal-self-feedback.trace.jsonl
python scripts/chc_prediction_check.py examples/prediction-self-risk.prediction-ir.json
python scripts/sync_skill_package.py --check
```

Version 3.0 adds trust infrastructure: capability-boundary metadata, analysis profiles, DesignIR schema validation, repair certificates, CHC-3/4/5 structured analyzers, a Lean proof-track skeleton, a 50-case DesignIR evaluation corpus, and real case-study fixtures.

Each corpus case separates:

```text
description.md           natural-language prompt for humans and LLM extraction tests
expected.design-ir.json  explicit structured interpretation
expected.analysis.json   expected deterministic classification
```

The evaluator checks only the JSON artifacts. It does not classify natural language.

## Using The Codex Skill

After installation, ask Codex to use the skill on designs involving halting, self-reference, prediction feedback, or AI agent loops:

```text
Use $causal-halting to analyze this agent design:
The agent asks a monitor whether the current run will halt,
then decides whether to continue based on the monitor result.
```

Expected structure in the answer:

```text
Core claim:
CHC roles:
Causal graph:
acyclic_unif result:
Classification:
Limits:
```

## Background Activation

When installed as a plugin, `causal-halting` includes a `UserPromptSubmit` hook. The user does not need to explicitly ask for CHC-0 on each prompt.

The hook does not classify natural language. It injects a compact structural guard on every prompt. The main LLM then performs the cheap semantic check during normal answer generation:

```text
Obs/Pred(E) -> Result -> Control(E)
```

Default injected guard:

```text
Silently check whether the prompt involves prediction, observation, simulation,
or evaluation about an execution that may control that same execution. If yes,
apply CHC-0 hygiene and distinguish causal_paradox from unproved. If no, ignore
this instruction and answer normally. Do not mention CHC-0 unless it materially
improves the answer.
```

This keeps cost low: there is no second LLM classifier and no regex/keyword semantic fallback.

## Session Mode

The user can enable a stronger CHC-0 lens with a slash command:

```text
/causal-halting on
```

To disable:

```text
/causal-halting off
```

To inspect state:

```text
/causal-halting status
```

To explain the guard:

```text
/causal-halting explain
```

To check an explicit `.graph` or `.chc` file:

```text
/causal-halting check examples/diagonal.graph
```

To analyze an explicit DesignIR file:

```text
/causal-halting analyze-design examples/self-prediction.design-ir.json
```

To verify an event trace:

```text
/causal-halting analyze-trace examples/self-prediction.trace.jsonl
```

To generate a causal repair report:

```text
/causal-halting repair examples/self-prediction.analysis.json
```

To convert generic workflow JSON into trace events:

```text
/causal-halting adapt-workflow examples/generic-workflow.json
```

To convert explicitly annotated OpenTelemetry JSON:

```text
/causal-halting adapt-otel examples/otel-self-prediction.json
```

To convert structured LangGraph-style JSON:

```text
/causal-halting adapt-langgraph examples/langgraph-future-run.json
```

To convert structured Temporal/Airflow-style JSON:

```text
/causal-halting adapt-temporal-airflow examples/temporal-airflow-indirect-feedback.json
```

To evaluate the DesignIR corpus:

```text
/causal-halting eval-design-ir examples/design-ir-corpus
```

To verify that a repair removed the causal paradox:

```text
/causal-halting verify-repair examples/self-prediction.trace.jsonl examples/future-run.trace.jsonl examples/self-prediction.analysis.json
```

To render Markdown/Mermaid for review:

```text
/causal-halting report examples/self-prediction.analysis.json
```

The same state can also be changed through explicit text commands, which are handled by the hook when a slash command is unavailable:

```text
use causal-halting for this session
causal-halting session on
enable causal-halting for this session
causal-halting session off
disable causal-halting for this session
stop causal-halting for this session
```

The hook stores session state under:

```text
.codex/causal-halting/sessions/<session_id>.json
```

The slash command stores workspace session mode under:

```text
.codex/causal-halting/session-mode.json
```

When session mode is active, the hook injects the stronger guard:

```text
Causal Halting session mode is active. For every answer, silently check for
prediction-feedback structure. When relevant, identify Code, Exec, H, and
HaltResult; classify structural feedback as causal_paradox and unresolved
semantic cases as unproved. If unrelated, answer normally without forcing CHC
terminology.
```

Prompts that should lead the main LLM to apply CHC-0:

```text
Can an agent predict whether its current run will halt?
My system changes strategy when it learns that its current execution will not finish.
Can an agent decide whether to continue based on a prediction about this same run?
Does this supervisor-worker loop feed the monitor result back into the observed worker?
E(AgentRun,input) -> R(AgentRun,input) -> E(AgentRun,input)
```

Prompts that should be answered normally:

```text
Explain how to write a Python function.
What is the capital of France?
How do I write a Python for loop?
How should a supervisor monitor worker logs after completion?
```

The guard is a routing aid, not a hidden theorem prover. It does not run semantic halting analysis and does not replace the formal checker.

## Automatic Use Example: Hexagonal Architecture

The plugin is not called like a visible function during normal conversation. The `UserPromptSubmit` hook silently adds a small instruction before the model answers. The model then performs a cheap structural check while writing the answer.

The check is:

```text
Is there an observation, prediction, simulation, or evaluation about an execution
whose result can control that same execution?

Obs/Pred(E) -> Result -> Control(E)
```

If the pattern is absent, the model ignores CHC-0 and answers normally.

### Prompt With No CHC-0 Trigger

User prompt:

```text
Explain how hexagonal architecture works.
```

What the hook injects silently:

```text
Silently check whether the prompt involves prediction, observation, simulation,
or evaluation about an execution that may control that same execution. If yes,
apply CHC-0 hygiene. If no, ignore this instruction and answer normally.
```

What the model sees structurally:

```text
Topic: software architecture
Code/Exec/HaltResult pattern: absent
Prediction about current execution: absent
Result controlling same execution: absent
CHC-0 action: ignore
```

Expected answer with the plugin:

```text
Hexagonal architecture separates the domain from external details. The center
contains business rules. Ports define contracts. Adapters connect databases,
APIs, queues, UI, and external services. This makes the domain easier to test
and keeps infrastructure replaceable.
```

Expected answer without the plugin:

```text
Hexagonal architecture separates the domain from external details. The center
contains business rules. Ports define contracts. Adapters connect databases,
APIs, queues, UI, and external services. This makes the domain easier to test
and keeps infrastructure replaceable.
```

Difference:

```text
No visible difference should appear.
The plugin added only a silent safety check and correctly stayed out of the answer.
```

This is intended. The plugin should not force CHC terminology onto unrelated software design questions.

### Prompt Where CHC-0 Activates Without Being Named

User prompt:

```text
Design a hexagonal architecture for an agent that asks a supervisor whether
the current execution will finish. If the supervisor says no, the same agent
execution changes strategy.
```

The user did not mention CHC-0, halting, Turing, or causal paradox. Still, the structure is present:

```text
E = current agent execution
Obs/Pred(E) = supervisor predicts whether this execution will terminate
Result = supervisor's prediction
Control(E) = same execution changes strategy because of that prediction
```

So the model applies CHC-0 hygiene:

```text
E(AgentRun,input) -> R(AgentRun,input) -> E(AgentRun,input)
```

Expected answer without the plugin:

```text
Use ports for the agent core, a supervisor adapter, and a strategy adapter.
The agent asks the supervisor whether it should continue. If the supervisor
predicts failure, the agent switches strategy and keeps running.
```

Problem with that answer:

```text
It sounds reasonable architecturally, but it misses the prediction-feedback loop:
the current run consumes a prediction about that same current run and changes
itself based on the result.
```

Expected answer with the plugin:

```text
Use hexagonal architecture, but do not let the current execution consume a
prediction about itself as a control input. That creates:

E(AgentRun,input) -> R(AgentRun,input) -> E(AgentRun,input)

Under CHC-0, this is a causal_paradox shape. Keep the supervisor behind an
outbound port, but route its prediction to a different execution boundary:
a later retry, an external orchestrator, or a separate controller that can stop
or restart the run. If the supervisor only reads logs after completion, it is
valid_acyclic. If it predicts the current run and that result controls the same
run, reject the design.
```

Plain-language version:

```text
The unsafe design is like asking someone to predict what you will do next,
then changing what you do because of the prediction, while the prediction was
supposed to be about the unchanged run. The plugin makes the model notice that
loop and recommend a cleaner boundary.
```

Practical hexagonal fix:

```text
Domain core:
  AgentPolicy
  StrategySelection

Inbound ports:
  StartRun
  SubmitObservation

Outbound ports:
  SupervisorPort
  RunStateStore
  SchedulerPort

Safe flow:
  AgentRun writes progress -> Supervisor observes -> Orchestrator decides
  whether to start a new run, stop externally, or schedule a retry.

Unsafe flow:
  AgentRun asks "will this same AgentRun finish?" -> prediction returns into
  AgentRun -> AgentRun changes itself based on that answer.
```

The gain is not a longer answer. The gain is a better boundary: the model can still explain hexagonal architecture, but it also prevents a subtle self-prediction loop when the prompt contains one.

## Measuring The Gain

The repository includes a small before/after evaluation harness. It compares baseline answers against guarded answers on prompts where CHC-0 should help and prompts where it should stay quiet.

Run:

```powershell
python scripts/evaluate_responses.py
python scripts/evaluate_responses.py --format json
```

Metrics:

```text
activation_precision  applies CHC when expected and stays quiet otherwise
activation_noise      forces CHC onto unrelated prompts
boundary_accuracy     separates causal_paradox, valid_acyclic, and unproved
overclaim_rate        claims CHC solves halting or arbitrary termination
answer_usefulness     activation + boundary correctness without overclaim
token_overhead        guarded response length minus baseline length
```

Example before/after:

Current bundled fixture result:

```text
baseline_answer_usefulness: 0.300
guarded_answer_usefulness: 1.000
baseline_boundary_accuracy: 0.300
guarded_boundary_accuracy: 1.000
guarded_activation_noise: 0.000
guarded_overclaim_rate: 0.000
average_token_overhead: 14.600
```

```text
Prompt:
Can an agent decide whether to continue based on a prediction about this same run?

Without causal-halting:
Yes, an agent can estimate whether to continue by using a confidence score,
timeout, or progress metric.

With causal-halting:
The risk is E(run) -> R(run) -> E(run): the prediction about the same run
controls that run. Under CHC-0 this is a causal_paradox pattern. A safer design
is a separate monitor whose result affects a later run or a different controller.
```

Second before/after:

```text
Prompt:
Q_e simulates e(e) and halts iff e(e) halts. Is this causally paradoxical?

Without causal-halting:
It is hard because simulation can take a long time. Use bounded execution.

With causal-halting:
This is not causally paradoxical if Q_e is H-free. It is valid_acyclic under
CHC-0, but its halting status is unproved in general because deciding it would
decide classical halting.
```

See [docs/evaluation.md](docs/evaluation.md) for the scoring notes and fixture layout.

## Testing

Run:

```powershell
python -m unittest discover -s tests
python C:\Users\Chrystyan\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\skills\causal-halting
python -m json.tool .codex-plugin\plugin.json
python -m json.tool hooks\hooks.json
python scripts\chc_session_guard.py --mode status --format human
python scripts\evaluate_responses.py
python scripts\chc_design_analyze.py examples\self-prediction.design-ir.json
python scripts\chc_trace_check.py examples\self-prediction.trace.jsonl
python scripts\chc_repair.py examples\self-prediction.analysis.json
python scripts\chc_workflow_adapter.py examples\generic-workflow.json
python scripts\chc_otel_adapter.py examples\otel-self-prediction.json
python scripts\chc_langgraph_adapter.py examples\langgraph-future-run.json
python scripts\chc_temporal_airflow_adapter.py examples\temporal-airflow-indirect-feedback.json
python scripts\chc_verify_repair.py examples\self-prediction.trace.jsonl examples\future-run.trace.jsonl --repair examples\self-prediction.analysis.json
python scripts\chc_report.py examples\self-prediction.analysis.json
python scripts\chc_eval_design_ir.py examples\design-ir-corpus
```

Expected:

```text
OK
Skill is valid!
```

## Publication Path

Current status:

```text
GitHub Pages site: https://chrystyan96.github.io/causal-halting/
openai/skills experimental PR: https://github.com/openai/skills/pull/380
official Codex plugin proposal package: submissions/codex-plugin-official-proposal.md
official request draft: submissions/codex-plugin-official-request.md
```

Recommended path:

1. Publish this repository as `causal-halting`.
2. Install the self-contained skill by GitHub URL and test it in fresh Codex sessions.
3. Install the same skill with `npx skills` and verify the checker resources are present.
4. Use the checker against several real agent/workflow designs.
5. Prepare an `openai/skills` experimental PR using `skills/causal-halting/` as the submitted package.
6. Separately prepare a full Codex plugin submission using the repository root if OpenAI accepts external plugin candidates.

Do not submit to curated/catalog paths until the checker and examples have been exercised on real cases.

## Limitations

- The checker analyzes explicit structured artifacts only: graph DSL, Mini-CHC v2 syntax, DesignIR, and trace JSONL.
- The checker detects CHC-0/1/2 causal graph failures only; it does not prove arbitrary termination or divergence.
- The checker does not perform semantic halting analysis.
- The design analyzer is conservative; natural-language input must be converted to explicit `DesignIR` by the LLM, and only the `DesignIR` classification is deterministic.
- The trace analyzer is deterministic, but only for traces that follow the documented event schema.
- The workflow, OpenTelemetry, and LangGraph adapters require explicit causal fields; they do not infer meaning from prose, span names, or node names.
- The repair engine proposes architecture boundaries and proof obligations; it does not patch arbitrary application code.
- The repair verifier checks trace-level obligations only when the before/after traces expose the relevant result and execution IDs.
- The evaluation harness scores response shape with transparent text checks; it is not a model-graded benchmark.
- Mini-CHC v2 is intentionally small and supports only the documented CHC-0/1/2 operational subset.
- Session mode through `/causal-halting` depends on the host plugin runtime exposing or propagating prompt/session context as expected.
- When a slash-command runtime does not expose hook `session_id` directly, `/causal-halting` falls back to workspace-local session mode.
- The background guard is a context rule, not a formal proof system.
- L0 is treated as opaque and H-free.
- CHC-1 recursion is implemented through conservative finite effect summaries; non-convergence returns `insufficient_info`.
- CHC-2 higher-order support requires explicit effect annotations; missing or incomplete composition returns `insufficient_info`.
- Runtime code generation remains out of scope.

## Roadmap

- Practical track: real traces and structured designs -> CHC events -> deterministic classification -> repair obligations -> verification -> Markdown/Mermaid report.
- Formal track: CHC-0 -> CHC-1 -> CHC-2 -> CHC-3 -> CHC-4 -> CHC-5 -> CHC-Meta, without claiming to decide classical halting.
- Stable interface docs: see `docs/interfaces.md`.
- Formal roadmap: see `docs/formal-roadmap.md`.
- CHC-3: process/session types for richer supervisor-worker protocols.
- CHC-4: temporal/distributed trace semantics beyond the current JSONL event model.
- CHC-5: probabilistic `PredictionResult` beyond binary halting observations.
- Codex-style session traces when available.
- Richer OpenTelemetry mappings for production span conventions beyond explicit `chc.*` attributes.
- Interactive graph visualization for inferred and trace-derived E/R graphs.
- Replace illustrative evaluation fixtures with live model comparison runs across several models.
- Benchmark corpus with 50-100 agent-loop prompts/designs and expected classifications.
- False-positive audit for normal monitoring, retries, and planning.
- Proof assistant encoding of core CHC-0 rules in Lean or Coq.

## License

Apache-2.0. See [LICENSE.txt](LICENSE.txt).
