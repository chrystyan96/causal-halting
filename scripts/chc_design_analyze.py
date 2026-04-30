#!/usr/bin/env python3
"""DesignIR-based analyzer for Causal Halting.

Natural-language design text is first converted into a small DesignIR. The
classification is then deterministic over that IR. This keeps LLM/prose
inference separate from the causal decision.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


def normalize(text: str) -> str:
    without_accents = "".join(
        char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char)
    )
    return " ".join(without_accents.lower().strip().split())


def has_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


OBSERVATION_PATTERNS = [
    r"\bpredict",
    r"\bprediction",
    r"\bobserve",
    r"\bobservation",
    r"\bmonitor",
    r"\bsupervisor",
    r"\bevaluate",
    r"\bsimulate",
    r"\bdecide whether\b",
    r"\bwill (finish|halt|complete|fail|continue)\b",
    r"\bcurrent (run|execution).*(finish|halt|complete|fail|continue)\b",
    r"\bexecucao atual\b",
    r"\bconcluir\b",
]

SELF_EXEC_PATTERNS = [
    r"\bsame (run|execution|agent)\b",
    r"\bcurrent (run|execution)\b",
    r"\bits own (run|execution)\b",
    r"\bitself\b",
    r"\bmesma execucao\b",
    r"\bexecucao atual\b",
    r"\bpropria execucao\b",
]

CONTROL_PATTERNS = [
    r"\bchange[s]? strateg",
    r"\bswitch(?:es)? strateg",
    r"\bdecides? (whether )?to (continue|stop|retry|restart|change)",
    r"\bschedules?\b",
    r"\bcontrols?\b",
    r"\bfeeds? back\b",
    r"\buses? (the )?(prediction|result|answer)",
    r"\bcontinua\b",
    r"\bmuda de estrategia\b",
    r"\bcontrola\b",
]

SAFE_BOUNDARY_PATTERNS = [
    r"\bafter completion\b",
    r"\bpost[- ]run\b",
    r"\blogs after\b",
    r"\bfuture run\b",
    r"\bnext run\b",
    r"\blater run\b",
    r"\bexternal orchestrator\b",
    r"\bseparate controller\b",
    r"\bapos (a )?conclusao\b",
    r"\bproxima execucao\b",
]


def safe_label(value: Any, fallback: str) -> str:
    text = str(value if value is not None else fallback)
    return "".join(char if char.isalnum() or char == "_" else "_" for char in text) or fallback


def exec_node(execution: dict[str, Any]) -> str:
    return f"E({safe_label(execution.get('program'), 'Exec')},{safe_label(execution.get('input'), 'input')})"


def result_node(execution: dict[str, Any]) -> str:
    return f"R({safe_label(execution.get('program'), 'Exec')},{safe_label(execution.get('input'), 'input')})"


def default_execution(exec_id: str = "run-1", program: str = "AgentRun", input_value: str = "input") -> dict[str, str]:
    return {"id": exec_id, "program": program, "input": input_value}


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
        "Code": ["AgentRun"],
        "Exec": ["AgentRun(input)"],
        "H": [],
        "HaltResult": [],
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
        "Exec": [f"{safe_label(execution.get('program'), 'Exec')}({safe_label(execution.get('input'), 'input')})" for execution in data["executions"]],
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
                    "action": control.get("action", "control"),
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


def infer_design_ir(text: str) -> dict[str, Any]:
    lowered = normalize(text)
    mentions_observation = has_any(lowered, OBSERVATION_PATTERNS)
    mentions_self = has_any(lowered, SELF_EXEC_PATTERNS)
    mentions_control = has_any(lowered, CONTROL_PATTERNS)
    mentions_safe_boundary = has_any(lowered, SAFE_BOUNDARY_PATTERNS)
    design_ir: dict[str, Any] = {
        "executions": [default_execution()],
        "observations": [],
        "controls": [],
        "uncertain": [],
    }

    if mentions_observation:
        design_ir["observations"].append(
            {
                "id": "obs-1",
                "observer": "SupervisorPrediction",
                "target_exec": "run-1",
                "result": "r-1",
            }
        )

    if mentions_observation and mentions_self and mentions_control and not mentions_safe_boundary:
        design_ir["controls"].append({"result": "r-1", "target_exec": "run-1", "action": "change_strategy"})
    elif mentions_observation and mentions_control and mentions_safe_boundary:
        design_ir["executions"].append(default_execution("run-2", "NextAgentRun", "input"))
        design_ir["controls"].append({"result": "r-1", "target_exec": "run-2", "action": "schedule_future_run"})
    elif mentions_observation and mentions_control and not mentions_self:
        design_ir["uncertain"].append(
            {
                "edge": "R(AgentRun,input) -> ?",
                "confidence": 0.45,
                "reason": "The design mentions control from an observation result, but not whether it controls the observed execution.",
            }
        )
    elif mentions_observation and not mentions_control:
        design_ir["uncertain"].append(
            {
                "edge": "R(AgentRun,input) -> ?",
                "confidence": 0.35,
                "reason": "The design describes observation but not where the result flows.",
            }
        )
    return design_ir


def analyze_design(text: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = infer_design_ir(text)
    if isinstance(data, dict) and {"executions", "observations", "controls"}.issubset(data.keys()):
        return analyze_design_ir(data)
    return analyze_design_ir(infer_design_ir(text))


def validate_shape(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {"causal_paradox", "valid_acyclic", "unproved", "insufficient_info", "parse_error"}
    if result.get("classification") not in allowed:
        errors.append("classification must be one of causal_paradox, valid_acyclic, unproved, insufficient_info, parse_error")
    if "design_ir" in result and not isinstance(result.get("design_ir"), dict):
        errors.append("design_ir must be an object when present")
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
    parser = argparse.ArgumentParser(description="Infer and analyze a CHC DesignIR from design text or JSON.")
    parser.add_argument("input", nargs="+", help="Design text, DesignIR JSON, or a path to a text/JSON file.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze_design(read_input(" ".join(args.input)))
    errors = validate_shape(result)
    if errors:
        result = {
            "classification": "parse_error",
            "design_ir": {},
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
