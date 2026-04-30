import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chc_session_guard.py"
SPEC = importlib.util.spec_from_file_location("chc_session_guard", SCRIPT)
chc_session_guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["chc_session_guard"] = chc_session_guard
SPEC.loader.exec_module(chc_session_guard)


class CausalHaltingSessionGuardTests(unittest.TestCase):
    def event(self, cwd: str, session_id: str = "session-1", prompt: str = "hello"):
        return {
            "cwd": cwd,
            "session_id": session_id,
            "user_prompt": prompt,
            "hook_event_name": "UserPromptSubmit",
        }

    def test_default_prompt_returns_compact_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = chc_session_guard.handle_event(self.event(tmp))

        self.assertTrue(result["continue"])
        self.assertTrue(result["suppressOutput"])
        self.assertEqual(result["systemMessage"], chc_session_guard.DEFAULT_GUARD)

    def test_enabled_session_returns_strong_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            enable = chc_session_guard.handle_event(
                self.event(tmp, prompt="use causal-halting for this session")
            )
            followup = chc_session_guard.handle_event(self.event(tmp, prompt="unrelated question"))

        self.assertEqual(enable["systemMessage"], chc_session_guard.SESSION_GUARD)
        self.assertEqual(followup["systemMessage"], chc_session_guard.SESSION_GUARD)

    def test_disabled_session_returns_compact_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            chc_session_guard.handle_event(self.event(tmp, prompt="causal-halting session on"))
            result = chc_session_guard.handle_event(self.event(tmp, prompt="causal-halting session off"))
            followup = chc_session_guard.handle_event(self.event(tmp, prompt="unrelated question"))

        self.assertEqual(result["systemMessage"], chc_session_guard.DEFAULT_GUARD)
        self.assertEqual(followup["systemMessage"], chc_session_guard.DEFAULT_GUARD)

    def test_malformed_hook_stdin_returns_nonblocking_json(self):
        result = chc_session_guard.handle_raw_input("not json")

        self.assertTrue(result["continue"])
        self.assertTrue(result["suppressOutput"])
        self.assertEqual(result["systemMessage"], chc_session_guard.DEFAULT_GUARD)

    def test_session_state_is_keyed_by_sanitized_session_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            event = self.event(tmp, session_id="abc/../123", prompt="causal-halting session on")
            chc_session_guard.handle_event(event)
            state_files = list((Path(tmp) / ".codex" / "causal-halting" / "sessions").glob("*.json"))

        self.assertEqual(len(state_files), 1)
        self.assertNotIn("/", state_files[0].name)

    def test_command_mode_enables_workspace_session_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = chc_session_guard.command_result(Path(tmp), "on")
            followup = chc_session_guard.handle_event(self.event(tmp, prompt="unrelated question"))

        self.assertTrue(command["enabled"])
        self.assertEqual(command["scope"], "project")
        self.assertEqual(followup["systemMessage"], chc_session_guard.SESSION_GUARD)

    def test_command_mode_disables_workspace_session_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            chc_session_guard.command_result(Path(tmp), "on")
            command = chc_session_guard.command_result(Path(tmp), "off")
            followup = chc_session_guard.handle_event(self.event(tmp, prompt="unrelated question"))

        self.assertFalse(command["enabled"])
        self.assertEqual(followup["systemMessage"], chc_session_guard.DEFAULT_GUARD)

    def test_empty_command_mode_defaults_to_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            command = chc_session_guard.command_result(Path(tmp), "")

        self.assertEqual(command["mode"], "status")
        self.assertFalse(command["enabled"])

    def test_cli_without_positional_mode_defaults_to_hook_mode(self):
        result = chc_session_guard.handle_raw_input("")

        self.assertEqual(result["systemMessage"], chc_session_guard.DEFAULT_GUARD)

    def test_command_result_status_is_default_for_empty_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = chc_session_guard.command_result(Path(tmp), "status")

        self.assertEqual(result["mode"], "status")
        self.assertFalse(result["enabled"])

    def test_explain_command_returns_guard_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = chc_session_guard.command_result(Path(tmp), "explain")

        self.assertEqual(result["mode"], "explain")
        self.assertIn("Obs/Pred(E)", result["structural_trigger"])
        self.assertIn("Silently check", result["default_guard"])

    def test_check_command_runs_checker_on_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "diagonal.graph"
            path.write_text("E(y,y) -> R(y,y)\nR(y,y) -> E(D,y)\n", encoding="utf-8")
            result = chc_session_guard.command_result(Path(tmp), "check", str(path))

        self.assertEqual(result["mode"], "check")
        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("classification: causal_paradox", result["checker_output"])

    def test_check_command_reports_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = chc_session_guard.command_result(Path(tmp), "check", "missing.graph")

        self.assertEqual(result["mode"], "check")
        self.assertIn("File not found", result["message"])

    def test_analyze_design_command_requires_design_ir_for_prose(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = chc_session_guard.command_result(
                Path(tmp),
                "analyze-design",
                "The current execution changes strategy when a supervisor predicts it will not finish.",
            )

        self.assertEqual(result["mode"], "analyze-design")
        self.assertEqual(result["classification"], "needs_design_ir")
        self.assertIn("classification: needs_design_ir", result["analysis_output"])

    def test_analyze_design_command_accepts_design_ir_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "design-ir.json"
            path.write_text(
                json.dumps(
                    {
                        "design_ir_version": "1.0",
                        "executions": [{"id": "run-1", "program": "AgentRun", "input": "task"}],
                        "observations": [
                            {"id": "obs-1", "observer": "Supervisor", "target_exec": "run-1", "result": "r-1"}
                        ],
                        "controls": [
                            {
                                "id": "ctrl-1",
                                "result": "r-1",
                                "target_exec": "run-1",
                                "timing": "during_observed_execution",
                                "action": "change_strategy",
                            }
                        ],
                        "semantic_evidence": [{"source": "test", "claim": "same run control"}],
                        "uncertain": [],
                    }
                ),
                encoding="utf-8",
            )
            result = chc_session_guard.command_result(Path(tmp), "analyze-design", str(path))

        self.assertEqual(result["mode"], "analyze-design")
        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("classification: causal_paradox", result["analysis_output"])

    def test_cli_analyze_design_text_with_spaces_returns_needs_design_ir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with redirect_stdout(io.StringIO()):
                exit_code = chc_session_guard.main(
                    [
                        "analyze-design",
                        "The",
                        "current",
                        "execution",
                        "changes",
                        "strategy",
                        "when",
                        "a",
                        "supervisor",
                        "predicts",
                        "it",
                        "will",
                        "not",
                        "finish.",
                        "--cwd",
                        tmp,
                        "--format",
                        "json",
                    ]
                )

        self.assertEqual(exit_code, 0)

    def test_analyze_trace_command_reports_feedback_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            path.write_text(
                "\n".join(
                    [
                        '{"type":"exec_start","exec_id":"run-1","program":"AgentRun","input":"task-a"}',
                        '{"type":"observe","observer":"Supervisor","target_exec_id":"run-1","result_id":"r-1"}',
                        '{"type":"control","result_id":"r-1","controlled_exec_id":"run-1","action":"change_strategy"}',
                    ]
                ),
                encoding="utf-8",
            )
            result = chc_session_guard.command_result(Path(tmp), "analyze-trace", str(path))

        self.assertEqual(result["mode"], "analyze-trace")
        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("feedback_paths:", result["analysis_output"])

    def test_repair_command_reports_proof_obligation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "analysis.json"
            path.write_text(
                json.dumps(
                    {
                        "classification": "causal_paradox",
                        "inferred_graph": [
                            "E(AgentRun,input) -> R(AgentRun,input)",
                            "R(AgentRun,input) -> E(AgentRun,input)",
                        ],
                    }
                ),
                encoding="utf-8",
            )
            result = chc_session_guard.command_result(Path(tmp), "repair", str(path))

        self.assertEqual(result["mode"], "repair")
        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("proof_obligations:", result["analysis_output"])

    def test_verify_repair_command_reports_passed(self):
        with tempfile.TemporaryDirectory() as tmp:
            before = Path(tmp) / "before.jsonl"
            after = Path(tmp) / "after.jsonl"
            before.write_text(
                "\n".join(
                    [
                        '{"type":"exec_start","exec_id":"run-1","program":"AgentRun","input":"task-a"}',
                        '{"type":"observe","observer":"Supervisor","target_exec_id":"run-1","result_id":"r-1"}',
                        '{"type":"consume","result_id":"r-1","consumer_exec_id":"run-1","purpose":"strategy_change"}',
                    ]
                ),
                encoding="utf-8",
            )
            after.write_text(
                "\n".join(
                    [
                        '{"type":"exec_start","exec_id":"run-1","program":"AgentRun","input":"task-a"}',
                        '{"type":"exec_start","exec_id":"run-2","program":"AgentRun","input":"task-a-retry"}',
                        '{"type":"observe","observer":"Supervisor","target_exec_id":"run-1","result_id":"r-1"}',
                        '{"type":"consume","result_id":"r-1","consumer_exec_id":"run-2","purpose":"schedule_retry"}',
                    ]
                ),
                encoding="utf-8",
            )
            result = chc_session_guard.command_result(Path(tmp), "verify-repair", f"{before} {after}")

        self.assertEqual(result["mode"], "verify-repair")
        self.assertEqual(result["classification"], "passed")

    def test_adapt_workflow_command_outputs_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = Path(tmp) / "workflow.json"
            workflow.write_text(
                json.dumps(
                    {
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
                ),
                encoding="utf-8",
            )
            result = chc_session_guard.command_result(Path(tmp), "adapt-workflow", str(workflow))

        self.assertEqual(result["mode"], "adapt-workflow")
        self.assertIn('"type": "exec_start"', result["analysis_output"])

    def test_adapt_otel_command_outputs_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "otel.json"
            path.write_text((ROOT / "examples" / "otel-self-prediction.json").read_text(encoding="utf-8"), encoding="utf-8")
            result = chc_session_guard.command_result(Path(tmp), "adapt-otel", str(path))

        self.assertEqual(result["mode"], "adapt-otel")
        self.assertIn('"type": "observe"', result["analysis_output"])

    def test_adapt_langgraph_command_outputs_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "langgraph.json"
            path.write_text((ROOT / "examples" / "langgraph-future-run.json").read_text(encoding="utf-8"), encoding="utf-8")
            result = chc_session_guard.command_result(Path(tmp), "adapt-langgraph", str(path))

        self.assertEqual(result["mode"], "adapt-langgraph")
        self.assertIn('"type": "consume"', result["analysis_output"])

    def test_adapt_temporal_airflow_command_outputs_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "temporal.json"
            path.write_text(
                (ROOT / "examples" / "temporal-airflow-indirect-feedback.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            result = chc_session_guard.command_result(Path(tmp), "adapt-temporal-airflow", str(path))

        self.assertEqual(result["mode"], "adapt-temporal-airflow")
        self.assertIn('"type": "control_exec"', result["analysis_output"])

    def test_report_command_renders_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "analysis.json"
            path.write_text(
                json.dumps({"classification": "valid_acyclic", "graph": ["E(A,x) -> R(A,x)"]}),
                encoding="utf-8",
            )
            result = chc_session_guard.command_result(Path(tmp), "report", str(path))

        self.assertEqual(result["mode"], "report")
        self.assertIn("```mermaid", result["analysis_output"])

    def test_eval_design_ir_command_reports_passed(self):
        result = chc_session_guard.command_result(
            ROOT,
            "eval-design-ir",
            str(ROOT / "examples" / "design-ir-corpus"),
        )

        self.assertEqual(result["mode"], "eval-design-ir")
        self.assertEqual(result["classification"], "passed")
        self.assertIn("status: passed", result["analysis_output"])


if __name__ == "__main__":
    unittest.main()
