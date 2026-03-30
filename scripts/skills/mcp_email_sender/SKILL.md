# MCP Email Sender Skill

**Date:** 2026-03-26
**Owner:** AI Employee
**Status:** active
**Script:** `scripts/mcp_email_sender.py`

---

## What It Does

The MCP Email Sender exposes a single MCP tool — `send_email` — over the **stdio transport** (JSON-RPC 2.0). It allows any MCP-compatible host (Claude Desktop, Claude Code, or another agent) to send emails via the Gmail API without direct Python imports.

When called it:

1. Authenticates with Gmail using the same OAuth credentials as `gmail_watcher.py`.
2. Constructs a plain-text MIME email from the provided `to`, `subject`, and `body` fields.
3. Sends the message via the Gmail API (`users.messages.send`).
4. Returns a JSON result with `status: "sent"` and the Gmail `message_id`.

The server runs indefinitely, reading JSON-RPC requests from stdin and writing responses to stdout — one JSON object per line.

---

## First-Time Setup

### 1. Install dependencies

```bash
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### 2. Place OAuth credentials

The script requires the Google Cloud OAuth2 client secret file in `scripts/`:

| File | Purpose |
|------|---------|
| `client_secret_...json` | OAuth2 credentials from Google Cloud Console |
| `gmail_token.json` | Auto-generated on first authorisation |

The credentials file must have the `gmail.send` scope enabled in Google Cloud Console.

### 3. First authorisation

On first run a browser window will open for Gmail OAuth consent. After approval `gmail_token.json` is saved to `scripts/` and reused on all subsequent runs.

---

## How to Run It

**WSL / Linux (as a standalone MCP server):**
```bash
python /mnt/d/AI-EMPLOYEE-VAULT/scripts/mcp_email_sender.py
```

**Windows (CMD or PowerShell):**
```powershell
python D:\AI-EMPLOYEE-VAULT\scripts\mcp_email_sender.py
```

The server starts silently and waits for JSON-RPC input on stdin.

### Registering with Claude Code (MCP config)

Add to your MCP server config (e.g. `.claude/mcp_servers.json`):

```json
{
  "mcp_email_sender": {
    "command": "python",
    "args": ["/mnt/d/AI-EMPLOYEE-VAULT/scripts/mcp_email_sender.py"]
  }
}
```

### Manual test (send a request directly)

```bash
echo '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"send_email","arguments":{"to":"you@example.com","subject":"Test","body":"Hello from vault."}}}' \
  | python scripts/mcp_email_sender.py
```

**Sample response:**
```json
{"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "{\"status\": \"sent\", \"message_id\": \"18f3a2c9d1e\"}"}], "isError": false}}
```

---

## Inputs / Outputs

### Tool: `send_email`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `to` | string | Yes | Recipient email address |
| `subject` | string | Yes | Email subject line |
| `body` | string | Yes | Plain-text email body |

**Output (success):**
```json
{"status": "sent", "message_id": "<gmail-message-id>"}
```

**Output (failure):**
```json
{"type": "text", "text": "Error: <exception message>"}
```
with `"isError": true`.

### MCP methods supported

| Method | Description |
|--------|-------------|
| `initialize` | Handshake — returns server info and capabilities |
| `tools/list` | Returns the `send_email` tool manifest |
| `tools/call` | Executes `send_email` with the provided arguments |

---

## When to Use It

| Situation | Use This? |
|-----------|-----------|
| An agent needs to send an email without direct Python access | Yes |
| Integrating email sending into a Claude Code workflow via MCP | Yes |
| Sending bulk or HTML emails | No — plain-text only |
| You need read/modify access to Gmail (not just send) | No — use `gmail_watcher.py` for reading |

---

## Limitations

- Sends plain-text emails only. HTML formatting is not supported.
- Sends as the authenticated Gmail account — no support for aliases or alternate senders.
- One message per `tools/call` invocation — no batch sending.
- Requires an active internet connection and valid OAuth token.
- Non-interactive environments must have a pre-existing valid `gmail_token.json` (no browser for re-auth).

---

## Related

- [[skills/gmail_watcher/SKILL]] — reads incoming Gmail; shares the same OAuth credentials
- [[skills/hitl_approval/SKILL]] — gate email sending behind human approval before calling this tool
- [[Company_Handbook]] — workflow rules for outbound communication
