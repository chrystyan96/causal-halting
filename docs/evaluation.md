---
layout: page
title: Evaluation
---

# Evaluation

The plugin should improve answers where prediction feedback matters and stay quiet where it does not.

Run the bundled comparison:

```powershell
python scripts/evaluate_responses.py
python scripts/evaluate_responses.py --format json
```

The harness compares `evals/baseline-responses.jsonl` and `evals/guarded-responses.jsonl` against `evals/prompts.jsonl`.

## Metrics

```text
activation_precision  answer uses CHC when the fixture expects CHC, or avoids it when not expected
activation_noise      answer forces CHC onto prompts where it should stay quiet
boundary_accuracy     answer separates causal_paradox, valid_acyclic, and unproved correctly
overclaim_rate        answer claims CHC solves halting or arbitrary termination
answer_usefulness     answer is activated correctly, has correct boundary, and avoids overclaim
token_overhead        guarded token count minus baseline token count
```

These are operational metrics. They do not prove the formal theory. They measure whether the plugin improves answer shape.

## DesignIR Corpus Evaluation

The repository also includes deterministic corpus checks:

```powershell
python scripts/chc_eval_design_ir.py examples/design-ir-corpus
chc eval evals/v4 --format json
```

The corpus is deliberately split:

```text
description.md              natural-language prompt for humans and LLM extraction tests
expected.design-ir.json      structured interpretation
expected.analysis.json       expected deterministic classification
```

The evaluator does not parse `description.md`. It validates the expected
`DesignIR` artifacts and verifies that the deterministic analyzer returns the
expected classification. This keeps the rule intact:

```text
natural language -> LLM writes DesignIR
DesignIR -> scripts verify structure
```

Response-quality evaluation and corpus evaluation answer different questions:

```text
response eval: did the assistant use the CHC lens well?
corpus eval: does explicit DesignIR classify correctly?
```

## V4 Corpus

V4 adds a 100-case structured corpus under `evals/v4`:

```text
40 causal_paradox
40 valid_acyclic
20 insufficient_info
```

The corpus includes safe non-problem examples such as ordinary loops, future-run retries, logging-only observations, post-run scoring, and local progress counters.

`chc eval` reports total cases, passed/failed counts, classification accuracy, coverage, and false-positive/false-negative categories. It still does not parse natural language; `description.md` files are human context and extraction fixtures only.

## Current Sample Result

The bundled sample responses are illustrative and deterministic. They show the intended delta:

```text
baseline: generic engineering advice
guarded: causal graph diagnosis and safer design boundary
```

Current output:

```text
case_count: 10
baseline_activation_precision: 0.300
guarded_activation_precision: 1.000
baseline_activation_noise: 0.000
guarded_activation_noise: 0.000
baseline_boundary_accuracy: 0.300
guarded_boundary_accuracy: 1.000
baseline_overclaim_rate: 0.000
guarded_overclaim_rate: 0.000
baseline_answer_usefulness: 0.300
guarded_answer_usefulness: 1.000
average_token_overhead: 14.600
```

Expected qualitative improvement:

```text
generic timeout/retry advice
-> prediction-feedback diagnosis

"hard because simulation is long"
-> valid_acyclic but unproved

"looks like a loop"
-> symbolic causal_paradox with unifier
```
