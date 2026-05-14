"""
cloud_memory.py — Zuki Cloud-Gedächtnis via Vercel-API
────────────────────────────────────────────────────────
Verhältnis zur Simulation:
  Die LLM-Simulation (kein Gemini/OpenAI Key) hat KEINEN Einfluss auf
  CloudMemory. Beide Systeme sind vollständig unabhängig.
  Cloud speichert auch wenn Zuki im Simulations-Modus läuft.

Konfiguration (.env):
  CLOUD_MEMORY_URL   = https://dein-echtes-projekt.vercel.app/api/memory
  CLOUD_MEMORY_TOKEN = dein-geheimer-token

Status-Feedback:
  save(..., source="manual") → wartet bis zu 5s und gibt Status zurück
  save(..., source="auto")   → fire-and-forget im Hintergrund
  ping()                     → synchroner Verbindungstest

Offline-Outbox:
  Bei Verbindungsausfall landen Saves in temp/cloud_outbox.jsonl.
  Beim nächsten erfolgreichen ping() oder Save wird die Outbox
  im Hintergrund in FIFO-Reihenfolge abgearbeitet.
"""

import os
import json
import uuid
import datetime
import threading
import urllib.request
import urllib.error

from core.logger import get_logger

log = get_logger("cloud_memory")

_AUTO_SAVE_THRESHOLD = 3

_OUTBOX_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp", "cloud_outbox.jsonl")
)

# Placeholder patterns that indicate an unconfigured URL
_URL_PLACEHOLDER_PATTERNS = [
    "your-project",
    "your-",
    "dein-projekt",
    "deine-projekt",
    "example.vercel",
    "placeholder",
    "localhost",
    "127.0.0.1",
]

_TOKEN_PLACEHOLDER_PATTERNS = [
    "your-",
    "dein-",
    "your-key",
    "your-secret",
    "geheim-here",
    "token-here",
    "change-me",
]


def _is_placeholder(value: str, patterns: list[str]) -> bool:
    v = value.lower()
    return any(p in v for p in patterns)


# ── Outbox ────────────────────────────────────────────────────────────────────

class _Outbox:
    """
    Offline-Puffer für Cloud-Saves bei Verbindungsausfall.
    Append-only JSONL, crash-sicher, FIFO-Reihenfolge.
    Status-API: size(), is_flushing(), last_flush_time()
    """

    def __init__(self, path: str, post_fn):
        self._path       = os.path.abspath(path)
        self._post_fn    = post_fn          # CloudMemory._post
        self._lock       = threading.Lock()
        self._flushing   = False
        self._in_flush   = False            # verhindert Re-Queue während Flush
        self._last_flush: datetime.datetime | None = None

    # ── Status-API ────────────────────────────────────────────────────────────

    def size(self) -> int:
        """Anzahl gepufferter Einträge."""
        try:
            if not os.path.exists(self._path):
                return 0
            with self._lock:
                with open(self._path, "r", encoding="utf-8") as f:
                    return sum(1 for line in f if line.strip())
        except Exception:
            return 0

    def is_flushing(self) -> bool:
        return self._flushing

    def last_flush_time(self) -> datetime.datetime | None:
        return self._last_flush

    # ── Öffentliche Methoden ──────────────────────────────────────────────────

    def queue(self, payload: dict) -> None:
        """Hängt payload als JSON-Zeile an die Outbox an (append-only, crash-sicher)."""
        if self._in_flush:
            return  # kein Re-Queue während Flush — würde Duplikate erzeugen
        try:
            os.makedirs(os.path.dirname(self._path), exist_ok=True)
            line = json.dumps(payload, ensure_ascii=False)
            with self._lock:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            log.info(f"[OUTBOX-QUEUE] Eintrag gepuffert | outbox={self.size()}")
        except Exception as e:
            log.error(f"[OUTBOX-QUEUE] Schreiben fehlgeschlagen: {e}")

    def flush_async(self) -> None:
        """Startet Hintergrund-Flush falls nicht bereits läuft und Einträge vorhanden."""
        if self._flushing:
            return
        if self.size() == 0:
            return
        t = threading.Thread(target=self._flush, daemon=True, name="outbox-flush")
        t.start()

    # ── Interner Flush ────────────────────────────────────────────────────────

    def _read_lines(self) -> list[str]:
        try:
            if not os.path.exists(self._path):
                return []
            with open(self._path, "r", encoding="utf-8") as f:
                return [l for l in f.read().splitlines() if l.strip()]
        except Exception:
            return []

    def _remove_first_line(self) -> None:
        """Entfernt die erste Zeile aus der Outbox-Datei (nach erfolgreichem Send)."""
        with self._lock:
            lines = self._read_lines()
            if not lines:
                return
            remaining = lines[1:]
            if remaining:
                with open(self._path, "w", encoding="utf-8") as f:
                    f.write("\n".join(remaining) + "\n")
                    f.flush()
                    os.fsync(f.fileno())
            else:
                try:
                    os.remove(self._path)
                except Exception:
                    open(self._path, "w").close()  # leeren falls remove scheitert

    def _flush(self) -> None:
        """Arbeitet Outbox in FIFO-Reihenfolge ab. Bricht bei erstem Fehler ab."""
        self._flushing = True
        self._in_flush = True
        sent = 0
        try:
            lines = self._read_lines()
            if not lines:
                return

            total = len(lines)
            log.info(f"[OUTBOX-FLUSH] Starte Flush | {total} Einträge")

            for line in lines:
                try:
                    payload = json.loads(line)
                except Exception:
                    log.warning("[OUTBOX-FLUSH] Ungültige JSON-Zeile übersprungen")
                    self._remove_first_line()
                    continue

                result = self._post_fn(payload)

                if result.startswith("ok"):
                    sent += 1
                    self._remove_first_line()
                    log.info(f"[OUTBOX-FLUSH] Gesendet {sent}/{total}")
                else:
                    log.warning(f"[OUTBOX-FAIL] Eintrag fehlgeschlagen: {result} — Abbruch")
                    break

        except Exception as e:
            log.error(f"[OUTBOX-FAIL] Flush-Fehler: {e}")
        finally:
            self._last_flush = datetime.datetime.now()
            self._flushing   = False
            self._in_flush   = False
            remaining = self.size()
            log.info(
                f"[OUTBOX-FLUSH] Abgeschlossen | {sent} gesendet | {remaining} verbleibend"
            )


# ── CloudMemory ───────────────────────────────────────────────────────────────

class CloudMemory:
    """
    Cloud-Gedächtnis für Zuki — unabhängig vom LLM-Simulations-Modus.
    Manuelle Saves geben Echtzeit-Feedback zurück.
    Auto-Saves laufen im Hintergrund (non-blocking).
    Bei Verbindungsausfall: Offline-Outbox puffert Saves in temp/cloud_outbox.jsonl.
    """

    def __init__(self):
        self._url   = os.environ.get("CLOUD_MEMORY_URL",   "").strip()
        self._token = os.environ.get("CLOUD_MEMORY_TOKEN", "").strip()
        self._session_id = str(uuid.uuid4())[:8]

        # Counters & flags
        self._save_count = 0
        self._auto_save  = False
        self._prompted   = False

        # Enabled check: URL must be set and not a placeholder
        self.enabled = (
            bool(self._url)
            and bool(self._token)
            and not _is_placeholder(self._url,   _URL_PLACEHOLDER_PATTERNS)
            and not _is_placeholder(self._token, _TOKEN_PLACEHOLDER_PATTERNS)
        )

        # Outbox — always present even when cloud is disabled
        self.outbox = _Outbox(path=_OUTBOX_PATH, post_fn=self._post)

        if self.enabled:
            log.info(f"CloudMemory aktiv | {self._url} | Session: {self._session_id}")
            # Startup flush: one-time attempt if outbox file exists
            if os.path.exists(_OUTBOX_PATH):
                log.info(f"[OUTBOX-FLUSH] Startup-Flush gestartet (Datei gefunden)")
                self.outbox.flush_async()
        else:
            if self._url and _is_placeholder(self._url, _URL_PLACEHOLDER_PATTERNS):
                log.warning(
                    f"CloudMemory: Platzhalter-URL erkannt — echte Vercel-URL eintragen: "
                    f"{self._url}"
                )
            else:
                log.info("CloudMemory deaktiviert — URL/TOKEN in .env setzen")

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def save_count(self) -> int:
        return self._save_count

    @property
    def auto_save(self) -> bool:
        """True wenn Auto-Save aktiv und Cloud konfiguriert ist."""
        return self._auto_save and self.enabled

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def ping(self, timeout: int = 5) -> tuple[bool, str]:
        """
        Synchroner Verbindungstest — zeigt ob URL und Token korrekt sind.
        Bei Erfolg wird die Outbox im Hintergrund geleert.
        Returns: (success, message)
        """
        if not self.enabled:
            if self._url and _is_placeholder(self._url, _URL_PLACEHOLDER_PATTERNS):
                return False, f"Platzhalter-URL in .env — echte Vercel-URL eintragen"
            return False, "CLOUD_MEMORY_URL / TOKEN nicht konfiguriert"

        try:
            req = urllib.request.Request(
                url     = f"{self._url}?limit=1",
                headers = {"x-zuki-token": self._token},
                method  = "GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                self.outbox.flush_async()  # Verbindung steht — Outbox leeren
                return True, f"Verbunden  ·  HTTP {resp.status}  ·  Session {self._session_id}"
        except urllib.error.HTTPError as e:
            if e.code == 401:
                return False, "Token falsch — CLOUD_MEMORY_TOKEN in .env und Vercel prüfen"
            if e.code == 404:
                return False, "Endpunkt nicht gefunden — CLOUD_MEMORY_URL prüfen"
            return False, f"HTTP {e.code}: {e.reason}"
        except urllib.error.URLError as e:
            return False, f"Keine Verbindung — URL prüfen: {e.reason}"
        except Exception as e:
            return False, f"Unbekannter Fehler: {e}"

    def save(self, text: str, source: str = "manual") -> str:
        """
        Speichert text in der Cloud.

        source="manual" → wartet bis zu 5s, gibt Status zurück ("ok" / Fehlermeldung)
        source="auto"   → fire-and-forget im Hintergrund, gibt "queued" zurück

        HINWEIS: Simulation des LLM hat KEINEN Einfluss auf diese Methode.
        Bei Verbindungsausfall landet der Save in der Offline-Outbox.
        """
        if not self.enabled:
            if _is_placeholder(self._url, _URL_PLACEHOLDER_PATTERNS):
                return "Platzhalter-URL — echte Vercel-URL in .env eintragen"
            return "Cloud-Gedächtnis nicht konfiguriert"

        if source == "manual":
            self._save_count += 1

        try:
            from core.tenant import get_tenant_manager
            _tenant = get_tenant_manager().current()
        except Exception:
            _tenant = "self"

        payload = {
            "text":       text[:8000],
            "source":     source,
            "session_id": self._session_id,
            "timestamp":  datetime.datetime.now().isoformat(),
            "save_nr":    self._save_count if source == "manual" else None,
            "v":          1,
            "tenant":     _tenant,
        }

        if source == "manual":
            # Kurz warten → Echtzeit-Feedback möglich
            result = {"status": "timeout"}
            done   = threading.Event()

            def _run():
                result["status"] = self._post(payload)
                done.set()

            t = threading.Thread(target=_run, daemon=True, name=f"cloud-save-{self._save_count}")
            t.start()
            done.wait(timeout=5)
            return result["status"]

        else:
            # Auto-Save: fire-and-forget
            t = threading.Thread(
                target = self._post,
                args   = (payload,),
                daemon = True,
                name   = "cloud-autosave",
            )
            t.start()
            return "queued"

    def get_latest_bio(self) -> dict | None:
        """
        Holt den neuesten Bio-Eintrag (source='bio') aus der Cloud.
        Gibt {'data': dict, 'saved_at': str} zurück oder None.
        Log-Marker: [BIO-CHECK]
        """
        if not self.enabled:
            return None
        log.info("[BIO-CHECK] Suche neuestes Bio-Backup in der Cloud...")
        try:
            from core.tenant import get_tenant_manager
            _tenant = get_tenant_manager().current()
        except Exception:
            _tenant = "self"

        try:
            req = urllib.request.Request(
                url     = f"{self._url}?source=bio&limit=1&tenant={_tenant}",
                headers = {"x-zuki-token": self._token},
                method  = "GET",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body     = json.loads(resp.read().decode())
                memories = body.get("memories", [])
                if not memories:
                    log.info("[BIO-CHECK] Kein Bio-Backup in der Cloud gefunden")
                    return None
                entry    = memories[0]
                bio_data = json.loads(entry.get("text", "{}"))
                saved_at = entry.get("saved_at", "")
                log.info(f"[BIO-CHECK] Bio-Backup gefunden | saved_at={saved_at[:10]}")
                return {"data": bio_data, "saved_at": saved_at}
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            log.warning(f"[BIO-CHECK] Verbindungsfehler: {e}")
            return None
        except Exception as e:
            log.warning(f"[BIO-CHECK] Fehler: {e}")
            return None

    def save_skill_conversation(self, skill_name: str, text: str) -> str:
        """
        Speichert eine Skill-Konversation in der Cloud.
        Redis-Key: zuki:skill:{name}:conversations:{tenant}
        Fire-and-forget im Hintergrund.
        """
        if not self.enabled:
            return "Cloud nicht konfiguriert"

        try:
            from core.tenant import get_tenant_manager
            _tenant = get_tenant_manager().current()
        except Exception:
            _tenant = "self"

        payload = {
            "skill_name": skill_name,
            "text":       text[:8000],
            "source":     "skill",
            "session_id": self._session_id,
            "tenant":     _tenant,
            "timestamp":  datetime.datetime.now().isoformat(),
            "v":          1,
        }

        t = threading.Thread(
            target=self._post_skill,
            args=(payload,),
            daemon=True,
            name=f"skill-save-{skill_name}",
        )
        t.start()
        return "queued"

    def get_skill_conversations(self, skill_name: str, limit: int = 20) -> list[dict]:
        """
        Holt Skill-Konversationen aus der Cloud.
        Gibt [] zurück wenn Cloud nicht konfiguriert oder Fehler.
        """
        if not self.enabled:
            return []

        try:
            from core.tenant import get_tenant_manager
            _tenant = get_tenant_manager().current()
        except Exception:
            _tenant = "self"

        try:
            skill_url = self._skill_conversations_url()
            req = urllib.request.Request(
                url     = f"{skill_url}?skill={skill_name}&tenant={_tenant}&limit={limit}",
                headers = {"x-zuki-token": self._token},
                method  = "GET",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode())
                return body.get("conversations", [])
        except Exception as e:
            log.warning(f"[SKILL-CONV] Abruf fehlgeschlagen ({skill_name}): {e}")
            return []

    def migrate_to_tenant(self, tenant: str) -> str:
        """
        Ruft POST /api/memory/migrate auf, um Legacy-Einträge (zuki:memories)
        in den Tenant-Key (zuki:memories:{tenant}) zu verschieben.
        Wird einmalig bei der Bundle-5-Migration aufgerufen.
        """
        if not self.enabled:
            return "Cloud nicht konfiguriert — übersprungen"
        try:
            migrate_url = self._url.rstrip("/") + "/migrate"
            data = json.dumps({"tenant": tenant}, ensure_ascii=False).encode("utf-8")
            req  = urllib.request.Request(
                url     = migrate_url,
                data    = data,
                headers = {
                    "Content-Type": "application/json",
                    "x-zuki-token": self._token,
                },
                method  = "POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body     = json.loads(resp.read().decode())
                migrated = body.get("migrated", 0)
                msg      = body.get("message", "")
                log.info(
                    f"[TENANT-MIGRATION] Cloud: {migrated} Einträge migriert"
                    + (f" — {msg}" if msg else "")
                )
                return f"ok  ·  {migrated} Einträge migriert"
        except urllib.error.HTTPError as e:
            return f"HTTP {e.code}: Migration fehlgeschlagen"
        except Exception as e:
            return f"Migration-Fehler: {e}"

    def cleanup_cloud(self, scope: str = "all") -> dict:
        """
        Bereinigt Cloud-Memories für den aktiven Tenant.
        Geschützt: source="bio", "system": True.
        scope: "all" | "source:<name>"
        Gibt {"deleted": int, "protected": int, "total": int, "error": str} zurück.
        """
        if not self.enabled:
            return {"deleted": 0, "protected": 0, "total": 0, "error": "Cloud nicht konfiguriert"}

        try:
            from core.tenant import get_tenant_manager
            _tenant = get_tenant_manager().current()
        except Exception:
            _tenant = "self"

        try:
            cleanup_url = self._cleanup_url()
            data = json.dumps(
                {"tenant": _tenant, "scope": scope}, ensure_ascii=False
            ).encode("utf-8")
            req = urllib.request.Request(
                url     = cleanup_url,
                data    = data,
                headers = {
                    "Content-Type": "application/json",
                    "x-zuki-token": self._token,
                },
                method  = "POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
                log.info(
                    f"[CLOUD-CLEANUP] tenant={_tenant}  scope={scope}  "
                    f"deleted={body.get('deleted', 0)}  "
                    f"protected={body.get('protected', 0)}"
                )
                return {
                    "deleted":   body.get("deleted",   0),
                    "protected": body.get("protected", 0),
                    "total":     body.get("total",     0),
                    "error":     "",
                }
        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}: Cleanup fehlgeschlagen"
            log.warning(f"[CLOUD-CLEANUP] {msg}")
            return {"deleted": 0, "protected": 0, "total": 0, "error": msg}
        except Exception as e:
            log.warning(f"[CLOUD-CLEANUP] Fehler: {e}")
            return {"deleted": 0, "protected": 0, "total": 0, "error": str(e)}

    def should_ask_auto(self) -> bool:
        return (
            self.enabled
            and self._save_count >= _AUTO_SAVE_THRESHOLD
            and not self._prompted
            and not self._auto_save
        )

    def mark_prompted(self) -> None:
        self._prompted = True

    def enable_auto_save(self) -> None:
        self._auto_save = True
        log.info("CloudMemory: Auto-Save aktiviert")

    def disable_auto_save(self) -> None:
        self._auto_save = False

    # ── HTTP-Backend ──────────────────────────────────────────────────────────

    def _cleanup_url(self) -> str:
        """Leitet die Cleanup-URL aus der Memory-URL ab."""
        base = self._url
        for suffix in ("/api/memory", "/memory"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        return base + "/api/memory/cleanup"

    def _skill_conversations_url(self) -> str:
        """Leitet die Skill-Conversations-URL aus der Memory-URL ab."""
        base = self._url
        for suffix in ("/api/memory", "/memory"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
                break
        return base + "/api/skill/conversations"

    def _post_skill(self, payload: dict) -> str:
        """Sendet eine Skill-Konversation an /api/skill/conversations."""
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req  = urllib.request.Request(
                url     = self._skill_conversations_url(),
                data    = data,
                headers = {
                    "Content-Type": "application/json",
                    "x-zuki-token": self._token,
                },
                method  = "POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body  = json.loads(resp.read().decode())
                total = body.get("total", "?")
                log.info(
                    f"[SKILL-CONV] Gespeichert | skill={payload.get('skill_name')} "
                    f"| total={total}"
                )
                return f"ok  ·  {total}"
        except Exception as e:
            log.warning(f"[SKILL-CONV] Post fehlgeschlagen: {e}")
            return f"Fehler: {e}"

    def _post(self, payload: dict) -> str:
        """
        Sendet payload als JSON-POST. Gibt Status-String zurück.
        Bei Netzwerkfehler: Payload in Offline-Outbox einreihen.
        Läuft im Thread — schreibt niemals direkt ins Terminal.
        """
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req  = urllib.request.Request(
                url     = self._url,
                data    = data,
                headers = {
                    "Content-Type": "application/json",
                    "x-zuki-token": self._token,
                },
                method  = "POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body   = json.loads(resp.read().decode())
                total  = body.get("total", "?")
                log.info(
                    f"Cloud gespeichert | HTTP {resp.status} | "
                    f"total={total} | session={self._session_id}"
                )
                # Connection live — drain outbox in the background
                self.outbox.flush_async()
                return f"ok  ·  {total} Einträge gesamt"

        except urllib.error.HTTPError as e:
            msg = f"HTTP {e.code}: {e.reason}"
            log.warning(f"CloudMemory {msg}")
            if e.code == 401:
                return "Token falsch (401) — CLOUD_MEMORY_TOKEN in .env prüfen"
            # HTTP error (4xx/5xx) → do not queue in outbox (not a network outage)
            return msg

        except (urllib.error.URLError, OSError, TimeoutError) as e:
            msg = str(getattr(e, "reason", e))
            if self.outbox._in_flush:
                # Do not re-queue during a flush
                log.warning(f"CloudMemory Verbindungsfehler (Flush): {msg}")
                return f"Keine Verbindung — {msg}"
            log.warning(f"CloudMemory Verbindungsfehler — Outbox: {msg}")
            self.outbox.queue(payload)
            return f"Keine Verbindung — in Outbox gepuffert ({self.outbox.size()} ausstehend)"

        except Exception as e:
            log.warning(f"CloudMemory unbekannter Fehler: {e}")
            return f"Fehler: {e}"
