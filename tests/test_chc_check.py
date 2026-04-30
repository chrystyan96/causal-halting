import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "chc_check.py"
SPEC = importlib.util.spec_from_file_location("chc_check", SCRIPT)
chc_check = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["chc_check"] = chc_check
SPEC.loader.exec_module(chc_check)


class CausalHaltingCheckerTests(unittest.TestCase):
    def test_diagonal_mini_chc_is_causal_paradox(self):
        result = chc_check.analyze_text(
            "D(y) = if H(y,y) then loop else halt\nrun D(D)\n"
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["unifier"], {})
        self.assertIn("E(D,D) -> R(D,D)", result["graph"])
        self.assertIn("R(D,D) -> E(D,D)", result["graph"])

    def test_diagonal_graph_dsl_is_causal_paradox(self):
        result = chc_check.analyze_text(
            "E(y,y) -> R(y,y)\nR(y,y) -> E(D,y)\n", mode="graph"
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["unifier"], {"y": "D"})

    def test_h_free_qe_is_valid_acyclic_and_unproved(self):
        result = chc_check.analyze_text(
            "Q_e() = simulate e(e); if e(e) halts then halt else diverge\nrun Q_e()\n"
        )

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertEqual(result["semantic_status"], "unproved")
        self.assertEqual(result["graph"], [])

    def test_safe_supervisor_graph_is_valid_acyclic(self):
        result = chc_check.analyze_text(
            "E(TaskA,input) -> R(TaskA,input)\n"
            "R(TaskA,input) -> E(Supervisor,input)\n",
            mode="graph",
        )

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertIsNone(result["unifier"])
        self.assertEqual(len(result["reachable_e_pairs"]), 1)

    def test_malformed_input_is_parse_error(self):
        result = chc_check.analyze_text("this is not valid")

        self.assertEqual(result["classification"], "parse_error")
        self.assertIn("Unsupported", result["explanation"])

    def test_unifier_detects_symbolic_feedback_path(self):
        source = chc_check.parse_node("E(y,y)")
        target = chc_check.parse_node("E(D,y)")

        unifier = chc_check.unify_node_labels(source, target)

        self.assertEqual(chc_check.subst_to_json(unifier), {"y": "D"})


if __name__ == "__main__":
    unittest.main()
