import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "evaluate_responses.py"
SPEC = importlib.util.spec_from_file_location("evaluate_responses", SCRIPT)
evaluate_responses = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["evaluate_responses"] = evaluate_responses
SPEC.loader.exec_module(evaluate_responses)


class EvaluationHarnessTests(unittest.TestCase):
    def test_sample_eval_shows_guarded_improvement(self):
        result = evaluate_responses.evaluate(
            ROOT / "evals" / "prompts.jsonl",
            ROOT / "evals" / "baseline-responses.jsonl",
            ROOT / "evals" / "guarded-responses.jsonl",
        )

        metrics = result["metrics"]
        self.assertEqual(result["case_count"], 10)
        self.assertGreater(
            metrics["guarded_answer_usefulness"],
            metrics["baseline_answer_usefulness"],
        )
        self.assertGreaterEqual(metrics["guarded_boundary_accuracy"], 0.8)
        self.assertEqual(metrics["guarded_overclaim_rate"], 0.0)

    def test_overclaim_detection(self):
        self.assertTrue(evaluate_responses.has_overclaim("This solves the Halting Problem."))
        self.assertFalse(evaluate_responses.has_overclaim("This does not solve the Halting Problem."))

    def test_token_counter_is_stable(self):
        self.assertEqual(evaluate_responses.approx_tokens("a b\nc"), 3)


if __name__ == "__main__":
    unittest.main()
