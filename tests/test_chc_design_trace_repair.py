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


class CausalHaltingDesignTraceRepairTests(unittest.TestCase):
    def test_text_design_current_run_self_prediction_is_causal_paradox(self):
        result = chc_design_analyze.analyze_design(
            "The agent asks a supervisor whether the current execution will finish. "
            "If the supervisor says no, the same execution changes strategy."
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("R(AgentRun,input) -> E(AgentRun,input)", result["inferred_graph"])
        self.assertTrue(result["repair"])

    def test_portuguese_current_execution_text_is_detected(self):
        result = chc_design_analyze.analyze_design(
            "Meu sistema muda de estrategia quando descobre que sua execução atual nao vai concluir."
        )

        self.assertEqual(result["classification"], "causal_paradox")

    def test_text_design_post_run_supervisor_audit_is_valid_acyclic(self):
        result = chc_design_analyze.analyze_design(
            "A supervisor monitors worker logs after completion and schedules the next run."
        )

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertIn("R(AgentRun,input) -> E(NextAgentRun,input)", result["inferred_graph"])

    def test_ambiguous_design_returns_insufficient_info(self):
        result = chc_design_analyze.analyze_design(
            "A supervisor predicts whether the worker will finish and uses the result."
        )

        self.assertEqual(result["classification"], "insufficient_info")
        self.assertTrue(result["uncertain_edges"])

    def test_design_schema_accepts_valid_design_analysis(self):
        result = chc_design_analyze.analyze_design(
            "The current run changes strategy when a monitor predicts it will not complete."
        )

        self.assertEqual(chc_design_schema.validate_design_analysis(result), [])

    def test_design_ir_causal_paradox(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                {
                    "executions": [{"id": "run-1", "program": "AgentRun", "input": "task"}],
                    "observations": [
                        {"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}
                    ],
                    "controls": [{"result": "r-1", "target_exec": "run-1", "action": "change_strategy"}],
                    "uncertain": [],
                }
            )
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["design_ir"]["controls"][0]["target_exec"], "run-1")

    def test_design_ir_future_run_is_valid_acyclic(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                {
                    "executions": [
                        {"id": "run-1", "program": "AgentRun", "input": "task"},
                        {"id": "run-2", "program": "AgentRun", "input": "retry"},
                    ],
                    "observations": [
                        {"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}
                    ],
                    "controls": [{"result": "r-1", "target_exec": "run-2", "action": "retry"}],
                    "uncertain": [],
                }
            )
        )

        self.assertEqual(result["classification"], "valid_acyclic")

    def test_design_ir_missing_consumer_is_insufficient_info(self):
        result = chc_design_analyze.analyze_design(
            json.dumps(
                {
                    "executions": [{"id": "run-1", "program": "AgentRun", "input": "task"}],
                    "observations": [
                        {"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}
                    ],
                    "controls": [{"result": "r-1", "action": "use_result"}],
                    "uncertain": [],
                }
            )
        )

        self.assertEqual(result["classification"], "insufficient_info")

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
            "executions": [{"id": "run-1", "program": "AgentRun", "input": "task"}],
            "observations": [{"observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}],
            "controls": [{"result": "r-1", "target_exec": "run-1", "purpose": "strategy_change"}],
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


if __name__ == "__main__":
    unittest.main()
