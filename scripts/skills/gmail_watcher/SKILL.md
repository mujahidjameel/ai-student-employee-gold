# Gmail Watcher Skill

**Date:** 2026-03-24
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/gmail_watcher.py`

---

## What It Does

The Gmail watcher polls your Gmail inbox every 60 seconds for **unread important emails** (Gmail query: `is:unread is:important`) and automatically saves each one as a task note in `/Needs_Action`.

For each email found it:

1. Fetches the full message (subject, sender, date, plain-text body).
2. Creates a `.md` task note in `/Needs_Action` named `YYYY-MM-DD Email - <Subject>.md`.
3. Embeds the Gmail Message ID in the note to prevent duplicate saves.
4. **Marks the email as read** in Gmail so it won't be picked up on the next poll.

The note includes a standard checklist (Read → Reply/Delegate → Move to Done) and is ready for triage without further setup.

---

## First-Time Setup

Install the required Python packages:

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

On first run, a browser window will open asking you to authorise access to your Gmail account. After approval a `gmail_token.json` file is saved to `scripts/` — subsequent runs use this token automatically and do not require re-authorisation unless the token is revoked.

**Required files in `scripts/`:**

| File | Purpose |
|------|---------|
| `client_secret_...json` | OAuth2 credentials from Google Cloud Console |
| `gmail_token.json` | Auto-generated after first authorisation |

---

## How to Run It

**WSL / Linux:**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/gmail_watcher.py
```

**Windows (CMD or PowerShell):**
```powershell
python D:\AI-EMPLOYEE-VAULT\scripts\gmail_watcher.py
```

Press `Ctrl+C` to stop cleanly.

**Sample output:**
```
AI Employee Vault — Gmail Watcher
Query: is:unread is:important
Polling every 60 seconds. Press Ctrl+C to stop.

[09:22:01] Found 2 unread important email(s)
  [note]  Saved: 2026-03-24 Email - Project Update Required.md
  [read]  Marked as read in Gmail
  [note]  Saved: 2026-03-24 Email - Invoice 1042 attached.md
  [read]  Marked as read in Gmail
```

---

## When to Use It

| Situation | Use Watcher? |
|-----------|-------------|
| You want important emails automatically triaged into the vault | Yes |
| Vault is running as an active AI employee workflow | Yes |
| You are on an active email-heavy workday and don't want to miss anything | Yes |
| Vault is idle / you are not actioning tasks | No — stop the watcher |
| You only want to process emails manually | No |

---

## Customising the Email Query

The Gmail query is defined at the top of `gmail_watcher.py`:

```python
QUERY = "is:unread is:important"
```

You can change this to any valid Gmail search string. Examples:

| Query | Effect |
|-------|--------|
| `is:unread is:important` | Default — unread + starred important |
| `is:unread label:inbox` | All unread inbox emails |
| `is:unread from:boss@company.com` | Unread emails from a specific sender |
| `is:unread subject:invoice` | Unread emails with "invoice" in the subject |

---

## Limitations

- Only plain-text email bodies are extracted. HTML-only emails will show a "no plain-text body available" placeholder.
- Marks emails as read in Gmail upon saving — this is intentional to prevent duplicates but means the email will no longer appear unread in your inbox.
- Processes a maximum of 20 emails per poll cycle.
- Requires an active internet connection and valid OAuth token.
- Task notes are stubs — **Owner** and **Desired Outcome** should be updated before actioning.

---

## Related

- [[skills/filesystem_watcher/SKILL]] — watches `/Inbox` folder instead of Gmail
- [[Company_Handbook]] — triage and execution workflow
