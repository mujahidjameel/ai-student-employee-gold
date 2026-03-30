# SKILL: MCP Email Sender

**Script:** `scripts/mcp_email_sender.py`

## Purpose
MCP (Model Context Protocol) server that exposes a `send_email` tool backed by the Gmail API. Allows any MCP-compatible AI agent to send emails from the vault owner's Gmail account.

## Tool Exposed

### `send_email`
| Parameter | Type   | Required | Description              |
|-----------|--------|----------|--------------------------|
| `to`      | string | Yes      | Recipient email address  |
| `subject` | string | Yes      | Email subject line       |
| `body`    | string | Yes      | Plain-text email body    |

Returns: `{"status": "sent", "message_id": "<gmail_id>"}`

## Setup
1. The Gmail OAuth credentials file must exist at:
   `scripts/client_secret_*.apps.googleusercontent.com.json`
2. On first run, a browser window opens for OAuth consent. The token is saved to `scripts/gmail_token.json` for subsequent runs.
3. The OAuth scope required: `https://www.googleapis.com/auth/gmail.send`

## Running as MCP Server
```bash
python scripts/mcp_email_sender.py
```
The server listens on **stdin/stdout** (MCP stdio transport).

## Claude Code Integration
Add to `.claude/settings.json`:
```json
{
  "mcpServers": {
    "email-sender": {
      "command": "python",
      "args": ["/mnt/d/AI-EMPLOYEE-VAULT/scripts/mcp_email_sender.py"]
    }
  }
}
```

## Dependencies
```
google-auth google-auth-oauthlib google-api-python-client
```
Install: `pip install google-auth google-auth-oauthlib google-api-python-client`

## Status: Active
