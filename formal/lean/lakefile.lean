import Lake
open Lake DSL

package «causal-halting» where
  version := v!"3.0.0"

lean_lib CausalHalting where
  roots := #[`CausalHalting]
