import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    script = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


chc_check = load_script("chc_check")
chc_trace_check = load_script("chc_trace_check")
chc_process_check = load_script("chc_process_check")
chc_temporal_check = load_script("chc_temporal_check")
chc_prediction_check = load_script("chc_prediction_check")
chc_report = load_script("chc_report")
chc_identity_check = load_script("chc_identity_check")
chc_theory_coverage = load_script("chc_theory_coverage")


class CausalHaltingV31Tests(unittest.TestCase):
    def assert_scoped(self, result):
        self.assertEqual(result["validity_scope"], "no_modeled_prediction_feedback_only")
        self.assertIn("identity_resolution", result)
        self.assertIn("formal_status", result)
        self.assertIn("theorem_coverage", result)

    def test_chc012_outputs_scope_and_formal_metadata(self):
        result = chc_check.analyze_text("D(y) = if H(y,y) then loop else halt\nrun D(D)\n")

        self.assertEqual(result["classification"], "causal_paradox")
        self.assert_scoped(result)

    def test_chc3_multihop_process_feedback_is_rejected(self):
        payload = {
            "processes": [{"id": "worker", "role": "worker"}, {"id": "sup", "role": "monitor_controller"}],
            "sessions": [{"id": "s-1"}],
            "channels": [{"id": "observe"}, {"id": "control"}],
            "executions": [
                {"id": "run-1", "process_id": "worker", "session_id": "s-1", "program": "AgentRun", "input": "task"}
            ],
            "observations": [{"id": "obs-1", "observer_process_id": "sup", "target_exec": "run-1", "result": "r-1"}],
            "controls": [
                {
                    "id": "ctrl-1",
                    "result": "r-1",
                    "target_exec": "run-1",
                    "timing": "during_observed_execution",
                    "channel_id": "control",
                    "route": ["Channel(observe)", "Process(sup)", "Channel(control)"],
                    "action": "change_strategy",
                }
            ],
        }

        result = chc_process_check.analyze_process_ir(payload)

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("Channel(control)", result["feedback_paths"][0]["path"])
        self.assert_scoped(result)

    def test_chc3_ambiguous_identity_is_insufficient_info(self):
        payload = json.loads((ROOT / "examples" / "process-future-run.process-ir.json").read_text(encoding="utf-8"))
        payload["controls"][0]["channel_id"] = "missing-channel"

        result = chc_process_check.analyze_process_ir(payload)

        self.assertEqual(result["classification"], "insufficient_info")
        self.assertTrue(result["identity_resolution"]["missing"])

    def test_chc4_happens_before_closure_is_reported(self):
        trace = "\n".join(
            [
                json.dumps({"id": "a", "type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task", "happens_before": ["b"]}),
                json.dumps({"id": "b", "type": "observe", "observer": "Sup", "target_exec_id": "run-1", "result_id": "r-1", "happens_before": ["c"]}),
                json.dumps({"id": "c", "type": "consume", "result_id": "r-1", "consumer_exec_id": "run-1", "purpose": "change_strategy", "execution_identity_relation": "same"}),
                json.dumps({"id": "d", "type": "exec_end", "exec_id": "run-1"}),
            ]
        )

        result = chc_temporal_check.analyze_temporal_text(trace)

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["temporal_order_status"], "complete")
        self.assertIn({"source": "a", "target": "c"}, result["happens_before_path"])
        self.assert_scoped(result)

    def test_chc4_missing_temporal_order_does_not_accept_valid(self):
        trace = (ROOT / "examples" / "future-run.trace.jsonl").read_text(encoding="utf-8")

        result = chc_temporal_check.analyze_temporal_text(trace)

        self.assertEqual(result["classification"], "insufficient_info")

    def test_chc4_mixed_logical_clock_values_do_not_crash(self):
        trace = "\n".join(
            [
                json.dumps({"id": "a", "type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task", "trace_id": "t", "logical_clock": 1}),
                json.dumps({"id": "b", "type": "observe", "observer": "Sup", "target_exec_id": "run-1", "result_id": "r-1", "trace_id": "t", "logical_clock": "2"}),
                json.dumps({"id": "c", "type": "consume", "result_id": "r-1", "consumer_exec_id": "run-1", "purpose": "change_strategy", "execution_identity_relation": "same", "trace_id": "t", "logical_clock": 10}),
                json.dumps({"id": "d", "type": "exec_end", "exec_id": "run-1", "trace_id": "t", "logical_clock": "11"}),
            ]
        )

        result = chc_temporal_check.analyze_temporal_text(trace)

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn({"source": "a", "target": "b"}, result["happens_before_path"])

    def test_chc4_numeric_timestamp_order_is_temporal_not_lexicographic(self):
        trace = "\n".join(
            [
                json.dumps({"id": "late", "type": "exec_end", "exec_id": "run-1", "timestamp": "10"}),
                json.dumps({"id": "early", "type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task", "timestamp": 2}),
            ]
        )

        result = chc_temporal_check.analyze_temporal_text(trace)

        self.assertIn({"source": "early", "target": "late"}, result["happens_before_path"])
        self.assertNotIn({"source": "late", "target": "early"}, result["happens_before_path"])

    def test_chc5_bounded_local_metric_is_valid_when_scope_is_local(self):
        payload = {
            "executions": [{"id": "run-1", "program": "AgentRun", "input": "task"}],
            "predictions": [
                {
                    "result_id": "metric-1",
                    "kind": "bounded_progress_metric",
                    "target_exec": "run-1",
                    "prediction_scope": "local_progress_metric",
                    "confidence": 1.0,
                    "semantics": "metric",
                }
            ],
            "controls": [
                {
                    "id": "ctrl-1",
                    "result_id": "metric-1",
                    "target_exec": "run-1",
                    "timing": "during_observed_execution",
                    "action": "continue_step",
                }
            ],
        }

        result = chc_prediction_check.analyze_prediction_ir(payload)

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertFalse(result["prediction_confidence_used_for_classification"])
        self.assert_scoped(result)

    def test_chc5_missing_prediction_scope_is_insufficient_for_future_control(self):
        payload = json.loads((ROOT / "examples" / "prediction-future-risk.prediction-ir.json").read_text(encoding="utf-8"))
        del payload["predictions"][0]["prediction_scope"]

        result = chc_prediction_check.analyze_prediction_ir(payload)

        self.assertEqual(result["classification"], "insufficient_info")

    def test_valid_acyclic_report_must_scope_claim(self):
        report = chc_report.render_markdown(
            {
                "classification": "valid_acyclic",
                "graph": [],
                "validity_scope": "no_modeled_prediction_feedback_only",
                "identity_resolution": {"resolved": [], "ambiguous": [], "missing": [], "conflicts": [], "assumptions": []},
                "explanation": "No modeled feedback.",
            }
        )

        self.assertIn("no_modeled_prediction_feedback_only", report)
        self.assertIn("does not prove termination", report)
        self.assertIn("does not solve classical halting", report)

    def test_identity_check_rejects_valid_with_missing_identity(self):
        errors = chc_identity_check.validate_identity_resolution(
            {
                "classification": "valid_acyclic",
                "identity_resolution": {
                    "resolved": [],
                    "ambiguous": [],
                    "missing": [{"field": "exec_id"}],
                    "conflicts": [],
                    "assumptions": [],
                },
            }
        )

        self.assertTrue(errors)

    def test_theory_coverage_reports_all_levels(self):
        result = chc_theory_coverage.coverage()

        for level in ("CHC-0", "CHC-1", "CHC-2", "CHC-3", "CHC-4", "CHC-5"):
            self.assertIn(level, result["levels"])


if __name__ == "__main__":
    unittest.main()
