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


chc_design_analyze = load_script("chc_design_analyze")
chc_design_schema = load_script("chc_design_schema")
chc_trace_check = load_script("chc_trace_check")
chc_repair = load_script("chc_repair")
chc_workflow_adapter = load_script("chc_workflow_adapter")
chc_verify_repair = load_script("chc_verify_repair")
chc_otel_adapter = load_script("chc_otel_adapter")
chc_langgraph_adapter = load_script("chc_langgraph_adapter")
chc_report = load_script("chc_report")
chc_eval_design_ir = load_script("chc_eval_design_ir")


def design_ir(executions, observations, controls, uncertain=None):
    return {
        "design_ir_version": "1.0",
        "executions": executions,
        "observations": observations,
        "controls": controls,
        "semantic_evidence": [{"source": "test", "claim": "structured fixture"}],
        "uncertain": uncertain or [],
    }


class CausalHaltingDesignTraceRepairTests(unittest.TestCase):
    def test_prose_input_requires_design_ir(self):
        result = chc_design_analyze.analyze_design(
            "The active worker receives an evaluator's forecast and revises its own route."
        )

        self.assertEqual(result["classification"], "needs_design_ir")
        self.assertEqual(result["inferred_graph"], [])

    def test_portuguese_prose_input_requires_design_ir(self):
        result = chc_design_analyze.analyze_design(
            "O agente em execucao recebe uma avaliacao sobre sua propria rodada e muda o plano."
        )

        self.assertEqual(result["classification"], "needs_design_ir")

    def test_spanish_prose_input_requires_design_ir(self):
        result = chc_design_analyze.analyze_design(
            "El proceso activo recibe una evaluacion de esa misma ejecucion y cambia su ruta."
        )

        self.assertEqual(result["classification"], "needs_design_ir")

    def test_design_schema_accepts_valid_design_analysis(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                design_ir(
                    [{"id": "run-1", "program": "AgentRun", "input": "task"}],
                    [{"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}],
                    [
                        {
                            "id": "ctrl-1",
                            "result": "r-1",
                            "target_exec": "run-1",
                            "timing": "during_observed_execution",
                            "action": "change_strategy",
                        }
                    ],
                )
            )
        )

        self.assertEqual(chc_design_schema.validate_design_analysis(result), [])

    def test_design_ir_causal_paradox(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                design_ir(
                    [{"id": "run-1", "program": "AgentRun", "input": "task"}],
                    [{"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}],
                    [
                        {
                            "id": "ctrl-1",
                            "result": "r-1",
                            "target_exec": "run-1",
                            "timing": "during_observed_execution",
                            "action": "change_strategy",
                        }
                    ],
                )
            )
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["design_ir"]["controls"][0]["target_exec"], "run-1")

    def test_non_keyword_design_ir_causal_paradox(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                design_ir(
                    [{"id": "run-1", "program": "Worker", "input": "task"}],
                    [{"id": "obs-1", "observer": "Evaluator", "target_exec": "run-1", "result": "r-1"}],
                    [
                        {
                            "id": "ctrl-1",
                            "result": "r-1",
                            "target_exec": "run-1",
                            "timing": "during_observed_execution",
                            "action": "revise_route",
                        }
                    ],
                )
            )
        )

        self.assertEqual(result["classification"], "causal_paradox")

    def test_design_ir_future_run_is_valid_acyclic(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                design_ir(
                    [
                        {"id": "run-1", "program": "AgentRun", "input": "task"},
                        {"id": "run-2", "program": "AgentRun", "input": "retry"},
                    ],
                    [{"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}],
                    [
                        {
                            "id": "ctrl-1",
                            "result": "r-1",
                            "target_exec": "run-2",
                            "timing": "future_execution",
                            "action": "retry",
                        }
                    ],
                )
            )
        )

        self.assertEqual(result["classification"], "valid_acyclic")

    def test_design_ir_missing_consumer_is_insufficient_info(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                design_ir(
                    [{"id": "run-1", "program": "AgentRun", "input": "task"}],
                    [{"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}],
                    [],
                    [{"field": "controls", "reason": "The consumer of r-1 is not specified."}],
                )
            )
        )

        self.assertEqual(result["classification"], "insufficient_info")

    def test_no_lexical_pattern_constants_remain_in_design_analyzer(self):
        source = (ROOT / "scripts" / "chc_design_analyze.py").read_text(encoding="utf-8")

        self.assertNotIn("OBSERVATION_PATTERNS", source)
        self.assertNotIn("SELF_EXEC_PATTERNS", source)
        self.assertNotIn("CONTROL_PATTERNS", source)
        self.assertNotIn("SAFE_BOUNDARY_PATTERNS", source)
        self.assertNotIn("import re", source)

    def test_trace_same_exec_consume_before_end_is_causal_paradox(self):
        trace = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer_exec_id": "run-1", "purpose": "strategy_change"}),
                json.dumps({"type": "exec_end", "exec_id": "run-1", "status": "halted"}),
            ]
        )

        result = chc_trace_check.analyze_text(trace)

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["feedback_paths"][0]["relation"], "same_execution")
        self.assertTrue(result["feedback_paths"][0]["before_observed_exec_end"])

    def test_trace_future_run_control_is_valid_acyclic(self):
        trace = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "exec_start", "exec_id": "run-2", "program": "AgentRun", "input": "task-a-retry"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer_exec_id": "run-2", "purpose": "schedule_retry"}),
            ]
        )

        result = chc_trace_check.analyze_text(trace)

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertEqual(result["valid_paths"][0]["relation"], "different_execution")

    def test_trace_external_orchestrator_consume_is_valid_acyclic(self):
        trace = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer": "Orchestrator", "purpose": "stop_or_retry"}),
            ]
        )

        result = chc_trace_check.analyze_text(trace)

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertEqual(result["valid_paths"][0]["relation"], "external_controller")

    def test_trace_same_exec_after_end_audit_is_valid_acyclic(self):
        trace = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "exec_end", "exec_id": "run-1", "status": "halted"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer_exec_id": "run-1", "purpose": "audit_only"}),
            ]
        )

        result = chc_trace_check.analyze_text(trace)

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertEqual(result["valid_paths"][0]["relation"], "audit_only")

    def test_generic_workflow_adapter_outputs_trace_events(self):
        workflow = {
            "design_ir_version": "1.0",
            "executions": [{"id": "run-1", "program": "AgentRun", "input": "task"}],
            "observations": [{"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}],
            "controls": [
                {
                    "id": "ctrl-1",
                    "result": "r-1",
                    "target_exec": "run-1",
                    "timing": "during_observed_execution",
                    "purpose": "strategy_change",
                }
            ],
        }

        events = chc_workflow_adapter.workflow_to_events(workflow)
        result = chc_trace_check.analyze_events(events)

        self.assertEqual(result["classification"], "causal_paradox")

    def test_repair_engine_moves_same_run_control_to_orchestrator(self):
        analysis = {
            "classification": "causal_paradox",
            "inferred_graph": [
                "E(AgentRun,input) -> R(AgentRun,input)",
                "R(AgentRun,input) -> E(AgentRun,input)",
            ],
        }

        result = chc_repair.repair_analysis(analysis)

        self.assertEqual(result["repair_status"], "repair_recommended")
        self.assertIn("R(AgentRun,input) -> E(Orchestrator,input)", result["repair_graph"])
        self.assertEqual(
            result["proof_obligations"][0]["obligation"],
            "prediction_result_not_consumed_by_observed_execution",
        )
        self.assertEqual(result["proof_obligations"][0]["valid_if"][0], "consumer is external_orchestrator")

    def test_verify_repair_compares_before_after_traces(self):
        before = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer_exec_id": "run-1", "purpose": "strategy_change"}),
                json.dumps({"type": "exec_end", "exec_id": "run-1", "status": "halted"}),
            ]
        )
        after = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "exec_start", "exec_id": "run-2", "program": "AgentRun", "input": "task-a-retry"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer_exec_id": "run-2", "purpose": "schedule_retry"}),
            ]
        )

        result = chc_verify_repair.verify_repair(before, after)

        self.assertEqual(result["verification"], "passed")

    def test_design_ir_corpus_expected_classifications(self):
        for case_dir in (ROOT / "examples" / "design-ir-corpus").iterdir():
            if not case_dir.is_dir():
                continue
            with self.subTest(case=case_dir.name):
                design = json.loads((case_dir / "expected.design-ir.json").read_text(encoding="utf-8"))
                expected = json.loads((case_dir / "expected.analysis.json").read_text(encoding="utf-8"))

                result = chc_design_analyze.analyze_design(json.dumps(design))

                self.assertEqual(result["classification"], expected["classification"])

    def test_otel_adapter_outputs_trace_events(self):
        payload = json.loads((ROOT / "examples" / "otel-self-prediction.json").read_text(encoding="utf-8"))

        events = chc_otel_adapter.otel_to_events(payload)
        result = chc_trace_check.analyze_events(events)

        self.assertEqual(result["classification"], "causal_paradox")

    def test_langgraph_adapter_outputs_trace_events(self):
        payload = json.loads((ROOT / "examples" / "langgraph-future-run.json").read_text(encoding="utf-8"))

        events = chc_langgraph_adapter.langgraph_to_events(payload)
        result = chc_trace_check.analyze_events(events)

        self.assertEqual(result["classification"], "valid_acyclic")

    def test_verify_repair_fails_specific_obligation_when_wrong_boundary_used(self):
        before = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer_exec_id": "run-1", "purpose": "strategy_change"}),
            ]
        )
        after = "\n".join(
            [
                json.dumps({"type": "exec_start", "exec_id": "run-1", "program": "AgentRun", "input": "task-a"}),
                json.dumps({"type": "observe", "observer": "Supervisor", "target_exec_id": "run-1", "result_id": "r-1"}),
                json.dumps({"type": "consume", "result_id": "r-1", "consumer": "Orchestrator", "purpose": "stop_or_retry"}),
            ]
        )
        obligations = [{"obligation": "future_run_control_only", "result_id": "r-1"}]

        result = chc_verify_repair.verify_repair(before, after, obligations)

        self.assertEqual(result["verification"], "failed")
        self.assertEqual(result["proof_obligations"][0]["status"], "failed")

    def test_report_renders_mermaid_graph(self):
        report = chc_report.render_markdown(
            {
                "classification": "causal_paradox",
                "graph": ["E(AgentRun,task) -> R(AgentRun,task)", "R(AgentRun,task) -> E(AgentRun,task)"],
                "explanation": "Feedback detected.",
            }
        )

        self.assertIn("```mermaid", report)
        self.assertIn("flowchart LR", report)

    def test_eval_design_ir_corpus_passes(self):
        result = chc_eval_design_ir.evaluate_corpus(ROOT / "examples" / "design-ir-corpus")

        self.assertEqual(result["status"], "passed")
        self.assertGreaterEqual(result["case_count"], 3)


if __name__ == "__main__":
    unittest.main()
