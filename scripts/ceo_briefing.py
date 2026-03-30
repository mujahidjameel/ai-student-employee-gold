"""
AI Employee Vault — Weekly CEO Briefing Generator
Reads /Done, /Needs_Action, and Dashboard.md, then uses Gemini to produce a
structured weekly briefing report saved to /Briefings/Weekly Briefing.md.

Audience: Student CEO reviewing their own week.
Covers: completed assignments, pending tasks, Panaversity AI course progress,
        university coursework, blockers, and the week ahead.
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from google import genai

# Load .env from vault root
load_dotenv(Path(__file__).parent.parent / ".env")

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

# ── Paths ───────────────────────────────────────────────────────────────────
VAULT        = Path("/mnt/d/AI-EMPLOYEE-VAULT")
DONE         = VAULT / "Done"
NEEDS_ACTION = VAULT / "Needs_Action"
DASHBOARD    = VAULT / "Dashboard.md"
BRIEFINGS    = VAULT / "Briefings"

# ── Config ──────────────────────────────────────────────────────────────────
MODEL     = "gemini-2.5-flash"
MAX_FILES = 60   # cap per folder to avoid blowing the context window


# ── Helpers ─────────────────────────────────────────────────────────────────
def read_folder(folder: Path, label: str) -> list[tuple[str, str]]:
    """Return [(filename, content), ...] for every .md file in folder."""
    if not folder.exists():
        return []
    files = sorted(folder.glob("*.md"))[:MAX_FILES]
    results = []
    for f in files:
        try:
            results.append((f.name, f.read_text(encoding="utf-8")))
        except OSError:
            results.append((f.name, f"[could not read {label}/{f.name}]"))
    return results


def read_dashboard() -> str:
    try:
        return DASHBOARD.read_text(encoding="utf-8")
    except OSError:
        return "[Dashboard.md not found]"


def format_folder_section(items: list[tuple[str, str]], folder_label: str) -> str:
    if not items:
        return f"_No files found in /{folder_label}._\n"
    parts = []
    for name, content in items:
        parts.append(f"#### {name}\n{content.strip()}")
    return "\n\n".join(parts)


def build_prompt(today: str, week_start: str, week_end: str,
                 done_items: list[tuple[str, str]],
                 pending_items: list[tuple[str, str]],
                 dashboard: str) -> str:

    done_section    = format_folder_section(done_items,    "Done")
    pending_section = format_folder_section(pending_items, "Needs_Action")

    return f"""You are an AI Chief of Staff writing a **Weekly CEO Briefing** for a student.
Today is {today}. This briefing covers the week of {week_start} to {week_end}.

The student manages two parallel tracks:
1. **University coursework** — assignments, labs, exams, projects with hard deadlines.
2. **Panaversity Agentic AI course** — daily AI learning modules, coding exercises, and projects.

Your job is to synthesise the vault data below into a concise, honest weekly briefing report
that the student can read in under 3 minutes and immediately know: what was done, what still
needs doing, how the learning is progressing, and what risks need attention.

---

## VAULT DATA

### Dashboard (current priorities and context)
{dashboard.strip()}

---

### /Done — Completed items ({len(done_items)} file(s))
{done_section}

---

### /Needs_Action — Pending items ({len(pending_items)} file(s))
{pending_section}

---

## OUTPUT FORMAT

Write a Markdown document with EXACTLY these sections in order. Be direct, student-specific,
and honest — do not pad or hedge. Use Obsidian wiki-link syntax ([[Note Name]]) for vault refs.

```
# Weekly CEO Briefing — {week_start} to {week_end}
**Generated:** {today}

---

## Executive Summary
3–5 bullet points. The week in plain English: wins, misses, key risks.

---

## Completed This Week
Table with columns: Item | Type | Outcome
Types: University / Panaversity / Email / Admin
Pull from /Done files. If /Done is empty, say so honestly.

---

## Pending & In Progress
Table with columns: Item | Type | Deadline | Priority
Types: University / Panaversity / Email / Admin
Priority: 🔴 Urgent / 🟡 This week / 🟢 Backlog
Pull from /Needs_Action files. Flag anything overdue in red (🔴).

---

## University Assignments Tracker
Table with columns: Subject | Assignment | Deadline | Status | Next Action
Status options: Not started / In progress / Submitted / Overdue
Extract from both /Done and /Needs_Action files. If no university items found, say so.

---

## Panaversity AI Learning Progress
Table with columns: Day | Module / Topic | Status | Key Concept Learned
Pull from Dashboard.md and any task notes. If no Panaversity entries found, note the gap
and recommend catching up.

---

## Week Ahead — Top 3 Priorities
Numbered list. What the student MUST focus on next week to stay on track.
Be specific: name the assignment, module, or action.

---

## Blockers & Risks
Bullet list. What could derail the week ahead? Missing materials, unclear briefs,
overdue items, Panaversity modules skipped, etc. If none, write "None identified."

---

## Vault Health
| Metric | Count |
|--------|-------|
| Items completed (Done folder) | {len(done_items)} |
| Items pending (Needs_Action) | {len(pending_items)} |
| Briefing generated | {today} |
```

Do not add any text outside these sections. Do not invent data — only use what is in the vault."""


# ── Core ────────────────────────────────────────────────────────────────────
def generate_briefing() -> str:
    today      = datetime.now().strftime("%Y-%m-%d")
    # Week: Monday to today (or Sunday if today is weekend)
    now        = datetime.now()
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    week_end   = (now - timedelta(days=now.weekday()) + timedelta(days=6)).strftime("%Y-%m-%d")

    print("Reading /Done...")
    done_items    = read_folder(DONE, "Done")

    print("Reading /Needs_Action...")
    pending_items = read_folder(NEEDS_ACTION, "Needs_Action")

    print("Reading Dashboard.md...")
    dashboard     = read_dashboard()

    print(f"  /Done:         {len(done_items)} file(s)")
    print(f"  /Needs_Action: {len(pending_items)} file(s)")

    prompt = build_prompt(today, week_start, week_end,
                          done_items, pending_items, dashboard)

    print("Calling Gemini to generate briefing...")
    client   = genai.Client(api_key=GOOGLE_API_KEY)
    response = client.models.generate_content(model=MODEL, contents=prompt)

    return response.text.strip()


# ── Entry point ─────────────────────────────────────────────────────────────
def main() -> None:
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        sys.exit(1)

    BRIEFINGS.mkdir(parents=True, exist_ok=True)

    print("AI Employee Vault — Weekly CEO Briefing Generator")
    print("=" * 50)

    briefing = generate_briefing()

    today       = datetime.now().strftime("%Y-%m-%d")
    dated_path  = BRIEFINGS / f"{today} Weekly Briefing.md"
    latest_path = BRIEFINGS / "Weekly Briefing.md"

    # Save dated archive copy
    dated_path.write_text(briefing + "\n", encoding="utf-8")
    print(f"Briefing saved (dated):  {dated_path}")

    # Overwrite latest for quick access
    latest_path.write_text(briefing + "\n", encoding="utf-8")
    print(f"Briefing saved (latest): {latest_path}")

    print("Done.")


if __name__ == "__main__":
    main()
