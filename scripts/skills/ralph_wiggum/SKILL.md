# Ralph Wiggum Stop Hook

**Date:** 2026-03-28
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/ralph_wiggum_hook.py`
**Hook type:** Claude Code `stop` hook

---

## What It Does

Ralph Wiggum is a **Claude Code stop hook** — it runs automatically every time Claude finishes a response and is about to stop. If there are any `.md` task files still sitting in `/Needs_Action`, Ralph blocks Claude from stopping and injects a prompt ordering Claude to process the remaining tasks.

The result: Claude keeps working in a continuous loop until `/Needs_Action` is completely empty and every task has been moved to `/Done`.

```
Claude responds
      │
      ▼
ralph_wiggum_hook.py runs
      │
      ├─ /Needs_Action is EMPTY  →  exit 0 (Claude stops normally)
      │
      └─ /Needs_Action has files →  {"decision": "block", "reason": "..."}
                                           │
                                           ▼
                                    Claude re-prompts itself
                                    and processes next task
                                           │
                                           ▼
                                    loop repeats…
```

---

## Student Task Coverage

### University Assignments

When Ralph detects an assignment task note, the injected prompt instructs Claude to:

- Read the assignment brief and extract key requirements.
- Draft a structured outline or action plan.
- Set or update the deadline in `Dashboard.md` → **University Assignments** table.
- Flag any blockers (missing materials, unclear instructions) in the task note.
- Append a `## Resolution` section and move the note to `/Done`.

### Panaversity Agentic AI Course

When Ralph detects a Panaversity module task note, the injected prompt instructs Claude to:

- Log the module/lesson completed in `Dashboard.md` → **Panaversity — Agentic AI Daily Learning** table.
- Extract 3–5 key concepts learned into the task note.
- Note any exercises or code tasks that still need doing.
- Append a `## Resolution` section and move the note to `/Done`.

### Email / General Tasks

For everything else, Claude actions or prepares a response per the task's **Desired Outcome**, gates sensitive actions through HITL approval, and archives to `/Done`.

---

## First-Time Setup

### 1. Register the hook in Claude Code settings

Run the `update-config` skill or add manually to `.claude/settings.json`:

```json
{
  "hooks": {
    "Stop": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ralph_wiggum_hook.py"
          }
        ]
      }
    ]
  }
}
```

> **Windows path note:** On WSL, use the `/mnt/d/...` path. On native Windows use `D:\AI-EMPLOYEE-VAULT\scripts\ralph_wiggum_hook.py`.

### 2. Verify it is active

Drop a test `.md` file into `/Needs_Action` and confirm that Claude does not stop at the end of its next response without processing it.

---

## How to Run / Test Manually

```bash
# Simulate: tasks present
echo "test" > /mnt/d/AI-EMPLOYEE-VAULT/Needs_Action/test-task.md
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ralph_wiggum_hook.py
# Expected: {"decision": "block", "reason": "RALPH WIGGUM SAYS ..."}

# Simulate: no tasks (empty or non-existent Needs_Action)
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/ralph_wiggum_hook.py
# Expected: no output, exit code 0
```

---

## Inputs / Outputs

| Item | Description |
|------|-------------|
| **Input** | `/Needs_Action/*.md` — task note files |
| **Output (tasks remain)** | JSON: `{"decision": "block", "reason": "<full task list + instructions>"}` → stdout |
| **Output (all done)** | Empty stdout, exit code 0 |
| **Side effects** | None — read-only scan |

---

## Task Note Format Expected

Every file in `/Needs_Action` should follow the vault convention:

```markdown
# YYYY-MM-DD Task — <title>

**Date:** YYYY-MM-DD
**Owner:** AI Employee
**Desired Outcome:** <what done looks like>
**Status:** Needs Action

---

<body / context>

---

## Resolution
[To be filled in when complete]
```

Ralph does not require this format — it will flag any `.md` file — but Claude's processing logic assumes it.

---

## Limitations

- Ralph only checks file presence; it does not parse task content or priority.
- If a task note has been opened and partially edited but not moved to `/Done`, Ralph will keep blocking.
- Ralph does not distinguish between task types — all `.md` files in `/Needs_Action` are treated as pending work.
- Does not run when Claude Code is not active (use `scheduler.py` + `filesystem_watcher.py` for background coverage).

---

## Related

- [[skills/filesystem_watcher/SKILL]] — moves new files into Needs_Action automatically
- [[skills/hitl_approval/SKILL]] — gates sensitive actions inside each task
- [[skills/plan_generator/SKILL]] — generates the daily plan from Inbox + Dashboard
- [[Company_Handbook]] — workflow rules Claude follows when processing tasks
- [[Dashboard]] — updated by Claude after each task completes
