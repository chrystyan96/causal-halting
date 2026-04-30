import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "causal_halting.cli", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


class V4CliTests(unittest.TestCase):
    def test_version_and_check_json(self):
        version = run_cli("version")
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("4.0.0", version.stdout)

        result = run_cli("check", "examples/diagonal.graph", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["classification"], "causal_paradox")
        self.assertEqual(payload["validity_scope"], "no_modeled_prediction_feedback_only")

    def test_demo_writes_expected_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            result = run_cli("demo", "--output", temp, "--format", "json")
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary["status"], "passed")
            for name in (
                "analysis.json",
                "repair.json",
                "verification.json",
                "certificate.json",
                "report.md",
            ):
                self.assertTrue((Path(temp) / name).is_file(), name)

    def test_eval_v4_corpus_passes(self):
        result = run_cli("eval", "evals/v4", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["case_count"], 100)
        self.assertEqual(payload["metrics"]["classification_accuracy"], 1.0)

    def test_explain_like_human_keeps_scope_warning(self):
        result = run_cli("trace", "examples/future-run.trace.jsonl", "--explain-like-human")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no modeled prediction-feedback cycle", result.stdout)
        self.assertIn("does not prove termination", result.stdout)

    def test_not_a_problem_examples_are_valid_acyclic(self):
        for path in sorted((ROOT / "examples" / "not-a-problem").glob("*.design-ir.json")):
            result = run_cli("design", str(path), "--format", "json")
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["classification"], "valid_acyclic", path.name)
            self.assertEqual(payload["validity_scope"], "no_modeled_prediction_feedback_only")

    def test_report_wording_does_not_overclaim(self):
        analysis = ROOT / "examples" / "demo" / "expected.analysis.json"
        result = run_cli("report", str(analysis), "--format", "markdown")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = result.stdout.lower()
        self.assertIn("does not solve classical halting", report)
        self.assertIn("does not prove termination", report)
        self.assertNotIn("valid_acyclic means safe", report)
        self.assertNotIn("valid_acyclic proves", report)


if __name__ == "__main__":
    unittest.main()
