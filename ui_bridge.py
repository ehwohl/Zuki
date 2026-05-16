"""
WebSocket bridge between the React frontend (Zuki-OS) and the Python backend.

Listens on ws://localhost:8765 (configurable via BRIDGE_PORT env var).
Runs in its own asyncio event loop inside a daemon thread — import and call start().

Message contracts follow the WebSocket spec in REFERENCES.md §WebSocket Message Contract.
"""

import asyncio
import json
import logging
import os
import threading
from typing import Any

import websockets
from websockets.server import WebSocketServerProtocol

logger = logging.getLogger("ui_bridge")

PORT = int(os.getenv("BRIDGE_PORT", "8765"))

# Shared set of connected frontend clients
_clients: set[WebSocketServerProtocol] = set()
_clients_lock = asyncio.Lock()

# asyncio loop reference — set once the bridge thread starts
_loop: asyncio.AbstractEventLoop | None = None

# Callback called when a command arrives from the frontend
_command_handler: Any = None

# Callback called when a pitch_event arrives from the frontend (MusicSkill)
_pitch_event_handler: Any = None


def set_pitch_event_handler(handler) -> None:
    """Register the handler that receives pitch_event WebSocket messages.

    The handler is called with the full message dict:
      { "type": "pitch_event", "note": "A4", "cents": -12, ... }
    It runs in a thread-pool executor so it must be thread-safe.
    """
    global _pitch_event_handler
    _pitch_event_handler = handler


# ── Public API (called from Python main thread / skill threads) ──────────────

def start(command_handler=None) -> None:
    """Start the bridge in a daemon thread. Call once at startup."""
    global _command_handler
    _command_handler = command_handler

    thread = threading.Thread(target=_run_loop, daemon=True, name="ui-bridge")
    thread.start()
    logger.info("[UI-BRIDGE] WebSocket server starting on ws://localhost:%d", PORT)


def emit(msg_type: str, **payload) -> None:
    """Thread-safe broadcast to all connected frontend clients."""
    if _loop is None or not _clients:
        return
    msg = json.dumps({"type": msg_type, **payload})
    asyncio.run_coroutine_threadsafe(_broadcast(msg), _loop)


def emit_response(text: str, html: str = "", workspace: str = "") -> None:
    emit("response", text=text, html=html, workspace=workspace)


def emit_tts_amplitude(value: float) -> None:
    """Call at ~30Hz during TTS playback. value: 0.0–1.0."""
    emit("tts_amplitude", value=round(max(0.0, min(1.0, value)), 3))


def emit_router_decision(skill: str, reason: str, sources: list[str]) -> None:
    emit("router_decision", skill=skill, reason=reason, sources=sources)


def emit_metrics(cpu: list[float], ram: float, disk_io: float) -> None:
    emit("metrics", cpu=cpu, ram=ram, disk_io=disk_io)


def emit_news_item(source: str, headline: str, timestamp: str) -> None:
    emit("news_item", source=source, headline=headline, timestamp=timestamp)


def emit_broker_tick(symbol: str, price: float, delta: float, sparkline: list[float]) -> None:
    emit("broker_tick", symbol=symbol, price=price, delta=delta, sparkline=sparkline)


def emit_workspace_change(workspace: str) -> None:
    emit("workspace_change", workspace=workspace)


def emit_broker_map_nodes(nodes: list[dict]) -> None:
    emit("broker_map_nodes", nodes=nodes)


def emit_business_prompt(text: str) -> None:
    emit("business_interview_prompt", text=text)


def emit_business_score(score: int, report_path: str = "") -> None:
    emit("business_score", score=score, report_path=report_path)


def emit_coding_output(text: str, language: str = "") -> None:
    emit("coding_output", text=text, language=language)


def emit_os_status(tts: dict, stt: dict, platform: str) -> None:
    emit("os_status", tts=tts, stt=stt, platform=platform)


def emit_business_city_data(buildings: list[dict]) -> None:
    emit("business_city_data", buildings=buildings)


def emit_coding_dep_graph(nodes: list[dict], edges: list[dict]) -> None:
    emit("coding_dep_graph", nodes=nodes, edges=edges)


def emit_office_status(
    total: int,
    categories: list[dict],
    auth_ready: bool,
    credentials_exist: bool,
    recent_reports: list[dict],
) -> None:
    emit(
        "office_status",
        total=total,
        categories=categories,
        auth_ready=auth_ready,
        credentials_exist=credentials_exist,
        recent_reports=recent_reports,
    )


def emit_office_search_results(query: str, results: list[dict]) -> None:
    emit("office_search_results", query=query, results=results)


def emit_business_reports(reports: list[dict]) -> None:
    emit("business_reports", reports=reports)


def emit_music_session(
    note_count: int,
    avg_cents_deviation: float,
    time_active_seconds: int,
    last_note: str,
    session_started: str,
) -> None:
    """Broadcast music session statistics to all connected frontend clients."""
    emit(
        "music_session_stats",
        note_count=note_count,
        avg_cents_deviation=avg_cents_deviation,
        time_active_seconds=time_active_seconds,
        last_note=last_note,
        session_started=session_started,
    )


def emit_neural_map_task(task_id: str, nodes: list[str], ttl: float = 4.0) -> None:
    """Highlight active task flow in the Neural Map.

    nodes: list of node IDs involved — any link between two of these turns hot.
    ttl:   seconds before the highlight auto-expires (safety net if clear is never called).
    """
    emit("neural_map_task", task_id=task_id, nodes=nodes, ttl=ttl)


def emit_neural_map_clear(task_id: str = "") -> None:
    """Remove a task highlight. Pass empty string to clear all active tasks."""
    emit("neural_map_clear", task_id=task_id)


# ── Internal ─────────────────────────────────────────────────────────────────

def _run_loop() -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(_serve())


async def _serve() -> None:
    async with websockets.serve(_handle_client, "localhost", PORT):
        logger.info("[UI-BRIDGE] Ready")
        await asyncio.Future()  # run forever


async def _handle_client(ws: WebSocketServerProtocol) -> None:
    async with _clients_lock:
        _clients.add(ws)
    logger.debug("[UI-BRIDGE] Client connected — total: %d", len(_clients))

    try:
        async for raw in ws:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("[UI-BRIDGE] Malformed message: %r", raw)
                continue
            await _handle_message(ws, msg)
    except websockets.exceptions.ConnectionClosedOK:
        pass
    except Exception as exc:
        logger.error("[UI-BRIDGE] Client error: %s", exc)
    finally:
        async with _clients_lock:
            _clients.discard(ws)
        logger.debug("[UI-BRIDGE] Client disconnected — total: %d", len(_clients))


async def _handle_message(ws: WebSocketServerProtocol, msg: dict) -> None:
    msg_type = msg.get("type", "")

    if msg_type == "command":
        text = msg.get("text", "").strip()
        workspace = msg.get("workspace", "")
        tenant = msg.get("tenant", "self")
        if text and _command_handler:
            # Dispatch to Python command handler in thread pool to avoid blocking asyncio
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _command_handler, text, workspace, tenant)

    elif msg_type == "navigate":
        workspace = msg.get("workspace", "")
        logger.info("[UI-BRIDGE] Navigate → %s", workspace)
        # Backend can react to workspace change (e.g. route window profiles)
        if _command_handler:
            asyncio.get_event_loop().run_in_executor(
                None, lambda: _on_navigate(workspace)
            )

    elif msg_type == "pitch_event":
        if _pitch_event_handler:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _pitch_event_handler, msg)

    elif msg_type == "presentation_mode":
        active = msg.get("active", False)
        logger.info("[UI-BRIDGE] Presentation mode: %s", active)


def _on_navigate(workspace: str) -> None:
    """Called when frontend switches workspace. Extend to trigger window_profiles.json routing."""
    logger.info("[UI-BRIDGE] Window profile routing for workspace: %s", workspace)


async def _broadcast(message: str) -> None:
    if not _clients:
        return
    async with _clients_lock:
        targets = set(_clients)
    results = await asyncio.gather(
        *[ws.send(message) for ws in targets],
        return_exceptions=True,
    )
    for r in results:
        if isinstance(r, Exception):
            logger.debug("[UI-BRIDGE] Send error (client likely disconnected): %s", r)


# ── Dev entrypoint ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    def echo_handler(text: str, workspace: str, _tenant: str) -> None:
        """Echo back the command as a mock response."""
        emit_response(f"[ECHO] {text}", workspace=workspace)

    start(command_handler=echo_handler)

    print(f"Zuki-OS bridge running on ws://localhost:{PORT}")
    print("Open http://localhost:5173 and press Ctrl+Space")
    threading.Event().wait()
