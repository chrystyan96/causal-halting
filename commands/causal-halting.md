---
description: Manage Causal Halting mode and checker
argument-hint: [on|off|status|explain|check] [file]
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
