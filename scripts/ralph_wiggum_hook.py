#!/usr/bin/env python3
"""
Ralph Wiggum Stop Hook
======================
"I'm helping!" — Ralph Wiggum

A Claude Code stop hook that blocks Claude from stopping while there are
unprocessed tasks in /Needs_Action. Claude keeps working until every task
note has been moved to /Done.

Context: Student AI Employee Vault
  - University assignments (essays, labs, exams, projects)
  - Panaversity Agentic AI course modules and exercises

How it works:
  1. Scans /Needs_Action for .md task files.
  2. If any remain, outputs a JSON block decision telling Claude exactly
     what still needs doing — Claude cannot stop until the list is empty.
  3. If /Needs_Action is empty, exits silently (Claude may stop normally).

Claude Code stop hook protocol:
  - stdout: JSON  {"decision": "block", "reason": "<message>"}  → forces re-prompt
  - stdout: empty / exit 0  → Claude stops normally
"""

import json
import os
import sys
from pathlib import Path

# ── Vault root is two levels up from scripts/ ──────────────────────────────
VAULT_ROOT = Path(__file__).resolve().parent.parent
NEEDS_ACTION = VAULT_ROOT / "Needs_Action"
DONE = VAULT_ROOT / "Done"


def list_pending_tasks() -> list[str]:
    """Return file names of all .md task notes currently in /Needs_Action."""
    if not NEEDS_ACTION.exists():
        return []
    return sorted(
        p.name for p in NEEDS_ACTION.iterdir()
        if p.is_file() and p.suffix == ".md"
    )


def summarise_tasks(tasks: list[str]) -> str:
    """Build a human-readable summary of the pending task list."""
    lines = []
    for i, name in enumerate(tasks, 1):
        stem = Path(name).stem
        lines.append(f"  {i}. {stem}")
    return "\n".join(lines)


def main() -> None:
    pending = list_pending_tasks()

    if not pending:
        # All clear — let Claude stop normally.
        sys.exit(0)

    count = len(pending)
    task_list = summarise_tasks(pending)

    reason = (
        f"RALPH WIGGUM SAYS: I'm not done yet!\n\n"
        f"There {'is' if count == 1 else 'are'} still {count} unprocessed "
        f"task{'s' if count != 1 else ''} in /Needs_Action that must be "
        f"completed and moved to /Done before you stop.\n\n"
        f"Pending tasks:\n{task_list}\n\n"
        f"Instructions:\n"
        f"  1. Open each task note in /Needs_Action.\n"
        f"  2. Read the Desired Outcome and complete the required work:\n"
        f"       • University assignments → draft outline, summarise requirements,\n"
        f"         set deadline reminder in Dashboard.md, flag blockers.\n"
        f"       • Panaversity AI modules → log progress in Dashboard.md,\n"
        f"         extract key concepts, create a study note in /Done when complete.\n"
        f"       • Emails / general tasks → action or respond as directed.\n"
        f"  3. Append a ## Resolution section to the task note.\n"
        f"  4. Move the completed note from /Needs_Action/ to /Done/.\n"
        f"  5. Update Dashboard.md to reflect the new state.\n"
        f"  6. Only stop when /Needs_Action is completely empty.\n\n"
        f"Do not stop. Keep going until every task is done."
    )

    output = {"decision": "block", "reason": reason}
    print(json.dumps(output))
    sys.exit(0)


if __name__ == "__main__":
    main()
