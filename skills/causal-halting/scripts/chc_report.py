#!/usr/bin/env python3
"""Render CHC analysis or repair JSON as Markdown with Mermaid graphs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def node_id(label: str) -> str:
    return "n_" + "".join(char if char.isalnum() else "_" for char in label)


def graph_to_mermaid(edges: list[str]) -> str:
    lines = ["flowchart LR"]
    if not edges:
        lines.append('  empty["No causal edges"]')
        return "\n".join(lines)
    for edge in edges:
        if "->" not in edge:
            continue
        source, target = [part.strip() for part in edge.split("->", 1)]
        lines.append(f'  {node_id(source)}["{source}"] --> {node_id(target)}["{target}"]')
    return "\n".join(lines)


def extract_edges(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    graph = data.get("graph") or data.get("inferred_graph") or []
    repair_graph = data.get("repair_graph") or []
    return [str(edge) for edge in graph if isinstance(edge, str)], [
        str(edge) for edge in repair_graph if isinstance(edge, str)
    ]


def render_markdown(data: dict[str, Any]) -> str:
    graph, repair_graph = extract_edges(data)
    classification = data.get("classification", data.get("verification", "unknown"))
    lines = [
        "# Causal Halting Report",
        "",
        f"**Classification:** `{classification}`",
    ]
    if data.get("semantic_status"):
        lines.append(f"**Semantic status:** `{data['semantic_status']}`")
    if data.get("repair_status"):
        lines.append(f"**Repair status:** `{data['repair_status']}`")
    if data.get("explanation"):
        lines.extend(["", data["explanation"]])
    if graph:
        lines.extend(["", "## Causal Graph", "", "```mermaid", graph_to_mermaid(graph), "```"])
    if data.get("feedback_paths"):
        lines.extend(["", "## Feedback Paths"])
        for path in data["feedback_paths"]:
            lines.append(
                f"- `{path.get('target_exec_id')}` -> `{path.get('result_id')}` -> `{path.get('consumer_exec_id')}`"
            )
    if repair_graph:
        lines.extend(["", "## Repair Graph", "", "```mermaid", graph_to_mermaid(repair_graph), "```"])
    obligations = data.get("proof_obligations") or []
    if obligations:
        lines.extend(["", "## Proof Obligations"])
        for obligation in obligations:
            status = obligation.get("status")
            suffix = f" - `{status}`" if status else ""
            lines.append(f"- `{obligation.get('obligation', 'unknown')}`{suffix}")
    recommendations = data.get("recommendations") or data.get("repair") or []
    if recommendations:
        lines.extend(["", "## Recommendations"])
        lines.extend(f"- {item}" for item in recommendations)
    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render CHC JSON as a Markdown report.")
    parser.add_argument("input", help="Analysis, repair, or verification JSON file.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not isinstance(data, dict):
        print("input must be a JSON object", file=sys.stderr)
        return 2
    print(render_markdown(data), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
