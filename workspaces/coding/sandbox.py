"""
sandbox.py — Isolated code execution with timeout
────────────────────────────────────────────────────
Runs code in temp/sandbox/ — one temp file per run,
deleted immediately after execution.

Supported languages: python, js, bash, go, ts (via ts-node if installed)
Not locally executable:  pine (Pine Script → TradingView)
"""

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

_ROOT       = Path(__file__).resolve().parent.parent.parent
_SANDBOX    = _ROOT / "temp" / "sandbox"
_DEFAULT_TO = 10   # seconds


@dataclass
class RunResult:
    lang:       str
    stdout:     str
    stderr:     str
    returncode: int
    timed_out:  bool
    error:      str = ""

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out and not self.error

    def format_output(self) -> str:
        parts = []
        if self.error:
            parts.append(f"Fehler: {self.error}")
        if self.timed_out:
            parts.append(f"Timeout nach {_DEFAULT_TO}s — Ausführung abgebrochen.")
        if self.stdout.strip():
            parts.append(self.stdout.rstrip())
        if self.stderr.strip():
            parts.append(f"[stderr]\n{self.stderr.rstrip()}")
        if not parts:
            parts.append("(kein Output)")
        return "\n".join(parts)


# ── Public API ────────────────────────────────────────────────────────────────

def run_code(lang: str, code: str, timeout: int = _DEFAULT_TO) -> RunResult:
    _SANDBOX.mkdir(parents=True, exist_ok=True)

    runners = {
        "python": _run_python,
        "js":     _run_js,
        "ts":     _run_ts,
        "bash":   _run_bash,
        "go":     _run_go,
    }

    runner = runners.get(lang)
    if runner is None:
        return RunResult(
            lang=lang, stdout="", stderr="", returncode=-1, timed_out=False,
            error=f"Language '{lang}' cannot be executed locally.",
        )
    return runner(code, timeout)


def is_available(lang: str) -> tuple[bool, str]:
    """Checks whether the interpreter for a language is present."""
    checks = {
        "python": ([sys.executable, "--version"], ""),
        "js":     (["node",    "--version"],      "node nicht gefunden — Node.js installieren"),
        "ts":     (["ts-node", "--version"],      "ts-node nicht installiert (npm install -g ts-node)"),
        "bash":   (["bash",    "--version"],      "bash nicht gefunden"),
        "go":     (["go",      "version"],        "Go nicht installiert (https://go.dev)"),
    }
    if lang not in checks:
        return False, f"'{lang}' nicht lokal ausführbar"

    cmd, hint = checks[lang]
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True, ""
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False, hint or f"'{lang}'-Interpreter nicht gefunden"


# ── Internal runners ──────────────────────────────────────────────────────────

def _exec(cmd: list[str], timeout: int) -> RunResult:
    lang = cmd[0]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ.copy(),
        )
        return RunResult(
            lang=lang,
            stdout=result.stdout[:4000],
            stderr=result.stderr[:2000],
            returncode=result.returncode,
            timed_out=False,
        )
    except subprocess.TimeoutExpired:
        return RunResult(lang=lang, stdout="", stderr="", returncode=-1, timed_out=True)
    except FileNotFoundError as e:
        return RunResult(
            lang=lang, stdout="", stderr="", returncode=-1, timed_out=False,
            error=f"Interpreter nicht gefunden: {e}",
        )


def _with_tempfile(suffix: str, code: str, cmd_builder) -> RunResult:
    """Writes code to a temp file, runs cmd_builder(path), deletes it afterwards."""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=suffix, dir=_SANDBOX,
            delete=False, encoding="utf-8",
        ) as f:
            f.write(code)
            path = f.name
    except OSError as e:
        return RunResult(lang=suffix.lstrip("."), stdout="", stderr="",
                         returncode=-1, timed_out=False, error=str(e))
    try:
        return cmd_builder(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _run_python(code: str, timeout: int) -> RunResult:
    return _with_tempfile(".py", code, lambda p: _exec([sys.executable, p], timeout))


def _run_js(code: str, timeout: int) -> RunResult:
    return _with_tempfile(".js", code, lambda p: _exec(["node", p], timeout))


def _run_ts(code: str, timeout: int) -> RunResult:
    return _with_tempfile(".ts", code, lambda p: _exec(["ts-node", p], timeout))


def _run_bash(code: str, timeout: int) -> RunResult:
    return _with_tempfile(".sh", code, lambda p: _exec(["bash", p], timeout))


def _run_go(code: str, timeout: int) -> RunResult:
    return _with_tempfile(".go", code, lambda p: _exec(["go", "run", p], timeout))
