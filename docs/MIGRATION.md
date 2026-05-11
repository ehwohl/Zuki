# Zuki — Migration-Hinweise für künftige Bundles

> Dieses Dokument erklärt was jedes neue Bundle beachten muss,
> damit die Tenant-Isolation aus Bundle 5 erhalten bleibt.
> **Pflicht-Lektüre vor jedem neuen Bundle das Daten speichert.**

---

## Goldene Regel

**Jede neue Funktion, die Daten pro User speichert, muss tenant-aware sein.**

"Pro User" bedeutet: Gedächtnis, Profil, History, Uploads, Cache, Reports,
Konversationen, Skills-Output — alles was sich von Tenant zu Tenant unterscheiden soll.

---

## Checkliste für neue Features

### Cloud-Daten (Redis via Vercel API)

- [ ] Neuer Redis-Key muss das Muster `zuki:{bereich}:{tenant}` verwenden
- [ ] POST-Endpoints lesen `tenant` aus dem Request-Body (`body.get("tenant", "self")`)
- [ ] GET-Endpoints lesen `tenant` aus Query-Params (`request.args.get("tenant", "self")`)
- [ ] Legacy-Fallback nur wenn nötig — mit TODO-Datum und Ablauf-Kommentar
- [ ] `CloudMemory.save()` schickt automatisch den aktuellen Tenant mit (kein Handlungsbedarf)
- [ ] Neue `get_*`-Methoden in `CloudMemory` müssen `&tenant={get_tenant_manager().current()}` anhängen

### Lokale Dateien (pro Tenant)

- [ ] Datei-Pattern: `{name}_{tenant}.{ext}` — Beispiel: `user_profile_self.txt`
- [ ] Pfad-Berechnung via `get_tenant_manager().current()` — nicht hardcoden
- [ ] Bei Tenant-Switch: Datei neu laden (analog zu `UserProfile.reload()`)
- [ ] Neue Manager-Klassen: `_current_path()` Methode als Single Source of Truth

### Chat-History

- [ ] Neue `append()`-artige Methoden: `tenant_id`-Feld setzen
- [ ] Neue `get_context()`-artige Methoden: nach `tenant_id` filtern
- [ ] Import-Pattern:
  ```python
  try:
      from core.tenant import get_tenant_manager
      tenant_id = get_tenant_manager().current()
  except Exception:
      tenant_id = "self"
  ```

### LLM-Provider (DSGVO)

- [ ] Keine direkten `api_mgr.provider`-Checks in Skills — `api_mgr.chat()` prüft selbst
- [ ] Business-Tenants (`require_dsgvo=True`) blockieren Gemini Free automatisch
- [ ] Skills müssen keine DSGVO-Logik kennen — das regelt `APIManager`

### Neue Skills

- [ ] Skills erhalten den `api_mgr` über den Context-Dict → tenant-aware via APIManager
- [ ] Skill-spezifischer Cloud-Speicher: eigener Redis-Key mit Tenant-Suffix
  ```python
  key = f"zuki:skill:{skill_name}:{tenant}"
  ```
- [ ] Kein direkter Redis-Zugriff aus Skills — über `cloud.save()` oder neuen Endpoint

---

## Import-Template

```python
# Tenant-sicherer Zugriff — immer so, nie direkt importieren ohne try/except
try:
    from core.tenant import get_tenant_manager
    tenant = get_tenant_manager().current()
except Exception:
    tenant = "self"
```

---

## Migration-Pattern für neue Bundles

Wenn ein Bundle eine neue Datenstruktur einführt die "geerbt" werden soll:

1. **Migrations-Flag** in `temp/tenants.json` setzen:
   ```python
   # In TenantManager: neuen Marker definieren
   _MIGRATION_KEY_V2 = "__migration_v2_done__"
   ```
2. **Migrations-Logik** in `main.py` analog zu Bundle 5:
   - Lokale Teile: **vor** der Initialisierung des betroffenen Managers
   - Cloud-Teile: **nach** `cloud = CloudMemory()`
3. **Idempotenz**: Immer prüfen ob Ziel schon befüllt, dann überspringen
4. **Keine Daten zerstören**: Bei Fehler Marker NICHT setzen → nächster Start versucht erneut
5. **Log-Marker**: `[TENANT-MIGRATION-V2]` o.ä. für grep-fähige Logs

---

## Audit-Log

Jeder Cloud-Save schreibt automatisch in `zuki:audit:{tenant}` (max. 500 Einträge).
Format: `{action, timestamp, source, summary}`.

Neuer Code soll **keine eigenen Audit-Einträge schreiben** — der POST-Handler in
`zuki_cloud/api/index.py` macht das zentral.

Falls ein Bundle einen eigenen Audit-Typ braucht (z.B. "tenant_switch"), direkt
in `zuki:audit:{tenant}` lpushen mit `action`-Feld.

---

## Legacy-Fallback — Ablaufplan

Der Legacy-Key `zuki:memories` (pre-Bundle-5) wird noch bis **2026-05-25** als
Fallback gelesen. Code-Stellen sind mit `# TODO: nach 2026-05-25 entfernen`
markiert.

**Bundle 7 oder das erste Bundle nach dem 25.05.2026** muss:
1. Legacy-Fallback in `zuki_cloud/api/index.py` entfernen (GET + view)
2. Log-Eintrag `[LEGACY-CLEANUP]` schreiben
3. Dieses Dokument aktualisieren

---

## Bekannte Einschränkungen (Bundle 5 MVP)

| Einschränkung | Workaround | Fix geplant |
|---|---|---|
| Outbox (`cloud_outbox.jsonl`) nicht tenant-aware | Selten genutzt; Einträge haben `tenant`-Feld im Payload | Bundle 7 |
| Audit-Log kein UI | Redis direkt via `/api/memory/view` nicht sichtbar | Bundle 13+ |
| `vision/` Temp-Ordner global | Screenshots nicht pro Tenant getrennt | Bundle 8 |
| `session_state.json` global | State enthält keinen Tenant-Kontext | Bundle 7 |
| History-Datei eine Datei für alle Tenants | Filtert korrekt; wächst aber global | optional, kein Datum |
