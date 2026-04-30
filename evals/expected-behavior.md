# Expected Evaluation Behavior

Use these fixtures to compare answers with and without the Causal Halting guard.

The guarded answer should:

- detect prediction-feedback structure when present;
- distinguish `causal_paradox` from `unproved`;
- avoid claiming that CHC-0 solves the classical Halting Problem;
- avoid forcing CHC language onto ordinary loops or unrelated monitoring questions;
- provide a concrete design implication when a causal risk exists.

The guarded answer should not:

- call every loop a causal paradox;
- treat all self-reference as invalid;
- claim arbitrary termination can be decided;
- replace ordinary engineering advice when no prediction-feedback structure exists.

Primary score dimensions:

```text
activation_precision
activation_noise
boundary_accuracy
overclaim_rate
answer_usefulness
token_overhead
```
