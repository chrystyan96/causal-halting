#!/usr/bin/env python3
"""Validate Causal Halting design-analysis JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_CLASSIFICATIONS = {
    "causal_paradox",
    "valid_acyclic",
    "unproved",
    "insufficient_info",
    "parse_error",
}


def validate_design_analysis(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if data.get("classification") not in ALLOWED_CLASSIFICATIONS:
        errors.append("classification must be causal_paradox, valid_acyclic, unproved, or insufficient_info")
    if not isinstance(data.get("inferred_graph"), list) or not all(
        isinstance(edge, str) for edge in data.get("inferred_graph", [])
    ):
        errors.append("inferred_graph must be a list of strings")
    if "design_ir" in data and not isinstance(data.get("design_ir"), dict):
        errors.append("design_ir must be an object when present")
    roles = data.get("roles")
    if not isinstance(roles, dict):
        errors.append("roles must be an object")
    else:
        for key in ("Code", "Exec", "H", "HaltResult"):
            if not isinstance(roles.get(key), list) or not all(isinstance(item, str) for item in roles.get(key, [])):
                errors.append(f"roles.{key} must be a list of strings")
    if not isinstance(data.get("uncertain_edges"), list):
        errors.append("uncertain_edges must be a list")
    if not isinstance(data.get("repair"), list) or not all(isinstance(item, str) for item in data.get("repair", [])):
        errors.append("repair must be a list of strings")
    if not isinstance(data.get("explanation"), str):
        errors.append("explanation must be a string")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate Causal Halting design-analysis JSON.")
    parser.add_argument("input", help="JSON file to validate.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    else:
        errors = validate_design_analysis(data if isinstance(data, dict) else {})

    result = {"valid": not errors, "errors": errors}
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    elif errors:
        print("invalid")
        for error in errors:
            print(f"- {error}")
    else:
        print("valid")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
