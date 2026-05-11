import os
import sys
import warnings
import logging
import tempfile
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as wav_write

from core.logger import get_logger

# Suppress FP16/CPU warnings from Whisper and PyTorch before any import
warnings.filterwarnings("ignore", message=".*FP16.*")
warnings.filterwarnings("ignore", message=".*torchaudio.*")
warnings.filterwarnings("ignore", category=UserWarning, module="whisper")
logging.getLogger("whisper").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)

log = get_logger("whisper")
SAMPLE_RATE = 16000


class WhisperEngine:
    """
    Speech-to-Text engine with automatic fallback.
    - OPENAI_API_KEY set   → OpenAI API (whisper-1, Cloud)
    - OPENAI_API_KEY unset → local Whisper model (WHISPER_MODEL env var)
    Audio capture: sounddevice + scipy (no pyaudio dependency)
    """

    def __init__(self, language: str = "de"):
        self.language     = language
        self._record_sec  = int(os.environ.get("RECORD_SECONDS", 5))
        self._model_name  = os.environ.get("WHISPER_MODEL", "tiny")
        self._tmp_files: list[str] = []

        api_key = os.environ.get("OPENAI_API_KEY", "")
        self._use_api = bool(api_key and not api_key.startswith("sk-your"))

        if self._use_api:
            log.info("STT mode: Cloud API (whisper-1)")
            self.mode_label = "Cloud API  (whisper-1)"
            try:
                from openai import OpenAI
                self._client = OpenAI(api_key=api_key)
            except Exception as e:
                log.error(f"OpenAI-Client konnte nicht initialisiert werden: {e}")
                raise
        else:
            log.info(f"STT mode: local | model={self._model_name}")
            self.mode_label = f"Lokal  (whisper/{self._model_name})"
            try:
                import whisper
                # Redirect stderr during load to suppress tqdm/torch noise
                _stderr = sys.stderr
                sys.stderr = open(os.devnull, "w")
                try:
                    self._model = whisper.load_model(self._model_name)
                finally:
                    sys.stderr.close()
                    sys.stderr = _stderr
            except Exception as e:
                log.error(f"Whisper-Modell '{self._model_name}' konnte nicht geladen werden: {e}")
                raise

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def transcribe_file(self, audio_path: str) -> str:
        """Transcribe an audio file (MP3/WAV). Returns plain text."""
        if not os.path.exists(audio_path):
            log.error(f"Audio-Datei nicht gefunden: {audio_path}")
            raise FileNotFoundError(f"Datei nicht gefunden: {audio_path}")
        if self._use_api:
            return self._transcribe_api(audio_path)
        return self._transcribe_local(audio_path)

    def transcribe_microphone(self, duration_sec: int | None = None) -> str:
        """Record from microphone via sounddevice and transcribe."""
        secs = duration_sec or self._record_sec
        log.info(f"Aufnahme startet ({secs}s)")
        try:
            audio = sd.rec(
                frames=int(SAMPLE_RATE * secs),
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
            )
            sd.wait()
        except Exception as e:
            log.error(f"Mikrofon-Aufnahme fehlgeschlagen: {e}")
            raise
        log.info("Aufnahme beendet")

        if self._use_api:
            return self._transcribe_via_tempfile(audio)

        audio_float = audio.flatten().astype(np.float32) / 32768.0
        return self._model.transcribe(audio_float, language=self.language)["text"].strip()

    def shutdown(self) -> None:
        """Clean up temp files and stop any active audio streams."""
        sd.stop()
        for path in self._tmp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    log.debug(f"Temp-Datei gelöscht: {path}")
            except OSError as e:
                log.warning(f"Konnte Temp-Datei nicht löschen: {path} — {e}")
        self._tmp_files.clear()
        log.info("WhisperEngine heruntergefahren.")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _transcribe_via_tempfile(self, audio: np.ndarray) -> str:
        tmp_path = tempfile.mktemp(suffix=".wav")
        self._tmp_files.append(tmp_path)
        try:
            wav_write(tmp_path, SAMPLE_RATE, audio)
            return self._transcribe_api(tmp_path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            if tmp_path in self._tmp_files:
                self._tmp_files.remove(tmp_path)

    def _transcribe_api(self, audio_path: str) -> str:
        with open(audio_path, "rb") as f:
            result = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language=self.language,
            )
        return result.text.strip()

    def _transcribe_local(self, audio_path: str) -> str:
        result = self._model.transcribe(audio_path, language=self.language)
        return result["text"].strip()
