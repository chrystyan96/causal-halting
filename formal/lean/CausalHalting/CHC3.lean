import CausalHalting.Graph

namespace CausalHalting

structure ProcessFlow where
  observedExec : String
  controlledExec : String
  beforeEnd : Bool

def process_session_non_interference (flow : ProcessFlow) : Bool :=
  !(flow.observedExec == flow.controlledExec && flow.beforeEnd)

theorem process_feedback_rejected :
  process_session_non_interference { observedExec := "run-1", controlledExec := "run-1", beforeEnd := true } = false := by
  native_decide

theorem future_process_control_allowed :
  process_session_non_interference { observedExec := "run-1", controlledExec := "run-2", beforeEnd := true } = true := by
  native_decide

end CausalHalting
