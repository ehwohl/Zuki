import json
import os
from datetime import datetime, timezone

from core.logger import get_logger

log = get_logger("history")

HISTORY_FILE  = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "chat_history.json"))
MAX_STORED    = 20   # max messages kept on disk
CONTEXT_WINDOW = 10  # messages passed to LLM per request


class HistoryManager:
    """
    Persistent chat history with automatic trimming.

    Storage  : memory/chat_history.json  (max MAX_STORED messages)
    LLM feed : last CONTEXT_WINDOW messages, always preceded by system prompt
    """

    def __init__(
        self,
        path: str = HISTORY_FILE,
        max_stored: int = MAX_STORED,
        context_window: int = CONTEXT_WINDOW,
    ):
        self._path           = path
        self._max_stored     = max_stored
        self._context_window = context_window
        self._messages: list[dict] = []
        self._load()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def append(self, role: str, content: str, source: str = "chat") -> None:
        """
        Add a message, trim to max_stored, persist to disk.

        source values:
          "chat"   — normaler Gesprächsverlauf (default)
          "broker" — Broker-Report: wird in get_context() isoliert
                     (nur letzter Eintrag, gekürzt auf BROKER_SUMMARY_WORDS)
        """
        try:
            from core.tenant import get_tenant_manager
            tenant_id = get_tenant_manager().current()
        except Exception:
            tenant_id = "self"

        self._messages.append({
            "role":      role,
            "content":   content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source":    source,
            "tenant_id": tenant_id,
        })
        if len(self._messages) > self._max_stored:
            removed = len(self._messages) - self._max_stored
            self._messages = self._messages[-self._max_stored:]
            log.debug(f"History getrimmt: {removed} alte Nachricht(en) entfernt")
        self._save()

    MAX_WORDS            = 500  # hard cap on total words sent to API
    BROKER_SUMMARY_WORDS = 80   # max words from a broker entry in context

    def get_context(self) -> list[dict]:
        """
        Return last CONTEXT_WINDOW meaningful messages, capped at MAX_WORDS.

        Broker-Isolierung:
          - "broker" entries are reduced to the single most recent one.
          - That entry is truncated to BROKER_SUMMARY_WORDS and prefixed
            with [Broker-Report] so the LLM knows it's a market summary,
            not part of the normal dialogue.
          - Fillers skipped. System prompt NOT included.
        Tenant-Isolation:
          - Nur Nachrichten des aktuellen Tenants werden zurückgegeben.
          - Legacy-Einträge ohne tenant_id gelten als "self".
        """
        try:
            from core.tenant import get_tenant_manager
            current_tenant = get_tenant_manager().current()
        except Exception:
            current_tenant = "self"

        # Only include entries from the active tenant
        tenant_msgs = [
            m for m in self._messages
            if m.get("tenant_id", "self") == current_tenant
        ]
        window = tenant_msgs[-self._context_window:]

        # Collect at most ONE broker entry (most recent assistant broker msg)
        last_broker: dict | None = None
        chat_messages: list[dict] = []

        for m in window:
            if m.get("source") == "broker":
                if m["role"] == "assistant":
                    last_broker = m       # keep overwriting → last wins
                # user "report" command also broker-tagged → skip from chat
            else:
                if not self._is_filler(m["content"]):
                    chat_messages.append({"role": m["role"], "content": m["content"]})

        # Build result: chat messages + optional truncated broker summary
        result: list[dict] = list(chat_messages)
        if last_broker:
            words  = last_broker["content"].split()
            snippet = " ".join(words[:self.BROKER_SUMMARY_WORDS])
            if len(words) > self.BROKER_SUMMARY_WORDS:
                snippet += " …"
            result.append({
                "role":    "assistant",
                "content": f"[Broker-Report] {snippet}",
            })

        # Walk backwards, apply word budget
        budget  = self.MAX_WORDS
        trimmed = []
        for msg in reversed(result):
            wc = len(msg["content"].split())
            if budget <= 0:
                break
            trimmed.append(msg)
            budget -= wc
        return list(reversed(trimmed))

    # Filler words that add zero context value
    _FILLERS = {
        "ok", "okay", "k", "ja", "nein", "ne", "jo", "nö",
        "danke", "bitte", "hmm", "hm", "aha", "achso", "ah",
        "gut", "super", "prima", "alles klar", "verstanden",
        "weiter", "los", "und", "also", "genau", "richtig",
    }

    @classmethod
    def _is_filler(cls, text: str) -> bool:
        """True if the message is too short or a known filler phrase."""
        t = text.strip().lower().rstrip(".!?,")
        return len(t) < 3 or t in cls._FILLERS

    def clear(self) -> None:
        """Wipe ALL history from memory and disk (alle Tenants)."""
        self._messages = []
        self._save()
        log.info("Chat-History gelöscht (alle Tenants)")

    def clear_tenant(self, tenant_id: str) -> int:
        """Löscht nur Einträge des angegebenen Tenants. Gibt Anzahl zurück."""
        before = len(self._messages)
        self._messages = [
            m for m in self._messages
            if m.get("tenant_id", "self") != tenant_id
        ]
        deleted = before - len(self._messages)
        self._save()
        log.info(f"Chat-History gelöscht: {deleted} Einträge für tenant='{tenant_id}'")
        return deleted

    @property
    def count(self) -> int:
        return len(self._messages)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not os.path.exists(self._path):
            log.debug("Keine gespeicherte History gefunden — starte frisch")
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._messages = data[-self._max_stored:]
                log.info(f"History geladen: {len(self._messages)} Nachrichten aus {self._path}")
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"History konnte nicht geladen werden: {e} — starte frisch")

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._messages, f, ensure_ascii=False, indent=2)
        except OSError as e:
            log.error(f"History konnte nicht gespeichert werden: {e}")
