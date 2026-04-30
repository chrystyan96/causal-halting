#!/usr/bin/env python3
"""Analyze CHC-5 probabilistic PredictionResult IR."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


BOUNDARY = {
    "does_not_prove_arbitrary_termination": True,
    "does_not_solve_classical_halting": True,
}


def analyze_prediction_ir(data: dict[str, Any]) -> dict[str, Any]:
    executions = {item.get("id"): item for item in data.get("executions", []) if isinstance(item, dict)}
    predictions = {item.get("result_id"): item for item in data.get("predictions", []) if isinstance(item, dict)}
    controls = [item for item in data.get("controls", []) if isinstance(item, dict)]
    if not executions or not predictions:
        return result("parse_error", None, [], "PredictionIR requires executions and predictions.")

    graph: list[str] = []
    feedback: list[dict[str, Any]] = []
    uncertain: list[dict[str, Any]] = []
    prediction_kind = None
    for prediction in predictions.values():
        target = executions.get(prediction.get("target_exec"))
        prediction_kind = prediction.get("kind", prediction_kind)
        if target is None:
            uncertain.append({"relation": "unknown_prediction_target", "result_id": prediction.get("result_id")})
            continue
        graph.append(f"E({target.get('program', 'Exec')},{target.get('input', 'input')}) -> P({prediction.get('result_id')})")

    for control in controls:
        prediction = predictions.get(control.get("result_id"))
        if prediction is None:
            uncertain.append({"relation": "unknown_prediction_result", "result_id": control.get("result_id")})
            continue
        target_exec_id = prediction.get("target_exec")
        controlled_exec_id = control.get("target_exec")
        if controlled_exec_id not in executions and control.get("consumer") != "external_controller":
            uncertain.append({"relation": "unknown_control_target", "result_id": control.get("result_id")})
            continue
        graph.append(f"P({control.get('result_id')}) -> Control({controlled_exec_id or control.get('consumer')})")
        if (
            controlled_exec_id == target_exec_id
            and control.get("timing") == "during_observed_execution"
            and prediction.get("kind") != "bounded_progress_metric"
        ):
            feedback.append(
                {
                    "relation": "prediction_result_controls_observed_execution",
                    "result_id": control.get("result_id"),
                    "target_exec_id": target_exec_id,
                    "confidence": prediction.get("confidence"),
                }
            )

    if feedback:
        output = result("causal_paradox", prediction_kind, graph, "PredictionResult controls the same execution it predicts.")
        output["feedback_paths"] = feedback
        return output
    if uncertain:
        output = result("insufficient_info", prediction_kind, graph, "PredictionIR has ambiguous prediction or control identity.")
        output["uncertain_paths"] = uncertain
        return output
    return result("valid_acyclic", prediction_kind, graph, "No probabilistic prediction-feedback path was found.")


def result(classification: str, kind: Any, graph: list[str], explanation: str) -> dict[str, Any]:
    return {
        "classification": classification,
        "chc_level": "CHC-5",
        "prediction_result_kind": kind,
        "prediction_confidence_used_for_classification": False,
        "graph": graph,
        "semantic_status": "not_analyzed",
        "analysis_profile": "trace_identity_limited",
        "capability_boundary": dict(BOUNDARY),
        "explanation": explanation,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze CHC-5 PredictionIR JSON.")
    parser.add_argument("input")
    parser.add_argument("--format", choices=("json", "human"), default="human")
    args = parser.parse_args(argv)
    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("input must be a JSON object")
        output = analyze_prediction_ir(data)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        output = result("parse_error", None, [], str(exc))
    if args.format == "json":
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(f"classification: {output['classification']}")
        print(f"prediction_result_kind: {output['prediction_result_kind']}")
        print(f"explanation: {output['explanation']}")
    return 2 if output["classification"] == "parse_error" else 0


if __name__ == "__main__":
    sys.exit(main())
