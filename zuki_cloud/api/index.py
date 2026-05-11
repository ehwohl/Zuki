"""
Zuki Cloud-Gedächtnis — Vercel Serverless API
───────────────────────────────────────────────
POST /api/memory             → Eintrag speichern (tenant-aware)
GET  /api/memory             → Letzte Einträge abrufen (JSON)
GET  /api/memory/view        → Erinnerungen im Browser anzeigen (HTML)
GET  /api/memory/health      → Verbindungstest
POST /api/memory/migrate     → Legacy-Key → Tenant-Key migrieren (einmalig)
POST /api/skill/conversations → Skill-Konversation speichern (Bundle 6)
GET  /api/skill/conversations → Skill-Konversationen abrufen (Bundle 6)

Redis-Keys (ab Bundle 5):
  zuki:memories:{tenant}                     ← Gedächtnis-Einträge pro Tenant
  zuki:audit:{tenant}                        ← Audit-Log pro Tenant
  zuki:memories                              ← Legacy-Key (pre-Bundle-5); Fallback bis 2026-05-25
  zuki:skill:{name}:conversations:{tenant}   ← Skill-Konversationen (ab Bundle 6)

Browser-URL:
  https://zuki-cloud.vercel.app/api/memory/view?token=DEIN_TOKEN&limit=50&tenant=self

Vercel Environment Variables:
  REDIS_URL           — wird automatisch von zuki-kv gesetzt
  CLOUD_MEMORY_TOKEN  — Auth-Token (identisch mit D:\\Zuki\\.env)
"""

import os
import json
import datetime
import redis
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

MAX_ENTRIES            = 200
MAX_AUDIT_ENTRIES      = 500
MAX_SKILL_CONV_ENTRIES = 100

# Legacy-Key vor Bundle-5-Migration
LEGACY_MEM_KEY = "zuki:memories"


def get_redis():
    url = os.environ.get("REDIS_URL", "")
    if not url:
        raise RuntimeError("REDIS_URL nicht gesetzt — zuki-kv mit Projekt verbinden")
    return redis.from_url(url, decode_responses=True)


def is_authorized(req) -> bool:
    expected = os.environ.get("CLOUD_MEMORY_TOKEN", "")
    received = req.headers.get("x-zuki-token", "")
    return bool(expected) and received == expected


def utc_now() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _mem_key(tenant: str = "self") -> str:
    return f"zuki:memories:{tenant}"


def _audit_key(tenant: str = "self") -> str:
    return f"zuki:audit:{tenant}"


def _skill_key(skill_name: str, tenant: str = "self") -> str:
    return f"zuki:skill:{skill_name}:conversations:{tenant}"


# ── POST /api/memory ───────────────────────────────────────────────────────────

@app.route("/api/memory", methods=["POST"])
def save_memory():
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert — CLOUD_MEMORY_TOKEN prüfen"}), 401

    body   = request.get_json(silent=True) or {}
    text   = body.get("text", "").strip()
    tenant = body.get("tenant", "self") or "self"

    if not text:
        return jsonify({"error": "'text' fehlt oder leer"}), 400

    entry = {
        "text":       text[:8000],
        "source":     body.get("source",     "manual"),
        "session_id": body.get("session_id", "unknown"),
        "tenant":     tenant,
        "timestamp":  body.get("timestamp",  utc_now()),
        "saved_at":   utc_now(),
        "v":          body.get("v", 1),
    }

    try:
        r       = get_redis()
        mem_key = _mem_key(tenant)

        r.lpush(mem_key, json.dumps(entry, ensure_ascii=False))
        r.ltrim(mem_key, 0, MAX_ENTRIES - 1)
        total = r.llen(mem_key)

        # Audit-Log: kompakter Eintrag pro Save
        audit_entry = {
            "action":    "save",
            "timestamp": utc_now(),
            "source":    entry["source"],
            "summary":   text[:100],
        }
        r.lpush(_audit_key(tenant), json.dumps(audit_entry, ensure_ascii=False))
        r.ltrim(_audit_key(tenant), 0, MAX_AUDIT_ENTRIES - 1)

    except Exception as e:
        return jsonify({"error": f"Redis-Fehler: {e}"}), 500

    return jsonify({
        "status":     "gespeichert",
        "session_id": entry["session_id"],
        "tenant":     tenant,
        "total":      total,
    })


# ── GET /api/memory ────────────────────────────────────────────────────────────

@app.route("/api/memory", methods=["GET"])
def get_memories():
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert"}), 401

    limit         = min(int(request.args.get("limit", 20)), 200)
    source_filter = request.args.get("source", "").strip()
    tenant        = request.args.get("tenant", "self") or "self"

    try:
        r       = get_redis()
        mem_key = _mem_key(tenant)
        fetch   = MAX_ENTRIES if source_filter else limit
        raw     = r.lrange(mem_key, 0, fetch - 1)
        total   = r.llen(mem_key)

        # Legacy-Fallback: wenn Tenant-Key leer, Legacy-Key lesen
        # TODO: nach 2026-05-25 entfernen
        if not raw and tenant == "self":
            raw   = r.lrange(LEGACY_MEM_KEY, 0, fetch - 1)
            total = r.llen(LEGACY_MEM_KEY)

    except Exception as e:
        return jsonify({"error": f"Redis-Fehler: {e}"}), 500

    memories = []
    for item in raw:
        try:
            entry = json.loads(item)
            if source_filter and entry.get("source") != source_filter:
                continue
            memories.append(entry)
            if len(memories) >= limit:
                break
        except Exception:
            if not source_filter:
                memories.append({"raw": item})

    return jsonify({"memories": memories, "total": total, "returned": len(memories)})


# ── POST /api/memory/migrate ───────────────────────────────────────────────────

@app.route("/api/memory/migrate", methods=["POST"])
def migrate_memories():
    """
    Einmalige Migration: zuki:memories → zuki:memories:{tenant}.
    Idempotent: übersprungen falls Ziel-Key bereits Daten hat.
    """
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert"}), 401

    body          = request.get_json(silent=True) or {}
    target_tenant = body.get("tenant", "self") or "self"

    try:
        r           = get_redis()
        all_entries = r.lrange(LEGACY_MEM_KEY, 0, -1)

        if not all_entries:
            return jsonify({
                "status":   "ok",
                "migrated": 0,
                "message":  "Legacy-Key leer — nichts zu migrieren",
            })

        existing = r.llen(_mem_key(target_tenant))
        if existing > 0:
            return jsonify({
                "status":   "ok",
                "migrated": 0,
                "message":  f"Ziel-Key bereits befüllt ({existing} Einträge) — übersprungen",
            })

        # Einträge in LIFO-Reihenfolge kopieren:
        # all_entries[0] = neuester → zuletzt lpush'd → landet am Kopf → korrekt
        for entry in reversed(all_entries):
            r.lpush(_mem_key(target_tenant), entry)
        r.ltrim(_mem_key(target_tenant), 0, MAX_ENTRIES - 1)

        total = r.llen(_mem_key(target_tenant))
        return jsonify({
            "status":   "ok",
            "migrated": len(all_entries),
            "total":    total,
        })

    except Exception as e:
        return jsonify({"error": f"Redis-Fehler: {e}"}), 500


# ── GET /api/memory/view — HTML-Ansicht für den Browser ───────────────────────

@app.route("/api/memory/view", methods=["GET"])
def view_memories():
    token    = request.args.get("token", "")
    expected = os.environ.get("CLOUD_MEMORY_TOKEN", "")
    if not expected or token != expected:
        return Response(
            "<html><body style='font-family:monospace;background:#0d0d0d;color:#ff4444;"
            "padding:40px'><h2>⛔ Zugriff verweigert</h2>"
            "<p>Token fehlt oder falsch.<br>"
            "URL: <code>/api/memory/view?token=DEIN_TOKEN</code></p></body></html>",
            status=401, mimetype="text/html"
        )

    limit  = min(int(request.args.get("limit", 50)), 200)
    tenant = request.args.get("tenant", "self") or "self"

    try:
        r       = get_redis()
        mem_key = _mem_key(tenant)
        raw     = r.lrange(mem_key, 0, limit - 1)
        total   = r.llen(mem_key)

        # Legacy-Fallback für self
        # TODO: nach 2026-05-25 entfernen
        if not raw and tenant == "self":
            raw   = r.lrange(LEGACY_MEM_KEY, 0, limit - 1)
            total = r.llen(LEGACY_MEM_KEY)

    except Exception as e:
        return Response(f"<pre>Redis-Fehler: {e}</pre>", status=500, mimetype="text/html")

    entries = []
    for item in raw:
        try:
            entries.append(json.loads(item))
        except Exception:
            entries.append({"text": item, "source": "?", "session_id": "?", "saved_at": ""})

    # ── HTML aufbauen ──────────────────────────────────────────────────────────
    cards = ""
    for e in entries:
        saved   = e.get("saved_at", e.get("timestamp", ""))[:19].replace("T", "  ")
        source  = e.get("source", "?")
        session = e.get("session_id", "?")
        text    = e.get("text", "").replace("&", "&amp;").replace("<", "&lt;")
        badge   = "#4fc3f7" if source == "manual" else "#81c784"
        label   = "💾 manuell" if source == "manual" else "⚡ auto"
        cards += f"""
        <div class="card">
            <div class="meta">
                <span class="time">🕐 {saved}</span>
                <span class="badge" style="background:{badge}">{label}</span>
                <span class="session">Session {session}</span>
            </div>
            <div class="text">{text}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Zuki — Cloud-Gedächtnis [{tenant}]</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Segoe UI', system-ui, sans-serif;
      background: #0d0d0d;
      color: #e0e0e0;
      padding: 32px 24px;
      min-height: 100vh;
    }}
    header {{
      display: flex;
      align-items: baseline;
      gap: 16px;
      margin-bottom: 28px;
      border-bottom: 1px solid #222;
      padding-bottom: 20px;
    }}
    h1 {{ font-size: 1.5rem; color: #4fc3f7; letter-spacing: 2px; }}
    .subtitle {{ color: #666; font-size: 0.85rem; }}
    .tenant-badge {{
      background: #1e1e2e;
      border: 1px solid #4fc3f7;
      border-radius: 4px;
      padding: 2px 10px;
      font-size: 0.78rem;
      color: #4fc3f7;
      font-family: monospace;
    }}
    .stats {{
      background: #111;
      border: 1px solid #222;
      border-radius: 8px;
      padding: 12px 18px;
      margin-bottom: 24px;
      font-size: 0.85rem;
      color: #888;
    }}
    .stats b {{ color: #4fc3f7; }}
    .card {{
      background: #111;
      border: 1px solid #1e1e1e;
      border-left: 3px solid #4fc3f7;
      border-radius: 8px;
      padding: 16px 20px;
      margin-bottom: 14px;
      transition: border-color 0.2s;
    }}
    .card:hover {{ border-left-color: #81c784; }}
    .meta {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
      flex-wrap: wrap;
    }}
    .time {{ color: #555; font-size: 0.78rem; font-family: monospace; }}
    .badge {{
      font-size: 0.72rem;
      padding: 2px 8px;
      border-radius: 12px;
      color: #0d0d0d;
      font-weight: 600;
    }}
    .session {{ color: #444; font-size: 0.75rem; font-family: monospace; }}
    .text {{
      color: #ccc;
      font-size: 0.9rem;
      line-height: 1.6;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .empty {{
      text-align: center;
      padding: 60px;
      color: #444;
    }}
  </style>
</head>
<body>
  <header>
    <h1>🤖 ZUKI</h1>
    <span class="subtitle">Cloud-Gedächtnis</span>
    <span class="tenant-badge">Tenant: {tenant}</span>
  </header>
  <div class="stats">
    <b>{total}</b> Einträge gesamt &nbsp;·&nbsp; zeige neueste <b>{len(entries)}</b>
    &nbsp;·&nbsp; Limit ändern: <code>?limit=100</code>
    &nbsp;·&nbsp; Tenant wechseln: <code>?tenant=client-xyz</code>
  </div>
  {"".join(cards) if cards else '<div class="empty">Noch keine Erinnerungen gespeichert.</div>'}
</body>
</html>"""

    return Response(html, mimetype="text/html")


# ── POST /api/skill/conversations ─────────────────────────────────────────────

@app.route("/api/skill/conversations", methods=["POST"])
def save_skill_conversation():
    """Skill-Konversation speichern. Redis-Key: zuki:skill:{name}:conversations:{tenant}"""
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert"}), 401

    body       = request.get_json(silent=True) or {}
    skill_name = (body.get("skill_name") or "").strip()
    text       = (body.get("text") or "").strip()
    tenant     = (body.get("tenant") or "self").strip()

    if not skill_name:
        return jsonify({"error": "'skill_name' fehlt"}), 400
    if not text:
        return jsonify({"error": "'text' fehlt oder leer"}), 400

    entry = {
        "skill_name": skill_name,
        "text":       text[:8000],
        "source":     body.get("source", "skill"),
        "session_id": body.get("session_id", "unknown"),
        "tenant":     tenant,
        "timestamp":  body.get("timestamp", utc_now()),
        "saved_at":   utc_now(),
        "v":          1,
    }

    try:
        r   = get_redis()
        key = _skill_key(skill_name, tenant)
        r.lpush(key, json.dumps(entry, ensure_ascii=False))
        r.ltrim(key, 0, MAX_SKILL_CONV_ENTRIES - 1)
        total = r.llen(key)
    except Exception as e:
        return jsonify({"error": f"Redis-Fehler: {e}"}), 500

    return jsonify({"status": "gespeichert", "skill": skill_name, "tenant": tenant, "total": total})


# ── GET /api/skill/conversations ───────────────────────────────────────────────

@app.route("/api/skill/conversations", methods=["GET"])
def get_skill_conversations():
    """Skill-Konversationen abrufen. Parameter: skill=<name>&tenant=<tenant>&limit=<n>"""
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert"}), 401

    skill_name = (request.args.get("skill") or "").strip()
    tenant     = (request.args.get("tenant") or "self").strip()
    limit      = min(int(request.args.get("limit", 20)), 100)

    if not skill_name:
        return jsonify({"error": "'skill' Parameter fehlt"}), 400

    try:
        r       = get_redis()
        key     = _skill_key(skill_name, tenant)
        raw     = r.lrange(key, 0, limit - 1)
        total   = r.llen(key)
    except Exception as e:
        return jsonify({"error": f"Redis-Fehler: {e}"}), 500

    conversations = []
    for item in raw:
        try:
            conversations.append(json.loads(item))
        except Exception:
            conversations.append({"raw": item})

    return jsonify({
        "skill":         skill_name,
        "tenant":        tenant,
        "conversations": conversations,
        "total":         total,
        "returned":      len(conversations),
    })


# ── POST /api/memory/cleanup ─────────────────────────────────────────────────

@app.route("/api/memory/cleanup", methods=["POST"])
def cleanup_memories():
    """
    Löscht Cloud-Memories für einen Tenant.
    Geschützt: source="bio", "system": True in Einträgen.
    Body: {"tenant": str, "scope": "all" | "source:<name>"}
    Response: {deleted, protected, total, tenant}
    """
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert"}), 401

    body   = request.get_json(silent=True) or {}
    tenant = (body.get("tenant") or "self").strip()
    scope  = (body.get("scope")  or "all").strip()

    try:
        r       = get_redis()
        mem_key = _mem_key(tenant)
        raw     = r.lrange(mem_key, 0, -1)
    except Exception as e:
        return jsonify({"error": f"Redis-Fehler: {e}"}), 500

    kept      = []
    deleted   = 0
    protected = 0

    for item in raw:
        try:
            entry = json.loads(item)
        except Exception:
            kept.append(item)
            continue

        is_bio    = entry.get("source") == "bio"
        is_system = bool(entry.get("system"))

        if is_bio or is_system:
            kept.append(item)
            protected += 1
            continue

        if scope != "all":
            # scope="source:<name>" — nur Einträge mit diesem source löschen
            target_source = scope.removeprefix("source:").strip()
            if entry.get("source") != target_source:
                kept.append(item)
                continue

        deleted += 1

    try:
        r.delete(mem_key)
        if kept:
            for item in reversed(kept):
                r.lpush(mem_key, item)
            r.ltrim(mem_key, 0, MAX_ENTRIES - 1)

        total = r.llen(mem_key)

        audit_entry = {
            "action":    "cleanup",
            "timestamp": utc_now(),
            "scope":     scope,
            "deleted":   deleted,
            "protected": protected,
        }
        r.lpush(_audit_key(tenant), json.dumps(audit_entry, ensure_ascii=False))
        r.ltrim(_audit_key(tenant), 0, MAX_AUDIT_ENTRIES - 1)

    except Exception as e:
        return jsonify({"error": f"Redis-Schreib-Fehler: {e}"}), 500

    return jsonify({
        "status":    "ok",
        "deleted":   deleted,
        "protected": protected,
        "total":     total,
        "tenant":    tenant,
        "scope":     scope,
    })


# ── GET /api/memory/health ─────────────────────────────────────────────────────

@app.route("/api/memory/health", methods=["GET"])
def health():
    try:
        r     = get_redis()
        total = r.llen(_mem_key("self"))
        return jsonify({"status": "ok", "service": "zuki-memory", "total_entries": total})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503
