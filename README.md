# Causal Halting

A Codex skill and experimental checker for detecting prediction-feedback loops in halting-style reasoning.

`causal-halting` packages three things:

1. a Codex skill for applying Causal Halting Calculus (CHC-0);
2. a formal reference note for the CHC-0 rules and theorems;
3. a small Python checker for CHC-0 causal graphs.

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

It makes a narrower claim:

```text
Classical diagonalization relies on unrestricted prediction feedback.
CHC-0 makes that feedback explicit as a causal graph.
The diagonal loop becomes a structural type error.
Ordinary semantic undecidability remains.
```

## How CHC-0 Works

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
  skills/
    causal-halting/
      SKILL.md
      agents/
        openai.yaml
      references/
        causal-halting-calculus.md
  scripts/
    chc_check.py
  examples/
    diagonal.chc
    diagonal.graph
    qe-valid-acyclic.chc
    safe-supervisor.graph
  tests/
    test_chc_check.py
```

## Installation

### Install The Codex Skill From GitHub

After publishing this repository, users can install the skill by URL:

```text
$skill-installer install https://github.com/chrystyan96/causal-halting/tree/master/skills/causal-halting
```

Restart Codex after installing a new skill.

### Use The Checker Locally

The checker uses Python standard library only.

```powershell
cd causal-halting
python scripts/chc_check.py examples/diagonal.chc
python scripts/chc_check.py --format json examples/diagonal.graph
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

### Mini-CHC Syntax

The mini parser supports canonical v1 examples:

```text
D(y) = if H(y,y) then loop else halt
run D(D)
```

It also supports H-free L0-style wrappers:

```text
Q_e() = simulate e(e); if e(e) halts then halt else diverge
run Q_e()
```

The mini parser is intentionally small. Unsupported language forms return `parse_error` rather than being guessed.

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

- `classification`: `causal_paradox`, `valid_acyclic`, or `parse_error`.
- `graph`: generated or parsed causal graph edges.
- `reachable_e_pairs`: E-node pairs connected by a nonempty path.
- `unifier`: first unifier proving a causal paradox, or `null`.
- `semantic_status`: `unproved` or `not_analyzed`.
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

### 4. Valid Supervisor-Worker Agent

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

### 5. Invalid Current-Run Self-Prediction

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

## Testing

Run:

```powershell
python -m unittest discover -s tests
python C:\Users\Chrystyan\.codex\skills\.system\skill-creator\scripts\quick_validate.py .\skills\causal-halting
```

Expected:

```text
OK
Skill is valid!
```

## Publication Path

Recommended path:

1. Publish this repository as `causal-halting`.
2. Install the skill by GitHub URL and test it in fresh Codex sessions.
3. Use the checker against several real agent/workflow designs.
4. Only then prepare an `openai/skills` experimental PR.

Do not submit to curated/catalog paths until the checker and examples have been exercised on real cases.

## Limitations

- The checker detects CHC-0 causal graph failures only.
- The checker does not perform semantic halting analysis.
- The mini-CHC parser supports only v1 canonical syntax.
- L0 is treated as opaque and H-free.
- Recursive CHC definitions are out of scope for v1.
- Higher-order code and runtime code generation are out of scope for v1.

## Roadmap

- CHC-1: recursive CHC definitions with fixed-point causal effect summaries.
- CHC-2: controlled higher-order code with effect-polymorphic causal types.
- More examples for AI agent supervision, tool loops, and self-evaluation protocols.
- Optional visualization for E/R causal graphs.

## License

Apache-2.0. See [LICENSE.txt](LICENSE.txt).
