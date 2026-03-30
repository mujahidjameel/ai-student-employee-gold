# SKILL: Human-in-the-Loop Approval Gate

**Script:** `scripts/hitl_approval.py`

## Purpose
Intercept any sensitive action before it executes and require explicit Y/N approval from a human operator in the terminal.

## How It Works
- Maintains a list of sensitive keywords (`delete`, `send`, `email`, `deploy`, etc.).
- If an action description contains any keyword, the operator is prompted.
- Returns exit code `0` (approved) or `1` (denied) when used as a CLI.
- Can be imported as a library: `from scripts.hitl_approval import guard`.

## CLI Usage
```bash
python scripts/hitl_approval.py "send daily report email" --details "To: boss@example.com"
python scripts/hitl_approval.py "delete temp files" --always
```

## Library Usage
```python
from scripts.hitl_approval import guard

if guard("delete old inbox files", details="Files older than 30 days"):
    # proceed
    pass
```

## Integration Points
- Call `guard()` before any vault write, email send, or file deletion in other scripts.
- Non-interactive environments (CI, cron) auto-deny to prevent unattended destructive actions.

## Status: Active
