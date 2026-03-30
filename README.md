# 🤖 AI Employee Vault

**Hackathon 0 — Gold Tier** | Student Edition

> An Obsidian-based vault that operates as a fully autonomous AI employee — ingesting emails and files, triaging tasks, generating daily plans, syncing with Odoo ERP, publishing to social media, and processing everything to completion with a human-approval gate on every sensitive action.

---

## 🏆 Tier Progress

| Tier | What was built |
|------|---------------|
| 🥉 **Bronze** | Vault structure, Gmail watcher, filesystem watcher, plan generator, scheduler, HITL approval, MCP email sender |
| 🥈 **Silver** | Ralph Wiggum stop hook, CEO weekly briefing, error recovery system, audit logging |
| 🥇 **Gold** | Odoo ERP integration, social media auto-publisher (LinkedIn, Twitter/X, Instagram), deadline tracker, grade logger, voice inbox |

---

## 🏗️ Architecture

```
  INPUTS                WATCHERS               VAULT
  ──────                ────────               ─────
  Gmail inbox      ──▶  gmail_watcher      ──▶  /Needs_Action
  Files in /Inbox  ──▶  filesystem_watcher ──▶  /Needs_Action
                                                     │
                                                     ▼
                                             plan_generator ──▶ Plan.md
                                             (Gemini 2.5 Flash, daily 09:00)
                                                     │
                                             ralph_wiggum_hook
                                             (blocks Claude until queue empty)
                                                     │
                                             hitl_approval (Y/N gate)
                                                     │
                              ┌──────────────────────┼──────────────────────┐
                              ▼                      ▼                      ▼
                    mcp_email_sender           odoo_sync              social_publisher
                    (send Gmail)               (ERP tasks)            (LinkedIn/Twitter/Instagram)
                                                     │
                                               /Done (archive)
                                                     │
                                             ceo_briefing ──▶ /Briefings/
                                             audit_tool_hook ──▶ logs/audit/
```

---

## 📁 Vault Structure

```
D:\AI-EMPLOYEE-VAULT\
├── CLAUDE.md                  ← AI constitution (rules + architecture)
├── Dashboard.md               ← Live status overview
├── Company_Handbook.md        ← SOPs and workflow rules
├── Plan.md                    ← Daily plan (auto-generated at 09:00)
├── Inbox\                     ← All new inputs land here first
├── Needs_Action\              ← Triaged tasks awaiting action
├── Done\                      ← Completed and archived tasks
├── Briefings\                 ← Weekly CEO progress reports
├── Alerts\                    ← Error alert notes (visible in Obsidian)
├── logs\
│   ├── error_recovery.log
│   └── audit\YYYY-MM-DD.jsonl
└── scripts\
    ├── filesystem_watcher.py
    ├── gmail_watcher.py
    ├── plan_generator.py
    ├── scheduler.py
    ├── hitl_approval.py
    ├── mcp_email_sender.py
    ├── ralph_wiggum_hook.py
    ├── ceo_briefing.py
    ├── error_recovery.py
    ├── audit_logger.py
    ├── audit_tool_hook.py
    ├── odoo_sync.py            ← 🥇 Gold
    ├── social_publisher.py     ← 🥇 Gold
    ├── deadline_tracker.py     ← 🥇 Gold
    ├── grade_logger.py         ← 🥇 Gold
    └── voice_inbox.py          ← 🥇 Gold
```

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 \
            google-api-python-client google-genai python-dotenv schedule
```

### 2. Create `.env`
```env
GOOGLE_API_KEY=your_gemini_api_key_here
ODOO_URL=https://your-odoo-instance.com
ODOO_DB=your_db
ODOO_USERNAME=your@email.com
ODOO_PASSWORD=your_password
```

### 3. Gmail OAuth
1. Google Cloud Console → Enable Gmail API
2. Create OAuth 2.0 credentials → Download JSON → place in `scripts/`
3. First run opens browser for auth → saves `scripts/gmail_token.json`

### 4. Start everything (Windows)
```
Double-click start_vault.bat
```
Or manually:
```bash
python3 scripts/filesystem_watcher.py   # Terminal 1
python3 scripts/gmail_watcher.py        # Terminal 2
python3 scripts/scheduler.py            # Terminal 3
python3 scripts/mcp_email_sender.py     # Terminal 4
```

### 5. Open Claude Code
```bash
cd /mnt/d/AI-EMPLOYEE-VAULT && claude
```

---

## 🥇 Gold Tier Features

### Odoo ERP Integration
Completed tasks sync automatically to Odoo as project tasks with time entries logged.
```bash
python3 scripts/odoo_sync.py
```

### Social Media Publisher 📣
After each CEO briefing, learning highlights are auto-drafted for LinkedIn, Twitter/X, and Instagram — always requiring HITL approval before posting.
```bash
python3 scripts/social_publisher.py
```

### Deadline Tracker ⏰
Scans task notes for date strings and fires alerts 48 hours before any deadline.
```bash
python3 scripts/deadline_tracker.py
```

### Grade Logger 📊
Parses submitted assignment notes, tracks grades, and computes GPA trend over the semester.

### Voice Inbox 🎙️
WhatsApp voice notes → Whisper transcript → task note in `/Needs_Action`.

---

## 🔁 Core Workflow

```
CAPTURE → TRIAGE → EXECUTE → GATE → ARCHIVE → PUBLISH
```

| Step | Folder | Rule |
|------|--------|------|
| Capture | `/Inbox` | All inputs land here first — no exceptions |
| Triage | `/Needs_Action` | Watchers create stub task notes |
| Execute | `/Needs_Action` | Claude works tasks; stop hook blocks until queue empty |
| Gate | — | HITL Y/N required for any send / delete / push / deploy |
| Archive | `/Done` | Append `## Resolution` before moving |
| Publish | Briefings + Social | CEO briefing → social posts (HITL gated) |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Vault / UI | Obsidian |
| AI Agent | Claude Code (claude-sonnet-4-6) |
| Planning AI | Gemini 2.5 Flash |
| Email | Gmail API (OAuth2) |
| ERP | Odoo (REST API) |
| Social | LinkedIn API, Twitter/X API, Instagram Graph API |
| Transport | MCP JSON-RPC 2.0 over stdio |
| Platform | WSL2 on Windows |

---

## 🪝 Claude Code Hooks

| Hook | Fires | Effect |
|------|-------|--------|
| `PostToolUse` | After every tool call | Logs to `logs/audit/YYYY-MM-DD.jsonl` |
| `Stop` | After every response | Blocks Claude if `/Needs_Action` is non-empty |

---

## 📅 Project History

| Date | Milestone |
|------|-----------|
| 2026-03-17 | 🥉 Bronze complete |
| 2026-03-28 | 🥈 Silver complete |
| 2026-03-30 | 🥇 Gold complete |

---

*Built for Hackathon 0 — Panaversity Agentic AI Course* 🚀
