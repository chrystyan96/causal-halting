import CausalHalting.Graph

namespace CausalHalting

structure PredictionFlow where
  predictsExec : String
  controlsExec : String
  duringExecution : Bool
  boundedLocalMetric : Bool
  confidence : Nat

def prediction_confidence_ignored_for_feedback_classification (flow : PredictionFlow) : Bool :=
  !(flow.predictsExec == flow.controlsExec && flow.duringExecution && !flow.boundedLocalMetric)

theorem probabilistic_self_feedback_rejected_low_confidence :
  prediction_confidence_ignored_for_feedback_classification
    { predictsExec := "run-1", controlsExec := "run-1", duringExecution := true, boundedLocalMetric := false, confidence := 51 } = false := by
  native_decide

theorem probabilistic_self_feedback_rejected_high_confidence :
  prediction_confidence_ignored_for_feedback_classification
    { predictsExec := "run-1", controlsExec := "run-1", duringExecution := true, boundedLocalMetric := false, confidence := 99 } = false := by
  native_decide

end CausalHalting
