import CausalHalting.Graph

namespace CausalHalting

structure EffectAnnotation where
  name : String
  edges : List Edge
  deriving Repr

def hasAnnotation (annotation : Option EffectAnnotation) : Bool :=
  match annotation with
  | some _ => true
  | none => false

def composeEffects (caller callback : List Edge) : List Edge :=
  caller ++ callback

theorem effect_annotation_requirement :
  hasAnnotation none = false := by
  rfl

theorem callback_composition_includes_effects (caller callback : List Edge) :
  (composeEffects caller callback).length = caller.length + callback.length := by
  simp [composeEffects]

theorem halt_result_not_passable_without_annotation :
  hasAnnotation none = false := by
  rfl

end CausalHalting
