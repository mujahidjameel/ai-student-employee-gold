"""
AI Employee Vault — Claude Code PostToolUse Audit Hook
=======================================================

Registered in .claude/settings.json as a PostToolUse hook.
Claude Code sends a JSON object to stdin after every tool call;
this script parses it and writes one CLAUDE_TOOL_USE entry to the
daily audit log.

stdin schema (from Claude Code):
{
  "session_id": "...",
  "tool_name":  "Write",
  "tool_input": { "file_path": "...", "content": "..." },
  "tool_response": { "success": true, ... }
}

This script never blocks Claude (exits 0 always, writes nothing to stdout).
Errors go to stderr only so they appear in Claude Code's debug log.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add scripts/ to path so we can import audit_logger
sys.path.insert(0, str(Path(__file__).parent))

from audit_logger import Action, audit


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return

        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"[audit_tool_hook] Failed to parse stdin: {exc}", file=sys.stderr)
        return

    tool_name: str  = data.get("tool_name", "unknown")
    tool_input: dict = data.get("tool_input", {})
    tool_response: dict = data.get("tool_response", {})

    # Derive a human-readable target from tool_input
    target = (
        tool_input.get("file_path")
        or tool_input.get("path")
        or tool_input.get("pattern")
        or tool_input.get("command", "")[:80]
        or tool_input.get("url", "")[:80]
        or ""
    )
    if target:
        target = Path(target).name if "/" in target or "\\" in target else target

    # Determine outcome from tool_response
    outcome = "success"
    if isinstance(tool_response, dict):
        if tool_response.get("error") or not tool_response.get("success", True):
            outcome = "failure"

    # Build a concise detail dict — strip large content fields
    detail: dict = {"tool": tool_name}
    if tool_input:
        safe_input = {
            k: (str(v)[:120] if isinstance(v, str) and len(str(v)) > 120 else v)
            for k, v in tool_input.items()
            if k not in ("content", "new_string", "old_string")  # skip large payloads
        }
        if safe_input:
            detail["input"] = safe_input

    if isinstance(tool_response, dict):
        error_msg = tool_response.get("error", "")
        if error_msg:
            detail["response_error"] = str(error_msg)[:200]

    try:
        audit(
            Action.CLAUDE_TOOL_USE,
            script="claude-code",
            target=target,
            detail=detail,
            outcome=outcome,
        )
    except Exception as exc:
        print(f"[audit_tool_hook] Failed to write audit entry: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
