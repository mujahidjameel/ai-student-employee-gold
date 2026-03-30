"""
AI Employee Vault — Error Recovery System
==========================================

A reusable module that every vault script imports to get:

  • Retry logic with exponential backoff + jitter
  • Typed exceptions for network, file, and script failures
  • A three-channel alert system (log file / vault note / console)
  • Safe file I/O (atomic writes, graceful missing-file handling)
  • Script runner with crash capture and auto-retry
  • Vault health check (required folders and env vars)

Usage (import in any vault script):

    from error_recovery import (
        with_retry, RetryConfig,
        alert, AlertLevel,
        safe_read, safe_write,
        run_script, VaultHealthCheck,
    )
"""

from __future__ import annotations

import functools
import logging
import os
import random
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar

# ── Vault paths ─────────────────────────────────────────────────────────────
VAULT    = Path(__file__).resolve().parent.parent
LOGS_DIR = VAULT / "logs"
ALERTS   = VAULT / "Alerts"

LOGS_DIR.mkdir(parents=True, exist_ok=True)
ALERTS.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOGS_DIR / "error_recovery.log"

F = TypeVar("F", bound=Callable[..., Any])


# ── Logging setup ────────────────────────────────────────────────────────────
def _build_logger() -> logging.Logger:
    logger = logging.getLogger("vault.error_recovery")
    if logger.handlers:          # already initialised in this process
        return logger
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler — DEBUG and above
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler — WARNING and above (keep terminals clean)
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.WARNING)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger


_log = _build_logger()


# ══════════════════════════════════════════════════════════════════════════════
# 1. Custom Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class VaultError(Exception):
    """Base class for all vault errors."""


class NetworkError(VaultError):
    """API call failed, DNS timeout, connection refused, etc."""


class FileError(VaultError):
    """File missing, unreadable, or write failed."""


class ScriptError(VaultError):
    """Subprocess exited with a non-zero code or crashed."""


class ConfigError(VaultError):
    """Missing environment variable or misconfigured setting."""


# ══════════════════════════════════════════════════════════════════════════════
# 2. Alert System
# ══════════════════════════════════════════════════════════════════════════════

class AlertLevel(Enum):
    INFO     = "INFO"
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"


_LEVEL_EMOJI = {
    AlertLevel.INFO:     "ℹ️",
    AlertLevel.WARNING:  "⚠️",
    AlertLevel.ERROR:    "🔴",
    AlertLevel.CRITICAL: "🚨",
}

_LEVEL_TO_LOG = {
    AlertLevel.INFO:     logging.INFO,
    AlertLevel.WARNING:  logging.WARNING,
    AlertLevel.ERROR:    logging.ERROR,
    AlertLevel.CRITICAL: logging.CRITICAL,
}


def alert(
    message: str,
    level: AlertLevel = AlertLevel.ERROR,
    context: str = "",
    script: str = "",
    exc: BaseException | None = None,
) -> None:
    """
    Fire an alert through three channels simultaneously:

      1. logs/error_recovery.log  — always written
      2. Alerts/<timestamp> Alert.md — visible in Obsidian
      3. stderr console            — for WARNING and above

    Args:
        message: Human-readable description of what went wrong.
        level:   AlertLevel (INFO / WARNING / ERROR / CRITICAL).
        context: Extra detail — file path, URL, task name, etc.
        script:  Which script raised this alert.
        exc:     Exception object (traceback appended to vault note).
    """
    now        = datetime.now()
    ts_display = now.strftime("%Y-%m-%d %H:%M:%S")
    ts_file    = now.strftime("%Y-%m-%d %H-%M-%S")
    emoji      = _LEVEL_EMOJI[level]

    # ── Channel 1: log file ──────────────────────────────────────────────────
    log_msg = f"{emoji} {message}"
    if context:
        log_msg += f" | context: {context}"
    if script:
        log_msg += f" | script: {script}"
    _log.log(_LEVEL_TO_LOG[level], log_msg)
    if exc:
        _log.debug("Traceback:\n%s", traceback.format_exc())

    # ── Channel 2: vault note ────────────────────────────────────────────────
    tb_section = ""
    if exc:
        tb_section = f"\n## Traceback\n\n```\n{traceback.format_exc().strip()}\n```\n"

    context_section = f"\n**Context:** {context}" if context else ""
    script_section  = f"\n**Script:** `{script}`"  if script  else ""

    note_content = f"""# {emoji} {level.value} Alert — {ts_display}

**Level:** {level.value}
**Time:** {ts_display}{script_section}{context_section}

---

## Message

{message}
{tb_section}
## Resolution

- [ ] Investigated
- [ ] Fixed
- [ ] Note added to [[Dashboard]]
"""
    note_name = f"{ts_file} {level.value} Alert.md"
    note_path = ALERTS / note_name
    try:
        note_path.write_text(note_content, encoding="utf-8")
    except OSError as write_err:
        _log.error("Could not write alert note %s: %s", note_path, write_err)

    # ── Channel 3: console (stderr) ──────────────────────────────────────────
    if level in (AlertLevel.WARNING, AlertLevel.ERROR, AlertLevel.CRITICAL):
        print(f"\n{emoji} [{level.value}] {message}", file=sys.stderr)
        if context:
            print(f"   Context : {context}", file=sys.stderr)
        if script:
            print(f"   Script  : {script}", file=sys.stderr)
        print(f"   See     : {note_path}", file=sys.stderr)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Retry Logic
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RetryConfig:
    """
    Controls retry behaviour for the @with_retry decorator and run_script().

    Attributes:
        max_attempts:   Total attempts including the first try (min 1).
        base_delay:     Seconds to wait before the second attempt.
        backoff_factor: Multiply delay by this after each failure (2 = double).
        max_delay:      Cap on delay between retries in seconds.
        jitter:         Add up to this many seconds of random noise to each delay.
        catch:          Tuple of exception types that trigger a retry.
                        Defaults to (Exception,) — catches everything.
    """
    max_attempts:   int            = 3
    base_delay:     float          = 2.0
    backoff_factor: float          = 2.0
    max_delay:      float          = 60.0
    jitter:         float          = 1.0
    catch:          tuple[type, ...]  = field(default_factory=lambda: (Exception,))

    # Pre-built profiles --------------------------------------------------
    @classmethod
    def network(cls) -> "RetryConfig":
        """For Gemini API, Gmail API, and any HTTP call."""
        return cls(max_attempts=4, base_delay=3.0, backoff_factor=2.0,
                   max_delay=30.0, jitter=1.5,
                   catch=(NetworkError, OSError, ConnectionError, TimeoutError))

    @classmethod
    def file(cls) -> "RetryConfig":
        """For file reads and writes that may hit transient OS locks."""
        return cls(max_attempts=3, base_delay=0.5, backoff_factor=2.0,
                   max_delay=5.0, jitter=0.2, catch=(OSError, FileError))

    @classmethod
    def script(cls) -> "RetryConfig":
        """For subprocess / script execution."""
        return cls(max_attempts=3, base_delay=5.0, backoff_factor=2.0,
                   max_delay=60.0, jitter=2.0, catch=(ScriptError, OSError))

    @classmethod
    def fast(cls) -> "RetryConfig":
        """Quick retries for lightweight operations."""
        return cls(max_attempts=2, base_delay=0.5, backoff_factor=1.5,
                   max_delay=3.0, jitter=0.1)


def _compute_delay(attempt: int, cfg: RetryConfig) -> float:
    """Return the seconds to sleep before attempt `attempt` (1-indexed, first retry = 2)."""
    delay = cfg.base_delay * (cfg.backoff_factor ** (attempt - 1))
    delay = min(delay, cfg.max_delay)
    delay += random.uniform(0, cfg.jitter)
    return delay


def with_retry(
    cfg: RetryConfig | None = None,
    *,
    script: str = "",
    operation: str = "",
) -> Callable[[F], F]:
    """
    Decorator — wrap a function with retry + exponential backoff.

    Usage:
        @with_retry(RetryConfig.network(), script="plan_generator.py")
        def call_gemini(prompt):
            ...

        @with_retry()          # uses default RetryConfig
        def read_inbox():
            ...
    """
    if cfg is None:
        cfg = RetryConfig()

    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            op = operation or fn.__name__
            last_exc: BaseException | None = None

            for attempt in range(1, cfg.max_attempts + 1):
                try:
                    return fn(*args, **kwargs)

                except cfg.catch as exc:
                    last_exc = exc
                    if attempt == cfg.max_attempts:
                        break  # no more retries

                    delay = _compute_delay(attempt, cfg)
                    _log.warning(
                        "[retry %d/%d] %s failed — %s. Retrying in %.1fs…",
                        attempt, cfg.max_attempts, op, exc, delay,
                    )
                    alert(
                        f"{op} failed on attempt {attempt}/{cfg.max_attempts}. "
                        f"Retrying in {delay:.1f}s.",
                        level=AlertLevel.WARNING,
                        context=str(exc),
                        script=script,
                    )
                    time.sleep(delay)

            # All attempts exhausted
            alert(
                f"{op} failed after {cfg.max_attempts} attempt(s). Giving up.",
                level=AlertLevel.ERROR,
                context=str(last_exc),
                script=script,
                exc=last_exc,
            )
            raise last_exc  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]
    return decorator


# ══════════════════════════════════════════════════════════════════════════════
# 4. Safe File I/O
# ══════════════════════════════════════════════════════════════════════════════

def safe_read(
    path: Path | str,
    fallback: str = "",
    encoding: str = "utf-8",
    script: str = "",
) -> str:
    """
    Read a file and return its contents.
    Returns `fallback` (default empty string) if the file is missing or
    unreadable, and fires a WARNING alert instead of crashing.
    """
    p = Path(path)
    try:
        return p.read_text(encoding=encoding)
    except FileNotFoundError:
        alert(
            f"File not found: {p}",
            level=AlertLevel.WARNING,
            context=str(p),
            script=script,
        )
        return fallback
    except OSError as exc:
        alert(
            f"Could not read {p}: {exc}",
            level=AlertLevel.ERROR,
            context=str(p),
            script=script,
            exc=exc,
        )
        return fallback


def safe_write(
    path: Path | str,
    content: str,
    encoding: str = "utf-8",
    script: str = "",
) -> bool:
    """
    Write content to path atomically (write to .tmp, then rename).
    Returns True on success, False on failure (with an ERROR alert).

    Atomic write prevents leaving a half-written file if the process
    crashes mid-write — important for Dashboard.md and Plan.md.
    """
    p   = Path(path)
    tmp = p.with_suffix(p.suffix + ".tmp")
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(content, encoding=encoding)
        tmp.replace(p)
        return True
    except OSError as exc:
        alert(
            f"Could not write {p}: {exc}",
            level=AlertLevel.ERROR,
            context=str(p),
            script=script,
            exc=exc,
        )
        # Clean up leftover .tmp if it exists
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False


# ══════════════════════════════════════════════════════════════════════════════
# 5. Script Runner with Crash Recovery
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScriptResult:
    success:    bool
    returncode: int
    stdout:     str
    stderr:     str
    attempts:   int


def run_script(
    script_path: Path | str,
    cfg: RetryConfig | None = None,
    timeout: int = 300,
    caller: str = "",
) -> ScriptResult:
    """
    Run a vault Python script as a subprocess with retry + crash capture.

    Args:
        script_path: Absolute path to the .py script.
        cfg:         RetryConfig (defaults to RetryConfig.script()).
        timeout:     Seconds before a subprocess is killed (default 5 min).
        caller:      Name of the calling script for alert attribution.

    Returns:
        ScriptResult with success flag, return code, captured output,
        and number of attempts made.

    Raises:
        ScriptError if all retries are exhausted.
    """
    if cfg is None:
        cfg = RetryConfig.script()

    script_path = Path(script_path)
    last_result: subprocess.CompletedProcess | None = None
    script_label = script_path.name

    for attempt in range(1, cfg.max_attempts + 1):
        try:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                capture_output=True,
                text=True,
                cwd=str(VAULT),
                timeout=timeout,
            )
            last_result = result

            if result.returncode == 0:
                _log.info("[run_script] %s completed OK (attempt %d).", script_label, attempt)
                return ScriptResult(
                    success=True,
                    returncode=result.returncode,
                    stdout=result.stdout,
                    stderr=result.stderr,
                    attempts=attempt,
                )

            # Non-zero exit
            err_preview = (result.stderr or result.stdout or "no output")[:300]
            exc = ScriptError(
                f"{script_label} exited with code {result.returncode}: {err_preview}"
            )

        except subprocess.TimeoutExpired as exc:  # type: ignore[assignment]
            alert(
                f"{script_label} timed out after {timeout}s (attempt {attempt}/{cfg.max_attempts}).",
                level=AlertLevel.ERROR,
                script=caller or script_label,
                exc=exc,
            )
            if attempt == cfg.max_attempts:
                raise ScriptError(f"{script_label} timed out") from exc

        except OSError as exc:  # type: ignore[assignment]
            alert(
                f"Could not launch {script_label}: {exc}",
                level=AlertLevel.CRITICAL,
                script=caller or script_label,
                exc=exc,
            )
            raise ScriptError(f"Could not launch {script_label}") from exc

        # Retry path
        if attempt < cfg.max_attempts:
            delay = _compute_delay(attempt, cfg)
            alert(
                f"{script_label} failed (attempt {attempt}/{cfg.max_attempts}). "
                f"Retrying in {delay:.1f}s.",
                level=AlertLevel.WARNING,
                context=f"exit={getattr(exc, 'returncode', '?')}",
                script=caller or script_label,
            )
            time.sleep(delay)

    # All attempts exhausted
    stderr_tail = ""
    if last_result:
        stderr_tail = (last_result.stderr or last_result.stdout or "")[:500]

    alert(
        f"{script_label} failed after {cfg.max_attempts} attempt(s).",
        level=AlertLevel.CRITICAL,
        context=stderr_tail,
        script=caller or script_label,
    )
    return ScriptResult(
        success=False,
        returncode=last_result.returncode if last_result else -1,
        stdout=last_result.stdout if last_result else "",
        stderr=last_result.stderr if last_result else "",
        attempts=cfg.max_attempts,
    )


# ══════════════════════════════════════════════════════════════════════════════
# 6. Vault Health Check
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class HealthReport:
    healthy:  bool
    issues:   list[str]
    warnings: list[str]

    def print(self) -> None:
        status = "OK" if self.healthy else "DEGRADED"
        print(f"\nVault Health: {status}")
        if self.issues:
            print("  Issues (blocking):")
            for i in self.issues:
                print(f"    🔴 {i}")
        if self.warnings:
            print("  Warnings (non-blocking):")
            for w in self.warnings:
                print(f"    ⚠️  {w}")
        if self.healthy and not self.warnings:
            print("  ✅ All checks passed.")
        print()


class VaultHealthCheck:
    """
    Check that the vault's required structure, env vars, and auth files
    are present before running a script.

    Usage:
        report = VaultHealthCheck().run()
        report.print()
        if not report.healthy:
            sys.exit(1)
    """

    REQUIRED_DIRS = [
        VAULT / "Inbox",
        VAULT / "Needs_Action",
        VAULT / "Done",
        VAULT / "Briefings",
        VAULT / "Alerts",
        VAULT / "logs",
    ]

    REQUIRED_FILES = [
        VAULT / "Dashboard.md",
        VAULT / ".env",
    ]

    OPTIONAL_FILES = [
        VAULT / "Plan.md",
        VAULT / "Company_Handbook.md",
    ]

    REQUIRED_ENV_VARS = [
        "GOOGLE_API_KEY",
    ]

    OPTIONAL_ENV_VARS = [
        "ANTHROPIC_API_KEY",
    ]

    def run(self, fix: bool = True) -> HealthReport:
        """
        Run all checks. If fix=True, auto-create missing directories.
        Returns a HealthReport.
        """
        issues:   list[str] = []
        warnings: list[str] = []

        # Required directories
        for d in self.REQUIRED_DIRS:
            if not d.exists():
                if fix:
                    try:
                        d.mkdir(parents=True, exist_ok=True)
                        warnings.append(f"Created missing directory: {d.relative_to(VAULT)}/")
                    except OSError as exc:
                        issues.append(f"Cannot create directory {d.relative_to(VAULT)}/: {exc}")
                else:
                    issues.append(f"Missing required directory: {d.relative_to(VAULT)}/")

        # Required files
        for f in self.REQUIRED_FILES:
            if not f.exists():
                issues.append(f"Missing required file: {f.relative_to(VAULT)}")

        # Optional files
        for f in self.OPTIONAL_FILES:
            if not f.exists():
                warnings.append(f"Optional file not found: {f.relative_to(VAULT)}")

        # Required env vars (load .env first)
        env_file = VAULT / ".env"
        if env_file.exists():
            _load_dotenv_simple(env_file)

        for var in self.REQUIRED_ENV_VARS:
            if not os.environ.get(var):
                issues.append(f"Missing required env var: {var} (add to .env)")

        for var in self.OPTIONAL_ENV_VARS:
            if not os.environ.get(var):
                warnings.append(f"Optional env var not set: {var}")

        # Alert files in /Alerts — flag if there are unresolved CRITICAL alerts
        critical_unresolved = _count_unresolved_alerts(AlertLevel.CRITICAL)
        error_unresolved    = _count_unresolved_alerts(AlertLevel.ERROR)
        if critical_unresolved:
            issues.append(
                f"{critical_unresolved} unresolved CRITICAL alert(s) in /Alerts — check immediately."
            )
        elif error_unresolved:
            warnings.append(
                f"{error_unresolved} unresolved ERROR alert(s) in /Alerts."
            )

        healthy = len(issues) == 0

        if not healthy:
            alert(
                "Vault health check failed.",
                level=AlertLevel.ERROR,
                context="; ".join(issues),
                script="VaultHealthCheck",
            )

        return HealthReport(healthy=healthy, issues=issues, warnings=warnings)


def _load_dotenv_simple(env_path: Path) -> None:
    """Minimal .env loader — sets os.environ for KEY=value lines."""
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key   = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except OSError:
        pass


def _count_unresolved_alerts(level: AlertLevel) -> int:
    """Count alert notes that have unchecked resolution checkboxes."""
    count = 0
    pattern = f"* {level.value} Alert.md"
    for note in ALERTS.glob(f"*{level.value} Alert.md"):
        try:
            content = note.read_text(encoding="utf-8")
            # Check if any resolution checkboxes are still unchecked
            if "- [ ] Investigated" in content:
                count += 1
        except OSError:
            pass
    return count


# ══════════════════════════════════════════════════════════════════════════════
# 7. CLI — run health check or test alerts from the terminal
# ══════════════════════════════════════════════════════════════════════════════

def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Employee Vault — Error Recovery System"
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("health", help="Run vault health check")

    ta = sub.add_parser("test-alert", help="Fire a test alert to verify all channels work")
    ta.add_argument("--level", default="ERROR",
                    choices=[l.value for l in AlertLevel],
                    help="Alert level (default: ERROR)")

    sub.add_parser("show-alerts", help="List all unresolved alert notes")

    args = parser.parse_args()

    if args.cmd == "health":
        report = VaultHealthCheck().run()
        report.print()
        sys.exit(0 if report.healthy else 1)

    elif args.cmd == "test-alert":
        lvl = AlertLevel(args.level)
        alert(
            f"This is a test {lvl.value} alert from the CLI.",
            level=lvl,
            context="Triggered manually via: python error_recovery.py test-alert",
            script="error_recovery.py",
        )
        print(f"Test alert fired at level {lvl.value}.")
        print(f"Check: {ALERTS}")
        print(f"Log:   {LOG_FILE}")

    elif args.cmd == "show-alerts":
        notes = sorted(ALERTS.glob("*.md"), reverse=True)
        if not notes:
            print("No alert notes in /Alerts.")
        else:
            print(f"{'File':<55} {'Resolved?'}")
            print("-" * 65)
            for n in notes:
                try:
                    content = n.read_text(encoding="utf-8")
                    resolved = "✅ Yes" if "- [ ] Investigated" not in content else "❌ No"
                except OSError:
                    resolved = "? (unreadable)"
                print(f"{n.name:<55} {resolved}")

    else:
        parser.print_help()


if __name__ == "__main__":
    _cli()
