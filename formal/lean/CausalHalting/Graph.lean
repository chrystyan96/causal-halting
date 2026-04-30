namespace CausalHalting

inductive Kind where
  | E
  | R
  | P
  | Control
  deriving DecidableEq, BEq, Repr

structure Node where
  kind : Kind
  label : String
  deriving DecidableEq, BEq, Repr

structure Edge where
  source : Node
  target : Node
  deriving DecidableEq, BEq, Repr

def edgeMatches (edge : Edge) (source target : Node) : Bool :=
  edge.source == source && edge.target == target

def finite_reachability (graph : List Edge) (source target : Node) : Bool :=
  graph.any (fun edge => edgeMatches edge source target) ||
  graph.any (fun left =>
    graph.any (fun right =>
      left.source == source && left.target == right.source && right.target == target))

theorem finite_reachability_decidable (graph : List Edge) (source target : Node) :
  Decidable (finite_reachability graph source target = true) := by
  infer_instance

def labelsUnify (left right : Node) : Bool :=
  left.label == right.label

def acyclic_unif (graph : List Edge) : Bool :=
  ! graph.any (fun left =>
    graph.any (fun right =>
      left.source.kind == Kind.E &&
      right.target.kind == Kind.E &&
      left.target == right.source &&
      labelsUnify left.source right.target))

theorem acyclic_unif_decidability (graph : List Edge) :
  Decidable (acyclic_unif graph = true) := by
  infer_instance

end CausalHalting
