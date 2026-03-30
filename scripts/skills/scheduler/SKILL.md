# Scheduler Skill

**Date:** 2026-03-26
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/scheduler.py`

---

## What It Does

The Scheduler runs `plan_generator.py` automatically every day at **09:00** using the `schedule` library. It is a long-running background process — start it once and it keeps the vault's daily plan fresh without manual intervention.

Each day at the configured time it:

1. Launches `plan_generator.py` as a subprocess using the same Python interpreter.
2. Captures stdout and stderr and logs them with timestamps.
3. Logs success or failure with the exit code.
4. Sleeps for 30 seconds between schedule checks (low CPU overhead).

---

## First-Time Setup

### 1. Install dependency

```bash
pip install schedule
```

### 2. Ensure `plan_generator.py` is configured

The scheduler delegates entirely to `plan_generator.py`. Make sure that script is working first:

- `GOOGLE_API_KEY` set in `.env` at vault root
- `python scripts/plan_generator.py` runs without errors

See [[skills/plan_generator/SKILL]] for setup details.

---

## How to Run It

**WSL / Linux:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/scheduler.py
```

**Windows (CMD or PowerShell):**
```powershell
python D:\AI-EMPLOYEE-VAULT\scripts\scheduler.py
```

Press `Ctrl+C` to stop.

**Sample output:**
```
2026-03-26 08:59:00 [scheduler] INFO Scheduler started — plan_generator.py will run daily at 09:00.
2026-03-26 09:00:00 [scheduler] INFO Running plan_generator.py …
2026-03-26 09:00:03 [scheduler] INFO plan_generator.py completed successfully.
2026-03-26 09:00:03 [scheduler] INFO   Reading Inbox (3 item(s))...
2026-03-26 09:00:03 [scheduler] INFO   Reading Dashboard.md...
2026-03-26 09:00:03 [scheduler] INFO   Calling Gemini to generate plan...
2026-03-26 09:00:05 [scheduler] INFO   Plan written to: /mnt/d/AI-EMPLOYEE-VAULT/Plan.md
```

### Running in the background (WSL)

```bash
nohup python /mnt/d/AI-EMPLOYEE-VAULT/scripts/scheduler.py >> /mnt/d/AI-EMPLOYEE-VAULT/scheduler.log 2>&1 &
```

### Running on Windows startup (Task Scheduler)

1. Open **Task Scheduler** → Create Basic Task.
2. Trigger: **At log on**.
3. Action: Start a program → `python.exe` with argument `D:\AI-EMPLOYEE-VAULT\scripts\scheduler.py`.

---

## Inputs / Outputs

| Item | Description |
|------|-------------|
| **Input:** none | No arguments — configuration is hardcoded in the script |
| **Output:** `Plan.md` | Written to vault root by `plan_generator.py` at run time |
| **Output:** logs | Timestamped log lines to stdout; redirect to a file to persist |

### Configurable constants (top of `scheduler.py`)

| Constant | Default | Description |
|----------|---------|-------------|
| `RUN_TIME` | `"09:00"` | Daily time to run the plan generator (24-hour format) |
| `SCRIPT` | `scripts/plan_generator.py` | Path to the script to run |
| `PYTHON` | current interpreter | Python executable used to launch the subprocess |

To change the run time, edit `RUN_TIME` in `scheduler.py`:
```python
RUN_TIME = "08:30"   # run at 8:30 AM instead
```

---

## When to Use It

| Situation | Use Scheduler? |
|-----------|---------------|
| Vault should auto-generate a plan every morning | Yes |
| You want a hands-off daily workflow | Yes |
| You prefer to run the plan generator manually | No — run `plan_generator.py` directly |
| You need a plan more than once a day | No — run `plan_generator.py` directly as needed |

---

## Limitations

- Runs only one job: `plan_generator.py` daily at `RUN_TIME`. Not a general-purpose task scheduler.
- No built-in retry on failure — if `plan_generator.py` fails, the next attempt is the following day.
- Must remain running as a foreground process (or a background/startup process) — it does not register a system cron job.
- All configuration (run time, script path) requires editing the source file directly.

---

## Related

- [[skills/plan_generator/SKILL]] — the script this scheduler drives
- [[Dashboard]] — updated by `plan_generator.py` each run
- [[Company_Handbook]] — daily workflow and operating rhythm
