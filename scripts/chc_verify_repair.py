#!/usr/bin/env python3
"""Verify that a Causal Halting repair removes same-run feedback."""

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


def verify_repair(before_text: str, after_text: str) -> dict[str, Any]:
    checker = load_trace_checker()
    before = checker.analyze_text(before_text)
    after = checker.analyze_text(after_text)
    passed = before["classification"] == "causal_paradox" and after["classification"] == "valid_acyclic"
    return {
        "verification": "passed" if passed else "failed",
        "before_classification": before["classification"],
        "after_classification": after["classification"],
        "before_feedback_paths": before.get("feedback_paths", []),
        "after_feedback_paths": after.get("feedback_paths", []),
        "proof_obligation": {
            "obligation": "prediction_result_not_consumed_by_observed_execution",
            "valid_if": [
                "consumer is external_orchestrator",
                "consumer exec starts after observed exec ends",
                "result is audit_only",
            ],
        },
        "explanation": (
            "Repair removes same-execution pre-end consumption of the observed result."
            if passed
            else "Repair verification requires before=causal_paradox and after=valid_acyclic."
        ),
    }


def format_human(result: dict[str, Any]) -> str:
    lines = [
        f"verification: {result['verification']}",
        f"before_classification: {result['before_classification']}",
        f"after_classification: {result['after_classification']}",
        f"explanation: {result['explanation']}",
        "proof_obligation:",
        f"  {result['proof_obligation']['obligation']}",
    ]
    if result["before_feedback_paths"]:
        lines.append("before_feedback_paths:")
        for path in result["before_feedback_paths"]:
            lines.append(f"  {path['target_exec_id']} -> {path['result_id']} -> {path['consumer_exec_id']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Verify before/after CHC trace repair.")
    parser.add_argument("before", help="Before trace JSONL file.")
    parser.add_argument("after", help="After trace JSONL file.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = verify_repair(
        Path(args.before).read_text(encoding="utf-8"),
        Path(args.after).read_text(encoding="utf-8"),
    )
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_human(result))
    return 0 if result["verification"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
