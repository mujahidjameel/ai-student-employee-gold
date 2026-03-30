# HITL Approval Skill

**Date:** 2026-03-26
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/hitl_approval.py`

---

## What It Does

The HITL (Human-in-the-Loop) approval gate intercepts **sensitive actions** before they execute and requires explicit Y/N confirmation from the user in the terminal.

It is both a **Python module** (imported by other scripts) and a **standalone CLI tool**.

When called, it:

1. Inspects the action description for sensitive keywords (`delete`, `send`, `email`, `push`, `deploy`, `drop`, `wipe`, etc.).
2. If the action is sensitive (or `--always` is passed), prints a clear approval prompt.
3. Waits for the user to type `Y` or `N`.
4. Returns `True` (proceed) or `False` (skip) — or exits with code `0`/`1` when used from the CLI.
5. In non-interactive environments (no TTY), **denies by default** and prints a warning to stderr.

---

## First-Time Setup

No installation required beyond the Python standard library. No credentials or environment variables needed.

---

## How to Run It

### As a CLI gate (shell scripts, `subprocess` calls)

**WSL / Linux:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/hitl_approval.py "send email to client"
echo "Exit code: $?"   # 0 = approved, 1 = denied
```

**With extra detail:**
```bash
python scripts/hitl_approval.py "delete file" --details "Inbox/old-task.md"
```

**Force prompt even for non-sensitive actions:**
```bash
python scripts/hitl_approval.py "generate report" --always
```

**Windows (CMD or PowerShell):**
```powershell
python D:\AI-EMPLOYEE-VAULT\scripts\hitl_approval.py "send email to client"
```

**Sample output:**
```
============================================================
  HUMAN APPROVAL REQUIRED
============================================================
  Action  : send email to client
  Details : To: boss@company.com | Subject: Invoice ready
============================================================
  Approve? [Y/N]: y
[HITL] Approved.
```

### As a Python module (imported by other scripts)

```python
from hitl_approval import guard

# Only prompts if action contains a sensitive keyword
if guard("send email", details="To: client@example.com"):
    send_the_email()

# Always prompts regardless of content
if guard("generate report", always_ask=True):
    generate()
```

---

## Inputs / Outputs

| Item | Description |
|------|-------------|
| **Input: `action`** | Short string describing the action to be taken |
| **Input: `--details`** | Optional extra context shown in the prompt |
| **Input: `--always`** | Flag — prompt even if action is not sensitive |
| **Output (CLI):** exit code | `0` = approved, `1` = denied |
| **Output (module):** return value | `True` = approved, `False` = denied |

**Sensitive keywords that trigger a prompt automatically:**

`delete` · `remove` · `overwrite` · `send` · `email` · `push` · `deploy` · `drop` · `truncate` · `wipe` · `format`

---

## When to Use It

| Situation | Use HITL? |
|-----------|-----------|
| Script is about to send an email | Yes |
| Script is about to delete or overwrite a file | Yes |
| Script is about to push or deploy anything | Yes |
| Read-only operation (generating a plan, reading inbox) | No |
| Running in a fully automated pipeline with no terminal | Not possible — will deny by default |

---

## Limitations

- Requires an interactive terminal (TTY). Automated/headless runs always deny.
- Keyword matching is simple substring search — `"overwrite"` in the action string is enough to trigger it.
- No logging of approval decisions — the calling script is responsible for recording outcomes.

---

## Related

- [[skills/gmail_watcher/SKILL]] — uses HITL before marking emails read
- [[skills/mcp_email_sender/SKILL]] — email sending that should be gated by this skill
- [[Company_Handbook]] — workflow rules for sensitive actions
