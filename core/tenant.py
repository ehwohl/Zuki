"""
tenant.py — Multi-Tenant-Manager für Zuki
──────────────────────────────────────────
Verwaltet Tenant-Kontexte. Standard-Tenant: "self" (persönlich).
Business-Tenants können per 'tenant create <name>' angelegt werden.

Persistenz : temp/tenants.json
Singleton   : get_tenant_manager()

TenantConfig-Felder:
  provider_preference : list[str]  — bevorzugte Provider-Reihenfolge
  require_dsgvo       : bool       — Gemini Free verboten wenn True
  description         : str
  created_at          : str (ISO)
"""

import os
import json
import threading
import datetime

from core.logger import get_logger

log = get_logger("tenant")

_ROOT         = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_TENANTS_FILE = os.path.join(_ROOT, "temp", "tenants.json")

# Interner Schlüssel im tenants-Dict — kein echter Tenant
_MIGRATION_KEY = "__migration_v1_done__"

_SELF_DEFAULTS = {
    "provider_preference": [],
    "require_dsgvo":       False,
    "description":         "Persönlicher Workspace",
}

_BUSINESS_DEFAULTS = {
    "provider_preference": [],
    "require_dsgvo":       True,
    "description":         "",
}


# ── TenantConfig ──────────────────────────────────────────────────────────────

class TenantConfig:
    """Immutable Snapshot der Konfiguration eines Tenants."""

    def __init__(self, data: dict):
        self.provider_preference: list[str] = list(data.get("provider_preference", []))
        self.require_dsgvo: bool            = bool(data.get("require_dsgvo", False))
        self.description: str               = str(data.get("description", ""))
        self.created_at: str                = str(data.get("created_at", ""))

    def to_dict(self) -> dict:
        return {
            "provider_preference": self.provider_preference,
            "require_dsgvo":       self.require_dsgvo,
            "description":         self.description,
            "created_at":          self.created_at,
        }


# ── TenantManager ─────────────────────────────────────────────────────────────

class TenantManager:
    """
    Singleton-Verwalter für Tenants.
    Instanz immer via get_tenant_manager() holen, nie direkt konstruieren.
    """

    def __init__(self):
        self._current: str         = "self"
        self._tenants: dict        = {}
        self._lock                 = threading.Lock()
        self._load()

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def current(self) -> str:
        """Gibt den Namen des aktiven Tenants zurück."""
        return self._current

    def switch(self, name: str) -> bool:
        """Wechselt zu einem bekannten Tenant. Gibt True bei Erfolg zurück."""
        with self._lock:
            if name not in self._tenants or name == _MIGRATION_KEY:
                return False
            self._current = name
            self._save()
        log.info(f"[TENANT] Gewechselt zu: {name}")
        return True

    def create(self, name: str, config: dict | None = None) -> bool:
        """
        Erstellt einen neuen Tenant mit Default-Config.
        Gibt False zurück falls Name schon belegt oder ungültig.
        """
        if not name or name == _MIGRATION_KEY:
            return False
        with self._lock:
            if name in self._tenants:
                return False
            base = _SELF_DEFAULTS.copy() if name == "self" else _BUSINESS_DEFAULTS.copy()
            base["created_at"] = datetime.datetime.now().isoformat()
            if config:
                base.update(config)
            self._tenants[name] = base
            self._save()
        log.info(f"[TENANT] Erstellt: {name}")
        return True

    def delete(self, name: str) -> bool:
        """
        Löscht einen Tenant aus tenants.json.
        'self' und der aktive Tenant können nicht gelöscht werden.
        """
        if name in ("self", _MIGRATION_KEY):
            return False
        with self._lock:
            if name not in self._tenants:
                return False
            if self._current == name:
                return False
            del self._tenants[name]
            self._save()
        log.info(f"[TENANT] Gelöscht: {name}")
        return True

    def list_known(self) -> list[str]:
        """Alle bekannten Tenant-Namen (ohne interne Marker)."""
        return [k for k in self._tenants if k != _MIGRATION_KEY]

    def config(self, name: str) -> dict:
        """Raw-Config-Dict eines Tenants oder leeres Dict."""
        return self._tenants.get(name, {}).copy()

    def get_config(self, name: str | None = None) -> TenantConfig:
        """TenantConfig-Snapshot für *name* oder den aktiven Tenant."""
        target = name if name is not None else self._current
        return TenantConfig(self._tenants.get(target, {}))

    # ── Migration-Marker ──────────────────────────────────────────────────────

    def migration_done(self) -> bool:
        """True wenn die Bundle-5-Migration bereits abgeschlossen ist."""
        return bool(self._tenants.get(_MIGRATION_KEY))

    def mark_migration_done(self) -> None:
        """Setzt den Migration-Marker (idempotent)."""
        with self._lock:
            self._tenants[_MIGRATION_KEY] = True
            self._save()
        log.info("[TENANT-MIGRATION] Abgeschlossen — Marker gesetzt")

    # ── Status-API (für system test) ──────────────────────────────────────────

    def self_test(self) -> dict:
        """Prüft die Tenant-Infrastruktur. Gibt dict mit status/summary zurück."""
        try:
            if not os.path.exists(_TENANTS_FILE):
                return {
                    "status":   "warn",
                    "summary":  "tenants.json noch nicht erstellt — wird beim nächsten Save angelegt",
                    "fix_hint": "",
                }

            known = self.list_known()

            if self._current not in known:
                return {
                    "status":   "fail",
                    "summary":  f"Aktiver Tenant '{self._current}' nicht in tenants.json",
                    "fix_hint": "tenant switch self",
                }

            for k in known:
                if not isinstance(self._tenants.get(k), dict):
                    return {
                        "status":   "fail",
                        "summary":  f"Config für Tenant '{k}' ungültig",
                        "fix_hint": "temp/tenants.json manuell prüfen oder löschen",
                    }

            if not self.migration_done():
                return {
                    "status":   "warn",
                    "summary":  "Migration noch nicht abgeschlossen",
                    "fix_hint": "Zuki neu starten — Migration läuft automatisch",
                }

            return {
                "status":  "ok",
                "summary": (
                    f"Aktiver Tenant: {self._current}  ·  "
                    f"{len(known)} bekannte Tenants  ·  Migration OK"
                ),
            }
        except Exception as e:
            return {"status": "fail", "summary": f"Tenant-Fehler: {e}", "fix_hint": ""}

    # ── Persistenz ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not os.path.exists(_TENANTS_FILE):
            log.debug("[TENANT] tenants.json nicht gefunden — 'self' angelegt")
            self._tenants = {
                "self": {
                    **_SELF_DEFAULTS,
                    "created_at": datetime.datetime.now().isoformat(),
                }
            }
            return

        try:
            with open(_TENANTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._tenants = data.get("tenants", {})
            self._current = data.get("current", "self")
            if "self" not in self._tenants:
                self._tenants["self"] = {
                    **_SELF_DEFAULTS,
                    "created_at": datetime.datetime.now().isoformat(),
                }
            log.info(
                f"[TENANT] Geladen: current={self._current}  ·  "
                f"{len(self.list_known())} Tenants"
            )
        except (json.JSONDecodeError, OSError) as e:
            log.warning(f"[TENANT] Ladefehler ({e}) — starte mit 'self'")
            self._tenants = {
                "self": {
                    **_SELF_DEFAULTS,
                    "created_at": datetime.datetime.now().isoformat(),
                }
            }

    def _save(self) -> None:
        try:
            os.makedirs(os.path.dirname(_TENANTS_FILE), exist_ok=True)
            with open(_TENANTS_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {"current": self._current, "tenants": self._tenants},
                    f, ensure_ascii=False, indent=2,
                )
        except OSError as e:
            log.error(f"[TENANT] Speicherfehler: {e}")


# ── Singleton ─────────────────────────────────────────────────────────────────

_tenant_manager: TenantManager | None = None
_tm_lock = threading.Lock()


def get_tenant_manager() -> TenantManager:
    """Gibt die Singleton-Instanz des TenantManagers zurück."""
    global _tenant_manager
    if _tenant_manager is None:
        with _tm_lock:
            if _tenant_manager is None:
                _tenant_manager = TenantManager()
    return _tenant_manager
