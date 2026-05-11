"""
linux_tts.py — TTS-Backend für Linux (Piper — Stub)
────────────────────────────────────────────────────
Stub-Implementierung für LinuxTTS via Piper TTS.
Piper ist ein lokales, hochqualitatives TTS für Linux/ARM.
https://github.com/rhasspy/piper

LIVE UPGRADE — Implementierungsschritte:
  1. Piper installieren:
       pip install piper-tts
     oder Binary von GitHub Releases: https://github.com/rhasspy/piper/releases

  2. Stimm-Modell herunterladen (z.B. Deutsch / Thorsten):
       wget https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx
       wget .../de_DE-thorsten-medium.onnx.json

  3. PIPER_MODEL_PATH in .env setzen (Pfad zu .onnx Datei)
     Optional: PIPER_BINARY_PATH wenn nicht im PATH

  4. Implementierung hier:
       import subprocess
       result = subprocess.run(
           [piper_bin, "--model", model_path, "--output-raw"],
           input=text.encode(),
           capture_output=True,
       )
       # raw PCM via sounddevice abspielen oder aplay pipen

  5. Spacebar-Mute: termios + select statt msvcrt (Linux-äquivalent)

Log-Marker: [TTS-LINUX]

Status:
  ready = False  (Stub — kein Piper installiert)
"""

import sys

from core.logger import get_logger
from core.text_to_speech.tts_backend import TTSBackend

log = get_logger("tts.linux")


class LinuxTTS(TTSBackend):
    """
    Piper-basiertes TTS-Backend für Linux.
    Aktuell Stub — alle Methoden werfen NotImplementedError.
    """

    def __init__(self) -> None:
        log.info("[TTS-LINUX] LinuxTTS-Stub initialisiert (kein Piper aktiv)")

    # ── TTSBackend Implementierung ────────────────────────────────────────────

    def speak(self, text: str) -> None:
        log.info(f"[TTS-LINUX-STUB] speak() aufgerufen — Piper nicht implementiert")
        raise NotImplementedError(
            "[TTS-LINUX-STUB] Piper TTS ist noch nicht implementiert.\n"
            "  Siehe LIVE UPGRADE Kommentar in core/text_to_speech/linux_tts.py"
        )

    def shutdown(self) -> None:
        log.info("[TTS-LINUX-STUB] shutdown() — nichts zu tun (Stub)")

    def list_voices(self) -> list[str]:
        log.info("[TTS-LINUX-STUB] list_voices() aufgerufen — Stub gibt [] zurück")
        return []

    def get_status(self) -> dict:
        return {
            "backend":  "LinuxTTS",
            "platform": "linux",
            "voice":    "Piper (nicht konfiguriert)",
            "ready":    False,
            "speaking": False,
        }
