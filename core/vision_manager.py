"""
vision_manager.py — Screen-Capture Modul für Zuki
────────────────────────────────────────────────────
Bibliothek : mss  (pip install mss Pillow)
Output     : temp/vision/current_frame.jpg

Ablauf:
  1. capture_active_screen() → nimmt Monitor 1 auf
  2. Speichert als JPEG in VISION_DIR
  3. Gibt Dateipfad zurück (für LLM-Call oder SIM-Output)

LIVE UPGRADE — Multimodaler LLM-Call:
  Nach dem Capture wird das Bild als Base64 in den API-Call eingebettet:

  ┌─────────────────────────────────────────────────────────────┐
  │  # Anthropic (Claude Vision)                                │
  │  import base64                                              │
  │  with open(frame_path, "rb") as f:                         │
  │      img_b64 = base64.b64encode(f.read()).decode()         │
  │  messages = [{                                              │
  │      "role": "user",                                        │
  │      "content": [                                           │
  │          {"type": "image", "source": {                      │
  │              "type": "base64",                              │
  │              "media_type": "image/jpeg",                    │
  │              "data": img_b64,                               │
  │          }},                                                │
  │          {"type": "text", "text": "Was siehst du?"},        │
  │      ]                                                      │
  │  }]                                                         │
  │  response = client.messages.create(...)                     │
  └─────────────────────────────────────────────────────────────┘

  # OpenAI (GPT-4o Vision)
  messages = [{"role": "user", "content": [
      {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
      {"type": "text", "text": "Was siehst du?"},
  ]}]
"""

import os
import glob as _glob
from datetime import datetime

from core.logger import get_logger

log = get_logger("vision")

ROOT       = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
VISION_DIR = os.path.join(ROOT, "temp", "vision")
FRAME_PATH = os.path.join(VISION_DIR, "current_frame.jpg")

JPEG_QUALITY = 85   # 0-95 — Kompromiss aus Dateigröße & Bildqualität


# ── Public API ─────────────────────────────────────────────────────────────────

def init() -> None:
    """
    Beim Start aufrufen:
    - Erstellt temp/vision/ falls nicht vorhanden
    - Löscht alle alten Screenshots (kein Müll-Akkumulation)
    """
    os.makedirs(VISION_DIR, exist_ok=True)
    _cleanup_old_frames()
    log.info(f"Vision-Dir initialisiert: {VISION_DIR}")


def capture_active_screen() -> str:
    """
    Nimmt Monitor 1 (primärer Bildschirm) auf.
    Speichert als JPEG → FRAME_PATH.
    Gibt den absoluten Pfad zurück.

    Raises:
        RuntimeError wenn mss oder Pillow nicht installiert ist.
        OSError      bei Schreibfehlern.
    """
    try:
        import mss
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(
            f"Vision-Abhängigkeit fehlt: {e}\n"
            f"Bitte installieren: pip install mss Pillow"
        ) from e

    os.makedirs(VISION_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with mss.mss() as sct:
        # monitor[0] = gesamte virtuelle Oberfläche, monitor[1] = primärer Bildschirm
        monitor = sct.monitors[1]
        raw     = sct.grab(monitor)

        # mss gibt BGR-Daten zurück → PIL konvertiert nach RGB
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        img.save(FRAME_PATH, format="JPEG", quality=JPEG_QUALITY, optimize=True)

    size_kb = os.path.getsize(FRAME_PATH) // 1024
    log.info(f"Screenshot erstellt: {FRAME_PATH}  ({size_kb} KB)  [{timestamp}]")
    return FRAME_PATH


def get_frame_path() -> str:
    """Gibt den Pfad zum aktuellen Frame zurück (existiert möglicherweise nicht)."""
    return FRAME_PATH


def frame_exists() -> bool:
    return os.path.exists(FRAME_PATH)


# ── Internal ───────────────────────────────────────────────────────────────────

def _cleanup_old_frames() -> None:
    """Löscht alle .jpg und .png Dateien in VISION_DIR."""
    patterns = [
        os.path.join(VISION_DIR, "*.jpg"),
        os.path.join(VISION_DIR, "*.png"),
    ]
    removed = 0
    for pattern in patterns:
        for fpath in _glob.glob(pattern):
            try:
                os.remove(fpath)
                removed += 1
                log.debug(f"Altes Frame gelöscht: {fpath}")
            except OSError as e:
                log.warning(f"Frame konnte nicht gelöscht werden: {fpath} — {e}")
    if removed:
        log.info(f"Vision-Cleanup: {removed} altes/alte Frame(s) entfernt")
