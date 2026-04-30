import Lake
open Lake DSL

package causal_halting where
  version := v!"3.1.0"

lean_lib CausalHalting where
  roots := #[`CausalHalting]
