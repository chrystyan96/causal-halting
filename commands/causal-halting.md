---
description: Manage Causal Halting mode, checker, design/trace analysis, workflow adapters, and repair verification
argument-hint: [on|off|status|explain|check|analyze-design|analyze-trace|repair|adapt-workflow|verify-repair] [args]
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
analyze-design <design-ir-json-file>
analyze-trace <jsonl-file>
repair <analysis-json>
adapt-workflow <workflow-json>
verify-repair <trace-before> <trace-after>
```

If no argument is provided, use `status`.

Important design-analysis rule:

```text
The script does not understand prose.
For natural-language design requests, first interpret the design semantically into DesignIR.
Then run analyze-design on the DesignIR JSON.
Never classify prose directly and never use keyword presence as evidence.
```

Run the mode command only after any required DesignIR extraction is complete:

```text
!`python "${CLAUDE_PLUGIN_ROOT}/scripts/chc_session_guard.py" "$@" --format human`
```

After the command output is available:

- For `on`, `off`, or `status`, report only the resulting status in one short sentence.
- For `explain`, summarize the guard in two short sentences.
- For `check`, report the checker classification and semantic status. Do not add claims beyond the checker output.
- For `analyze-design`, report the DesignIR classification, graph, uncertain edges, and repair recommendations. If the output is `needs_design_ir`, provide the DesignIR that should be analyzed next instead of making a classification.
- For `analyze-trace`, report the deterministic trace classification and exact feedback path when present.
- For `repair`, report the before/after causal boundary and proof obligations.
- For `adapt-workflow`, report the generated JSONL events and say they still need trace analysis.
- For `verify-repair`, report whether verification passed, with before/after classifications.
