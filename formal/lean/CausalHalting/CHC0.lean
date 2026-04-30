import CausalHalting.Graph

namespace CausalHalting

def diagonalExec : Node := { kind := Kind.E, label := "D,D" }
def diagonalResult : Node := { kind := Kind.R, label := "D,D" }

def diagonalGraph : List Edge :=
  [
    { source := diagonalExec, target := diagonalResult },
    { source := diagonalResult, target := diagonalExec }
  ]

def hasDirectFeedback (graph : List Edge) : Bool :=
  graph.any (fun left =>
    graph.any (fun right =>
      left.source.kind == Kind.E &&
      right.target.kind == Kind.E &&
      left.target == right.source &&
      left.source == right.target))

theorem diagonal_rejection :
  hasDirectFeedback diagonalGraph = true := by
  native_decide

theorem diagonal_rejected_by_acyclic_unif :
  acyclic_unif diagonalGraph = false := by
  native_decide

end CausalHalting
