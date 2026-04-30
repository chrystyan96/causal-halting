import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "causal-halting"


class PortableSkillPackageTests(unittest.TestCase):
    def test_required_portable_files_are_present(self):
        required_paths = [
            "SKILL.md",
            "README.md",
            "LICENSE.txt",
            "agents/openai.yaml",
            "references/causal-halting-calculus.md",
            "references/chc-1-2-operational.md",
            "references/design-ir-extraction.md",
            "scripts/chc_check.py",
            "scripts/chc_design_analyze.py",
            "scripts/chc_design_schema.py",
            "scripts/chc_trace_check.py",
            "scripts/chc_repair.py",
            "scripts/chc_workflow_adapter.py",
            "scripts/chc_verify_repair.py",
            "scripts/chc_otel_adapter.py",
            "scripts/chc_langgraph_adapter.py",
            "scripts/chc_temporal_airflow_adapter.py",
            "scripts/chc_report.py",
            "scripts/chc_eval_design_ir.py",
            "scripts/chc_eval_suite.py",
            "scripts/chc_certificate.py",
            "scripts/chc_process_check.py",
            "scripts/chc_temporal_check.py",
            "scripts/chc_prediction_check.py",
            "scripts/sync_skill_package.py",
            "examples/diagonal.chc",
            "examples/diagonal.graph",
            "examples/chc1-recursive-feedback.chc",
            "examples/chc2-higher-order-safe.chc",
            "examples/qe-valid-acyclic.chc",
            "examples/safe-supervisor.graph",
            "examples/self-prediction.trace.jsonl",
            "examples/future-run.trace.jsonl",
            "examples/generic-workflow.json",
            "examples/post-end-audit.trace.jsonl",
            "examples/self-prediction.design-ir.json",
            "examples/self-prediction.analysis.json",
            "examples/otel-self-prediction.json",
            "examples/langgraph-future-run.json",
            "examples/temporal-airflow-indirect-feedback.json",
            "examples/process-self-feedback.process-ir.json",
            "examples/temporal-self-feedback.trace.jsonl",
            "examples/prediction-self-risk.prediction-ir.json",
            "references/chc-3-4-5-operational.md",
            "schemas/design-ir.schema.json",
            "schemas/effect-summary.schema.json",
            "schemas/process-ir.schema.json",
            "schemas/temporal-trace.schema.json",
            "schemas/prediction-result.schema.json",
            "schemas/repair-certificate.schema.json",
            "examples/design-ir-corpus/current-run-self-feedback/expected.design-ir.json",
            "examples/design-ir-corpus/portuguese-external-orchestrator/expected.design-ir.json",
            "examples/design-ir-corpus/spanish-ambiguous-consumer/expected.design-ir.json",
        ]

        missing = [path for path in required_paths if not (SKILL_ROOT / path).is_file()]

        self.assertEqual([], missing)

    def test_portable_checker_matches_repository_checker(self):
        for script_name in (
            "chc_check.py",
            "chc_design_analyze.py",
            "chc_design_schema.py",
            "chc_trace_check.py",
            "chc_repair.py",
            "chc_workflow_adapter.py",
            "chc_verify_repair.py",
            "chc_otel_adapter.py",
            "chc_langgraph_adapter.py",
            "chc_temporal_airflow_adapter.py",
            "chc_report.py",
            "chc_eval_design_ir.py",
            "chc_eval_suite.py",
            "chc_certificate.py",
            "chc_process_check.py",
            "chc_temporal_check.py",
            "chc_prediction_check.py",
            "sync_skill_package.py",
        ):
            root_checker = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
            skill_checker = (SKILL_ROOT / "scripts" / script_name).read_text(encoding="utf-8")

            self.assertEqual(root_checker, skill_checker)

    def test_portable_checker_detects_diagonal_paradox(self):
        result = self.run_skill_checker("examples/diagonal.graph")

        self.assertEqual("causal_paradox", result["classification"])
        self.assertEqual({"y": "D"}, result["unifier"])

    def test_portable_checker_preserves_unproved_semantic_status(self):
        result = self.run_skill_checker("examples/qe-valid-acyclic.chc")

        self.assertEqual("valid_acyclic", result["classification"])
        self.assertEqual("unproved", result["semantic_status"])

    def test_sync_tool_runs_from_isolated_skill_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            isolated = Path(tmp) / "causal-halting"
            shutil.copytree(SKILL_ROOT, isolated)

            completed = subprocess.run(
                [
                    sys.executable,
                    str(isolated / "scripts" / "sync_skill_package.py"),
                    "--check",
                    "--format",
                    "json",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            result = json.loads(completed.stdout)
            self.assertEqual("unknown", result["plugin_version"])
            self.assertTrue(Path(result["portable_skill"]).samefile(isolated))
            self.assertEqual([], result["targets"][0]["mismatches"])

    def run_skill_checker(self, relative_input):
        completed = subprocess.run(
            [
                sys.executable,
                str(SKILL_ROOT / "scripts" / "chc_check.py"),
                "--format",
                "json",
                str(SKILL_ROOT / relative_input),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(completed.stdout)


if __name__ == "__main__":
    unittest.main()
