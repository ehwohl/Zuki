import os
import re

ROOT          = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
IDENTITY_PATH = os.path.join(ROOT, "PERSONA.md")


def _load_system_prompt(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def _compress_prompt(raw: str) -> str:
    """Extract keyword skeleton from identity.md — minimal tokens, full intent."""
    keywords: dict[str, list[str]] = {}
    current = None
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("## "):
            current = line[3:].strip()
            keywords[current] = []
        elif current and line and not line.startswith("#"):
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", line)
            clean = re.sub(r"^[-•]\s*", "", clean).strip()
            if clean:
                keywords[current].append(clean.split("—")[0].strip())

    parts = []
    for section, items in keywords.items():
        parts.append(f"{section}: {', '.join(items)}")

    return (
        "Du bist Zuki. "
        + " | ".join(parts)
        + " | Stil: kurz, direkt, ohne Floskeln."
    )


class LLMManager:
    """
    Sends messages to an LLM provider.
    Simulation mode is active when no valid API key is configured.
    """

    def __init__(self, identity_path: str = IDENTITY_PATH):
        self._anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._openai_key    = os.environ.get("OPENAI_API_KEY", "")
        self.simulation     = not self._has_valid_key()
        _raw                = _load_system_prompt(identity_path)
        self.system_prompt  = _compress_prompt(_raw)   # compact for API
        self._full_prompt   = _raw                     # full version for display
        self._persona       = self._parse_persona(_raw)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    @property
    def system_prompt_info(self) -> str:
        est_tokens = len(self.system_prompt) // 4  # rough 1 token ≈ 4 chars
        return f"System-Prompt  :  {len(self.system_prompt)} Zeichen  (~{est_tokens} Tokens)"

    def chat(self, messages: list[dict], max_tokens: int = 2048) -> str:
        if self.simulation:
            return self._simulate(messages)
        return self._call_api(messages, max_tokens)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _has_valid_key(self) -> bool:
        """
        Returns True when at least one key looks genuine.
        Placeholder detection: keys starting with 'sk-your' or 'sk-ant-your'
        are treated as unset — simulation stays active.
        Switch to LIVE happens automatically when a real key is present.
        """
        _PLACEHOLDERS = ("sk-your", "sk-ant-your", "your-key", "")
        for key in (self._anthropic_key, self._openai_key):
            if key and not any(key.startswith(p) for p in _PLACEHOLDERS):
                return True
        return False

    def _parse_persona(self, text: str) -> dict:
        """Extract rolle and werte from identity.md for simulation replies."""
        persona = {"rolle": "", "werte": []}
        for line in text.splitlines():
            if not persona["rolle"] and "Analyst" in line and not line.startswith("#"):
                persona["rolle"] = line.strip()
            if line.startswith("- **"):
                wert = line.split("**")[1]
                persona["werte"].append(wert)
        return persona

    def _simulate(self, messages: list[dict]) -> str:
        last    = messages[-1]["content"].strip() if messages else ""
        lower   = last.lower()
        name    = self._extract_name(messages)
        address = f", {name}" if name else ""

        # Profile context injected by main.py as first message
        profile_text = self._extract_profile_context(messages)

        # Greeting
        if any(g in lower for g in ("hallo", "hi ", "guten morgen", "guten tag", "hey")):
            return f"Hallo{address}, freut mich von Ihnen zu hören."

        # Profile / identity questions → show profile file content
        _PROFILE_TRIGGERS = (
            "wie heiß", "mein name", "wer bin ich", "kennst du mich",
            "was weißt du über mich", "was weißt du von mir",
            "mein profil", "meine daten", "was hast du gespeichert",
            "kennst du meinen namen",
        )
        if any(p in lower for p in _PROFILE_TRIGGERS):
            if profile_text:
                return (
                    f"Das ist alles, was ich über Sie gespeichert habe{address}:\n\n"
                    f"{profile_text}"
                )
            if name:
                return f"Ihr Name ist {name}, weitere Daten habe ich noch nicht."
            return "Ich kenne Ihren Namen noch nicht — bitte stellen Sie sich vor."

        # Generic fallback
        return f"[SIM] Verstanden{address}. (Hinweis: Für volle KI-Leistung API-Key aktivieren.)"

    @staticmethod
    def _extract_profile_context(messages: list[dict]) -> str:
        """
        Liest den [Nutzerprofil]-Block, den main.py als erste Nachricht injiziert.
        Gibt den Rohtext zurück (leer wenn nicht vorhanden).
        """
        for msg in messages:
            content = msg.get("content", "")
            if content.startswith("[Nutzerprofil]"):
                return content[len("[Nutzerprofil]"):].strip()
        return ""

    @staticmethod
    def _extract_name(messages: list[dict]) -> str:
        """Scan history for 'ich bin X', 'ich heiße X', 'mein name ist X'."""
        patterns = [
            r"ich (?:bin|hei[sß]e)\s+([A-ZÄÖÜ][a-zäöüß]+)",
            r"mein name ist\s+([A-ZÄÖÜ][a-zäöüß]+)",
            r"nennen? sie mich\s+([A-ZÄÖÜ][a-zäöüß]+)",
            r"ich hei[sß]e\s+([A-ZÄÖÜ][a-zäöüß]+)",
        ]
        for msg in messages:
            if msg.get("role") != "user":
                continue
            for pattern in patterns:
                match = re.search(pattern, msg["content"], re.IGNORECASE)
                if match:
                    return match.group(1).capitalize()
        return ""

    def _call_api(self, messages: list[dict], max_tokens: int = 2048) -> str:
        if self._anthropic_key and not self._anthropic_key.startswith("sk-ant-your"):
            return self._call_anthropic(messages, max_tokens)
        return self._call_openai(messages, max_tokens)

    def _call_anthropic(self, messages: list[dict], max_tokens: int = 2048) -> str:
        import anthropic  # noqa: PLC0415
        client = anthropic.Anthropic(api_key=self._anthropic_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=max_tokens,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text

    def _call_openai(self, messages: list[dict], max_tokens: int = 2048) -> str:
        from openai import OpenAI  # noqa: PLC0415
        client = OpenAI(api_key=self._openai_key)
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages
        response = client.chat.completions.create(
            model="gpt-4o",
            max_tokens=max_tokens,
            messages=full_messages,
        )
        return response.choices[0].message.content
