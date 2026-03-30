# Error Recovery Skill

**Date:** 2026-03-28
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/error_recovery.py`

---

## What It Does

`error_recovery.py` is a shared utility module that every other vault script imports to gain production-grade fault tolerance. It handles the three most common failure modes in the student vault:

| Failure mode | What happens without this | What happens with this |
|---|---|---|
| Gemini / Gmail API down | Script crashes, task lost | Retry with backoff, alert written, graceful fallback |
| Missing file (Dashboard.md, token, .env) | `FileNotFoundError` kills script | `safe_read()` returns fallback, WARNING alert created |
| Script subprocess crashes | Scheduler silently fails | `run_script()` retries, captures stderr, CRITICAL alert written |

---

## Architecture

```
error_recovery.py
│
├── AlertSystem          ── fires to 3 channels simultaneously
│   ├── logs/error_recovery.log   (every alert, DEBUG+)
│   ├── Alerts/<ts> Alert.md      (visible in Obsidian, has resolution checklist)
│   └── stderr console            (WARNING+ only, keeps terminals clean)
│
├── @with_retry          ── decorator wrapping any function with retry + backoff
│   └── RetryConfig      ── profiles: .network() / .file() / .script() / .fast()
│
├── safe_read()          ── reads files without crashing on missing/unreadable
├── safe_write()         ── atomic writes via .tmp + rename (no half-written files)
│
├── run_script()         ── subprocess runner with retry, timeout, crash capture
│   └── ScriptResult     ── structured result: success, returncode, stdout, stderr
│
└── VaultHealthCheck     ── pre-flight checker for dirs, files, env vars, alerts
    └── HealthReport      ── .healthy bool + issues list + warnings list
```

---

## Alert Levels

| Level | When used | Console? | Log? | Vault note? |
|-------|-----------|----------|------|-------------|
| `INFO` | Routine event worth recording | No | Yes | Yes |
| `WARNING` | Retry happening, optional file missing | No | Yes | Yes |
| `ERROR` | Operation failed after all retries | Yes (stderr) | Yes | Yes |
| `CRITICAL` | Script crash, blocking vault operation | Yes (stderr) | Yes | Yes |

Alert notes land in `/Alerts/` with this structure:

```markdown
# 🔴 ERROR Alert — 2026-03-28 09:15:42
**Level:** ERROR
**Script:** `plan_generator.py`
**Context:** HTTPSConnectionPool: Max retries exceeded

## Message
call_gemini failed after 4 attempts. Giving up.

## Traceback
...

## Resolution
- [ ] Investigated
- [ ] Fixed
- [ ] Note added to [[Dashboard]]
```

Check these off when you resolve the issue. `show-alerts` CLI lists all unresolved ones.

---

## Retry Profiles

```python
RetryConfig.network()   # 4 attempts, 3s base, 2× backoff, 30s cap — for Gemini/Gmail API
RetryConfig.file()      # 3 attempts, 0.5s base — for OS-level file locks
RetryConfig.script()    # 3 attempts, 5s base   — for subprocess execution
RetryConfig.fast()      # 2 attempts, 0.5s base — for lightweight quick ops
RetryConfig()           # default: 3 attempts, 2s base
```

Custom config:
```python
RetryConfig(
    max_attempts=5,
    base_delay=1.0,
    backoff_factor=3.0,
    max_delay=120.0,
    jitter=2.0,
    catch=(NetworkError, TimeoutError),
)
```

Delay formula: `min(base_delay × backoff_factor^(attempt-1), max_delay) + random(0, jitter)`

---

## Integration Guide

### Wrap an API call with retry

```python
from error_recovery import with_retry, RetryConfig, NetworkError

@with_retry(RetryConfig.network(), script="plan_generator.py", operation="call_gemini")
def call_gemini(prompt: str) -> str:
    try:
        client = genai.Client(api_key=GOOGLE_API_KEY)
        return client.models.generate_content(model=MODEL, contents=prompt).text
    except Exception as exc:
        raise NetworkError(f"Gemini API failed: {exc}") from exc
```

### Read a file safely

```python
from error_recovery import safe_read

dashboard = safe_read(VAULT / "Dashboard.md", fallback="[Dashboard unavailable]",
                      script="ceo_briefing.py")
```

### Write a file atomically

```python
from error_recovery import safe_write

ok = safe_write(VAULT / "Plan.md", plan_text, script="plan_generator.py")
if not ok:
    # alert was already fired — decide whether to abort or continue
    sys.exit(1)
```

### Run a sub-script with crash recovery

```python
from error_recovery import run_script, RetryConfig
from pathlib import Path

result = run_script(
    Path("/mnt/d/AI-EMPLOYEE-VAULT/scripts/plan_generator.py"),
    cfg=RetryConfig.script(),
    timeout=120,
    caller="scheduler.py",
)
if not result.success:
    print(f"Plan generator failed after {result.attempts} attempt(s).")
```

### Fire a manual alert

```python
from error_recovery import alert, AlertLevel

alert(
    "Gmail token expired — re-auth required.",
    level=AlertLevel.CRITICAL,
    context="TOKEN_FILE missing or invalid",
    script="gmail_watcher.py",
)
```

### Pre-flight health check

```python
from error_recovery import VaultHealthCheck

report = VaultHealthCheck().run()   # auto-creates missing dirs
report.print()
if not report.healthy:
    sys.exit(1)
```

---

## What VaultHealthCheck Verifies

| Check | Blocking? | Auto-fix? |
|-------|-----------|-----------|
| Required directories exist (`/Inbox`, `/Needs_Action`, `/Done`, `/Briefings`, `/Alerts`, `/logs`) | Yes | Yes — creates them |
| `Dashboard.md` exists | Yes | No |
| `.env` exists | Yes | No |
| `GOOGLE_API_KEY` set in env | Yes | No |
| `ANTHROPIC_API_KEY` set in env | No (warning) | No |
| `Plan.md` exists | No (warning) | No |
| Unresolved CRITICAL alerts in `/Alerts` | Yes | No — needs human review |
| Unresolved ERROR alerts in `/Alerts` | No (warning) | No |

---

## CLI Commands

```bash
# Run vault health check
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/error_recovery.py health

# Fire a test alert to verify all three channels work
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/error_recovery.py test-alert --level ERROR

# List all alert notes and their resolution status
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/error_recovery.py show-alerts
```

**Health check sample output:**
```
Vault Health: DEGRADED
  Issues (blocking):
    🔴 Missing required env var: GOOGLE_API_KEY (add to .env)
  Warnings (non-blocking):
    ⚠️  2 unresolved ERROR alert(s) in /Alerts.
```

---

## Vault Structure Added by This Skill

```
D:\AI-EMPLOYEE-VAULT\
├── logs\
│   └── error_recovery.log        ← all alerts, DEBUG+, persistent
└── Alerts\
    ├── Weekly Briefing.md         ← (example) from ceo_briefing
    ├── 2026-03-28 09-15-42 ERROR Alert.md
    └── 2026-03-28 08-00-01 WARNING Alert.md
```

---

## Limitations

- Alert notes accumulate in `/Alerts` indefinitely — archive or delete old ones periodically.
- `safe_write()` atomic rename may fail across different filesystem mounts (rare on WSL).
- `VaultHealthCheck` does not verify OAuth token validity — only that the token file exists.
- Retry jitter is random per-attempt; deterministic behaviour requires setting `jitter=0`.
- The module uses only the standard library plus what is already installed — no new `pip install` needed.

---

## Related

- [[skills/ralph_wiggum/SKILL]] — stop hook; use `safe_read()` pattern to handle empty Needs_Action
- [[skills/plan_generator/SKILL]] — wrap `call_gemini` with `@with_retry(RetryConfig.network())`
- [[skills/ceo_briefing/SKILL]] — wrap `generate_briefing` with `@with_retry(RetryConfig.network())`
- [[skills/scheduler/SKILL]] — replace raw `subprocess.run` with `run_script()` for crash recovery
- [[skills/gmail_watcher/SKILL]] — wrap `poll()` with `@with_retry(RetryConfig.network())`
- [[Dashboard]] — update when CRITICAL alerts appear
