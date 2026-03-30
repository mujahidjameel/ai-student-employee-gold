# Audit Logging Skill

**Date:** 2026-03-28
**Owner:** AI Employee
**Status:** active
**Scripts:** `scripts/audit_logger.py` · `scripts/audit_tool_hook.py`

---

## What It Does

Every action the AI employee takes — reading a file, calling Gemini, creating a
task note, sending an email, running a script, getting HITL approval — is recorded
as a structured JSON entry in a daily log file.

This gives you a complete, timestamped, queryable trail of everything that happened
in the vault, which session did it, how long it took, and whether it succeeded.

**Two components work together:**

| Component | Role |
|---|---|
| `audit_logger.py` | Core module — writes entries, provides `audit()`, `audit_action()`, `@audited`, and the CLI |
| `audit_tool_hook.py` | PostToolUse hook — captures every Claude Code tool call automatically |

---

## Log Storage

```
logs/audit/
├── 2026-03-28.jsonl      ← today (one JSON object per line)
├── 2026-03-27.jsonl
└── ...
```

One file per day. Auto-rotated at midnight. Each line is a complete, self-contained
JSON record — easy to `grep`, pipe to `jq`, or load into a spreadsheet.

**Never delete these files.** They are your permanent record of AI employee activity.

---

## Log Entry Schema

```json
{
  "ts":          "2026-03-28T09:15:42.103847",
  "date":        "2026-03-28",
  "session_id":  "a1b2c3d4",
  "pid":         12345,
  "script":      "plan_generator.py",
  "action":      "API_CALL",
  "target":      "gemini-2.5-flash",
  "detail":      { "model": "gemini-2.5-flash", "prompt_len": 4200 },
  "outcome":     "success",
  "duration_ms": 3421,
  "error":       ""
}
```

| Field | Description |
|---|---|
| `ts` | ISO-8601 with microseconds |
| `date` | YYYY-MM-DD (fast date filtering without parsing `ts`) |
| `session_id` | 8-char UUID prefix shared by all entries in one process run |
| `pid` | OS process ID |
| `script` | Which vault script wrote this entry |
| `action` | Action type (see taxonomy below) |
| `target` | File path, URL, model name, email address, etc. |
| `detail` | Arbitrary dict — counts, sizes, parameters |
| `outcome` | `success` · `failure` · `pending` · `approved` · `denied` |
| `duration_ms` | Wall-clock ms (0 if not measured) |
| `error` | Exception message on failure |

---

## Action Taxonomy

| Group | Actions |
|---|---|
| **File** | `FILE_READ` `FILE_WRITE` `FILE_MOVE` `FILE_DELETE` |
| **API** | `API_CALL` `API_SUCCESS` `API_FAILURE` |
| **Script** | `SCRIPT_START` `SCRIPT_SUCCESS` `SCRIPT_FAILURE` |
| **Task** | `TASK_CREATED` `TASK_UPDATED` `TASK_COMPLETED` `TASK_ESCALATED` |
| **Email** | `EMAIL_INGESTED` `EMAIL_SENT` |
| **HITL** | `HITL_REQUEST` `HITL_APPROVED` `HITL_DENIED` |
| **Vault** | `VAULT_HEALTH` `ALERT_FIRED` `PLAN_GENERATED` `BRIEFING_GENERATED` |
| **Claude** | `CLAUDE_TOOL_USE` `CLAUDE_STOP` |
| **Session** | `SESSION_START` `SESSION_END` |

Run `python audit_logger.py actions` to see the full list at any time.

---

## Automatic Capture (No Code Changes Needed)

The **PostToolUse hook** in `.claude/settings.json` fires `audit_tool_hook.py` after
every Claude Code tool call. This means `Read`, `Write`, `Edit`, `Bash`, `Glob`,
`Grep`, `WebFetch` — all logged automatically with zero changes to existing scripts.

```
Claude uses Write tool
         │
         ▼
PostToolUse hook fires
         │
         ▼
audit_tool_hook.py reads stdin JSON
         │
         ▼
logs/audit/2026-03-28.jsonl ← one CLAUDE_TOOL_USE entry appended
```

---

## Integration Guide

### One-shot log entry

```python
from audit_logger import audit, Action

audit(Action.FILE_READ, script=__file__, target="Dashboard.md",
      detail={"lines": 61})

audit(Action.TASK_COMPLETED, script=__file__, target="2026-03-28 Task - essay.md",
      detail={"moved_to": "Done"})

audit(Action.HITL_DENIED, script=__file__, target="delete Inbox/old.md",
      outcome="denied")
```

### Context manager — auto-times and captures failures

```python
from audit_logger import audit_action, Action

with audit_action(Action.API_CALL, script=__file__, target="gemini-2.5-flash",
                  detail={"prompt_chars": len(prompt)}):
    response = client.models.generate_content(model=MODEL, contents=prompt)
# → writes entry with duration_ms set; outcome="failure" + error= on exception
```

### Decorator — wraps an entire function

```python
from audit_logger import audited, Action

@audited(Action.PLAN_GENERATED, script=__file__)
def generate_plan() -> str:
    ...

@audited(Action.FILE_READ, script=__file__, target_arg="path")
def read_inbox(path: Path) -> str:
    ...
```

### Integrate with error_recovery alerts

```python
from audit_logger import audit, Action
from error_recovery import alert, AlertLevel

# Log the alert as an audit entry too
audit(Action.ALERT_FIRED, script=__file__,
      target="gmail_watcher.py",
      detail={"level": "ERROR", "message": "Token expired"},
      outcome="failure")
alert("Gmail token expired", level=AlertLevel.ERROR, script=__file__)
```

---

## CLI Reference

```bash
# Last 20 entries from today
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/audit_logger.py tail

# Last 50, filter by script
python audit_logger.py tail --n 50 --script plan_generator.py

# All entries for a specific date
python audit_logger.py show --date 2026-03-28

# Filter: failures only, today
python audit_logger.py filter --outcome failure

# Filter: API calls on a specific day
python audit_logger.py filter --date 2026-03-28 --action API_CALL

# Filter: everything a specific session did
python audit_logger.py filter --session a1b2c3d4

# Daily summary statistics
python audit_logger.py summary

python audit_logger.py summary --date 2026-03-27

# List all sessions and their activity ranges
python audit_logger.py sessions

# List all action types
python audit_logger.py actions

# List all log files with sizes and entry counts
python audit_logger.py files
```

**Sample `tail` output:**
```
Timestamp            Sess    Action                  Script                    Target                               Outcome
────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
2026-03-28 09:15:40  [a1b2c3]  SESSION_START           plan_generator.py         —                                    ✅
2026-03-28 09:15:41  [a1b2c3]  FILE_READ               plan_generator.py         Dashboard.md                         ✅ 12ms
2026-03-28 09:15:41  [a1b2c3]  FILE_READ               plan_generator.py         2026-03-28 Task - essay.md           ✅ 3ms
2026-03-28 09:15:44  [a1b2c3]  API_CALL                plan_generator.py         gemini-2.5-flash                     ✅ 3421ms
2026-03-28 09:15:44  [a1b2c3]  PLAN_GENERATED          plan_generator.py         Plan.md                              ✅ 3892ms
2026-03-28 09:15:44  [a1b2c3]  FILE_WRITE              plan_generator.py         Plan.md                              ✅ 8ms
2026-03-28 09:15:44  [a1b2c3]  SESSION_END             plan_generator.py         —                                    ✅
2026-03-28 09:20:01  [b3c4d5]  CLAUDE_TOOL_USE         claude-code               Dashboard.md                         ✅
```

**Sample `summary` output:**
```
Audit Summary — 2026-03-28
========================================
  Total entries  : 47
  Sessions       : 6
  Failures       : 2
  Avg duration   : 284ms

  Outcomes:
    success      44
    failure       2
    approved      1

  Top actions:
    CLAUDE_TOOL_USE              18
    SESSION_START                 6
    SESSION_END                   6
    FILE_READ                     5
    API_CALL                      3
    TASK_COMPLETED                2
    PLAN_GENERATED                1

  Top scripts:
    claude-code                  18
    plan_generator.py             8
    ceo_briefing.py               7
    gmail_watcher.py              4
```

---

## Session Tracking

Every time a vault script starts, `audit_logger` generates a random 8-character
**session ID** shared by every entry that process writes. This lets you reconstruct
exactly what one script run did:

```bash
# Find the session ID of a failed plan_generator run
python audit_logger.py filter --script plan_generator --outcome failure

# Replay everything that session did
python audit_logger.py filter --session a1b2c3d4
```

---

## Thread Safety

`_write_entry()` uses `fcntl.flock(LOCK_EX)` before each write. Multiple vault
scripts can safely append to the same daily file concurrently without corruption.

---

## Limitations

- `fcntl` is Unix-only — works on WSL and Linux. Windows native Python would need
  the `msvcrt` locking API (swap `fcntl.flock` for `msvcrt.locking`).
- Large `detail` dicts with binary content are not filtered automatically — keep
  `detail` values small and string-safe.
- Log files grow unboundedly — archive or compress files older than 90 days.
- `audit_tool_hook.py` strips `content`, `new_string`, `old_string` from tool
  inputs to avoid logging large file contents. Raw content is never stored.
- `duration_ms` is only set when using `audit_action()` or `@audited` — plain
  `audit()` calls leave it as 0.

---

## Related

- [[skills/error_recovery/SKILL]] — fire `ALERT_FIRED` audit entries when alerts trigger
- [[skills/ralph_wiggum/SKILL]] — stop hook; add `CLAUDE_STOP` entries when it fires
- [[skills/plan_generator/SKILL]] — wrap with `@audited(Action.PLAN_GENERATED)`
- [[skills/ceo_briefing/SKILL]] — wrap with `@audited(Action.BRIEFING_GENERATED)`
- [[skills/hitl_approval/SKILL]] — log `HITL_REQUEST` / `HITL_APPROVED` / `HITL_DENIED`
- [[skills/gmail_watcher/SKILL]] — log `EMAIL_INGESTED` per email saved
- [[Dashboard]] — Vault Health section; reference audit summary counts here
