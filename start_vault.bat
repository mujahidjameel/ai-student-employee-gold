@echo off
echo Starting AI Employee Vault...

start "Filesystem Watcher" /MIN python D:\AI-EMPLOYEE-VAULT\scripts\filesystem_watcher.py
start "Gmail Watcher" /MIN python D:\AI-EMPLOYEE-VAULT\scripts\gmail_watcher.py
start "Scheduler" /MIN python D:\AI-EMPLOYEE-VAULT\scripts\scheduler.py

echo.
echo All scripts started in background!
echo You can now open Obsidian and start working.
echo.
pause
