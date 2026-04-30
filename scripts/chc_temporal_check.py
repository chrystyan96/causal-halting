#!/usr/bin/env python3
"""Analyze CHC-4 temporal/distributed trace JSONL."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


def load_trace_checker():
    script = Path(__file__).resolve().with_name("chc_trace_check.py")
    spec = importlib.util.spec_from_file_location("chc_trace_check", script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load trace checker from {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["chc_trace_check"] = module
    spec.loader.exec_module(module)
    return module


def parse_events(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {line_no}: {exc}")
            continue
        if not isinstance(event, dict):
            errors.append(f"line {line_no}: event must be an object")
            continue
        event["_index"] = len(events)
        events.append(event)
    return events, errors


def temporal_order_status(events: list[dict[str, Any]]) -> str:
    if any(event.get("happens_before") for event in events):
        return "complete"
    if all("timestamp" in event or "logical_clock" in event or "span_id" in event for event in events):
        return "partial"
    return "insufficient_info"


def analyze_temporal_text(text: str) -> dict[str, Any]:
    events, errors = parse_events(text)
    if errors:
        return {
            "classification": "parse_error",
            "chc_level": "CHC-4",
            "temporal_order_status": "insufficient_info",
            "happens_before_path": [],
            "semantic_status": "not_analyzed",
            "capability_boundary": {
                "does_not_prove_arbitrary_termination": True,
                "does_not_solve_classical_halting": True,
            },
            "explanation": "; ".join(errors),
        }
    status = temporal_order_status(events)
    checker = load_trace_checker()
    base = checker.analyze_events(events)
    output = {
        **base,
        "chc_level": "CHC-4",
        "temporal_order_status": status,
        "happens_before_path": [
            {"event": event.get("_index"), "happens_before": event.get("happens_before")}
            for event in events
            if event.get("happens_before")
        ],
    }
    if status == "insufficient_info" and base["classification"] == "valid_acyclic":
        output["classification"] = "insufficient_info"
        output["explanation"] = "Temporal ordering is insufficient to prove the trace is acyclic."
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze CHC-4 temporal trace JSONL.")
    parser.add_argument("input")
    parser.add_argument("--format", choices=("json", "human"), default="human")
    args = parser.parse_args(argv)
    output = analyze_temporal_text(Path(args.input).read_text(encoding="utf-8"))
    if args.format == "json":
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print(f"classification: {output['classification']}")
        print(f"temporal_order_status: {output['temporal_order_status']}")
        print(f"explanation: {output['explanation']}")
    return 2 if output["classification"] == "parse_error" else 0


if __name__ == "__main__":
    sys.exit(main())
