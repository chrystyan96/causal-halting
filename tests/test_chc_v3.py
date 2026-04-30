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
chc_design_analyze = load_script("chc_design_analyze")
chc_design_schema = load_script("chc_design_schema")
chc_trace_check = load_script("chc_trace_check")
chc_certificate = load_script("chc_certificate")
chc_process_check = load_script("chc_process_check")
chc_temporal_check = load_script("chc_temporal_check")
chc_prediction_check = load_script("chc_prediction_check")
chc_eval_suite = load_script("chc_eval_suite")
sync_skill_package = load_script("sync_skill_package")


class CausalHaltingV3Tests(unittest.TestCase):
    def test_checker_outputs_boundary_and_profile(self):
        result = chc_check.analyze_text("D(y) = if H(y,y) then loop else halt\nrun D(D)\n")

        self.assertTrue(result["capability_boundary"]["does_not_solve_classical_halting"])
        self.assertEqual(result["analysis_profile"], "complete_for_chc0")

    def test_chc1_outputs_effect_summary_details(self):
        result = chc_check.analyze_text("Rec(y) = Rec(y)\nrun Rec(Task)\n")

        self.assertEqual(result["chc_level"], "CHC-1")
        self.assertIn(result["fixed_point_status"], {"converged_exact", "not_needed"})
        self.assertIn("Rec", result["effect_summary_details"])
        self.assertIn("summary_id", result["effect_summary_details"]["Rec"])

    def test_chc2_missing_annotation_has_diagnostic(self):
        result = chc_check.analyze_text("Cb(x) = halt\nApply(cb,x) = cb(x)\nrun Apply(Cb,Task)\n")

        self.assertEqual(result["classification"], "insufficient_info")
        self.assertEqual(result["effect_composition_status"], "incomplete")
        self.assertTrue(result["capability_boundary"]["does_not_prove_arbitrary_termination"])

    def test_design_ir_rejects_llm_supplied_classification(self):
        design = {
            "design_ir_version": "1.0",
            "classification": "valid_acyclic",
            "executions": [{"id": "run-1", "program": "AgentRun", "input": "task"}],
            "observations": [{"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}],
            "controls": [],
            "semantic_evidence": [],
            "uncertain": [],
        }

        result = chc_design_analyze.analyze_design(json.dumps(design))

        self.assertEqual(result["classification"], "parse_error")
        self.assertIn("classification is script-owned", result["explanation"])

    def test_design_schema_validates_design_ir(self):
        design = json.loads((ROOT / "examples" / "self-prediction.design-ir.json").read_text(encoding="utf-8"))

        self.assertEqual(chc_design_schema.validate_design_ir(design), [])

    def test_trace_identity_unknown_is_insufficient_info(self):
        trace = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task"}),
                json.dumps({"type": "exec_start", "exec_id": "run-2", "program": "AgentRun", "input": "retry"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer_exec_id": "run-2", "purpose": "retry", "execution_identity_relation": "unknown"}),
            ]
        )

        result = chc_trace_check.analyze_text(trace)

        self.assertEqual(result["classification"], "insufficient_info")

    def test_certificate_result(self):
        before = (ROOT / "examples" / "self-prediction.trace.jsonl").read_text(encoding="utf-8")
        after = (ROOT / "examples" / "future-run.trace.jsonl").read_text(encoding="utf-8")
        verifier = load_script("chc_verify_repair")
        verification = verifier.verify_repair(before, after)

        certificate = chc_certificate.certificate_from_verification(verification)

        self.assertEqual(certificate["claim"], "prediction_feedback_removed")
        self.assertEqual(certificate["result"], "passed")

    def test_chc3_process_self_feedback(self):
        payload = json.loads((ROOT / "examples" / "process-self-feedback.process-ir.json").read_text(encoding="utf-8"))

        result = chc_process_check.analyze_process_ir(payload)

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["chc_level"], "CHC-3")

    def test_chc4_temporal_trace(self):
        result = chc_temporal_check.analyze_temporal_text(
            (ROOT / "examples" / "temporal-self-feedback.trace.jsonl").read_text(encoding="utf-8")
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["chc_level"], "CHC-4")

    def test_chc5_prediction_result(self):
        payload = json.loads((ROOT / "examples" / "prediction-self-risk.prediction-ir.json").read_text(encoding="utf-8"))

        result = chc_prediction_check.analyze_prediction_ir(payload)

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertFalse(result["prediction_confidence_used_for_classification"])

    def test_eval_suite_requires_50_cases(self):
        result = chc_eval_suite.evaluate_suite(ROOT / "examples" / "design-ir-corpus")

        self.assertEqual(result["status"], "passed")
        self.assertGreaterEqual(result["case_count"], 50)
        self.assertFalse(result["coverage"]["natural_language_parsed_by_scripts"])

    def test_sync_skill_package_status_can_check_portable_skill(self):
        result = sync_skill_package.status([ROOT / "skills" / "causal-halting"])

        self.assertEqual(result["targets"][0]["mismatches"], [])

    def test_report_wording_does_not_overclaim(self):
        report = load_script("chc_report").render_markdown(
            {"classification": "valid_acyclic", "graph": [], "explanation": "No modeled feedback."}
        )

        self.assertIn("does not solve classical halting", report)
        self.assertNotIn("proves termination", report.lower())


if __name__ == "__main__":
    unittest.main()
