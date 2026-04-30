#!/usr/bin/env python3
"""Deterministic DesignIR analyzer for Causal Halting.

This script intentionally does not understand natural language. The LLM must
interpret prose into DesignIR first. This analyzer only validates and classifies
structured causal roles.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def safe_label(value: Any, fallback: str) -> str:
    text = str(value if value is not None else fallback)
    return "".join(char if char.isalnum() or char == "_" else "_" for char in text) or fallback


def exec_node(execution: dict[str, Any]) -> str:
    return f"E({safe_label(execution.get('program'), 'Exec')},{safe_label(execution.get('input'), 'input')})"


def result_node(execution: dict[str, Any]) -> str:
    return f"R({safe_label(execution.get('program'), 'Exec')},{safe_label(execution.get('input'), 'input')})"


def repair_for_self_feedback() -> list[str]:
    return [
        "Move the prediction result to an external orchestrator or controller.",
        "Make the result affect a future execution, not the execution being observed.",
        "Convert current-run self-prediction into post-run audit when possible.",
        "Replace self-halting prediction with bounded local progress metrics.",
        "Keep monitor and controller roles separate.",
    ]


def base_roles() -> dict[str, list[str]]:
    return {
        "Code": [],
        "Exec": [],
        "H": [],
        "HaltResult": [],
    }


def needs_design_ir_result(text: str) -> dict[str, Any]:
    return {
        "classification": "needs_design_ir",
        "design_ir": None,
        "inferred_graph": [],
        "roles": base_roles(),
        "uncertain_edges": [],
        "repair": [],
        "explanation": (
            "Natural-language input is not analyzed by this script. "
            "Interpret the design into DesignIR first, then rerun the analyzer."
        ),
        "input_preview": text.strip()[:200],
    }


def validate_design_ir(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    executions = data.get("executions")
    observations = data.get("observations")
    controls = data.get("controls")
    uncertain = data.get("uncertain", [])
    if not isinstance(executions, list):
        errors.append("executions must be a list")
    if not isinstance(observations, list):
        errors.append("observations must be a list")
    if not isinstance(controls, list):
        errors.append("controls must be a list")
    if not isinstance(uncertain, list):
        errors.append("uncertain must be a list when present")
    if errors:
        return errors

    exec_ids: set[str] = set()
    result_ids: set[str] = set()
    for index, execution in enumerate(executions):
        if not isinstance(execution, dict):
            errors.append(f"executions[{index}] must be an object")
            continue
        if not isinstance(execution.get("id"), str):
            errors.append(f"executions[{index}].id must be a string")
            continue
        exec_ids.add(execution["id"])

    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            errors.append(f"observations[{index}] must be an object")
            continue
        if not isinstance(observation.get("result"), str):
            errors.append(f"observations[{index}].result must be a string")
        if observation.get("target_exec") not in exec_ids:
            errors.append(f"observations[{index}].target_exec must reference an execution")
        if isinstance(observation.get("result"), str):
            result_ids.add(observation["result"])

    for index, control in enumerate(controls):
        if not isinstance(control, dict):
            errors.append(f"controls[{index}] must be an object")
            continue
        if control.get("result") not in result_ids:
            errors.append(f"controls[{index}].result must reference an observation result")
        target = control.get("target_exec")
        if target is not None and target not in exec_ids:
            errors.append(f"controls[{index}].target_exec must reference an execution when present")
    return errors


def analyze_design_ir(data: dict[str, Any]) -> dict[str, Any]:
    errors = validate_design_ir(data)
    if errors:
        return {
            "classification": "parse_error",
            "design_ir": data,
            "inferred_graph": [],
            "roles": base_roles(),
            "uncertain_edges": [],
            "repair": [],
            "explanation": "; ".join(errors),
        }

    executions = {execution["id"]: execution for execution in data["executions"]}
    observations = {observation["result"]: observation for observation in data["observations"]}
    graph: list[str] = []
    uncertain_edges = list(data.get("uncertain", []))
    feedback: list[dict[str, Any]] = []
    roles = {
        "Code": sorted({safe_label(execution.get("program"), "Exec") for execution in data["executions"]}),
        "Exec": [
            f"{safe_label(execution.get('program'), 'Exec')}({safe_label(execution.get('input'), 'input')})"
            for execution in data["executions"]
        ],
        "H": sorted({safe_label(observation.get("observer"), "Observer") for observation in data["observations"]}),
        "HaltResult": sorted(observations.keys()),
    }

    for observation in data["observations"]:
        observed = executions[observation["target_exec"]]
        graph.append(f"{exec_node(observed)} -> {result_node(observed)}")

    for control in data["controls"]:
        observation = observations[control["result"]]
        observed = executions[observation["target_exec"]]
        target_exec = control.get("target_exec")
        if target_exec is None:
            uncertain_edges.append(
                {
                    "edge": f"{result_node(observed)} -> ?",
                    "confidence": 0.5,
                    "reason": "Control target is not specified.",
                }
            )
            continue
        controlled = executions[target_exec]
        graph.append(f"{result_node(observed)} -> {exec_node(controlled)}")
        if target_exec == observation["target_exec"]:
            feedback.append(
                {
                    "result": control["result"],
                    "target_exec": target_exec,
                    "action": control.get("action", control.get("purpose", "control")),
                }
            )

    if feedback:
        return {
            "classification": "causal_paradox",
            "design_ir": data,
            "inferred_graph": graph,
            "roles": roles,
            "uncertain_edges": uncertain_edges,
            "repair": repair_for_self_feedback(),
            "explanation": "A prediction or observation result controls the same execution it observes.",
        }

    if uncertain_edges:
        return {
            "classification": "insufficient_info",
            "design_ir": data,
            "inferred_graph": graph,
            "roles": roles,
            "uncertain_edges": uncertain_edges,
            "repair": ["Specify the consumer execution or external boundary for each observation result."],
            "explanation": "The DesignIR leaves at least one result consumer unspecified.",
        }

    return {
        "classification": "valid_acyclic",
        "design_ir": data,
        "inferred_graph": graph,
        "roles": roles,
        "uncertain_edges": [],
        "repair": [],
        "explanation": "No DesignIR control edge routes an observation result back into its observed execution.",
    }


def analyze_design(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return needs_design_ir_result(text)
    if isinstance(data, dict) and {"executions", "observations", "controls"}.issubset(data.keys()):
        return analyze_design_ir(data)
    return {
        "classification": "parse_error",
        "design_ir": data if isinstance(data, dict) else None,
        "inferred_graph": [],
        "roles": base_roles(),
        "uncertain_edges": [],
        "repair": [],
        "explanation": "Input JSON is not a DesignIR object with executions, observations, and controls.",
    }


def validate_shape(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {
        "causal_paradox",
        "valid_acyclic",
        "unproved",
        "insufficient_info",
        "needs_design_ir",
        "parse_error",
    }
    if result.get("classification") not in allowed:
        errors.append(
            "classification must be one of causal_paradox, valid_acyclic, unproved, insufficient_info, needs_design_ir, parse_error"
        )
    if "design_ir" in result and result.get("design_ir") is not None and not isinstance(result.get("design_ir"), dict):
        errors.append("design_ir must be an object or null when present")
    if not isinstance(result.get("inferred_graph"), list):
        errors.append("inferred_graph must be a list")
    if not isinstance(result.get("roles"), dict):
        errors.append("roles must be an object")
    else:
        for key in ("Code", "Exec", "H", "HaltResult"):
            if not isinstance(result["roles"].get(key), list):
                errors.append(f"roles.{key} must be a list")
    if not isinstance(result.get("uncertain_edges"), list):
        errors.append("uncertain_edges must be a list")
    if not isinstance(result.get("repair"), list):
        errors.append("repair must be a list")
    if not isinstance(result.get("explanation"), str):
        errors.append("explanation must be a string")
    return errors


def read_input(value: str) -> str:
    path = Path(value).expanduser()
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8")
    return value


def format_human(result: dict[str, Any]) -> str:
    lines = [
        f"classification: {result['classification']}",
        f"explanation: {result['explanation']}",
    ]
    if result.get("inferred_graph"):
        lines.append("inferred_graph:")
        lines.extend(f"  {edge}" for edge in result["inferred_graph"])
    if result.get("uncertain_edges"):
        lines.append("uncertain_edges:")
        for edge in result["uncertain_edges"]:
            lines.append(f"  {edge['edge']} | confidence={edge['confidence']} | {edge['reason']}")
    if result.get("repair"):
        lines.append("repair:")
        lines.extend(f"  - {item}" for item in result["repair"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Causal Halting DesignIR JSON.")
    parser.add_argument("input", nargs="+", help="DesignIR JSON or a path to a DesignIR JSON file.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze_design(read_input(" ".join(args.input)))
    errors = validate_shape(result)
    if errors:
        result = {
            "classification": "parse_error",
            "design_ir": None,
            "inferred_graph": [],
            "roles": base_roles(),
            "uncertain_edges": [],
            "repair": [],
            "explanation": "; ".join(errors),
        }
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_human(result))
    return 2 if result["classification"] == "parse_error" else 0


if __name__ == "__main__":
    sys.exit(main())
