"""
windows_tts.py — TTS-Backend für Windows (pyttsx3 / SAPI5)
────────────────────────────────────────────────────────────
Implementiert TTSBackend mit:
  - Stimm-Auswahl per TTS_VOICE env var (z.B. "Katja")
  - Spacebar-Mute via msvcrt-Watcher-Thread
  - Rate + Volume per TTS_RATE / TTS_VOLUME env var

Log-Marker: [TTS-WIN]
"""

import os
import threading
import time

from core.logger import get_logger
from core.text_to_speech.tts_backend import TTSBackend

log = get_logger("tts.windows")

_DIM  = "\033[2m"
_GRAY = "\033[90m"
_R    = "\033[0m"


class WindowsTTS(TTSBackend):
    """
    pyttsx3-basiertes TTS-Backend für Windows SAPI5.
    Einziges Backend das aktuell voll funktional ist.
    """

    def __init__(self) -> None:
        import pyttsx3  # noqa: PLC0415 — Windows only

        rate   = int(os.environ.get("TTS_RATE", 165))
        volume = float(os.environ.get("TTS_VOLUME", 1.0))
        self._preferred = os.environ.get("TTS_VOICE", "Katja").lower()

        self._engine = pyttsx3.init()
        self._engine.setProperty("rate",   rate)
        self._engine.setProperty("volume", volume)
        self._voice_name = self._select_voice()

        self._speaking   = False
        self._stop_event = threading.Event()

        log.info(f"[TTS-WIN] Initialisiert | Stimme: {self._voice_name} | rate={rate}")

    # ── TTSBackend Implementierung ────────────────────────────────────────────

    def speak(self, text: str) -> None:
        self._stop_event.clear()
        self._speaking = True

        watcher = threading.Thread(
            target=self._key_watcher,
            daemon=True,
            name="tts-mute-watcher",
        )
        watcher.start()

        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            log.warning(f"[TTS-WIN] Sprachausgabe fehlgeschlagen: {e}")
        finally:
            self._speaking = False
            self._stop_event.set()
            watcher.join(timeout=0.3)

    def shutdown(self) -> None:
        try:
            self._stop_event.set()
            self._engine.stop()
            log.info("[TTS-WIN] Heruntergefahren.")
        except Exception as e:
            log.warning(f"[TTS-WIN] Shutdown-Fehler: {e}")

    def list_voices(self) -> list[str]:
        return [v.name for v in self._engine.getProperty("voices")]

    def get_status(self) -> dict:
        return {
            "backend":   "WindowsTTS",
            "platform":  "win32",
            "voice":     self._voice_name,
            "ready":     True,
            "speaking":  self._speaking,
        }

    # ── Interner Key-Watcher ──────────────────────────────────────────────────

    def _key_watcher(self) -> None:
        import msvcrt  # noqa: PLC0415 — Windows only

        while not self._stop_event.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b" ":
                    log.debug("[TTS-WIN] Mute: Leertaste erkannt")
                    print(f"\n  {_GRAY}[🔇]{_R}  {_DIM}Audio stummgeschaltet.{_R}")
                    try:
                        self._engine.stop()
                    except Exception:
                        pass
                    return
            time.sleep(0.04)

    # ── Interne Hilfsfunktionen ───────────────────────────────────────────────

    def _select_voice(self) -> str:
        voices = self._engine.getProperty("voices")

        for voice in voices:
            if self._preferred in voice.name.lower():
                self._engine.setProperty("voice", voice.id)
                return voice.name

        for voice in voices:
            if "german" in voice.name.lower() or "deutsch" in voice.name.lower():
                self._engine.setProperty("voice", voice.id)
                # info statt warning — wenn eine deutsche Stimme verfügbar ist,
                # ist das OK, kein Drama. Nur informativ falls TTS_VOICE updaten.
                log.info(
                    f"[TTS-WIN] Stimme '{self._preferred}' nicht installiert — "
                    f"nutze stattdessen: {voice.name}"
                )
                return voice.name

        default = voices[0].name if voices else "System-Standard"
        log.warning(f"[TTS-WIN] Keine deutsche Stimme installiert. Fallback: {default}")
        return f"{default} (Fallback)"
