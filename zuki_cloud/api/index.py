"""
Zuki Cloud-Gedächtnis — Vercel Serverless API
───────────────────────────────────────────────
POST /api/memory             → Eintrag speichern
GET  /api/memory             → Letzte Einträge abrufen (JSON)
GET  /api/memory/view        → Erinnerungen im Browser anzeigen (HTML)
GET  /api/memory/health      → Verbindungstest

Browser-URL:
  https://zuki-cloud.vercel.app/api/memory/view?token=DEIN_TOKEN&limit=50

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

MAX_ENTRIES = 200


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


# ── POST /api/memory ───────────────────────────────────────────────────────────

@app.route("/api/memory", methods=["POST"])
def save_memory():
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert — CLOUD_MEMORY_TOKEN prüfen"}), 401

    body = request.get_json(silent=True) or {}
    text = body.get("text", "").strip()
    if not text:
        return jsonify({"error": "'text' fehlt oder leer"}), 400

    entry = {
        "text":       text[:8000],
        "source":     body.get("source",     "manual"),
        "session_id": body.get("session_id", "unknown"),
        "timestamp":  body.get("timestamp",  utc_now()),
        "saved_at":   utc_now(),
        "v":          body.get("v", 1),
    }

    try:
        r = get_redis()
        r.lpush("zuki:memories", json.dumps(entry, ensure_ascii=False))
        r.ltrim("zuki:memories", 0, MAX_ENTRIES - 1)
        total = r.llen("zuki:memories")
    except Exception as e:
        return jsonify({"error": f"Redis-Fehler: {e}"}), 500

    return jsonify({"status": "gespeichert", "session_id": entry["session_id"], "total": total})


# ── GET /api/memory ────────────────────────────────────────────────────────────

@app.route("/api/memory", methods=["GET"])
def get_memories():
    if not is_authorized(request):
        return jsonify({"error": "Nicht autorisiert"}), 401

    limit         = min(int(request.args.get("limit", 20)), 200)
    source_filter = request.args.get("source", "").strip()

    try:
        r     = get_redis()
        # Mit Source-Filter: alle Einträge scannen, dann Python-seitig filtern
        fetch = MAX_ENTRIES if source_filter else limit
        raw   = r.lrange("zuki:memories", 0, fetch - 1)
        total = r.llen("zuki:memories")
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


# ── GET /api/memory/view — HTML-Ansicht für den Browser ───────────────────────

@app.route("/api/memory/view", methods=["GET"])
def view_memories():
    token = request.args.get("token", "")
    expected = os.environ.get("CLOUD_MEMORY_TOKEN", "")
    if not expected or token != expected:
        return Response(
            "<html><body style='font-family:monospace;background:#0d0d0d;color:#ff4444;"
            "padding:40px'><h2>⛔ Zugriff verweigert</h2>"
            "<p>Token fehlt oder falsch.<br>"
            "URL: <code>/api/memory/view?token=DEIN_TOKEN</code></p></body></html>",
            status=401, mimetype="text/html"
        )

    limit = min(int(request.args.get("limit", 50)), 200)

    try:
        r     = get_redis()
        raw   = r.lrange("zuki:memories", 0, limit - 1)
        total = r.llen("zuki:memories")
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
  <title>Zuki — Cloud-Gedächtnis</title>
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
  </header>
  <div class="stats">
    <b>{total}</b> Einträge gesamt &nbsp;·&nbsp; zeige neueste <b>{len(entries)}</b>
    &nbsp;·&nbsp; Limit ändern: <code>?limit=100</code>
  </div>
  {"".join(cards) if cards else '<div class="empty">Noch keine Erinnerungen gespeichert.</div>'}
</body>
</html>"""

    return Response(html, mimetype="text/html")


# ── GET /api/memory/health ─────────────────────────────────────────────────────

@app.route("/api/memory/health", methods=["GET"])
def health():
    try:
        total = get_redis().llen("zuki:memories")
        return jsonify({"status": "ok", "service": "zuki-memory", "total_entries": total})
    except Exception as e:
        return jsonify({"status": "error", "detail": str(e)}), 503
