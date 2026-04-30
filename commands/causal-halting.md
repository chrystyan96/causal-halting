---
description: Manage Causal Halting mode, checker, design analysis, trace analysis, and repairs
argument-hint: [on|off|status|explain|check|analyze-design|analyze-trace|repair] [file-or-text]
allowed-tools: Bash(python:*)
---

Manage Causal Halting for this workspace.

Valid modes:

```text
on
off
status
explain
check <file>
analyze-design <text-or-file>
analyze-trace <jsonl-file>
repair <analysis-json>
```

If no argument is provided, use `status`.

Run the mode command:

```text
!`python "${CLAUDE_PLUGIN_ROOT}/scripts/chc_session_guard.py" "$1" "$2" --format human`
```

After the command output is available:

- For `on`, `off`, or `status`, report only the resulting status in one short sentence.
- For `explain`, summarize the guard in two short sentences.
- For `check`, report the checker classification and semantic status. Do not add claims beyond the checker output.
- For `analyze-design`, report the inferred classification, graph, uncertain edges, and repair recommendations. State that this is an inferred model.
- For `analyze-trace`, report the deterministic trace classification and exact feedback path when present.
- For `repair`, report the before/after causal boundary and proof obligations.
