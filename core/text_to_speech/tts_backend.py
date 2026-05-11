"""
tts_backend.py — Abstrakte Basis für TTS-Backends
──────────────────────────────────────────────────
Neue Backends erben von TTSBackend und implementieren alle
abstractmethods. Die Factory in tts_engine.py wählt per
sys.platform das richtige Backend.

Aktuell verfügbare Backends:
  WindowsTTS  (pyttsx3 / SAPI5)   — core/text_to_speech/windows_tts.py
  LinuxTTS    (Piper — Stub)       — core/text_to_speech/linux_tts.py

Status-API:
  backend.get_status() -> dict
"""

from abc import ABC, abstractmethod


class TTSBackend(ABC):
    """Abstrakte Basis für plattform-spezifische TTS-Implementierungen."""

    # ── Pflicht-Implementierungen ─────────────────────────────────────────────

    @abstractmethod
    def speak(self, text: str) -> None:
        """Synthesize text and play audio. Blocks until done or muted."""

    @abstractmethod
    def shutdown(self) -> None:
        """Release audio resources and stop running threads."""

    @abstractmethod
    def list_voices(self) -> list[str]:
        """Return list of available voice names."""

    # ── Status-API ────────────────────────────────────────────────────────────

    @abstractmethod
    def get_status(self) -> dict:
        """
        Return current backend state as serializable dict.
        Mindestfelder: backend, voice, ready (bool), platform.
        """
