import CausalHalting.Graph
import CausalHalting.CHC0
import CausalHalting.CHC1
import CausalHalting.CHC2
import CausalHalting.CHC3
import CausalHalting.CHC4
import CausalHalting.CHC5

namespace CausalHalting

structure Boundary where
  causalParadoxStable : Prop
  unprovedMayShrink : Prop

axiom qe_boundary :
  Exists (fun _semanticHardCase : String => True)

theorem boundary_theorem_skeleton :
  (Boundary.mk True True).causalParadoxStable := by
  simp

end CausalHalting
