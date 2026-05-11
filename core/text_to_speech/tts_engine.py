"""
tts_engine.py — TTS-Factory (plattform-agnostisch)
────────────────────────────────────────────────────
Wählt automatisch das richtige TTS-Backend per sys.platform:
  win32  → WindowsTTS  (pyttsx3 / SAPI5)
  linux  → LinuxTTS    (Piper — Stub, bereit für Live-Upgrade)
  other  → NotImplementedError

TTSEngine ist die öffentliche API — intern delegiert sie an ein TTSBackend.
Die TTSBackend-Klassen liegen in:
  core/text_to_speech/windows_tts.py
  core/text_to_speech/linux_tts.py

Status-API:
  engine.get_status() -> dict    (delegiert ans Backend)
  engine.list_voices() -> list   (delegiert ans Backend)

Log-Marker: [TTS-FACTORY]
"""

import sys

from core.logger import get_logger
from core.text_to_speech.tts_backend import TTSBackend

log = get_logger("tts")


def _build_backend() -> TTSBackend:
    platform = sys.platform
    if platform == "win32":
        from core.text_to_speech.windows_tts import WindowsTTS
        log.info("[TTS-FACTORY] Platform: win32 → WindowsTTS (pyttsx3)")
        return WindowsTTS()
    elif platform.startswith("linux"):
        from core.text_to_speech.linux_tts import LinuxTTS
        log.info("[TTS-FACTORY] Platform: linux → LinuxTTS (Piper-Stub)")
        return LinuxTTS()
    else:
        raise NotImplementedError(
            f"[TTS-FACTORY] Kein TTS-Backend für Platform '{platform}' verfügbar.\n"
            f"  Unterstützt: win32, linux"
        )


class TTSEngine:
    """
    Plattform-agnostische TTS-Schnittstelle.
    Erstellt beim Initialisieren das passende Backend via _build_backend().
    Alle Methoden delegieren ans Backend — kein plattform-spezifischer Code hier.
    """

    def __init__(self) -> None:
        try:
            self._backend: TTSBackend = _build_backend()
        except NotImplementedError:
            raise
        except Exception as e:
            log.error(f"[TTS-FACTORY] Backend-Initialisierung fehlgeschlagen: {e}")
            raise

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """Synthesize and play text. Blocks until audio finishes or is muted."""
        self._backend.speak(text)

    def shutdown(self) -> None:
        """Stop engine and release audio resources."""
        self._backend.shutdown()

    def list_voices(self) -> list[str]:
        return self._backend.list_voices()

    def get_status(self) -> dict:
        return self._backend.get_status()
