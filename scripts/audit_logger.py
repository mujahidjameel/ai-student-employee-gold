"""
AI Employee Vault — Audit Logging System
=========================================

Every action the AI employee takes is recorded here: file I/O, API calls,
task lifecycle events, HITL decisions, script runs, and Claude tool calls.

Log format : JSONL (one JSON object per line) — easy to append and grep.
Log files  : logs/audit/YYYY-MM-DD.jsonl   (one file per day, auto-rotated)
Session ID : UUID4 generated once per process — trace a full script run.

Usage (import in any vault script):
------------------------------------
    from audit_logger import audit, Action, audited, audit_action

    # One-shot log entry
    audit(Action.FILE_READ, target="Dashboard.md", detail={"lines": 61})

    # Context manager — captures duration and outcome automatically
    with audit_action(Action.API_CALL, target="gemini-2.5-flash", script=__file__):
        response = client.models.generate_content(...)

    # Decorator — same as context manager but wraps a whole function
    @audited(Action.PLAN_GENERATED, script=__file__)
    def generate_plan():
        ...

CLI:
----
    python audit_logger.py tail [--n 20]
    python audit_logger.py show  --date 2026-03-28
    python audit_logger.py filter --action API_CALL --script plan_generator.py
    python audit_logger.py summary [--date 2026-03-28]
    python audit_logger.py sessions [--date 2026-03-28]
"""

from __future__ import annotations

import contextlib
import fcntl
import functools
import json
import os
import sys
import time
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator, TypeVar

# ── Vault paths ──────────────────────────────────────────────────────────────
VAULT     = Path(__file__).resolve().parent.parent
AUDIT_DIR = VAULT / "logs" / "audit"
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

F = TypeVar("F", bound=Callable[..., Any])

# ── Session identity ─────────────────────────────────────────────────────────
# One UUID per process launch. All entries from the same script run share it.
_SESSION_ID: str = str(uuid.uuid4())[:8]
_PID:        int = os.getpid()


# ══════════════════════════════════════════════════════════════════════════════
# 1. Action Taxonomy
# ══════════════════════════════════════════════════════════════════════════════

class Action(str, Enum):
    # ── File operations ──────────────────────────────────────────────────────
    FILE_READ        = "FILE_READ"        # any file read
    FILE_WRITE       = "FILE_WRITE"       # any file write / create
    FILE_MOVE        = "FILE_MOVE"        # move between vault folders
    FILE_DELETE      = "FILE_DELETE"      # deletion (rare; needs HITL)

    # ── API / network ────────────────────────────────────────────────────────
    API_CALL         = "API_CALL"         # Gemini, Gmail, any HTTP
    API_SUCCESS      = "API_SUCCESS"      # API call completed OK
    API_FAILURE      = "API_FAILURE"      # API call failed (all retries exhausted)

    # ── Script lifecycle ─────────────────────────────────────────────────────
    SCRIPT_START     = "SCRIPT_START"     # subprocess launched
    SCRIPT_SUCCESS   = "SCRIPT_SUCCESS"   # subprocess exited 0
    SCRIPT_FAILURE   = "SCRIPT_FAILURE"   # subprocess exited non-zero / crashed

    # ── Task lifecycle ───────────────────────────────────────────────────────
    TASK_CREATED     = "TASK_CREATED"     # new task note written to /Needs_Action
    TASK_UPDATED     = "TASK_UPDATED"     # task note edited in place
    TASK_COMPLETED   = "TASK_COMPLETED"   # task moved to /Done
    TASK_ESCALATED   = "TASK_ESCALATED"   # task flagged as blocked / urgent

    # ── Email ────────────────────────────────────────────────────────────────
    EMAIL_INGESTED   = "EMAIL_INGESTED"   # gmail_watcher saved email as task note
    EMAIL_SENT       = "EMAIL_SENT"       # mcp_email_sender dispatched an email

    # ── Human-in-the-loop ────────────────────────────────────────────────────
    HITL_REQUEST     = "HITL_REQUEST"     # hitl_approval.py prompted user
    HITL_APPROVED    = "HITL_APPROVED"    # user typed Y
    HITL_DENIED      = "HITL_DENIED"      # user typed N or non-interactive deny

    # ── Vault maintenance ────────────────────────────────────────────────────
    VAULT_HEALTH     = "VAULT_HEALTH"     # VaultHealthCheck.run() called
    ALERT_FIRED      = "ALERT_FIRED"      # error_recovery.alert() called
    PLAN_GENERATED   = "PLAN_GENERATED"   # plan_generator.py produced Plan.md
    BRIEFING_GENERATED = "BRIEFING_GENERATED"  # ceo_briefing.py produced briefing

    # ── Claude Code tool calls ───────────────────────────────────────────────
    CLAUDE_TOOL_USE  = "CLAUDE_TOOL_USE"  # any Claude Code tool (Read, Write, Bash…)
    CLAUDE_STOP      = "CLAUDE_STOP"      # claude finished responding (stop hook)

    # ── Session bookends ─────────────────────────────────────────────────────
    SESSION_START    = "SESSION_START"    # logged once when audit_logger is imported
    SESSION_END      = "SESSION_END"      # logged when process exits (atexit)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Log Entry Schema
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class LogEntry:
    """
    One audit record. Every field except `ts` and `action` is optional.

    Fields
    ------
    ts          ISO-8601 timestamp with microseconds.
    date        YYYY-MM-DD (for easy filtering without parsing ts).
    session_id  8-char hex shared by all entries in one process run.
    pid         OS process ID.
    script      Basename of the calling script (e.g. "plan_generator.py").
    action      Action enum value (string in JSON).
    target      What the action operated on: filename, URL, model name, etc.
    detail      Arbitrary dict of extra context.
    outcome     "success" | "failure" | "pending" | "denied" | "approved".
    duration_ms Wall-clock milliseconds (set by audit_action context manager).
    error       Exception message if outcome == "failure".
    """
    ts:          str
    date:        str
    session_id:  str
    pid:         int
    action:      str
    script:      str  = ""
    target:      str  = ""
    detail:      dict = field(default_factory=dict)
    outcome:     str  = "success"
    duration_ms: int  = 0
    error:       str  = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Writer
# ══════════════════════════════════════════════════════════════════════════════

def _log_path(for_date: date | None = None) -> Path:
    d = for_date or date.today()
    return AUDIT_DIR / f"{d.isoformat()}.jsonl"


def _write_entry(entry: LogEntry) -> None:
    """Append one JSONL line to today's audit file. Thread-safe via flock."""
    path = _log_path()
    line = entry.to_json() + "\n"
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fcntl.flock(fh, fcntl.LOCK_EX)
            try:
                fh.write(line)
            finally:
                fcntl.flock(fh, fcntl.LOCK_UN)
    except OSError:
        # Absolute last resort: print to stderr so nothing is silently lost
        print(f"[audit_logger] WRITE FAILED: {line.strip()}", file=sys.stderr)


def _resolve_script(script: str | Path | None) -> str:
    if not script:
        return ""
    return Path(script).name


# ══════════════════════════════════════════════════════════════════════════════
# 4. Public API — audit(), audit_action(), @audited
# ══════════════════════════════════════════════════════════════════════════════

def audit(
    action: Action | str,
    *,
    script:      str | Path = "",
    target:      str        = "",
    detail:      dict       = None,
    outcome:     str        = "success",
    duration_ms: int        = 0,
    error:       str        = "",
) -> None:
    """
    Write a single audit entry immediately.

    Args:
        action:      Action enum (or raw string for one-off custom actions).
        script:      Calling script name / path.
        target:      File path, URL, model name, or other subject of the action.
        detail:      Dict of extra context (counts, sizes, params, etc.).
        outcome:     "success" | "failure" | "pending" | "denied" | "approved".
        duration_ms: Elapsed time in ms (leave 0 if not measured).
        error:       Exception message on failure.
    """
    now = datetime.now()
    entry = LogEntry(
        ts          = now.isoformat(timespec="microseconds"),
        date        = now.date().isoformat(),
        session_id  = _SESSION_ID,
        pid         = _PID,
        action      = action.value if isinstance(action, Action) else str(action),
        script      = _resolve_script(script),
        target      = target,
        detail      = detail or {},
        outcome     = outcome,
        duration_ms = duration_ms,
        error       = error,
    )
    _write_entry(entry)


@contextmanager
def audit_action(
    action: Action | str,
    *,
    script:  str | Path = "",
    target:  str        = "",
    detail:  dict       = None,
) -> Iterator[None]:
    """
    Context manager — logs start timing, then writes the entry on exit
    with duration_ms and outcome set automatically.

    Usage:
        with audit_action(Action.API_CALL, target="gemini-2.5-flash",
                          script=__file__):
            response = call_api(prompt)
    """
    t0 = time.monotonic()
    try:
        yield
        elapsed = int((time.monotonic() - t0) * 1000)
        audit(action, script=script, target=target, detail=detail,
              outcome="success", duration_ms=elapsed)
    except Exception as exc:
        elapsed = int((time.monotonic() - t0) * 1000)
        audit(action, script=script, target=target, detail=detail,
              outcome="failure", duration_ms=elapsed,
              error=f"{type(exc).__name__}: {exc}")
        raise


def audited(
    action: Action | str,
    *,
    script:     str | Path = "",
    target_arg: str        = "",   # name of a kwarg to use as `target`
) -> Callable[[F], F]:
    """
    Decorator — wraps a function with audit_action().

    Usage:
        @audited(Action.PLAN_GENERATED, script=__file__)
        def generate_plan():
            ...

        @audited(Action.FILE_READ, script=__file__, target_arg="path")
        def read_file(path: Path):
            ...
    """
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            target = str(kwargs.get(target_arg, "")) if target_arg else ""
            with audit_action(action, script=script or fn.__module__, target=target):
                return fn(*args, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# 5. Session bookend — log SESSION_START on import, SESSION_END on exit
# ══════════════════════════════════════════════════════════════════════════════

def _session_start() -> None:
    script_name = Path(sys.argv[0]).name if sys.argv else ""
    audit(
        Action.SESSION_START,
        script=script_name,
        detail={"argv": sys.argv, "python": sys.version.split()[0]},
    )


def _session_end() -> None:
    import atexit as _atexit  # already registered; just being explicit
    script_name = Path(sys.argv[0]).name if sys.argv else ""
    audit(Action.SESSION_END, script=script_name)


import atexit as _atexit_module
_atexit_module.register(_session_end)
_session_start()


# ══════════════════════════════════════════════════════════════════════════════
# 6. Reader helpers — used by the CLI
# ══════════════════════════════════════════════════════════════════════════════

def read_entries(
    for_date:   date | None  = None,
    action:     str          = "",
    script:     str          = "",
    outcome:    str          = "",
    session_id: str          = "",
    limit:      int          = 0,
) -> list[dict]:
    """
    Read and filter audit entries from a JSONL file.

    Args:
        for_date:   Which day's file to read (default: today).
        action:     Filter by action string (substring match, case-insensitive).
        script:     Filter by script name (substring match).
        outcome:    Filter by outcome ("success", "failure", etc.).
        session_id: Filter by session_id prefix.
        limit:      Return at most this many entries (0 = all).
    """
    path = _log_path(for_date)
    if not path.exists():
        return []

    entries = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue

            if action     and action.lower()     not in e.get("action", "").lower():
                continue
            if script     and script.lower()     not in e.get("script", "").lower():
                continue
            if outcome    and outcome.lower()    != e.get("outcome", "").lower():
                continue
            if session_id and not e.get("session_id", "").startswith(session_id):
                continue

            entries.append(e)

    if limit:
        entries = entries[-limit:]
    return entries


def summarise(entries: list[dict]) -> dict:
    """Return aggregate counts over a list of entries."""
    from collections import Counter
    actions  = Counter(e["action"]  for e in entries)
    scripts  = Counter(e["script"]  for e in entries if e.get("script"))
    outcomes = Counter(e["outcome"] for e in entries)
    failures = [e for e in entries if e.get("outcome") == "failure"]

    total_ms = sum(e.get("duration_ms", 0) for e in entries)
    avg_ms   = total_ms // len(entries) if entries else 0

    return {
        "total":      len(entries),
        "outcomes":   dict(outcomes),
        "by_action":  dict(actions.most_common(10)),
        "by_script":  dict(scripts.most_common(10)),
        "failures":   len(failures),
        "avg_ms":     avg_ms,
        "sessions":   len(set(e.get("session_id") for e in entries)),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. CLI
# ══════════════════════════════════════════════════════════════════════════════

def _fmt_entry(e: dict) -> str:
    ts      = e.get("ts", "")[:19].replace("T", " ")
    sess    = e.get("session_id", "?")[:6]
    action  = e.get("action", "?")[:22]
    script  = (e.get("script") or "—")[:24]
    target  = (e.get("target") or "—")[:35]
    outcome = e.get("outcome", "?")
    ms      = e.get("duration_ms", 0)
    err     = f"  !! {e['error'][:60]}" if e.get("error") else ""

    outcome_marker = {"success": "✅", "failure": "🔴", "denied": "🚫",
                      "approved": "✅", "pending": "⏳"}.get(outcome, "•")

    ms_str = f"{ms}ms" if ms else ""
    return (
        f"{ts}  [{sess}]  {action:<22}  {script:<24}  {target:<35}"
        f"  {outcome_marker} {ms_str}{err}"
    )


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="audit_logger",
        description="AI Employee Vault — Audit Log Viewer",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # tail
    p_tail = sub.add_parser("tail", help="Show the most recent N entries from today")
    p_tail.add_argument("--n",      type=int, default=20, help="Number of entries (default 20)")
    p_tail.add_argument("--script", default="",           help="Filter by script name")
    p_tail.add_argument("--action", default="",           help="Filter by action type")

    # show
    p_show = sub.add_parser("show", help="Show all entries for a specific date")
    p_show.add_argument("--date",   required=True, help="Date: YYYY-MM-DD")
    p_show.add_argument("--script", default="",    help="Filter by script name")
    p_show.add_argument("--action", default="",    help="Filter by action type")
    p_show.add_argument("--outcome",default="",    help="Filter by outcome")

    # filter
    p_filt = sub.add_parser("filter", help="Filter entries across any combination of fields")
    p_filt.add_argument("--date",    default="",  help="Date: YYYY-MM-DD (default: today)")
    p_filt.add_argument("--action",  default="",  help="Action substring (e.g. API_CALL)")
    p_filt.add_argument("--script",  default="",  help="Script substring")
    p_filt.add_argument("--outcome", default="",  help="Outcome: success|failure|denied")
    p_filt.add_argument("--session", default="",  help="Session ID prefix")
    p_filt.add_argument("--n",       type=int, default=0, help="Limit results")

    # summary
    p_sum = sub.add_parser("summary", help="Aggregate statistics for a day")
    p_sum.add_argument("--date", default="", help="Date: YYYY-MM-DD (default: today)")

    # sessions
    p_sess = sub.add_parser("sessions", help="List unique sessions for a day")
    p_sess.add_argument("--date", default="", help="Date: YYYY-MM-DD (default: today)")

    # actions
    sub.add_parser("actions", help="List all available action types")

    # files
    sub.add_parser("files", help="List all audit log files on disk")

    args = parser.parse_args()

    def _parse_date(s: str) -> date | None:
        if not s:
            return None
        try:
            return date.fromisoformat(s)
        except ValueError:
            print(f"Invalid date: {s}  (expected YYYY-MM-DD)", file=sys.stderr)
            sys.exit(1)

    # ── tail ─────────────────────────────────────────────────────────────────
    if args.cmd == "tail":
        entries = read_entries(action=args.action, script=args.script, limit=args.n)
        if not entries:
            print("No entries found.")
            return
        print(f"{'Timestamp':<19}  {'Sess':<6}  {'Action':<22}  {'Script':<24}  {'Target':<35}  Outcome")
        print("-" * 130)
        for e in entries:
            print(_fmt_entry(e))

    # ── show ─────────────────────────────────────────────────────────────────
    elif args.cmd == "show":
        d = _parse_date(args.date)
        entries = read_entries(for_date=d, action=args.action,
                               script=args.script, outcome=args.outcome)
        if not entries:
            print(f"No entries for {args.date}.")
            return
        print(f"{'Timestamp':<19}  {'Sess':<6}  {'Action':<22}  {'Script':<24}  {'Target':<35}  Outcome")
        print("-" * 130)
        for e in entries:
            print(_fmt_entry(e))
        print(f"\n{len(entries)} entries.")

    # ── filter ────────────────────────────────────────────────────────────────
    elif args.cmd == "filter":
        d = _parse_date(args.date)
        entries = read_entries(for_date=d, action=args.action, script=args.script,
                               outcome=args.outcome, session_id=args.session, limit=args.n)
        if not entries:
            print("No matching entries.")
            return
        print(f"{'Timestamp':<19}  {'Sess':<6}  {'Action':<22}  {'Script':<24}  {'Target':<35}  Outcome")
        print("-" * 130)
        for e in entries:
            print(_fmt_entry(e))
        print(f"\n{len(entries)} entries.")

    # ── summary ───────────────────────────────────────────────────────────────
    elif args.cmd == "summary":
        d = _parse_date(args.date)
        label = (d or date.today()).isoformat()
        entries = read_entries(for_date=d)
        if not entries:
            print(f"No entries for {label}.")
            return
        s = summarise(entries)
        print(f"\nAudit Summary — {label}")
        print("=" * 40)
        print(f"  Total entries  : {s['total']}")
        print(f"  Sessions       : {s['sessions']}")
        print(f"  Failures       : {s['failures']}")
        print(f"  Avg duration   : {s['avg_ms']}ms")
        print(f"\n  Outcomes:")
        for k, v in sorted(s["outcomes"].items()):
            print(f"    {k:<12} {v}")
        print(f"\n  Top actions:")
        for k, v in s["by_action"].items():
            print(f"    {k:<28} {v}")
        print(f"\n  Top scripts:")
        for k, v in s["by_script"].items():
            print(f"    {k:<28} {v}")

    # ── sessions ──────────────────────────────────────────────────────────────
    elif args.cmd == "sessions":
        d = _parse_date(args.date)
        entries = read_entries(for_date=d)
        if not entries:
            print("No entries found.")
            return
        seen: dict[str, list] = {}
        for e in entries:
            sid = e.get("session_id", "?")
            seen.setdefault(sid, []).append(e)
        print(f"\n{'Session':<10}  {'Script':<28}  {'Start':<19}  {'End':<19}  {'Entries':>7}  {'Failures':>8}")
        print("-" * 105)
        for sid, evs in seen.items():
            start   = evs[0]["ts"][:19].replace("T", " ")
            end     = evs[-1]["ts"][:19].replace("T", " ")
            scripts = ", ".join(sorted({e.get("script","?") for e in evs if e.get("script")}))
            fails   = sum(1 for e in evs if e.get("outcome") == "failure")
            print(f"{sid:<10}  {scripts[:28]:<28}  {start}  {end}  {len(evs):>7}  {fails:>8}")

    # ── actions ───────────────────────────────────────────────────────────────
    elif args.cmd == "actions":
        print("\nAvailable action types:")
        groups = {
            "File":       [a for a in Action if a.name.startswith("FILE")],
            "API":        [a for a in Action if a.name.startswith("API")],
            "Script":     [a for a in Action if a.name.startswith("SCRIPT")],
            "Task":       [a for a in Action if a.name.startswith("TASK")],
            "Email":      [a for a in Action if a.name.startswith("EMAIL")],
            "HITL":       [a for a in Action if a.name.startswith("HITL")],
            "Vault":      [a for a in Action if a.name in
                          ("VAULT_HEALTH","ALERT_FIRED","PLAN_GENERATED","BRIEFING_GENERATED")],
            "Claude":     [a for a in Action if a.name.startswith("CLAUDE")],
            "Session":    [a for a in Action if a.name.startswith("SESSION")],
        }
        for group, actions in groups.items():
            print(f"\n  {group}:")
            for a in actions:
                print(f"    {a.value}")

    # ── files ─────────────────────────────────────────────────────────────────
    elif args.cmd == "files":
        files = sorted(AUDIT_DIR.glob("*.jsonl"), reverse=True)
        if not files:
            print("No audit log files yet.")
            return
        print(f"\n{'File':<32}  {'Size':>8}  {'Entries':>8}")
        print("-" * 55)
        total_entries = 0
        for f in files:
            size    = f.stat().st_size
            entries = sum(1 for _ in open(f, encoding="utf-8") if _.strip())
            total_entries += entries
            print(f"{f.name:<32}  {size:>7}B  {entries:>8}")
        print(f"\n{len(files)} file(s), {total_entries} total entries.")


if __name__ == "__main__":
    _cli()
