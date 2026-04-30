import json
import subprocess
import sys
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
            "scripts/chc_check.py",
            "scripts/chc_design_analyze.py",
            "scripts/chc_design_schema.py",
            "scripts/chc_trace_check.py",
            "scripts/chc_repair.py",
            "examples/diagonal.chc",
            "examples/diagonal.graph",
            "examples/qe-valid-acyclic.chc",
            "examples/safe-supervisor.graph",
            "examples/self-prediction.trace.jsonl",
            "examples/future-run.trace.jsonl",
            "examples/self-prediction.analysis.json",
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
