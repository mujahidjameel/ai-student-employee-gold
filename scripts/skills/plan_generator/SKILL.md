# Plan Generator Skill

**Date:** 2026-03-25
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/plan_generator.py`

---

## What It Does

The plan generator reads the current state of the vault and uses Claude to produce a structured `Plan.md` at the vault root. It is run on-demand — not as a background watcher.

It:

1. Reads all `.md` files in `/Inbox` to discover pending, unprocessed items.
2. Reads `Dashboard.md` for current context and priorities.
3. Sends both to Claude (`claude-sonnet-4-20250514`) with a structured reasoning prompt.
4. Writes a dated `Plan.md` to `D:\AI-EMPLOYEE-VAULT\Plan.md`, overwriting any previous plan.

The output `Plan.md` contains:

- Today's date
- Summary of items found in `/Inbox`
- Prioritised task list (urgent items flagged)
- Any blockers or notes Claude identifies

---

## First-Time Setup

Install the required Python package into the vault's existing venv:

```bash
pip install anthropic
```

Set your Anthropic API key as an environment variable:

**WSL / Linux / macOS:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
```

Or add it permanently to your shell profile / system environment variables.

---

## How to Run It

**WSL / Linux:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/plan_generator.py
```

**Windows (CMD or PowerShell):**
```powershell
python D:\AI-EMPLOYEE-VAULT\scripts\plan_generator.py
```

The script exits after writing `Plan.md`. It does not loop.

**Sample output:**
```
AI Employee Vault — Plan Generator
Reading Inbox (3 item(s))...
Reading Dashboard.md...
Calling Claude to generate plan...
Plan written to: /mnt/d/AI-EMPLOYEE-VAULT/Plan.md
Done.
```

---

## When to Use It

| Situation | Run Plan Generator? |
|-----------|-------------------|
| Start of workday — want a prioritised view of pending Inbox items | Yes |
| After a batch of new items land in `/Inbox` | Yes |
| Before a triage session to decide what moves to `/Needs_Action` | Yes |
| Inbox is empty | No — plan will say so, but there is little value |
| You only want to process one specific item | No — action it directly |

---

## Output Format

`Plan.md` is overwritten on every run. Structure:

```markdown
# Daily Plan — YYYY-MM-DD

## Inbox Summary
...

## Prioritised Task List
1. [URGENT] ...
2. ...

## Notes & Blockers
...
```

---

## Limitations

- Only reads `/Inbox` — does not inspect `/Needs_Action` or `/Done`.
- Reads a maximum of 50 files from `/Inbox` to stay within context limits.
- Requires `ANTHROPIC_API_KEY` to be set in the environment.
- Overwrites `Plan.md` on every run — previous plan is not archived.
- Claude's output is a best-effort prioritisation; always review before actioning.

---

## Related

- [[skills/filesystem_watcher/SKILL]] — watches `/Inbox` and routes new files automatically
- [[skills/gmail_watcher/SKILL]] — feeds emails into `/Needs_Action`
- [[Company_Handbook]] — triage and execution workflow
