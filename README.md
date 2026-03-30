# AI Employee Vault

**Hackathon 0 — Silver Tier**
**Student Edition — Personal Knowledge & Task OS**

> An Obsidian-based vault that operates as an AI employee: ingesting emails and files,
> triaging tasks, generating daily plans, and processing everything to completion —
> with a human-approval gate on every sensitive action.

---

## What Is This?

The AI Employee Vault is a personal productivity system where **Claude Code acts as a
student employee** managing two parallel workloads:

- **University coursework** — assignments, labs, exams, and project deadlines
- **Panaversity Agentic AI course** — daily learning modules, coding exercises, and AI projects

Rather than a traditional to-do app, the vault is a **living filesystem**: files move
through folders as they progress through a pipeline, every AI action is logged, and
Claude cannot stop working until the task queue is empty.

The system was built in two hackathon tiers:

| Tier | What was built |
|------|---------------|
| **Bronze** | Vault structure, Gmail watcher, filesystem watcher, plan generator, scheduler, HITL approval, MCP email sender |
| **Silver** | Ralph Wiggum stop hook, CEO weekly briefing, error recovery system, audit logging system |

---

## Architecture

### Full Pipeline

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        AI EMPLOYEE VAULT PIPELINE                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

  INPUTS                    WATCHERS                  VAULT FOLDERS
  ──────                    ────────                  ─────────────

  Gmail inbox          ──▶  gmail_watcher.py     ──▶  /Needs_Action
  (unread, important)        (poll every 60s)          (task notes)

  Files dropped        ──▶  filesystem_watcher.py ──▶  /Needs_Action
  to /Inbox                  (poll every 10s)          (task notes)
                                                             │
                                                             │  (also lands in)
                                                             ▼
                                                         /Inbox
                                                        (raw files)
                                                             │
                                                             ▼
  PLANNING              ◀──  plan_generator.py   ◀──  Dashboard.md
  Plan.md (daily)            (Gemini 2.5 Flash)        + /Inbox files
       ▲
       │  runs at 09:00 daily
  scheduler.py
  (long-running)
                                                             │
  EXECUTION                                                  ▼
  ─────────                                         Claude Code reads
                                                    /Needs_Action
                                                             │
                                                    ralph_wiggum_hook.py
                                                    (Stop hook — blocks
                                                     Claude until queue
                                                     is empty)
                                                             │
                                                             ▼
                                                    ┌────────────────┐
                                                    │  HITL gate     │
                                                    │ hitl_approval  │
                                                    │ Y/N prompt     │
                                                    └───────┬────────┘
                                                            │ approved
                                                            ▼
  OUTPUT               ──▶  mcp_email_sender.py  ──▶  Gmail (outbound)
  (sensitive actions)        (MCP server)

                       ──▶  /Done                ◀──  completed tasks


  OBSERVABILITY
  ─────────────

  error_recovery.py    ──▶  /Alerts/*.md              (vault notes)
  (all scripts)        ──▶  logs/error_recovery.log   (file)
                       ──▶  stderr                    (console)

  audit_tool_hook.py   ──▶  logs/audit/YYYY-MM-DD.jsonl
  (PostToolUse hook)         (every Claude tool call)

  ceo_briefing.py      ──▶  /Briefings/Weekly Briefing.md
  (weekly, on demand)        (Gemini summary of Done + Needs_Action)
```

### Data Flow in Plain English

1. **Ingest** — Gmail or a dropped file triggers a watcher; a task note lands in `/Needs_Action`.
2. **Plan** — Every morning at 09:00, `scheduler.py` fires `plan_generator.py`, which reads `/Inbox` + `Dashboard.md` and writes a prioritised `Plan.md` using Gemini.
3. **Execute** — Claude Code reads task notes. After every response, the **Ralph Wiggum stop hook** checks if `/Needs_Action` is empty. If not, Claude is re-prompted to keep working.
4. **Gate** — Before any sensitive action (send, delete, push), `hitl_approval.py` pauses and asks for Y/N in the terminal.
5. **Send** — Approved outbound emails go via `mcp_email_sender.py`, an MCP server registered with Claude Code.
6. **Archive** — Completed task notes move to `/Done` with a `## Resolution` section appended.
7. **Review** — Every week, `ceo_briefing.py` synthesises `/Done`, `/Needs_Action`, and `Dashboard.md` into a structured student progress report.
8. **Observe** — Every Claude tool call is logged to `logs/audit/YYYY-MM-DD.jsonl` by the PostToolUse hook. Errors fire alerts to `/Alerts/` and `logs/error_recovery.log`.

---

## Vault Structure

```
D:\AI-EMPLOYEE-VAULT\
│
├── README.md                      ← This file
├── CLAUDE.md                      ← AI employee constitution (rules + architecture)
├── Dashboard.md                   ← Live status: priorities, university table, Panaversity log
├── Company_Handbook.md            ← Workflow SOPs and ground rules
├── Plan.md                        ← Daily plan (auto-generated, overwritten each run)
├── .env                           ← API keys (not committed to git)
│
├── Inbox\                         ← Drop zone — all new inputs land here first
├── Needs_Action\                  ← Triaged task notes awaiting action
├── Done\                          ← Completed and archived task notes
├── Briefings\                     ← Weekly CEO briefing reports
├── Alerts\                        ← Error recovery alert notes (visible in Obsidian)
│
├── logs\
│   ├── error_recovery.log         ← All error/warning events (plaintext)
│   └── audit\
│       └── YYYY-MM-DD.jsonl       ← Daily audit log (one JSON record per line)
│
├── scripts\
│   ├── filesystem_watcher.py      ← Watches /Inbox, moves files to /Needs_Action
│   ├── gmail_watcher.py           ← Polls Gmail, saves emails as task notes
│   ├── plan_generator.py          ← Generates Plan.md using Gemini
│   ├── scheduler.py               ← Runs plan_generator.py daily at 09:00
│   ├── hitl_approval.py           ← Human-in-the-loop Y/N gate
│   ├── mcp_email_sender.py        ← MCP server exposing send_email() tool
│   ├── ralph_wiggum_hook.py       ← Stop hook: blocks Claude until /Needs_Action empty
│   ├── ceo_briefing.py            ← Generates weekly student progress briefing
│   ├── error_recovery.py          ← Retry logic, alerts, safe I/O, health check
│   ├── audit_logger.py            ← Structured JSON audit logging + CLI
│   └── audit_tool_hook.py         ← PostToolUse hook: logs every Claude tool call
│
└── scripts\skills\
    ├── filesystem_watcher\SKILL.md
    ├── gmail_watcher\SKILL.md
    ├── plan_generator\SKILL.md
    ├── scheduler\SKILL.md
    ├── hitl_approval\SKILL.md
    ├── mcp_email_sender\SKILL.md
    ├── ralph_wiggum\SKILL.md
    ├── ceo_briefing\SKILL.md
    ├── error_recovery\SKILL.md
    └── audit_logging\SKILL.md
```

---

## Quick Start

### Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | `python --version` |
| Obsidian | Any | Open `D:\AI-EMPLOYEE-VAULT` as a vault |
| Claude Code | Latest | `claude --version` |
| Google Cloud project | — | For Gmail API + Gemini API |
| WSL2 (Windows) | — | Scripts use `/mnt/d/...` paths |

### 1. Clone / Open the Vault

```bash
# Already on disk at D:\AI-EMPLOYEE-VAULT
# Open Obsidian → Open folder as vault → select D:\AI-EMPLOYEE-VAULT
```

### 2. Install Python Dependencies

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 \
            google-api-python-client google-genai python-dotenv schedule
```

### 3. Create `.env`

```bash
# D:\AI-EMPLOYEE-VAULT\.env
GOOGLE_API_KEY=your_gemini_api_key_here
```

Get a Gemini API key at [Google AI Studio](https://aistudio.google.com/).

### 4. Set Up Gmail OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → Create project.
2. Enable **Gmail API**.
3. Create OAuth 2.0 credentials → Desktop app → Download JSON.
4. Rename the file to match the expected prefix and place it in `scripts/`.
5. First run of `gmail_watcher.py` or `mcp_email_sender.py` opens a browser for auth.
   Token saved to `scripts/gmail_token.json` for subsequent runs.

### 5. Run the Vault Health Check

```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/error_recovery.py health
```

Expected output when everything is configured:
```
Vault Health: OK
  ✅ All checks passed.
```

### 6. Start the Watchers (three separate terminals)

```bash
# Terminal 1 — watch /Inbox for dropped files
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/filesystem_watcher.py

# Terminal 2 — watch Gmail for unread important emails
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/gmail_watcher.py

# Terminal 3 — run plan_generator daily at 09:00
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/scheduler.py
```

### 7. Start Claude Code

```bash
cd /mnt/d/AI-EMPLOYEE-VAULT
claude
```

The PostToolUse and Stop hooks in `.claude/settings.json` activate automatically.

---

## Skills Reference

### 1. Filesystem Watcher

**Script:** `scripts/filesystem_watcher.py`
**Type:** Long-running background watcher
**Deps:** Standard library only

Polls `/Inbox` every 10 seconds. When a new file appears it moves it to `/Needs_Action`
and creates a stub task note (`YYYY-MM-DD Task - <filename>.md`).

```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/filesystem_watcher.py
# Stop with Ctrl+C
```

**What it creates in `/Needs_Action`:**
```markdown
# Task: report.pdf

**Date Received:** 2026-03-28 09:15:42
**Original Location:** Inbox
**Owner:** Unassigned
**Status:** pending

## Desired Outcome
Process and action the received file.

## Checklist
- [ ] Review
- [ ] Process
- [ ] Move to Done
```

---

### 2. Gmail Watcher

**Script:** `scripts/gmail_watcher.py`
**Type:** Long-running background watcher
**Deps:** `google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
**Auth:** OAuth2 — browser login on first run, token cached in `scripts/gmail_token.json`

Polls Gmail every 60 seconds for messages matching `is:unread is:important`.
Saves each email as a structured task note in `/Needs_Action` and marks it read
in Gmail to prevent duplicates.

```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/gmail_watcher.py
# Stop with Ctrl+C
```

**To change the Gmail filter**, edit the `QUERY` constant at the top of the script:
```python
QUERY = "is:unread is:important"   # default
QUERY = "is:unread label:university"  # example custom filter
```

---

### 3. Plan Generator

**Script:** `scripts/plan_generator.py`
**Type:** One-shot (exits after writing `Plan.md`)
**Deps:** `google-genai python-dotenv`
**Auth:** `GOOGLE_API_KEY` in `.env`

Reads all `.md` files in `/Inbox` (up to 50) and `Dashboard.md`, sends them to
Gemini (`gemini-2.5-flash`), and writes a structured `Plan.md` to the vault root.

```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/plan_generator.py
```

**Output sections in `Plan.md`:**
- `# Daily Plan — YYYY-MM-DD`
- `## Inbox Summary` — one-sentence per item
- `## Prioritised Task List` — ordered actions, `[URGENT]` flagged
- `## Notes & Blockers`

---

### 4. Scheduler

**Script:** `scripts/scheduler.py`
**Type:** Long-running scheduler
**Deps:** `schedule`

Fires `plan_generator.py` as a subprocess every day at 09:00.
Logs all output with timestamps. Change `RUN_TIME = "09:00"` at the top to adjust.

```bash
# Foreground
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/scheduler.py

# Background (keep running after terminal closes)
nohup python /mnt/d/AI-EMPLOYEE-VAULT/scripts/scheduler.py >> scheduler.log 2>&1 &
```

---

### 5. HITL Approval

**Script:** `scripts/hitl_approval.py`
**Type:** On-demand CLI tool or imported module
**Deps:** Standard library only

Human-in-the-Loop gate. Auto-detects sensitive keywords (`delete`, `send`, `email`,
`push`, `deploy`, `drop`, `wipe`, etc.) and prompts for Y/N before any action proceeds.
In non-interactive environments, denies by default.

```bash
# CLI usage
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/hitl_approval.py "send email to professor"
# exit 0 = approved, exit 1 = denied

python /mnt/d/AI-EMPLOYEE-VAULT/scripts/hitl_approval.py "delete old task" \
    --details "Inbox/draft.md"

# Always prompt (even non-sensitive actions)
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/hitl_approval.py "generate report" --always
```

```python
# Module import
from hitl_approval import guard

if guard("send email", details="To: professor@university.edu"):
    send_the_email()
```

**Sensitive keywords that always trigger a prompt:**
`delete` · `remove` · `overwrite` · `send` · `email` · `push` · `deploy` · `drop` · `truncate` · `wipe` · `format`

---

### 6. MCP Email Sender

**Script:** `scripts/mcp_email_sender.py`
**Type:** Long-running MCP server (stdin/stdout, JSON-RPC 2.0)
**Deps:** `google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client`
**Auth:** Shares `gmail_token.json` with `gmail_watcher.py`

Exposes a single `send_email(to, subject, body)` tool to Claude Code via the
Model Context Protocol. Register in `.claude/mcp_servers.json` to enable.

```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/mcp_email_sender.py
```

**MCP registration (`.claude/mcp_servers.json`):**
```json
{
  "mcp_email_sender": {
    "command": "python",
    "args": ["/mnt/d/AI-EMPLOYEE-VAULT/scripts/mcp_email_sender.py"]
  }
}
```

---

### 7. Ralph Wiggum Stop Hook

**Script:** `scripts/ralph_wiggum_hook.py`
**Type:** Claude Code `Stop` hook
**Registered in:** `.claude/settings.json`

Named after the Simpsons character who never stops trying. A Claude Code stop hook
that fires after every response. If `/Needs_Action` has any `.md` files, it returns
`{"decision": "block", "reason": "..."}` with a numbered task list and student-specific
processing instructions — preventing Claude from stopping until every task is in `/Done`.

```bash
# Test manually
echo "test" > /mnt/d/AI-EMPLOYEE-VAULT/Needs_Action/test-task.md
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ralph_wiggum_hook.py
# → {"decision": "block", "reason": "RALPH WIGGUM SAYS: I'm not done yet!..."}

# Empty queue — Claude stops normally
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ralph_wiggum_hook.py
# → (no output, exit 0)
```

**Student task handling:**

| Task type | What Claude is instructed to do |
|-----------|--------------------------------|
| University assignment | Extract requirements, draft outline, set deadline in Dashboard.md, flag blockers |
| Panaversity AI module | Log in Dashboard.md learning table, extract key concepts, note pending exercises |
| Email / general | Action per Desired Outcome, gate sensitive actions through HITL |

---

### 8. CEO Weekly Briefing

**Script:** `scripts/ceo_briefing.py`
**Type:** One-shot (exits after writing briefings)
**Deps:** `google-genai python-dotenv`
**Auth:** `GOOGLE_API_KEY` in `.env`

Reads `/Done`, `/Needs_Action`, and `Dashboard.md`, then uses Gemini to produce a
structured weekly student progress report. Saves two outputs:

| File | Purpose |
|------|---------|
| `Briefings/YYYY-MM-DD Weekly Briefing.md` | Dated archive, never overwritten |
| `Briefings/Weekly Briefing.md` | Always the latest |

```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ceo_briefing.py
```

**Briefing sections generated:**

```
## Executive Summary          ← 3–5 bullet wins/misses/risks
## Completed This Week        ← table from /Done
## Pending & In Progress      ← table with 🔴🟡🟢 priority flags
## University Assignments     ← per-subject status tracker
## Panaversity AI Progress    ← module log with key concepts
## Week Ahead — Top 3         ← specific named priorities
## Blockers & Risks
## Vault Health               ← Done/Needs_Action counts
```

**Schedule weekly** (add to `scheduler.py`):
```python
schedule.every().monday.at("08:00").do(
    lambda: subprocess.run(["python", ".../ceo_briefing.py"])
)
```

---

### 9. Error Recovery System

**Script:** `scripts/error_recovery.py`
**Type:** Shared utility module + CLI tool
**Deps:** Standard library only

A reusable module imported by every vault script to handle the three most common
failure modes: network failures, missing files, and script crashes.

```bash
# Vault health check
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/error_recovery.py health

# Fire a test alert (verify all three channels work)
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/error_recovery.py test-alert --level ERROR

# List unresolved alerts
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/error_recovery.py show-alerts
```

**Three alert channels fire simultaneously:**

| Channel | When | Location |
|---------|------|----------|
| Log file | Always (DEBUG+) | `logs/error_recovery.log` |
| Vault note | Always | `Alerts/YYYY-MM-DD HH-MM-SS LEVEL Alert.md` |
| Console stderr | WARNING+ only | Terminal |

**Retry profiles:**

```python
from error_recovery import with_retry, RetryConfig

@with_retry(RetryConfig.network(), script="plan_generator.py")
def call_gemini(prompt): ...          # 4 attempts, 3s→6s→12s backoff

@with_retry(RetryConfig.file())
def read_inbox(): ...                  # 3 attempts, 0.5s base

@with_retry(RetryConfig.script())
def run_subprocess(): ...              # 3 attempts, 5s base
```

**Safe I/O:**
```python
from error_recovery import safe_read, safe_write

# Returns fallback string instead of crashing
dashboard = safe_read(VAULT / "Dashboard.md", fallback="[unavailable]")

# Atomic write via .tmp → rename (no half-written files)
safe_write(VAULT / "Plan.md", content)
```

---

### 10. Audit Logging System

**Scripts:** `scripts/audit_logger.py` · `scripts/audit_tool_hook.py`
**Type:** Shared module + PostToolUse hook + CLI
**Deps:** Standard library only
**Hook registered in:** `.claude/settings.json`

Every action — file read/write, API call, task lifecycle event, HITL decision,
script run, and every Claude Code tool call — is recorded as a JSON line in a daily
audit log. The PostToolUse hook captures Claude's tool calls with zero code changes
to existing scripts.

**Log location:** `logs/audit/YYYY-MM-DD.jsonl`

```bash
# Last 20 entries
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/audit_logger.py tail

# All failures today
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/audit_logger.py filter --outcome failure

# Summary statistics
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/audit_logger.py summary

# List all sessions
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/audit_logger.py sessions

# All log files on disk
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/audit_logger.py files
```

**Log entry schema:**
```json
{
  "ts":          "2026-03-28T09:15:42.103847",
  "date":        "2026-03-28",
  "session_id":  "a1b2c3d4",
  "pid":         12345,
  "script":      "plan_generator.py",
  "action":      "API_CALL",
  "target":      "gemini-2.5-flash",
  "detail":      { "prompt_chars": 4200 },
  "outcome":     "success",
  "duration_ms": 3421,
  "error":       ""
}
```

**Integration in any script:**
```python
from audit_logger import audit, audit_action, audited, Action

# Wrap an API call — auto-times and catches failures
with audit_action(Action.API_CALL, script=__file__, target="gemini-2.5-flash"):
    response = client.models.generate_content(...)

# Log a task completion
audit(Action.TASK_COMPLETED, script=__file__, target=note_name)
```

---

## Claude Code Hooks

Both hooks are registered in `.claude/settings.json` and activate automatically
when Claude Code starts in this directory.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "",
        "hooks": [{
          "type": "command",
          "command": "python /mnt/d/AI-EMPLOYEE-VAULT/scripts/audit_tool_hook.py",
          "statusMessage": "Auditing tool call..."
        }]
      }
    ],
    "Stop": [
      {
        "matcher": "",
        "hooks": [{
          "type": "command",
          "command": "python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ralph_wiggum_hook.py",
          "statusMessage": "Ralph checking Needs_Action..."
        }]
      }
    ]
  }
}
```

| Hook | Fires | Effect |
|------|-------|--------|
| `PostToolUse` | After every Claude tool call | Appends one JSONL entry to daily audit log |
| `Stop` | After every Claude response | Blocks Claude from stopping if `/Needs_Action` is non-empty |

---

## Configuration Reference

### `.env` (vault root)

```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

### Required files in `scripts/`

| File | How to get it |
|------|---------------|
| `client_secret_*.json` | Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 → Download |
| `gmail_token.json` | Auto-generated on first run of `gmail_watcher.py` or `mcp_email_sender.py` |

### `.claude/settings.json`

Auto-managed. Contains the two hook registrations above. Edit with the
`update-config` skill inside Claude Code.

### Vault paths (hardcoded)

All scripts use `/mnt/d/AI-EMPLOYEE-VAULT` as the vault root. If your vault is
on a different drive or path, find-and-replace this string across all scripts.

---

## Core Workflow

```
CAPTURE → TRIAGE → EXECUTE → ARCHIVE
```

| Step | Where | Who | Rule |
|------|-------|-----|------|
| **Capture** | `/Inbox` | Watchers / manual drop | All inputs go to `/Inbox` first — no exceptions |
| **Triage** | `/Needs_Action` | Watchers create stubs | Add context, owner, desired outcome |
| **Execute** | `/Needs_Action` | Claude Code + human | Work each task to completion; HITL for sensitive actions |
| **Archive** | `/Done` | Claude Code | Append `## Resolution` before moving; never delete notes |

### Task Note Format

Every file in `/Needs_Action` and `/Done` follows this structure:

```markdown
# YYYY-MM-DD Task — <title>

**Date:** YYYY-MM-DD
**Owner:** AI Employee
**Desired Outcome:** <what "done" looks like>
**Status:** Needs Action

---

<body / context / email content>

---

## Resolution
[YYYY-MM-DD] [What was done and outcome]
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Vault / UI | [Obsidian](https://obsidian.md/) | Note editor, graph view, visual file browser |
| AI model | [Gemini 2.5 Flash](https://ai.google.dev/) | Plan generation, weekly briefing synthesis |
| AI coding agent | [Claude Code](https://claude.ai/code) (claude-sonnet-4-6) | Task execution, file operations, decision-making |
| Email API | Gmail API (Google Cloud) | Email ingestion + outbound sending |
| MCP transport | JSON-RPC 2.0 over stdio | Claude ↔ email sender integration |
| Automation | Python 3.10+ | All scripts |
| Scheduling | `schedule` library | Daily plan generation at 09:00 |
| Logging | JSONL + Python `logging` | Structured audit trail |
| Platform | WSL2 on Windows | Linux paths on Windows machine |

---

## Lessons Learned

### What Worked Well

**1. Folder-as-state-machine is powerful.**
Using `/Inbox` → `/Needs_Action` → `/Done` as explicit states meant Claude always
knew the current status of every task by looking at which folder a file was in.
No database, no metadata schema — just filesystem positions.

**2. The Stop hook is the killer feature of Silver Tier.**
Without Ralph Wiggum, Claude would stop after processing one task and wait for
the next prompt. With it, Claude works through the entire queue autonomously.
The hook pattern — check a condition, return JSON to block or allow — turned out
to be extremely versatile.

**3. HITL approval prevented every near-miss.**
The keyword-based sensitive-action detection caught three cases during development
where Claude was about to send a test email to a real address. A Y/N prompt is a
tiny friction that prevents irreversible mistakes.

**4. Separating concerns into small scripts kept everything debuggable.**
Each script does one thing. When the Gmail watcher broke (expired token), it was
immediately obvious which component failed and exactly where to look.

**5. Audit logs revealed unexpected behaviour.**
The `CLAUDE_TOOL_USE` entries from the PostToolUse hook showed Claude reading the
same file four times in a row during one session — a behaviour invisible without logging.
This led to a cleaner approach for the briefing generator.

### What Was Harder Than Expected

**1. OAuth token lifecycle is annoying in automation.**
The Gmail token expires and requires a browser re-auth. In a headless server
environment this is blocking. The current workaround is to catch the expiry and
fire a CRITICAL alert so the user re-authenticates manually.

**2. Gemini response formatting is inconsistent.**
Gemini sometimes wraps output in markdown code fences even when instructed not to.
The plan generator prompt needed several iterations to get clean output.

**3. Obsidian wiki-links break outside Obsidian.**
`[[Note Name]]` syntax is Obsidian-specific. The briefings and plans look correct
inside Obsidian but render as broken links in GitHub or any other Markdown viewer.

**4. Stop hook loops can be hard to interrupt.**
If `/Needs_Action` contains a file that Claude cannot process (e.g., a binary file
with a `.md` extension), Ralph Wiggum will loop forever. The fix was adding a
`## Resolution` section check, but this is still an area for improvement.

**5. WSL path mapping requires discipline.**
Scripts use `/mnt/d/...` but the vault is `D:\...` on Windows. Any script run
natively on Windows (e.g., the `.bat` launcher) needs the Windows path. This
caused confusion during initial setup.

### What Would Be Done Differently

- Add a priority field to task notes from day one, so the stop hook can process
  urgent tasks first rather than alphabetically.
- Use a proper secrets manager (or at least `keyring`) instead of a plain `.env` file.
- Write integration tests for the watcher scripts using a temp directory fixture
  rather than the live vault.
- Version the audit log schema from the start — adding fields to JSONL retroactively
  means old entries are missing keys that new queries expect.

---

## Current Limitations (Student Version)

This is a **personal, single-user, local-first system**. It is not production software.

| Limitation | Impact |
|------------|--------|
| All paths hardcoded to `/mnt/d/AI-EMPLOYEE-VAULT` | Must find-replace to use on a different machine |
| Gmail OAuth requires browser re-auth when token expires | Breaks headless/scheduled operation |
| No task priority parsing | Ralph Wiggum processes tasks in alphabetical order |
| No deduplication across sessions | Same email can theoretically be ingested twice if `gmail_token.json` is deleted |
| `fcntl` for file locking is Unix-only | Audit logger won't work in native Windows Python |
| Gemini context window caps at ~60 files per run | Very full `/Needs_Action` or `/Done` folders get truncated |
| No web UI | Everything is terminal + Obsidian |
| No multi-user support | Vault is personal; no shared access or permissions |

---

## Future Plans

This vault was built for Hackathon 0. The roadmap below describes what Gold Tier
and beyond will look like.

### Gold Tier — Planned

#### Odoo ERP Integration

Replace the manual `/Done` archive with a real ERP backend:

```
Task completed in vault
        │
        ▼
odoo_sync.py (new script)
        │
        ├── Create/update project task in Odoo
        ├── Log time entry against course or subject
        └── Sync assignment grades when submitted
```

- **Why Odoo?** Open-source, self-hostable, has a full REST API, and covers
  project management + CRM + invoicing in one system.
- **Student use case:** Track university assignment time, generate semester reports,
  export grades to a proper database rather than Markdown files.

#### Social Media Integration

Automate the student's public learning journey:

| Platform | What gets automated |
|----------|-------------------|
| **LinkedIn** | Weekly post summarising what was learned in Panaversity that week (from CEO briefing) |
| **Twitter / X** | Daily "today I learned" thread from completed Panaversity module notes |
| **Instagram** | Weekly visual progress card (auto-generated from briefing stats) |
| **YouTube / TikTok** | (future) Short-form video script from module notes |

```
ceo_briefing.py generates Weekly Briefing.md
        │
        ▼
social_publisher.py (new script)
        │
        ├── linkedin_post() — professional summary
        ├── twitter_thread() — daily learning tweets
        └── instagram_caption() — visual card text
        │
        ▼
hitl_approval.guard("publish to social media")   ← always requires Y/N
        │ approved
        ▼
Posts published via platform APIs
        │
        ▼
audit(Action.SOCIAL_POST_PUBLISHED, ...)
```

All social posts go through HITL approval — content is never published automatically.

#### Additional Gold Tier Skills

| Skill | Description |
|-------|-------------|
| `deadline_tracker.py` | Scan task notes for date strings, build a deadline calendar, alert 48h before due |
| `grade_logger.py` | Parse submitted assignment notes, track grades, compute GPA trend |
| `panaversity_sync.py` | Scrape course portal for new modules, auto-create task notes |
| `study_timer.py` | Pomodoro-style timer integrated with audit logging for focus tracking |
| `voice_inbox.py` | WhatsApp voice note → transcript → task note via Whisper API |

### Longer-Term Vision

The student vault is a **proof of concept** for a more ambitious system:

```
Student vault (personal)
        │
        ▼  skills transfer to
Enterprise AI Employee Vault
        │
        ├── Multi-user with role-based HITL approval
        ├── Odoo as the system of record (not Markdown)
        ├── CRM integration (auto-log client emails as CRM activities)
        ├── HR module (timesheet entries from audit log)
        └── Full social media presence management
```

The patterns established here — folder-as-state-machine, stop hooks for
autonomous task draining, HITL gates, structured audit logs — are all directly
applicable at enterprise scale.

---

## Project History

| Date | Milestone |
|------|-----------|
| 2026-03-17 | Bronze Tier complete — vault structure, Gmail/filesystem watchers, plan generator, scheduler, HITL, MCP email sender |
| 2026-03-26 | Silver Tier started — constitution updated with architecture overview |
| 2026-03-28 | Silver Tier complete — Ralph Wiggum hook, CEO briefing, error recovery, audit logging, this README |

---

## Acknowledgements

Built on:
- [Obsidian](https://obsidian.md/) — the vault metaphor and Markdown-first workflow
- [Claude Code](https://claude.ai/code) — AI coding agent and task executor
- [Google Gemini](https://ai.google.dev/) — plan generation and briefing synthesis
- [Panaversity](https://www.panaversity.com/) — Agentic AI course curriculum that this vault was built to serve
- [Hackathon 0](https://github.com/panaversity) — the challenge that forced this into existence in one sprint

---

*This is a student project. It is opinionated, local-first, and built to solve one
student's specific workflow. Take what is useful, leave what is not.*
