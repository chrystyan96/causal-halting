# Causal Halting Lean Track

This is the first mechanized proof track for CHC.

Current scope:

- CHC-0 node and edge model, finite reachability decidability, `acyclic_unif` decidability, and diagonal rejection.
- CHC-1 effect-summary status model with the conservative non-convergence rule.
- CHC-2 effect-annotation and callback-composition invariants.
- CHC-3 process/session non-interference core rule.
- CHC-4 temporal happens-before feedback core rule.
- CHC-5 probabilistic prediction-feedback core rule, with confidence ignored for classification.
- Boundary skeleton separating structural causal paradox from semantic hard cases.

This is intentionally not a proof that CHC decides arbitrary halting. The `Q_e`
boundary remains stated as an external computability boundary. The Lean track
proves the structural CHC safety invariants, not semantic termination.

Run, when Lean 4 and Lake are installed:

```powershell
lake build
```
