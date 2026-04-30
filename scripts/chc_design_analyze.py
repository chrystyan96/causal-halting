#!/usr/bin/env python3
"""Explicit design analyzer for Causal Halting.

This analyzer is intentionally conservative. It is not the background prompt
router and it is not a theorem prover. It turns common agent/workflow design
descriptions into a small CHC-style analysis object so users can inspect the
inferred causal model before moving to trace-level verification.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


SELF_EXEC = "E(AgentRun,input)"
SELF_RESULT = "R(AgentRun,input)"
SUPERVISOR_EXEC = "E(Supervisor,input)"
FUTURE_EXEC = "E(NextAgentRun,input)"


def normalize(text: str) -> str:
    return " ".join(text.lower().strip().split())


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
    r"\bexecu[cç][aã]o atual\b",
    r"\bconcluir\b",
]

SELF_EXEC_PATTERNS = [
    r"\bsame (run|execution|agent)\b",
    r"\bcurrent (run|execution)\b",
    r"\bits own (run|execution)\b",
    r"\bitself\b",
    r"\bmesma execu[cç][aã]o\b",
    r"\bexecu[cç][aã]o atual\b",
    r"\bpropria execu[cç][aã]o\b",
    r"\bpr[oó]pria execu[cç][aã]o\b",
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
    r"\bmuda de estrat[eé]gia\b",
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
    r"\bap[oó]s (a )?conclus[aã]o\b",
    r"\bpr[oó]xima execu[cç][aã]o\b",
]


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


def analyze_design(text: str) -> dict[str, Any]:
    lowered = normalize(text)
    mentions_observation = has_any(lowered, OBSERVATION_PATTERNS)
    mentions_self = has_any(lowered, SELF_EXEC_PATTERNS)
    mentions_control = has_any(lowered, CONTROL_PATTERNS)
    mentions_safe_boundary = has_any(lowered, SAFE_BOUNDARY_PATTERNS)

    roles = base_roles()
    graph: list[str] = []
    uncertain_edges: list[dict[str, Any]] = []
    repair: list[str] = []

    if mentions_observation:
        roles["H"].append("SupervisorPrediction")
        roles["HaltResult"].append("PredictionResult(AgentRun,input)")
        graph.append(f"{SELF_EXEC} -> {SELF_RESULT}")

    if mentions_observation and mentions_self and mentions_control and not mentions_safe_boundary:
        graph.append(f"{SELF_RESULT} -> {SELF_EXEC}")
        repair = repair_for_self_feedback()
        return {
            "classification": "causal_paradox",
            "inferred_graph": graph,
            "roles": roles,
            "uncertain_edges": [],
            "repair": repair,
            "explanation": (
                "The design lets a prediction or observation about the current "
                "execution control that same execution."
            ),
        }

    if mentions_observation and mentions_control and mentions_safe_boundary:
        graph.append(f"{SELF_RESULT} -> {FUTURE_EXEC}")
        return {
            "classification": "valid_acyclic",
            "inferred_graph": graph,
            "roles": roles,
            "uncertain_edges": [],
            "repair": [],
            "explanation": (
                "The prediction result is routed across an execution boundary "
                "instead of controlling the observed execution."
            ),
        }

    if mentions_observation and mentions_control and not mentions_self:
        graph.append(f"{SELF_RESULT} -> {SUPERVISOR_EXEC}")
        uncertain_edges.append(
            {
                "edge": f"{SELF_RESULT} -> ?",
                "confidence": 0.45,
                "reason": "The design mentions control from an observation result, but not whether it controls the observed execution.",
            }
        )
        return {
            "classification": "insufficient_info",
            "inferred_graph": graph,
            "roles": roles,
            "uncertain_edges": uncertain_edges,
            "repair": [
                "Specify whether the prediction result controls the observed execution, a future execution, or an external controller."
            ],
            "explanation": "The design includes observation and control, but the execution boundary is ambiguous.",
        }

    if mentions_observation and not mentions_control:
        uncertain_edges.append(
            {
                "edge": f"{SELF_RESULT} -> ?",
                "confidence": 0.35,
                "reason": "The design describes observation but not where the result flows.",
            }
        )
        return {
            "classification": "insufficient_info",
            "inferred_graph": graph,
            "roles": roles,
            "uncertain_edges": uncertain_edges,
            "repair": [
                "State whether the observation result is discarded, audited after completion, or used to control an execution."
            ],
            "explanation": "The observation result has no specified consumer.",
        }

    return {
        "classification": "valid_acyclic",
        "inferred_graph": graph,
        "roles": roles,
        "uncertain_edges": [],
        "repair": [],
        "explanation": "No prediction-feedback structure was inferred from the design text.",
    }


def validate_shape(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    allowed = {"causal_paradox", "valid_acyclic", "unproved", "insufficient_info"}
    if result.get("classification") not in allowed:
        errors.append("classification must be one of causal_paradox, valid_acyclic, unproved, insufficient_info")
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
    if result["inferred_graph"]:
        lines.append("inferred_graph:")
        lines.extend(f"  {edge}" for edge in result["inferred_graph"])
    if result["uncertain_edges"]:
        lines.append("uncertain_edges:")
        for edge in result["uncertain_edges"]:
            lines.append(f"  {edge['edge']} | confidence={edge['confidence']} | {edge['reason']}")
    if result["repair"]:
        lines.append("repair:")
        lines.extend(f"  - {item}" for item in result["repair"])
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Infer a CHC causal model from design text.")
    parser.add_argument("input", help="Design text or a path to a text file.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze_design(read_input(args.input))
    errors = validate_shape(result)
    if errors:
        result = {
            "classification": "parse_error",
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
