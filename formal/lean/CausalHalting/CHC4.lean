import CausalHalting.Graph

namespace CausalHalting

structure TemporalFlow where
  sameExecution : Bool
  consumeBeforeEnd : Bool
  auditOnly : Bool

def happens_before_feedback_rejection (flow : TemporalFlow) : Bool :=
  !(flow.sameExecution && flow.consumeBeforeEnd && !flow.auditOnly)

theorem temporal_pre_end_feedback_rejected :
  happens_before_feedback_rejection { sameExecution := true, consumeBeforeEnd := true, auditOnly := false } = false := by
  native_decide

theorem temporal_post_end_audit_allowed :
  happens_before_feedback_rejection { sameExecution := true, consumeBeforeEnd := false, auditOnly := true } = true := by
  native_decide

end CausalHalting
