"""
api_manager.py — Zentraler KI-API-Manager für Zuki
─────────────────────────────────────────────────────
Unterstützte Provider (Priorität):
  1. Gemini    (Google)  — GEMINI_API_KEY
  2. Anthropic (Claude)  — ANTHROPIC_API_KEY
  3. OpenAI    (GPT-4o)  — OPENAI_API_KEY
  4. SIM                 — kein gültiger Key → Simulation

Fehler-Handling:
  - 429 Rate-Limit  → freundliche Meldung an User, Details in logs/error.log
  - 404 Not-Found   → automatischer Modell-Fallback (nur bei Gemini)
  - Sonstige        → freundliche Meldung + Details in logs/error.log
"""

import os
import datetime
from core.logger import get_logger

log = get_logger("api_manager")

# ── Pfad zur Error-Log-Datei ───────────────────────────────────────────────────
_ROOT      = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ERROR_LOG = os.path.join(_ROOT, "logs", "error.log")


def _write_error_log(context: str, exc: Exception) -> None:
    """Schreibt technische Fehlerdetails in logs/error.log (nicht ins Terminal)."""
    try:
        os.makedirs(os.path.dirname(_ERROR_LOG), exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(_ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}]  {context}\n  {type(exc).__name__}: {exc}\n\n")
    except Exception:
        pass   # Log-Fehler niemals an den User weitergeben


# ── Gemini-Modell-Fallback-Kette ───────────────────────────────────────────────
# Nur bei 404 / Model-Not-Found aktiv.
# Reihenfolge: stabilste zuerst — 2.0-flash nur als letzter Ausweg.
_GEMINI_FALLBACK_MODELS = [
    "gemini-1.5-flash-latest",   # primär (entspricht .env Standard)
    "gemini-1.5-flash-002",
    "gemini-1.5-flash-001",
    "gemini-1.5-pro-latest",
    "gemini-2.0-flash",          # nur Notfall-Fallback
]

# ── Placeholder-Listen ─────────────────────────────────────────────────────────
_GEMINI_PLACEHOLDERS    = {"", "your-gemini-key-here", "your-key"}
_ANTHROPIC_PLACEHOLDERS = {"", "your-key"}
_OPENAI_PLACEHOLDERS    = {"", "your-key"}
_LOCAL_PLACEHOLDERS     = {"", "http://localhost:11434"}   # Ollama-Default gilt als Stub


def _is_valid_gemini(key: str) -> bool:
    if not key or key.strip() in _GEMINI_PLACEHOLDERS:
        return False
    if key.startswith("your-") or "your-gemini" in key.lower():
        return False
    return True


def _is_valid_anthropic(key: str) -> bool:
    if not key or key.strip() in _ANTHROPIC_PLACEHOLDERS:
        return False
    if key.startswith("sk-ant-your") or "your-key" in key.lower():
        return False
    return True


def _is_valid_openai(key: str) -> bool:
    if not key or key.strip() in _OPENAI_PLACEHOLDERS:
        return False
    if key.startswith("sk-your") or "your-key" in key.lower():
        return False
    return True


def _is_valid_local(url: str) -> bool:
    """True wenn LOCAL_LLM_URL gesetzt und kein Placeholder."""
    if not url or url.strip() in _LOCAL_PLACEHOLDERS:
        return False
    url = url.strip().lower()
    return url.startswith("http://") or url.startswith("https://")


def _is_404(e: Exception) -> bool:
    """Modell nicht gefunden / falscher Name."""
    msg = str(e).lower()
    return (
        "404" in msg
        or "not found" in msg
        or "model not found" in msg
        or "does not exist" in msg
        or "invalid model" in msg
    )


def _is_429(e: Exception) -> bool:
    """Rate-Limit oder Quota überschritten."""
    msg = str(e).lower()
    return (
        "429" in msg
        or "quota" in msg
        or "rate limit" in msg
        or "resource has been exhausted" in msg
        or "too many requests" in msg
    )


def _friendly_error(provider: str, exc: Exception) -> str:
    """Gibt eine kurze, freundliche Fehlermeldung für das Terminal zurück."""
    if _is_429(exc):
        labels = {
            "gemini":    "Google (Gemini)",
            "anthropic": "Anthropic (Claude)",
            "openai":    "OpenAI",
        }
        name = labels.get(provider, provider)
        return (
            f"Zuki: {name} macht gerade eine kurze Pause — "
            f"das Anfrage-Limit ist erreicht.\n"
            f"Bitte warte eine Minute und versuche es dann nochmal."
        )
    return (
        f"Zuki: Es gab einen kurzen Verbindungsfehler ({provider}).\n"
        f"Technische Details findest du in logs/error.log."
    )


# ── Manager-Klasse ─────────────────────────────────────────────────────────────

class APIManager:
    """
    Zentraler API-Manager — wählt automatisch den besten verfügbaren Provider.
    Fehlerdetails landen in logs/error.log, nicht im Terminal.
    """

    def __init__(self):
        self._gemini_key    = os.environ.get("GEMINI_API_KEY",    "").strip()
        self._anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self._openai_key    = os.environ.get("OPENAI_API_KEY",    "").strip()
        self._local_url     = os.environ.get("LOCAL_LLM_URL",     "").strip()
        self._local_model   = os.environ.get("LOCAL_LLM_MODEL",   "").strip()

        # Modell aus .env — Fallback auf gemini-1.5-flash-latest (stabil)
        env_model = os.environ.get("GEMINI_MODEL", "").strip()
        self._gemini_model = env_model if env_model else "gemini-1.5-flash-latest"

        self.provider   = self._detect_provider()
        self.simulation = self.provider == "sim"

        log.info(
            f"APIManager initialisiert — Provider: {self.provider.upper()}  |  "
            f"{'LIVE' if not self.simulation else 'SIMULATION'}  |  "
            f"Gemini-Modell: {self._gemini_model}"
        )

    # ── Provider-Erkennung ─────────────────────────────────────────────────────

    def _detect_provider(self) -> str:
        if _is_valid_gemini(self._gemini_key):
            return "gemini"
        if _is_valid_anthropic(self._anthropic_key):
            return "anthropic"
        if _is_valid_openai(self._openai_key):
            return "openai"
        if _is_valid_local(self._local_url):
            log.info(f"[LOCAL-LLM-STUB] URL erkannt: {self._local_url} — Stub aktiv")
            return "local"
        return "sim"

    @property
    def provider_label(self) -> str:
        """Lesbarer Provider-Name für UI."""
        return {
            "gemini":    "Gemini (Google)",
            "anthropic": "Claude (Anthropic)",
            "openai":    "GPT-4o (OpenAI)",
            "local":     f"Local LLM ({self._local_model or 'model?'})",
            "sim":       "SIMULATION",
        }.get(self.provider, self.provider)

    # ── Gemini Modell-Fallback (nur bei 404) ───────────────────────────────────

    def _gemini_model_with_fallback(self, genai, gen_config, system: str, call_fn) -> str:
        """
        Baut Gemini-Modelle in Prioritätsreihenfolge und ruft call_fn(model) auf.
        Wechsel zum nächsten Modell NUR bei 404 (falscher Modellname).
        429 und andere Fehler werden sofort weitergegeben.
        """
        # .env-Modell hat immer Vorrang — danach kommen Fallbacks ohne Duplikat
        candidates = [self._gemini_model] + [
            m for m in _GEMINI_FALLBACK_MODELS if m != self._gemini_model
        ]

        last_404 = None
        for model_name in candidates:
            try:
                model = genai.GenerativeModel(
                    model_name         = model_name,
                    generation_config  = gen_config,
                    system_instruction = system if system else None,
                )
                result = call_fn(model)

                # Gewähltes Modell für nächste Calls merken (silent)
                if model_name != self._gemini_model:
                    log.info(f"Gemini Fallback erfolgreich: {model_name}")
                    self._gemini_model = model_name
                return result

            except Exception as e:
                if _is_404(e):
                    log.warning(f"Gemini 404: '{model_name}' nicht gefunden — nächstes Modell")
                    last_404 = e
                    continue          # nächsten Kandidaten versuchen
                raise                 # 429, Auth-Fehler usw. → sofort raus

        # Alle Modelle erschöpft
        raise RuntimeError(
            f"Alle Gemini-Modelle liefern 404. Letzter Fehler: {last_404}"
        )

    # ── Öffentliche Schnittstelle ──────────────────────────────────────────────

    def chat(self, prompt: str, system: str = "", max_tokens: int = 2048) -> str:
        """Einzelner Prompt → Antwort-String."""
        if self.simulation:
            return self._simulate(prompt)
        try:
            if self.provider == "gemini":
                return self._call_gemini(prompt, system, max_tokens)
            if self.provider == "anthropic":
                return self._call_anthropic_prompt(prompt, system, max_tokens)
            if self.provider == "openai":
                return self._call_openai_prompt(prompt, system, max_tokens)
            if self.provider == "local":
                return self._call_local(prompt, system, max_tokens)
        except NotImplementedError:
            raise   # Stub-Fehler immer durchreichen — kein Schlucken
        except Exception as e:
            _write_error_log(f"chat() — provider={self.provider}", e)
            return _friendly_error(self.provider, e)
        return "[Kein Provider verfügbar]"

    def chat_messages(
        self, messages: list[dict], system: str = "", max_tokens: int = 2048
    ) -> str:
        """Multi-Turn Conversation im OpenAI-Format."""
        if self.simulation:
            last = messages[-1]["content"] if messages else ""
            return self._simulate(last)
        try:
            if self.provider == "gemini":
                return self._call_gemini_messages(messages, system, max_tokens)
            if self.provider == "anthropic":
                return self._call_anthropic_messages(messages, system, max_tokens)
            if self.provider == "openai":
                return self._call_openai_messages(messages, system, max_tokens)
            if self.provider == "local":
                last = messages[-1]["content"] if messages else ""
                return self._call_local(last, system, max_tokens)
        except NotImplementedError:
            raise   # Stub-Fehler immer durchreichen — kein Schlucken
        except Exception as e:
            _write_error_log(f"chat_messages() — provider={self.provider}", e)
            return _friendly_error(self.provider, e)
        return "[Kein Provider verfügbar]"

    # ── Gemini ─────────────────────────────────────────────────────────────────

    def _call_gemini(self, prompt: str, system: str, max_tokens: int) -> str:
        import google.generativeai as genai  # noqa: PLC0415
        genai.configure(api_key=self._gemini_key)
        gen_config = genai.types.GenerationConfig(max_output_tokens=max_tokens)

        def _do(model):
            response = model.generate_content(prompt)
            log.debug(f"Gemini chat: {len(response.text)} Zeichen")
            return response.text

        return self._gemini_model_with_fallback(genai, gen_config, system, _do)

    def _call_gemini_messages(
        self, messages: list[dict], system: str, max_tokens: int
    ) -> str:
        import google.generativeai as genai  # noqa: PLC0415
        genai.configure(api_key=self._gemini_key)
        gen_config = genai.types.GenerationConfig(max_output_tokens=max_tokens)

        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})
        last_msg = messages[-1]["content"] if messages else ""

        def _do(model):
            chat     = model.start_chat(history=history)
            response = chat.send_message(last_msg)
            log.debug(f"Gemini messages: {len(response.text)} Zeichen")
            return response.text

        return self._gemini_model_with_fallback(genai, gen_config, system, _do)

    # ── Anthropic ──────────────────────────────────────────────────────────────

    def _call_anthropic_prompt(self, prompt: str, system: str, max_tokens: int) -> str:
        import anthropic  # noqa: PLC0415
        client   = anthropic.Anthropic(api_key=self._anthropic_key)
        response = client.messages.create(
            model      = "claude-sonnet-4-6",
            max_tokens = max_tokens,
            system     = system or "",
            messages   = [{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _call_anthropic_messages(
        self, messages: list[dict], system: str, max_tokens: int
    ) -> str:
        import anthropic  # noqa: PLC0415
        client   = anthropic.Anthropic(api_key=self._anthropic_key)
        response = client.messages.create(
            model      = "claude-sonnet-4-6",
            max_tokens = max_tokens,
            system     = system or "",
            messages   = messages,
        )
        return response.content[0].text

    # ── OpenAI ─────────────────────────────────────────────────────────────────

    def _call_openai_prompt(self, prompt: str, system: str, max_tokens: int) -> str:
        from openai import OpenAI  # noqa: PLC0415
        client = OpenAI(api_key=self._openai_key)
        msgs   = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=      "gpt-4o",
            max_tokens= max_tokens,
            messages=   msgs,
        )
        return response.choices[0].message.content

    def _call_openai_messages(
        self, messages: list[dict], system: str, max_tokens: int
    ) -> str:
        from openai import OpenAI  # noqa: PLC0415
        client = OpenAI(api_key=self._openai_key)
        full   = []
        if system:
            full.append({"role": "system", "content": system})
        full.extend(messages)
        response = client.chat.completions.create(
            model=      "gpt-4o",
            max_tokens= max_tokens,
            messages=   full,
        )
        return response.choices[0].message.content

    # ── Vision / Multimodal ────────────────────────────────────────────────────

    def chat_vision(
        self,
        image_path: str,
        question:   str,
        system:     str = "",
        max_tokens: int = 1024,
    ) -> str:
        """Bild + Frage → Antwort-String (multimodal)."""
        if self.simulation:
            return self._simulate_vision(question)
        try:
            if self.provider == "gemini":
                return self._call_gemini_vision(image_path, question, system, max_tokens)
            if self.provider == "anthropic":
                return self._call_anthropic_vision(image_path, question, system, max_tokens)
            if self.provider == "openai":
                return self._call_openai_vision(image_path, question, system, max_tokens)
        except Exception as e:
            _write_error_log(f"chat_vision() — provider={self.provider}", e)
            return _friendly_error(self.provider, e)
        return "[Kein Vision-Provider verfügbar]"

    def _call_gemini_vision(
        self, image_path: str, question: str, system: str, max_tokens: int
    ) -> str:
        import google.generativeai as genai  # noqa: PLC0415
        import PIL.Image                     # noqa: PLC0415
        genai.configure(api_key=self._gemini_key)
        gen_config = genai.types.GenerationConfig(max_output_tokens=max_tokens)
        image = PIL.Image.open(image_path)

        def _do(model):
            response = model.generate_content([question, image])
            log.info(f"Gemini Vision: {len(response.text)} Zeichen")
            return response.text

        return self._gemini_model_with_fallback(genai, gen_config, system, _do)

    def _call_anthropic_vision(
        self, image_path: str, question: str, system: str, max_tokens: int
    ) -> str:
        import anthropic  # noqa: PLC0415
        import base64
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        client   = anthropic.Anthropic(api_key=self._anthropic_key)
        response = client.messages.create(
            model      = "claude-sonnet-4-6",
            max_tokens = max_tokens,
            system     = system or "",
            messages   = [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {
                        "type":       "base64",
                        "media_type": "image/jpeg",
                        "data":       img_b64,
                    }},
                    {"type": "text", "text": question},
                ],
            }],
        )
        return response.content[0].text

    def _call_openai_vision(
        self, image_path: str, question: str, system: str, max_tokens: int
    ) -> str:
        import base64
        from openai import OpenAI  # noqa: PLC0415
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        client = OpenAI(api_key=self._openai_key)
        msgs   = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": [
            {"type": "image_url",
             "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            {"type": "text", "text": question},
        ]})
        response = client.chat.completions.create(
            model=      "gpt-4o",
            max_tokens= max_tokens,
            messages=   msgs,
        )
        return response.choices[0].message.content

    # ── Local LLM (Stub) ───────────────────────────────────────────────────────

    def _call_local(self, prompt: str, system: str, max_tokens: int) -> str:
        """
        [LOCAL-LLM-STUB] Platzhalter für lokale LLM-Integration.

        LIVE UPGRADE — Ollama-Beispiel:
          import requests
          payload = {
              "model":  self._local_model or "llama3",
              "prompt": f"{system}\n\n{prompt}" if system else prompt,
              "stream": False,
              "options": {"num_predict": max_tokens},
          }
          r = requests.post(f"{self._local_url}/api/generate", json=payload, timeout=60)
          r.raise_for_status()
          return r.json().get("response", "")

        LIVE UPGRADE — OpenAI-kompatibler Endpunkt (LM Studio, llama.cpp):
          from openai import OpenAI
          client = OpenAI(base_url=self._local_url, api_key="local")
          resp = client.chat.completions.create(
              model=self._local_model or "local-model",
              messages=[{"role": "user", "content": prompt}],
              max_tokens=max_tokens,
          )
          return resp.choices[0].message.content
        """
        log.info(
            f"[LOCAL-LLM-STUB] chat() aufgerufen — URL={self._local_url}  "
            f"Modell={self._local_model or '(keins gesetzt)'}"
        )
        raise NotImplementedError(
            f"[LOCAL-LLM-STUB] Local-LLM-Integration noch nicht implementiert.\n"
            f"  URL:   {self._local_url}\n"
            f"  Modell: {self._local_model or '(LOCAL_LLM_MODEL nicht gesetzt)'}\n"
            f"Bitte _call_local() in core/api_manager.py mit echtem HTTP-Call befüllen."
        )

    # ── Simulation ─────────────────────────────────────────────────────────────

    @staticmethod
    def _simulate(prompt: str) -> str:
        short = prompt[:80].replace("\n", " ")
        return (
            f"[API-SIM] Kein gültiger API-Key.\n"
            f"Prompt erhalten: \"{short}...\"\n"
            f"→ GEMINI_API_KEY in .env eintragen für Live-Antworten."
        )

    @staticmethod
    def _simulate_vision(question: str) -> str:
        return (
            f"[VISION-SIM] Kein API-Key für Bildanalyse.\n"
            f"Frage war: \"{question}\"\n"
            f"→ GEMINI_API_KEY in .env setzen für echte Bildanalyse."
        )
