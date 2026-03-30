# SKILL: Daily Plan Scheduler

**Script:** `scripts/scheduler.py`

## Purpose
Automatically run `plan_generator.py` every day at 09:00 using the `schedule` library.

## How It Works
- Uses Python `schedule` (pure-Python cron-like library, no system cron required).
- Polls every 30 seconds, fires `plan_generator.py` via subprocess at the configured time.
- Logs output from the subprocess to stdout with timestamps.

## Usage
```bash
# Start the scheduler (runs indefinitely in foreground)
python scripts/scheduler.py

# Run as a background daemon (Linux)
nohup python scripts/scheduler.py &> logs/scheduler.log &
```

## Configuration
Edit `scripts/scheduler.py` to change the run time:
```python
RUN_TIME = "09:00"   # 24-hour HH:MM
```

## Dependencies
```
schedule
```
Install: `pip install schedule`

## Status: Active
