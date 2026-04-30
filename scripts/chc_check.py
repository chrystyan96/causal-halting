#!/usr/bin/env python3
"""Experimental CHC-0 causal graph checker.

This checker is intentionally narrow. It detects unifiable prediction-feedback
cycles in either a graph DSL or a small canonical mini-CHC syntax.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Term:
    name: str
    args: tuple["Term", ...] = ()

    @property
    def is_var(self) -> bool:
        return not self.args and bool(re.match(r"^[a-z][A-Za-z0-9_]*$", self.name))

    def substitute(self, mapping: dict[str, "Term"]) -> "Term":
        if self.is_var and self.name in mapping:
            return mapping[self.name]
        if not self.args:
            return self
        return Term(self.name, tuple(arg.substitute(mapping) for arg in self.args))

    def to_string(self) -> str:
        if not self.args:
            return self.name
        return f"{self.name}({','.join(arg.to_string() for arg in self.args)})"


@dataclass(frozen=True)
class Node:
    kind: str
    left: Term
    right: Term

    def to_string(self) -> str:
        return f"{self.kind}({self.left.to_string()},{self.right.to_string()})"


@dataclass(frozen=True)
class Edge:
    source: Node
    target: Node

    def to_string(self) -> str:
        return f"{self.source.to_string()} -> {self.target.to_string()}"


class ParseError(ValueError):
    pass


class TermParser:
    def __init__(self, text: str):
        self.text = text
        self.index = 0

    def parse_term(self) -> Term:
        self._skip_ws()
        name = self._parse_identifier()
        self._skip_ws()
        if self._peek() != "(":
            return Term(name)

        self.index += 1
        args: list[Term] = []
        self._skip_ws()
        if self._peek() == ")":
            self.index += 1
            return Term(name, ())

        while True:
            args.append(self.parse_term())
            self._skip_ws()
            char = self._peek()
            if char == ",":
                self.index += 1
                continue
            if char == ")":
                self.index += 1
                break
            raise ParseError(f"Expected ',' or ')' at offset {self.index} in {self.text!r}.")
        return Term(name, tuple(args))

    def require_end(self) -> None:
        self._skip_ws()
        if self.index != len(self.text):
            raise ParseError(f"Unexpected text at offset {self.index}: {self.text[self.index:]!r}.")

    def _parse_identifier(self) -> str:
        match = re.match(r"[A-Za-z_][A-Za-z0-9_]*", self.text[self.index :])
        if not match:
            raise ParseError(f"Expected identifier at offset {self.index} in {self.text!r}.")
        self.index += len(match.group(0))
        return match.group(0)

    def _peek(self) -> str:
        if self.index >= len(self.text):
            return ""
        return self.text[self.index]

    def _skip_ws(self) -> None:
        while self.index < len(self.text) and self.text[self.index].isspace():
            self.index += 1


def parse_term(text: str) -> Term:
    parser = TermParser(text)
    term = parser.parse_term()
    parser.require_end()
    return term


def split_top_level_pair(text: str) -> tuple[str, str]:
    depth = 0
    for index, char in enumerate(text):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            return text[:index], text[index + 1 :]
    raise ParseError(f"Expected a top-level comma in {text!r}.")


def parse_node(text: str) -> Node:
    text = text.strip()
    match = re.match(r"^(E|R)\((.*)\)$", text)
    if not match:
        raise ParseError(f"Expected E(term,term) or R(term,term), got {text!r}.")
    left_text, right_text = split_top_level_pair(match.group(2))
    return Node(match.group(1), parse_term(left_text), parse_term(right_text))


def strip_comments(text: str) -> list[str]:
    lines = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def parse_graph_dsl(text: str) -> list[Edge]:
    edges: list[Edge] = []
    lines = strip_comments(text)
    for line in lines:
        parts = [part.strip() for part in line.split("->")]
        if len(parts) < 2:
            raise ParseError(f"Expected an edge with '->', got {line!r}.")
        nodes = [parse_node(part) for part in parts]
        edges.extend(Edge(source, target) for source, target in zip(nodes, nodes[1:]))
    return edges


def parse_arg_term(text: str) -> Term:
    text = text.strip()
    if not text:
        return Term("Unit")
    return parse_term(text)


def parse_mini_chc(text: str) -> tuple[list[Edge], str]:
    lines = strip_comments(text)
    definitions: dict[str, tuple[str | None, str]] = {}
    run_target: tuple[str, Term] | None = None

    for line in lines:
        run_match = re.match(r"^run\s+([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$", line)
        if run_match:
            run_target = (run_match.group(1), parse_arg_term(run_match.group(2)))
            continue

        def_match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)\)\s*=\s*(.+)$", line)
        if def_match:
            name = def_match.group(1)
            param_text = def_match.group(2).strip()
            if "," in param_text:
                raise ParseError("Mini-CHC v1 supports zero or one function parameter.")
            definitions[name] = (param_text or None, def_match.group(3).strip())
            continue

        raise ParseError(f"Unsupported mini-CHC line: {line!r}.")

    if run_target is None:
        raise ParseError("Mini-CHC input must include a run statement.")

    name, run_arg = run_target
    if name not in definitions:
        raise ParseError(f"run references undefined function {name!r}.")

    param, body = definitions[name]
    h_match = re.search(r"H\(([^()]*(?:\([^)]*\)[^()]*)*)\)", body)
    if not h_match:
        return [], "unproved"

    if "if" not in body or "then" not in body or "else" not in body:
        raise ParseError("Mini-CHC v1 only supports H inside an if-then-else branch.")

    h_left_text, h_right_text = split_top_level_pair(h_match.group(1))
    mapping: dict[str, Term] = {}
    if param:
        mapping[param] = run_arg

    h_left = parse_term(h_left_text).substitute(mapping)
    h_right = parse_term(h_right_text).substitute(mapping)
    self_node = Node("E", Term(name), run_arg)
    result_node = Node("R", h_left, h_right)
    observed_node = Node("E", h_left, h_right)
    return [Edge(observed_node, result_node), Edge(result_node, self_node)], "not_analyzed"


def is_graph_like(text: str) -> bool:
    lines = strip_comments(text)
    return bool(lines) and all("->" in line for line in lines)


def parse_input(text: str, mode: str) -> tuple[list[Edge], str]:
    if mode == "graph":
        return parse_graph_dsl(text), "not_analyzed"
    if mode == "mini-chc":
        return parse_mini_chc(text)
    if is_graph_like(text):
        return parse_graph_dsl(text), "not_analyzed"
    return parse_mini_chc(text)


Substitution = dict[str, Term]


def walk(term: Term, subst: Substitution) -> Term:
    while term.is_var and term.name in subst:
        term = subst[term.name]
    return term


def occurs(var_name: str, term: Term, subst: Substitution) -> bool:
    term = walk(term, subst)
    if term.is_var:
        return term.name == var_name
    return any(occurs(var_name, arg, subst) for arg in term.args)


def bind(var: Term, term: Term, subst: Substitution) -> Substitution | None:
    if var == term:
        return subst
    if occurs(var.name, term, subst):
        return None
    next_subst = dict(subst)
    next_subst[var.name] = term
    return next_subst


def unify_term(left: Term, right: Term, subst: Substitution) -> Substitution | None:
    left = walk(left, subst)
    right = walk(right, subst)
    if left == right:
        return subst
    if left.is_var:
        return bind(left, right, subst)
    if right.is_var:
        return bind(right, left, subst)
    if left.name != right.name or len(left.args) != len(right.args):
        return None
    for left_arg, right_arg in zip(left.args, right.args):
        subst = unify_term(left_arg, right_arg, subst)
        if subst is None:
            return None
    return subst


def unify_node_labels(left: Node, right: Node) -> Substitution | None:
    subst: Substitution = {}
    subst = unify_term(left.left, right.left, subst)
    if subst is None:
        return None
    return unify_term(left.right, right.right, subst)


def subst_to_json(subst: Substitution | None) -> dict[str, str] | None:
    if subst is None:
        return None
    return {name: walk(term, subst).to_string() for name, term in sorted(subst.items())}


def graph_nodes(edges: Iterable[Edge]) -> list[Node]:
    seen: set[Node] = set()
    nodes: list[Node] = []
    for edge in edges:
        for node in (edge.source, edge.target):
            if node not in seen:
                seen.add(node)
                nodes.append(node)
    return nodes


def find_path(edges: list[Edge], source: Node, target: Node) -> list[Node] | None:
    adjacency: dict[Node, list[Node]] = {}
    for edge in edges:
        adjacency.setdefault(edge.source, []).append(edge.target)

    stack: list[tuple[Node, list[Node]]] = [(source, [source])]
    while stack:
        node, path = stack.pop()
        for neighbor in adjacency.get(node, []):
            next_path = path + [neighbor]
            if neighbor == target:
                return next_path
            if neighbor not in path:
                stack.append((neighbor, next_path))
    return None


def analyze_edges(edges: list[Edge], semantic_status: str = "not_analyzed") -> dict:
    nodes = graph_nodes(edges)
    e_nodes = [node for node in nodes if node.kind == "E"]
    reachable_pairs = []
    first_paradox = None

    for source in e_nodes:
        for target in e_nodes:
            path = find_path(edges, source, target)
            if path is None:
                continue
            unifier = unify_node_labels(source, target)
            pair = {
                "source": source.to_string(),
                "target": target.to_string(),
                "path": [node.to_string() for node in path],
                "unifier": subst_to_json(unifier),
            }
            reachable_pairs.append(pair)
            if unifier is not None and first_paradox is None:
                first_paradox = pair

    if first_paradox:
        return {
            "classification": "causal_paradox",
            "graph": [edge.to_string() for edge in edges],
            "reachable_e_pairs": reachable_pairs,
            "unifier": first_paradox["unifier"],
            "semantic_status": semantic_status,
            "explanation": (
                "Found a nonempty E-to-E path whose endpoint labels unify, "
                "so the graph contains prediction feedback."
            ),
        }

    return {
        "classification": "valid_acyclic",
        "graph": [edge.to_string() for edge in edges],
        "reachable_e_pairs": reachable_pairs,
        "unifier": None,
        "semantic_status": semantic_status,
        "explanation": "No unifiable E-to-E feedback path was found.",
    }


def analyze_text(text: str, mode: str = "auto") -> dict:
    try:
        edges, semantic_status = parse_input(text, mode)
        return analyze_edges(edges, semantic_status=semantic_status)
    except ParseError as exc:
        return {
            "classification": "parse_error",
            "graph": [],
            "reachable_e_pairs": [],
            "unifier": None,
            "semantic_status": "not_analyzed",
            "explanation": str(exc),
        }


def format_human(result: dict) -> str:
    lines = [
        f"classification: {result['classification']}",
        f"semantic_status: {result['semantic_status']}",
        f"explanation: {result['explanation']}",
    ]
    if result["graph"]:
        lines.append("graph:")
        lines.extend(f"  {edge}" for edge in result["graph"])
    if result["unifier"]:
        lines.append("unifier:")
        lines.extend(f"  {key} = {value}" for key, value in result["unifier"].items())
    if result["reachable_e_pairs"]:
        lines.append("reachable_e_pairs:")
        for pair in result["reachable_e_pairs"]:
            unifier = pair["unifier"] if pair["unifier"] is not None else "none"
            lines.append(f"  {pair['source']} ->+ {pair['target']} | unifier={unifier}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check CHC-0 causal graph feedback.")
    parser.add_argument("input", help="Input file containing graph DSL or mini-CHC syntax.")
    parser.add_argument(
        "--mode",
        choices=("auto", "graph", "mini-chc"),
        default="auto",
        help="Input parser mode. Default: auto.",
    )
    parser.add_argument(
        "--format",
        choices=("human", "json"),
        default="human",
        help="Output format. Default: human.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    text = Path(args.input).read_text(encoding="utf-8")
    result = analyze_text(text, mode=args.mode)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(format_human(result))
    return 2 if result["classification"] == "parse_error" else 0


if __name__ == "__main__":
    sys.exit(main())
