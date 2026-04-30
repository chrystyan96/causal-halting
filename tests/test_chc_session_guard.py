import importlib.util
import json
import sys
import tempfile
import unittest
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

    def test_analyze_design_command_reports_inferred_paradox(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = chc_session_guard.command_result(
                Path(tmp),
                "analyze-design",
                "The current execution changes strategy when a supervisor predicts it will not finish.",
            )

        self.assertEqual(result["mode"], "analyze-design")
        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("classification: causal_paradox", result["analysis_output"])

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


if __name__ == "__main__":
    unittest.main()
