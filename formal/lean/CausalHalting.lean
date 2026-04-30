namespace CausalHalting

inductive Kind where
  | E
  | R
  deriving DecidableEq, Repr

structure Node where
  kind : Kind
  program : String
  input : String
  deriving DecidableEq, Repr

structure Edge where
  source : Node
  target : Node
  deriving DecidableEq, Repr

def diagonalExec : Node := { kind := Kind.E, program := "D", input := "D" }
def diagonalResult : Node := { kind := Kind.R, program := "D", input := "D" }

def diagonalGraph : List Edge :=
  [
    { source := diagonalExec, target := diagonalResult },
    { source := diagonalResult, target := diagonalExec }
  ]

def hasDirectCycle (graph : List Edge) : Bool :=
  graph.any (fun e1 =>
    graph.any (fun e2 =>
      e1.source.kind = Kind.E &&
      e2.target.kind = Kind.E &&
      e1.target = e2.source &&
      e1.source = e2.target))

theorem diagonal_rejected : hasDirectCycle diagonalGraph = true := by
  native_decide

structure Boundary where
  causalParadoxStable : Prop
  unprovedMayShrink : Prop

axiom qe_boundary :
  ∃ (_semanticHardCase : String), True

theorem boundary_skeleton :
  (Boundary.mk True True).causalParadoxStable := by
  simp

end CausalHalting
