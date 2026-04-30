#!/usr/bin/env python3
"""Deterministic trace analyzer for Causal Halting event JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ExecInfo:
    exec_id: str
    program: str
    input: str

    def node(self) -> str:
        return f"E({self.program},{self.input})"


@dataclass(frozen=True)
class Observation:
    observer: str
    target_exec_id: str
    result_id: str


@dataclass(frozen=True)
class Control:
    result_id: str
    controlled_exec_id: str | None
    action: str
    controller: str | None = None


def value_to_label(value: Any) -> str:
    if value is None:
        return "Unit"
    text = str(value)
    return "".join(char if char.isalnum() or char == "_" else "_" for char in text) or "Unit"


def parse_jsonl(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {index}: {exc}")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {index}: event must be an object")
            continue
        events.append(event)
    return events, errors


def analyze_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    execs: dict[str, ExecInfo] = {}
    observations: dict[str, Observation] = {}
    controls: list[Control] = []
    errors: list[str] = []

    for index, event in enumerate(events, start=1):
        event_type = event.get("type")
        if event_type == "exec_start":
            exec_id = event.get("exec_id")
            program = event.get("program")
            if not isinstance(exec_id, str) or not isinstance(program, str):
                errors.append(f"event {index}: exec_start requires string exec_id and program")
                continue
            execs[exec_id] = ExecInfo(exec_id, value_to_label(program), value_to_label(event.get("input")))
        elif event_type == "observe":
            result_id = event.get("result_id")
            target_exec_id = event.get("target_exec_id")
            observer = event.get("observer", "Observer")
            if not isinstance(result_id, str) or not isinstance(target_exec_id, str):
                errors.append(f"event {index}: observe requires string result_id and target_exec_id")
                continue
            observations[result_id] = Observation(str(observer), target_exec_id, result_id)
        elif event_type == "control":
            result_id = event.get("result_id")
            controlled_exec_id = event.get("controlled_exec_id")
            action = event.get("action", "control")
            controller = event.get("controller")
            if not isinstance(result_id, str):
                errors.append(f"event {index}: control requires string result_id")
                continue
            if controlled_exec_id is not None and not isinstance(controlled_exec_id, str):
                errors.append(f"event {index}: controlled_exec_id must be a string when present")
                continue
            controls.append(
                Control(
                    result_id=result_id,
                    controlled_exec_id=controlled_exec_id,
                    action=str(action),
                    controller=str(controller) if controller is not None else None,
                )
            )
        else:
            errors.append(f"event {index}: unsupported event type {event_type!r}")

    graph: list[str] = []
    feedback_paths: list[dict[str, Any]] = []
    valid_paths: list[dict[str, Any]] = []

    for observation in observations.values():
        target = execs.get(observation.target_exec_id)
        if target is None:
            errors.append(f"observe result {observation.result_id}: unknown target_exec_id {observation.target_exec_id!r}")
            continue
        result_node = f"R({target.program},{target.input})"
        graph.append(f"{target.node()} -> {result_node}")

    for control in controls:
        observation = observations.get(control.result_id)
        if observation is None:
            errors.append(f"control result {control.result_id}: unknown result_id")
            continue
        target = execs.get(observation.target_exec_id)
        if target is None:
            continue
        result_node = f"R({target.program},{target.input})"
        if control.controlled_exec_id is None:
            valid_paths.append(
                {
                    "result_id": control.result_id,
                    "relation": "external_controller",
                    "target_exec_id": observation.target_exec_id,
                    "controlled_exec_id": None,
                    "action": control.action,
                }
            )
            continue
        controlled = execs.get(control.controlled_exec_id)
        if controlled is None:
            errors.append(f"control result {control.result_id}: unknown controlled_exec_id {control.controlled_exec_id!r}")
            continue
        graph.append(f"{result_node} -> {controlled.node()}")
        path = {
            "result_id": control.result_id,
            "relation": "same_execution"
            if control.controlled_exec_id == observation.target_exec_id
            else "different_execution",
            "target_exec_id": observation.target_exec_id,
            "controlled_exec_id": control.controlled_exec_id,
            "path": [target.node(), result_node, controlled.node()],
            "action": control.action,
        }
        if control.controlled_exec_id == observation.target_exec_id:
            feedback_paths.append(path)
        else:
            valid_paths.append(path)

    if errors:
        return {
            "classification": "parse_error",
            "graph": graph,
            "feedback_paths": feedback_paths,
            "valid_paths": valid_paths,
            "semantic_status": "not_analyzed",
            "explanation": "; ".join(errors),
        }

    if feedback_paths:
        return {
            "classification": "causal_paradox",
            "graph": graph,
            "feedback_paths": feedback_paths,
            "valid_paths": valid_paths,
            "semantic_status": "not_analyzed",
            "explanation": "A prediction or observation result controls the same execution that it observed.",
        }

    return {
        "classification": "valid_acyclic",
        "graph": graph,
        "feedback_paths": [],
        "valid_paths": valid_paths,
        "semantic_status": "not_analyzed",
        "explanation": "No trace event routes an observation result back into the same observed execution.",
    }


def analyze_text(text: str) -> dict[str, Any]:
    events, errors = parse_jsonl(text)
    if errors:
        return {
            "classification": "parse_error",
            "graph": [],
            "feedback_paths": [],
            "valid_paths": [],
            "semantic_status": "not_analyzed",
            "explanation": "; ".join(errors),
        }
    return analyze_events(events)


def format_human(result: dict[str, Any]) -> str:
    lines = [
        f"classification: {result['classification']}",
        f"semantic_status: {result['semantic_status']}",
        f"explanation: {result['explanation']}",
    ]
    if result["graph"]:
        lines.append("graph:")
        lines.extend(f"  {edge}" for edge in result["graph"])
    if result["feedback_paths"]:
        lines.append("feedback_paths:")
        for path in result["feedback_paths"]:
            lines.append(
                f"  {path['target_exec_id']} -> {path['result_id']} -> {path['controlled_exec_id']} "
                f"({path['relation']}, action={path['action']})"
            )
    if result["valid_paths"]:
        lines.append("valid_paths:")
        for path in result["valid_paths"]:
            lines.append(
                f"  {path['target_exec_id']} -> {path['result_id']} -> {path['controlled_exec_id']} "
                f"({path['relation']}, action={path['action']})"
            )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze Causal Halting JSONL traces.")
    parser.add_argument("input", help="JSONL trace file.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = analyze_text(Path(args.input).read_text(encoding="utf-8"))
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_human(result))
    return 2 if result["classification"] == "parse_error" else 0


if __name__ == "__main__":
    sys.exit(main())
