import CausalHalting.Graph

namespace CausalHalting

inductive SummaryStatus where
  | convergedExact
  | convergedConservative
  | notConverged
  deriving DecidableEq, Repr

def summaryAccepted (status : SummaryStatus) : Bool :=
  match status with
  | SummaryStatus.convergedExact => true
  | SummaryStatus.convergedConservative => true
  | SummaryStatus.notConverged => false

def monotone_effect_summaries (old new universe : List Edge) : Prop :=
  old.all (fun edge => new.contains edge) = true ∧
  new.all (fun edge => universe.contains edge) = true

theorem non_convergence_is_insufficient_info :
  summaryAccepted SummaryStatus.notConverged = false := by
  rfl

theorem converged_summary_can_be_accepted :
  summaryAccepted SummaryStatus.convergedExact = true := by
  rfl

end CausalHalting
