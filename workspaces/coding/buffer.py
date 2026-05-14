"""
buffer.py — Persistent code buffer per language
─────────────────────────────────────────────────
Stores the current code buffer per language in temp/coding_buffers.json.
Survives restarts — buffers persist until explicitly cleared.
"""

import json
from pathlib import Path

_ROOT        = Path(__file__).resolve().parent.parent.parent
_BUFFER_FILE = _ROOT / "temp" / "coding_buffers.json"

LANGUAGES      = {"python", "js", "ts", "bash", "go", "pine"}
NO_RUN_LANGS   = {"pine", "ts"}   # ts without ts-node, pine never locally
LANG_EXTENSION = {
    "python": ".py",
    "js":     ".js",
    "ts":     ".ts",
    "bash":   ".sh",
    "go":     ".go",
    "pine":   ".pine",
}
LANG_LABEL = {
    "python": "Python",
    "js":     "JavaScript",
    "ts":     "TypeScript",
    "bash":   "Bash",
    "go":     "Go",
    "pine":   "Pine Script",
}


class CodeBuffer:
    def __init__(self) -> None:
        self._data:   dict[str, str] = {}
        self._active: str            = "python"
        self._load()

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not _BUFFER_FILE.exists():
            return
        try:
            raw           = json.loads(_BUFFER_FILE.read_text(encoding="utf-8"))
            self._data    = raw.get("buffers", {})
            self._active  = raw.get("active", "python")
        except Exception:
            pass

    def _save(self) -> None:
        _BUFFER_FILE.parent.mkdir(parents=True, exist_ok=True)
        _BUFFER_FILE.write_text(
            json.dumps(
                {"buffers": self._data, "active": self._active},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # ── Buffer operations ─────────────────────────────────────────────────────

    def get(self, lang: str) -> str:
        return self._data.get(lang, "")

    def set(self, lang: str, code: str) -> None:
        self._data[lang] = code
        self._save()

    def append_line(self, lang: str, line: str) -> None:
        existing         = self._data.get(lang, "")
        self._data[lang] = (existing + "\n" + line).lstrip("\n")
        self._save()

    def clear(self, lang: str) -> None:
        self._data.pop(lang, None)
        self._save()

    # ── Active language ───────────────────────────────────────────────────────

    def set_active(self, lang: str) -> None:
        self._active = lang
        self._save()

    def active(self) -> str:
        return self._active

    # ── Helpers ───────────────────────────────────────────────────────────────

    def has_content(self) -> list[str]:
        """Languages with non-empty buffers."""
        return [lang for lang, code in self._data.items() if code.strip()]

    def get_status(self) -> dict:
        return {
            "active":   self._active,
            "buffers":  {lang: len(code) for lang, code in self._data.items() if code.strip()},
            "file":     str(_BUFFER_FILE),
        }
