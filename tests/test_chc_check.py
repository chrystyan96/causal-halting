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

    def test_chc0_let_without_branch_does_not_create_feedback(self):
        result = chc_check.analyze_text(
            "Ignore(y) = let r = H(y,y) in halt\nrun Ignore(D)\n"
        )

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertIn("E(D,D) -> R(D,D)", result["graph"])

    def test_chc0_data_branch_adds_no_causal_edge(self):
        result = chc_check.analyze_text(
            "B(flag) = if flag then halt else loop\nrun B(True)\n"
        )

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertEqual(result["graph"], [])

    def test_chc0_l0_call_rejects_halt_result_argument(self):
        result = chc_check.analyze_text(
            "l0 Sink\nBad(y) = let r = H(y,y) in Sink(r)\nrun Bad(D)\n"
        )

        self.assertEqual(result["classification"], "parse_error")
        self.assertIn("HaltResult cannot be passed", result["explanation"])

    def test_chc0_chc_call_rejects_halt_result_argument(self):
        result = chc_check.analyze_text(
            "Sink(x) = halt\nBad(y) = let r = H(y,y) in Sink(r)\nrun Bad(D)\n"
        )

        self.assertEqual(result["classification"], "parse_error")
        self.assertIn("HaltResult cannot be passed", result["explanation"])

    def test_chc0_nonrecursive_call_inlines_graph(self):
        result = chc_check.analyze_text(
            "Observe(y) = let r = H(y,y) in if r then loop else halt\n"
            "Top(y) = Observe(y)\n"
            "run Top(Top)\n"
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertIn("R(Top,Top) -> E(Top,Top)", result["graph"])

    def test_chc1_direct_recursive_feedback_is_causal_paradox(self):
        result = chc_check.analyze_text(
            "Rec(y) = let r = H(Rec,y) in if r then Rec(y) else halt\nrun Rec(Task)\n"
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["chc_level"], "CHC-1")
        self.assertEqual(result["fixed_point_status"], "converged_exact")
        self.assertIn("Rec", result["effect_summaries"])

    def test_chc1_mutual_recursive_feedback_is_causal_paradox(self):
        result = chc_check.analyze_text(
            "F(y) = G(y)\n"
            "G(y) = let r = H(F,y) in if r then F(y) else halt\n"
            "run F(Task)\n"
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["chc_level"], "CHC-1")

    def test_chc1_recursive_clean_program_is_valid_unproved(self):
        result = chc_check.analyze_text(
            "Loop(y) = Loop(y)\nrun Loop(Task)\n"
        )

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertEqual(result["semantic_status"], "unproved")
        self.assertEqual(result["chc_level"], "CHC-1")

    def test_chc1_non_converging_summary_is_insufficient_info(self):
        result = chc_check.analyze_text(
            "Grow(y) = let r = H(y,y) in if r then Grow(F(y)) else halt\nrun Grow(Task)\n"
        )

        self.assertEqual(result["classification"], "insufficient_info")
        self.assertEqual(result["fixed_point_status"], "not_converged")

    def test_chc2_safe_higher_order_function_with_explicit_effect(self):
        result = chc_check.analyze_text(
            "Cb(x) = halt\nApply(cb!Clean,x) = cb(x)\nrun Apply(Cb,Task)\n"
        )

        self.assertEqual(result["classification"], "valid_acyclic")
        self.assertEqual(result["chc_level"], "CHC-2")
        self.assertEqual(result["effect_composition_status"], "complete")
        self.assertEqual(result["higher_order_effects"][0]["callee"], "Cb")

    def test_chc2_callback_hiding_feedback_is_causal_paradox(self):
        result = chc_check.analyze_text(
            "Bad(x) = let r = H(Apply,Args(Bad,x)) in if r then loop else halt\n"
            "Apply(cb!Eff,x) = cb(x)\n"
            "run Apply(Bad,Task)\n"
        )

        self.assertEqual(result["classification"], "causal_paradox")
        self.assertEqual(result["chc_level"], "CHC-2")

    def test_chc2_missing_effect_annotation_is_insufficient_info(self):
        result = chc_check.analyze_text(
            "Cb(x) = halt\nApply(cb,x) = cb(x)\nrun Apply(Cb,Task)\n"
        )

        self.assertEqual(result["classification"], "insufficient_info")
        self.assertEqual(result["effect_composition_status"], "incomplete")

    def test_chc2_callback_cannot_capture_halt_result_argument(self):
        result = chc_check.analyze_text(
            "Cb(x) = halt\nApply(cb!Eff,x) = let r = H(x,x) in cb(r)\nrun Apply(Cb,Task)\n"
        )

        self.assertEqual(result["classification"], "parse_error")
        self.assertIn("HaltResult cannot be passed", result["explanation"])


if __name__ == "__main__":
    unittest.main()
