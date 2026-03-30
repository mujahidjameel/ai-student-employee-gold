# CEO Briefing Skill

**Date:** 2026-03-28
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/ceo_briefing.py`

---

## What It Does

The CEO Briefing skill is a one-shot script that reads the current state of the student's vault and uses Gemini to produce a structured **Weekly CEO Briefing** — a 3-minute read that answers:

- What did I actually complete this week?
- What is still pending, and what is most urgent?
- How is my Panaversity AI course progress tracking?
- What university assignments are at risk?
- What should I focus on next week?

It reads three vault sources:

| Source | What it tells the briefing |
|--------|---------------------------|
| `/Done` | Everything completed — assignments submitted, emails handled, modules finished |
| `/Needs_Action` | Everything still pending — deadlines, priorities, blockers |
| `Dashboard.md` | Current priorities, Panaversity daily learning log, university table |

Output is saved to two locations:

| File | Purpose |
|------|---------|
| `Briefings/YYYY-MM-DD Weekly Briefing.md` | Dated archive — one per run, never overwritten |
| `Briefings/Weekly Briefing.md` | Latest — always the most recent run |

---

## Briefing Sections

```
# Weekly CEO Briefing — YYYY-MM-DD to YYYY-MM-DD

## Executive Summary          ← 3–5 bullets: wins, misses, risks
## Completed This Week        ← table from /Done: Item | Type | Outcome
## Pending & In Progress      ← table from /Needs_Action: Item | Type | Deadline | Priority
## University Assignments     ← per-subject table with deadlines and status
## Panaversity AI Progress    ← module log with key concepts learned
## Week Ahead — Top 3         ← specific, named priorities for next week
## Blockers & Risks           ← what could derail the week
## Vault Health               ← Done count, Needs_Action count, generated date
```

Priority flags used in Pending table:
- `🔴 Urgent` — overdue or due today/tomorrow
- `🟡 This week` — due within 7 days
- `🟢 Backlog` — no imminent deadline

---

## First-Time Setup

No additional dependencies beyond what `plan_generator.py` already requires.

```bash
pip install google-genai python-dotenv
```

Requires `GOOGLE_API_KEY` in `.env` at the vault root:

```
GOOGLE_API_KEY=your_google_api_key_here
```

---

## How to Run It

**WSL / Linux (on-demand):**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ceo_briefing.py
```

**Windows (CMD or PowerShell):**
```powershell
python D:\AI-EMPLOYEE-VAULT\scripts\ceo_briefing.py
```

**Schedule weekly (every Monday at 08:00) — add to `scheduler.py`:**

```python
import schedule
schedule.every().monday.at("08:00").do(
    lambda: subprocess.run(
        ["python", "/mnt/d/AI-EMPLOYEE-VAULT/scripts/ceo_briefing.py"],
        check=True
    )
)
```

**Sample terminal output:**
```
AI Employee Vault — Weekly CEO Briefing Generator
==================================================
Reading /Done...
Reading /Needs_Action...
Reading Dashboard.md...
  /Done:         12 file(s)
  /Needs_Action: 8 file(s)
Calling Gemini to generate briefing...
Briefing saved (dated):  /mnt/d/AI-EMPLOYEE-VAULT/Briefings/2026-03-28 Weekly Briefing.md
Briefing saved (latest): /mnt/d/AI-EMPLOYEE-VAULT/Briefings/Weekly Briefing.md
Done.
```

---

## When to Run It

| Situation | Run Briefing? |
|-----------|--------------|
| End of week review (Friday evening / Sunday night) | Yes — primary use case |
| Monday morning before planning the week | Yes — see what carried over |
| Before a meeting with a tutor or mentor | Yes — quick status pull |
| Mid-week check-in | Optional — useful if a lot of tasks moved |
| /Done and /Needs_Action are both empty | Skip — briefing will have nothing to say |

---

## Student-Specific Behaviour

### University Assignments
The briefing extracts all task notes referencing coursework and builds a per-subject table showing:
- What has been submitted (from `/Done`)
- What is outstanding with deadline and next action (from `/Needs_Action`)
- What is overdue (flagged `🔴`)

### Panaversity Agentic AI Course
The briefing pulls the **Panaversity — Agentic AI Daily Learning** section from `Dashboard.md` and surfaces:
- Which modules were completed this week
- Key concepts logged
- Any gaps (days with no entry get flagged as a risk)

If the Dashboard Panaversity table is empty or outdated, the briefing's **Blockers & Risks** section will call it out explicitly.

---

## Output File Conventions

```
Briefings/
├── Weekly Briefing.md              ← latest (overwritten each run)
├── 2026-03-28 Weekly Briefing.md   ← archive
├── 2026-03-21 Weekly Briefing.md   ← archive
└── ...
```

Dated archive files follow the vault naming convention: `YYYY-MM-DD Topic Name.md`.
Never delete archived briefings — they form a longitudinal record of student progress.

---

## Limitations

- Reads up to 60 files per folder — very large `/Done` or `/Needs_Action` folders may be truncated.
- Does not parse task note deadlines programmatically — relies on Gemini to extract them from note content.
- Gemini's output is a best-effort synthesis; always verify deadlines against source task notes.
- `/Done` folder contents accumulate over time — old completed items will keep appearing in the data sent to Gemini (but Gemini is instructed to focus on the current week where possible).

---

## Related

- [[skills/ralph_wiggum/SKILL]] — stop hook that keeps Claude processing until /Needs_Action is empty
- [[skills/plan_generator/SKILL]] — daily plan from /Inbox + Dashboard
- [[skills/scheduler/SKILL]] — schedule this script to run every Monday morning
- [[skills/filesystem_watcher/SKILL]] — moves items into /Needs_Action automatically
- [[Dashboard]] — Panaversity learning log and university assignment tables
