# 🤖 AI Employee Vault

**Hackathon 0 — Gold Tier** | Panaversity Agentic AI Course

An Obsidian-based vault that runs as an AI student employee — ingesting emails and files, triaging tasks, generating daily plans, and working through everything autonomously via Claude Code.

---

## 🏆 What We Built

| Tier | What was built |
|------|---------------|
| 🥉 **Bronze** | Installed Obsidian vault, connected with Claude Code, created `Inbox/`, `Needs_Action/`, `Done/` folders, built `filesystem_watcher.py` |
| 🥈 **Silver** | `gmail_watcher.py`, `plan_generator.py`, `scheduler.py`, `mcp_email_sender.py` |
| 🥇 **Gold** | `ceo_briefing.py`, `error_recovery.py`, `audit_logger.py`, `ralph_wiggum_hook.py`, `audit_tool_hook.py` |

---

## 📜 Scripts

| Script | What it does |
|--------|-------------|
| `gmail_watcher.py` | Polls Gmail every 60s, saves unread important emails as task notes in `/Needs_Action` |
| `filesystem_watcher.py` | Watches `/Inbox` every 10s, moves new files to `/Needs_Action` |
| `plan_generator.py` | Reads `/Inbox` + `Dashboard.md`, generates `Plan.md` using Gemini |
| `scheduler.py` | Runs `plan_generator.py` daily at 09:00 |
| `hitl_approval.py` | Y/N approval gate before any sensitive action (send, delete, push) |
| `mcp_email_sender.py` | MCP server exposing `send_email()` tool to Claude Code |
| `ralph_wiggum_hook.py` | Stop hook — blocks Claude from stopping while `/Needs_Action` has tasks |
| `ceo_briefing.py` | Generates weekly student progress report using Gemini → `/Briefings/` |
| `error_recovery.py` | Retry logic, vault health check, alerts to `/Alerts/` |
| `audit_logger.py` | Structured JSONL audit logging + CLI |
| `audit_tool_hook.py` | PostToolUse hook — logs every Claude tool call to `logs/audit/` |

---

## ⚡ Setup

```bash
# 1. Install dependencies
pip install google-auth google-auth-oauthlib google-auth-httplib2 \
            google-api-python-client google-genai python-dotenv schedule

# 2. Create .env at vault root
GOOGLE_API_KEY=your_gemini_api_key_here

# 3. Place Gmail OAuth credentials JSON in scripts/
#    (Google Cloud Console → Gmail API → OAuth 2.0 → Download)

# 4. Start all services (Windows)
start_vault.bat

# OR manually
python3 scripts/filesystem_watcher.py
python3 scripts/gmail_watcher.py
python3 scripts/scheduler.py
python3 scripts/mcp_email_sender.py

# 5. Run Claude Code
cd /mnt/d/AI-EMPLOYEE-VAULT && claude
```

---

## 🛠️ Tech Stack

| | |
|-|-|
| AI Agent | Claude Code (claude-sonnet-4-6) |
| Planning AI | Gemini 2.5 Flash |
| Vault / UI | Obsidian |
| Email | Gmail API (OAuth2) |
| MCP Transport | JSON-RPC 2.0 over stdio |
| Platform | WSL2 on Windows |

---

*Built in one sprint for Hackathon 0 — Panaversity Agentic AI Course 🚀*
