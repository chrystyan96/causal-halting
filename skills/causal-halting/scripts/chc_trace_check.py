#!/usr/bin/env python3
"""Deterministic trace analyzer for Causal Halting event JSONL."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


AUDIT_PURPOSES = {"audit", "audit_only", "log", "logging", "post_run_audit", "record"}


@dataclass(frozen=True)
class ExecInfo:
    exec_id: str
    program: str
    input: str
    start_index: int
    end_index: int | None = None

    def node(self) -> str:
        return f"E({self.program},{self.input})"


@dataclass(frozen=True)
class Observation:
    observer: str
    target_exec_id: str
    result_id: str
    index: int


@dataclass(frozen=True)
class Consumption:
    result_id: str
    consumer_exec_id: str | None
    purpose: str
    index: int
    consumer: str | None = None


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
        event["_index"] = len(events)
        events.append(event)
    return events, errors


def is_audit_only(purpose: str) -> bool:
    return value_to_label(purpose).lower() in AUDIT_PURPOSES


def is_before_exec_end(consumer_index: int, observed: ExecInfo) -> bool:
    return observed.end_index is None or consumer_index < observed.end_index


def analyze_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    execs: dict[str, ExecInfo] = {}
    observations: dict[str, Observation] = {}
    consumptions: list[Consumption] = []
    errors: list[str] = []

    for fallback_index, event in enumerate(events):
        index = int(event.get("_index", fallback_index))
        event_type = event.get("type")
        if event_type == "exec_start":
            exec_id = event.get("exec_id")
            program = event.get("program")
            if not isinstance(exec_id, str) or not isinstance(program, str):
                errors.append(f"event {index + 1}: exec_start requires string exec_id and program")
                continue
            execs[exec_id] = ExecInfo(exec_id, value_to_label(program), value_to_label(event.get("input")), index)
        elif event_type == "exec_end":
            exec_id = event.get("exec_id")
            if not isinstance(exec_id, str):
                errors.append(f"event {index + 1}: exec_end requires string exec_id")
                continue
            if exec_id not in execs:
                errors.append(f"event {index + 1}: exec_end references unknown exec_id {exec_id!r}")
                continue
            current = execs[exec_id]
            execs[exec_id] = ExecInfo(current.exec_id, current.program, current.input, current.start_index, index)
        elif event_type == "observe":
            result_id = event.get("result_id")
            target_exec_id = event.get("target_exec_id")
            observer = event.get("observer", "Observer")
            if not isinstance(result_id, str) or not isinstance(target_exec_id, str):
                errors.append(f"event {index + 1}: observe requires string result_id and target_exec_id")
                continue
            observations[result_id] = Observation(str(observer), target_exec_id, result_id, index)
        elif event_type in {"consume", "control"}:
            result_id = event.get("result_id")
            consumer_exec_id = event.get("consumer_exec_id", event.get("controlled_exec_id"))
            purpose = event.get("purpose", event.get("action", "control"))
            consumer = event.get("consumer", event.get("controller"))
            if not isinstance(result_id, str):
                errors.append(f"event {index + 1}: {event_type} requires string result_id")
                continue
            if consumer_exec_id is not None and not isinstance(consumer_exec_id, str):
                errors.append(f"event {index + 1}: consumer_exec_id must be a string when present")
                continue
            consumptions.append(
                Consumption(
                    result_id=result_id,
                    consumer_exec_id=consumer_exec_id,
                    purpose=str(purpose),
                    consumer=str(consumer) if consumer is not None else None,
                    index=index,
                )
            )
        else:
            errors.append(f"event {index + 1}: unsupported event type {event_type!r}")

    graph: list[str] = []
    feedback_paths: list[dict[str, Any]] = []
    valid_paths: list[dict[str, Any]] = []

    for observation in observations.values():
        target = execs.get(observation.target_exec_id)
        if target is None:
            errors.append(f"observe result {observation.result_id}: unknown target_exec_id {observation.target_exec_id!r}")
            continue
        graph.append(f"{target.node()} -> R({target.program},{target.input})")

    for consumption in consumptions:
        observation = observations.get(consumption.result_id)
        if observation is None:
            errors.append(f"consume result {consumption.result_id}: unknown result_id")
            continue
        observed = execs.get(observation.target_exec_id)
        if observed is None:
            continue
        result_node = f"R({observed.program},{observed.input})"

        if consumption.consumer_exec_id is None:
            valid_paths.append(
                {
                    "result_id": consumption.result_id,
                    "relation": "external_controller",
                    "target_exec_id": observation.target_exec_id,
                    "consumer_exec_id": None,
                    "purpose": consumption.purpose,
                }
            )
            continue

        consumer_exec = execs.get(consumption.consumer_exec_id)
        if consumer_exec is None:
            errors.append(f"consume result {consumption.result_id}: unknown consumer_exec_id {consumption.consumer_exec_id!r}")
            continue
        graph.append(f"{result_node} -> {consumer_exec.node()}")

        same_execution = consumption.consumer_exec_id == observation.target_exec_id
        before_end = is_before_exec_end(consumption.index, observed)
        audit_only = is_audit_only(consumption.purpose)
        relation = "same_execution" if same_execution else "different_execution"
        if same_execution and not before_end:
            relation = "same_execution_after_end"
        if audit_only:
            relation = "audit_only"

        path = {
            "result_id": consumption.result_id,
            "relation": relation,
            "target_exec_id": observation.target_exec_id,
            "consumer_exec_id": consumption.consumer_exec_id,
            "path": [observed.node(), result_node, consumer_exec.node()],
            "purpose": consumption.purpose,
            "before_observed_exec_end": before_end,
        }
        if same_execution and before_end and not audit_only:
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
            "explanation": "An observation result is consumed by the same execution before that execution ends.",
        }

    return {
        "classification": "valid_acyclic",
        "graph": graph,
        "feedback_paths": [],
        "valid_paths": valid_paths,
        "semantic_status": "not_analyzed",
        "explanation": "No trace event routes an observation result back into the same observed execution before it ends.",
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
                f"  {path['target_exec_id']} -> {path['result_id']} -> {path['consumer_exec_id']} "
                f"({path['relation']}, purpose={path['purpose']}, before_end={path['before_observed_exec_end']})"
            )
    if result["valid_paths"]:
        lines.append("valid_paths:")
        for path in result["valid_paths"]:
            lines.append(
                f"  {path['target_exec_id']} -> {path['result_id']} -> {path['consumer_exec_id']} "
                f"({path['relation']}, purpose={path['purpose']})"
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
