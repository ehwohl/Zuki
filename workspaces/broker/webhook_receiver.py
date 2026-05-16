"""
webhook_receiver.py — n8n HTTP Webhook Entry Point for Zuki
─────────────────────────────────────────────────────────────
Accepts POST requests from n8n and forwards them to the Zuki skill router.

Endpoint:
  POST http://127.0.0.1:<N8N_WEBHOOK_PORT>/webhook/n8n

Enabled by:
  N8N_WEBHOOK_ENABLED=true   in .env  (default: false — stub only)
  N8N_WEBHOOK_PORT=8766       in .env  (default: 8766)

Architecture constraint:
  - No business logic here. This file routes only.
  - Handler callable is injected by main.py at startup.
  - Nothing from n8n ever reaches core/ directly (CLAUDE.md §Hard Rules rule 8).

────────────────────────────────────────────────────────────────────────────────
Expected Payload Schemas (n8n → Zuki contract)
────────────────────────────────────────────────────────────────────────────────

  news_item
  ─────────
  {
    "type": "news_item",
    "payload": {
      "source":    str,   // e.g. "Reuters", "Bloomberg"
      "headline":  str,   // article title or summary
      "timestamp": str    // ISO-8601, e.g. "2026-05-16T14:30:00Z"
    }
  }
  → Forwarded to NewsFeed panel via ui_bridge.emit_news_item()

  price_alert
  ───────────
  {
    "type": "price_alert",
    "payload": {
      "symbol":    str,   // e.g. "AAPL", "BTC-USD"
      "price":     float, // current price
      "delta":     float  // percentage change, e.g. -0.023 = -2.3%
    }
  }
  → Forwarded to Watchlist panel via ui_bridge.emit_broker_tick()

  All other "type" values are rejected with HTTP 400.

────────────────────────────────────────────────────────────────────────────────
Log marker: [WEBHOOK]
"""

import logging
import threading
from typing import Callable

log = logging.getLogger("broker.webhook_receiver")

_ACCEPTED_TYPES: frozenset[str] = frozenset({"news_item", "price_alert"})

_server_thread: "threading.Thread | None" = None


def start(port: int, handler: Callable[[str, dict], None]) -> None:
    """
    Start the n8n webhook receiver in a daemon thread.

    Args:
        port:    HTTP port to listen on (from N8N_WEBHOOK_PORT, default 8766).
        handler: called with (msg_type, payload) for each valid webhook.
                 Injected by main.py — no business logic here.
    """
    global _server_thread

    try:
        from flask import Flask, request, jsonify
    except ImportError:
        log.error("[WEBHOOK] Flask not installed — run: pip install flask")
        return

    import logging as _logging
    # Suppress Werkzeug request logs — Zuki uses its own logger
    _logging.getLogger("werkzeug").setLevel(_logging.ERROR)

    app = Flask("zuki_n8n_webhook")

    @app.post("/webhook/n8n")
    def receive():
        data = request.get_json(silent=True)

        if not data:
            log.warning("[WEBHOOK] Empty or non-JSON body — rejected")
            return jsonify({"error": "body must be JSON"}), 400

        msg_type = data.get("type", "")
        payload  = data.get("payload", {})

        if msg_type not in _ACCEPTED_TYPES:
            log.warning("[WEBHOOK] Unknown type=%r — rejected", msg_type)
            return jsonify({"error": f"unknown type '{msg_type}'"}), 400

        if not isinstance(payload, dict):
            log.warning("[WEBHOOK] payload must be an object — rejected")
            return jsonify({"error": "payload must be an object"}), 400

        log.info("[WEBHOOK] Received type=%s", msg_type)

        # Dispatch to main.py handler in a thread to avoid blocking Flask
        threading.Thread(
            target=handler,
            args=(msg_type, payload),
            daemon=True,
            name=f"webhook-dispatch-{msg_type}",
        ).start()

        return jsonify({"status": "accepted"}), 202

    _server_thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1",
            port=port,
            debug=False,
            use_reloader=False,
        ),
        daemon=True,
        name="webhook-receiver",
    )
    _server_thread.start()
    log.info(
        "[WEBHOOK] n8n receiver active — http://127.0.0.1:%d/webhook/n8n", port
    )


def is_running() -> bool:
    """Returns True if the receiver thread is alive."""
    return _server_thread is not None and _server_thread.is_alive()
