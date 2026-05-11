import os
import sys
import threading
import time
import pyttsx3

from core.logger import get_logger

log = get_logger("tts")

_WINDOWS = sys.platform == "win32"

# ANSI für den Mute-Hinweis im Terminal
_DIM  = "\033[2m"
_GRAY = "\033[90m"
_R    = "\033[0m"


class TTSEngine:
    """
    Local Text-to-Speech via pyttsx3 (Windows SAPI5).

    Mute-Funktion:
      Während der Sprachausgabe kann mit der LEERTASTE die Audio-Ausgabe
      sofort abgebrochen werden. Der Text im Terminal bleibt unberührt,
      da er bereits vor dem TTS-Call gedruckt wird.

    Voice preference controlled via TTS_VOICE env var (e.g. 'Katja').
    Falls back to system default if preferred voice not found.
    """

    def __init__(self):
        rate    = int(os.environ.get("TTS_RATE",   165))
        volume  = float(os.environ.get("TTS_VOLUME", 1.0))
        self._preferred = os.environ.get("TTS_VOICE", "Katja").lower()

        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate",   rate)
            self._engine.setProperty("volume", volume)
            self._voice_name = self._select_voice()
            log.info(f"TTS initialisiert | Stimme: {self._voice_name} | rate={rate}")
        except Exception as e:
            log.error(f"TTS-Engine konnte nicht initialisiert werden: {e}")
            raise

        self._speaking   = False          # True während runAndWait läuft
        self._stop_event = threading.Event()

    # ── Öffentliche API ────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """
        Synthesize and play text. Blocks until audio finishes or is muted.

        Text ist zu diesem Zeitpunkt bereits im Terminal (via ui.speak_zuki).
        LEERTASTE → engine.stop() → Audio bricht sofort ab, Text bleibt.
        """
        self._stop_event.clear()
        self._speaking = True

        # Watcher-Thread startet parallel — hört auf Leertaste
        if _WINDOWS:
            watcher = threading.Thread(
                target = self._key_watcher,
                daemon = True,
                name   = "tts-mute-watcher",
            )
            watcher.start()
        else:
            watcher = None

        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            log.warning(f"TTS-Sprachausgabe fehlgeschlagen: {e}")
        finally:
            self._speaking = False
            self._stop_event.set()     # Watcher-Thread beenden
            if watcher is not None:
                watcher.join(timeout=0.3)

    def shutdown(self) -> None:
        """Stop engine and release audio resources."""
        try:
            self._stop_event.set()
            self._engine.stop()
            log.info("TTSEngine heruntergefahren.")
        except Exception as e:
            log.warning(f"TTS-Shutdown-Fehler: {e}")

    def list_voices(self) -> list[str]:
        return [v.name for v in self._engine.getProperty("voices")]

    # ── Interner Key-Watcher ───────────────────────────────────────────────────

    def _key_watcher(self) -> None:
        """
        Läuft als Daemon-Thread während speak() blockiert.
        Erkennt LEERTASTE per msvcrt (non-blocking) und ruft engine.stop() auf.
        Beendet sich automatisch wenn stop_event gesetzt wird.
        """
        import msvcrt  # noqa: PLC0415 — Windows only

        while not self._stop_event.is_set():
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b" ":                        # Leertaste
                    log.debug("Mute: Leertaste — stoppe TTS-Audio")
                    print(
                        f"\n  {_GRAY}[🔇]{_R}  {_DIM}Audio stummgeschaltet.{_R}"
                    )
                    try:
                        self._engine.stop()            # unterbricht runAndWait()
                    except Exception:
                        pass
                    return
            time.sleep(0.04)   # ~25 Checks/Sekunde — reaktionsschnell ohne CPU-Last

    # ── Interne Hilfsfunktionen ────────────────────────────────────────────────

    def _select_voice(self) -> str:
        voices = self._engine.getProperty("voices")

        # 1. Pass — bevorzugte Stimme aus .env
        for voice in voices:
            if self._preferred in voice.name.lower():
                self._engine.setProperty("voice", voice.id)
                return voice.name

        # 2. Pass — beliebige deutsche Stimme
        for voice in voices:
            if "german" in voice.name.lower() or "deutsch" in voice.name.lower():
                self._engine.setProperty("voice", voice.id)
                log.warning(
                    f"Bevorzugte Stimme '{self._preferred}' nicht gefunden. "
                    f"Nutze: {voice.name}"
                )
                return voice.name

        # Fallback
        default = voices[0].name if voices else "System-Standard"
        log.warning(f"Keine deutsche Stimme gefunden. Fallback: {default}")
        return f"{default} (Fallback)"
