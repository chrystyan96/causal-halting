"""Unified CLI for Causal Halting.

The CLI is a stable front door over the existing stdlib-only analyzers in
``scripts/``. The script entrypoints remain supported for compatibility.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

from . import __version__


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
EXAMPLES = ROOT / "examples"


SCRIPT_BY_COMMAND = {
    "check": "chc_check.py",
    "design": "chc_design_analyze.py",
    "trace": "chc_trace_check.py",
    "process": "chc_process_check.py",
    "temporal": "chc_temporal_check.py",
    "prediction": "chc_prediction_check.py",
    "repair": "chc_repair.py",
    "verify-repair": "chc_verify_repair.py",
    "report": "chc_report.py",
    "eval": "chc_eval_suite.py",
}


def load_script(name: str) -> Any:
    path = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[path.stem] = module
    spec.loader.exec_module(module)
    return module


def run_script(command: str, argv: list[str]) -> int:
    module = load_script(SCRIPT_BY_COMMAND[command])
    return int(module.main(argv))


def capture_script_json(command: str, argv: list[str]) -> tuple[int, dict[str, Any] | None, str]:
    output = io.StringIO()
    code = 1
    with contextlib.redirect_stdout(output):
        code = run_script(command, [*argv, "--format", "json"])
    text = output.getvalue()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return code, None, text
    return code, parsed if isinstance(parsed, dict) else None, text


def human_explanation(data: dict[str, Any]) -> str:
    classification = data.get("classification", data.get("verification", "unknown"))
    explanation = data.get("explanation", "")
    lines = [f"Result: {classification}"]
    if explanation:
        lines.append(explanation)
    if classification == "causal_paradox":
        paths = data.get("feedback_paths") or data.get("reachable_e_pairs") or []
        if paths:
            lines.append("Why: a prediction or observation result can control the execution it observes.")
    elif classification == "valid_acyclic":
        lines.append("Scope: no modeled prediction-feedback cycle was found.")
        lines.append("This does not prove termination, safety, correctness, or absence of unmodeled feedback.")
    elif classification == "insufficient_info":
        missing = data.get("missing") or data.get("identity_resolution", {}).get("missing") or []
        if missing:
            lines.append(f"Missing or ambiguous identity: {missing}")
        asks = data.get("ask") or []
        if asks:
            lines.extend(f"Ask: {item}" for item in asks)
    if data.get("validity_scope"):
        lines.append(f"Validity scope: {data['validity_scope']}")
    return "\n".join(lines)


def command_with_optional_explain(command: str, argv: list[str]) -> int:
    explain = False
    filtered: list[str] = []
    for item in argv:
        if item == "--explain-like-human":
            explain = True
        else:
            filtered.append(item)
    if not explain:
        return run_script(command, filtered)
    code, data, raw = capture_script_json(command, filtered)
    if data is None:
        print(raw, end="")
        return code
    print(human_explanation(data))
    return code


def demo_command(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Run the Causal Halting end-to-end demo.")
    parser.add_argument("--output", default=".tmp/demo", help="Directory for demo artifacts.")
    parser.add_argument("--format", choices=("human", "json"), default="human")
    args = parser.parse_args(argv)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    design_module = load_script("chc_design_analyze.py")
    repair_module = load_script("chc_repair.py")
    verify_module = load_script("chc_verify_repair.py")
    report_module = load_script("chc_report.py")

    input_design = EXAMPLES / "demo" / "input.design-ir.json"
    before_trace = EXAMPLES / "demo" / "before.trace.jsonl"
    after_trace = EXAMPLES / "demo" / "after.trace.jsonl"

    analysis = design_module.analyze_design(input_design.read_text(encoding="utf-8"))
    repair = repair_module.repair_analysis(analysis)
    verification = verify_module.verify_repair(
        before_trace.read_text(encoding="utf-8"),
        after_trace.read_text(encoding="utf-8"),
        repair.get("proof_obligations"),
    )
    certificate = verify_module.repair_certificate(verification)
    report = report_module.render_markdown(analysis)

    artifacts = {
        "analysis.json": analysis,
        "repair.json": repair,
        "verification.json": verification,
        "certificate.json": certificate,
    }
    for filename, payload in artifacts.items():
        (output_dir / filename).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "report.md").write_text(report, encoding="utf-8")
    shutil.copyfile(input_design, output_dir / "input.design-ir.json")
    shutil.copyfile(before_trace, output_dir / "before.trace.jsonl")
    shutil.copyfile(after_trace, output_dir / "after.trace.jsonl")

    summary = {
        "status": "passed" if verification.get("verification") == "passed" else "failed",
        "output": str(output_dir),
        "analysis_classification": analysis.get("classification"),
        "repair_verification": verification.get("verification"),
        "validity_scope": analysis.get("validity_scope"),
        "artifacts": sorted([path.name for path in output_dir.iterdir() if path.is_file()]),
    }
    if args.format == "json":
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"status: {summary['status']}")
        print(f"analysis_classification: {summary['analysis_classification']}")
        print(f"repair_verification: {summary['repair_verification']}")
        print(f"output: {summary['output']}")
        print("artifacts:")
        for artifact in summary["artifacts"]:
            print(f"  - {artifact}")
    return 0 if summary["status"] == "passed" else 1


def version_command(_: list[str]) -> int:
    print(f"causal-halting {__version__}")
    return 0


def print_help() -> None:
    commands = sorted([*SCRIPT_BY_COMMAND, "demo", "version"])
    print("usage: chc <command> [args...]")
    print("")
    print("Commands:")
    for command in commands:
        print(f"  {command}")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print_help()
        return 0
    command, *remainder = argv
    handlers: dict[str, Callable[[list[str]], int]] = {
        "demo": demo_command,
        "version": version_command,
    }
    if command in handlers:
        return handlers[command](remainder)
    if command in SCRIPT_BY_COMMAND:
        return command_with_optional_explain(command, remainder)
    print(f"Unknown command: {command}", file=sys.stderr)
    print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
