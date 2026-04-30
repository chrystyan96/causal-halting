# Causal Halting Lean Track

This is the first mechanized proof track for CHC.

Current scope:

- CHC-0 node and edge skeleton.
- Direct diagonal feedback graph.
- A checked theorem that the direct diagonal graph has a cycle.
- Boundary skeleton separating structural causal paradox from semantic hard cases.

This is intentionally not a proof that CHC decides arbitrary halting. The `Q_e`
boundary remains stated as an external computability boundary while the core
CHC definitions stabilize.

Run, when Lean 4 and Lake are installed:

```powershell
lake build
```
