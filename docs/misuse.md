---
layout: page
title: Misuse
---

# Misuse Guide

Do not use Causal Halting as a general termination prover.

Bad conclusions:

- "The checker returned `valid_acyclic`, so the program terminates."
- "The checker found `causal_paradox`, so the whole agent is unsafe."
- "The checker returned `unproved`, so the design is invalid."

Correct conclusions:

- `valid_acyclic`: no modeled prediction-feedback cycle was found.
- `causal_paradox`: a modeled observation/prediction result controls the same execution it observes.
- `unproved`: the question is semantically hard or outside the proof strength used.
- `insufficient_info`: the structured artifact does not expose enough identity/effect data.

CHC does not solve the classical Halting Problem and does not prove arbitrary termination.
