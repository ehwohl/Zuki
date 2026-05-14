"""
system_test.py — Selbst-Diagnose aller Zuki-Subsysteme
────────────────────────────────────────────────────────
Aufruf:
  tester  = SystemTest(cloud=cloud, api_mgr=api_mgr, ...)
  results = tester.run_all()            # alle 12 Subsysteme
  result  = tester.run_one("cloud")    # Einzeltest

Status-API:
  run_all()         -> list[TestResult]
  run_one(name)     -> TestResult | None
  available_names() -> list[str]

Log-Marker: [SYSTEM-TEST-START], [SYSTEM-TEST-RESULT]
"""

import os
from dataclasses import dataclass

from core.logger import get_logger

log = get_logger("system_test")

_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_PLACEHOLDER_PATTERNS = [
    "your-", "your_", "dein-", "deine-", "example",
    "placeholder", "change-me", "key-here", "token-here",
    "geheim-here", "your-project", "dein-projekt",
]


@dataclass
class TestResult:
    name: str
    status: str        # "ok" | "warn" | "fail"
    summary: str
    fix_hint: str = ""


class SystemTest:
    """
    Führt Selbst-Tests für alle Zuki-Subsysteme durch.
    Manager-Instanzen werden per Keyword-Argument übergeben.
    """

    def __init__(
        self,
        *,
        cloud=None,
        api_mgr=None,
        stt=None,
        tts=None,
        history=None,
        profile=None,
        skill_registry_module=None,
        session_state=None,
        auto_backup=None,
        github_backup=None,
        tenant_mgr=None,
        router_agent=None,
        knowledge_base=None,
    ):
        self._cloud      = cloud
        self._api_mgr    = api_mgr
        self._stt        = stt
        self._tts        = tts
        self._history    = history
        self._profile    = profile
        self._skills     = skill_registry_module
        self._session    = session_state
        self._backup     = auto_backup
        self._github     = github_backup
        self._tenant_mgr = tenant_mgr
        self._router     = router_agent
        self._knowledge  = knowledge_base

        self._tests = {
            "cloud":      self._test_cloud,
            "llm":        self._test_llm,
            "stt":        self._test_stt,
            "tts":        self._test_tts,
            "vision":     self._test_vision,
            "mic":        self._test_mic,
            "filesystem": self._test_filesystem,
            "memory":     self._test_memory,
            "skills":     self._test_skills,
            "session":    self._test_session,
            "backup":     self._test_backup,
            "env":        self._test_env,
            "github":     self._test_github,
            "tenant":     self._test_tenant,
            "router":     self._test_router,
            "cleanup":    self._test_cleanup,
            "platform":   self._test_platform,
            "scraper":    self._test_scraper,
            "report":     self._test_report,
            "knowledge":  self._test_knowledge,
            "coding":     self._test_coding,
        }

    # ── Öffentliche API ───────────────────────────────────────────────────────

    def available_names(self) -> list[str]:
        return list(self._tests.keys())

    def run_all(self) -> list[TestResult]:
        log.info("[SYSTEM-TEST-START] Vollständige System-Diagnose gestartet")
        results = []
        for name, fn in self._tests.items():
            result = self._run_safe(name, fn)
            results.append(result)
            log.info(f"[SYSTEM-TEST-RESULT] {name:<12} {result.status:<4} — {result.summary}")

        ok   = sum(1 for r in results if r.status == "ok")
        warn = sum(1 for r in results if r.status == "warn")
        fail = sum(1 for r in results if r.status == "fail")
        log.info(f"[SYSTEM-TEST-RESULT] Gesamt: {ok} OK  {warn} WARN  {fail} FAIL")
        return results

    def run_one(self, name: str) -> "TestResult | None":
        fn = self._tests.get(name.lower())
        if fn is None:
            return None
        log.info(f"[SYSTEM-TEST-START] Einzeltest: {name}")
        result = self._run_safe(name, fn)
        log.info(f"[SYSTEM-TEST-RESULT] {result.name:<12} {result.status:<4} — {result.summary}")
        return result

    # ── Interner Ausführungshelfer ────────────────────────────────────────────

    def _run_safe(self, name: str, fn) -> TestResult:
        try:
            return fn()
        except Exception as e:
            log.error(f"[SYSTEM-TEST] Ausnahme in Test '{name}': {e}")
            return TestResult(
                name     = name,
                status   = "fail",
                summary  = f"Test-Ausnahme: {e}",
                fix_hint = "Bug in system_test.py — Logs prüfen",
            )

    # ── Cloud ─────────────────────────────────────────────────────────────────

    def _test_cloud(self) -> TestResult:
        c = self._cloud
        if c is None:
            return TestResult("cloud", "warn", "CloudMemory nicht übergeben",
                              "SystemTest mit cloud=cloud instanziieren")
        if not c.enabled:
            url = getattr(c, "_url", "")
            if url:
                return TestResult("cloud", "warn", f"Platzhalter-URL erkannt: {url[:40]}",
                                  "Echte Vercel-URL in CLOUD_MEMORY_URL eintragen")
            return TestResult("cloud", "warn", "Cloud nicht konfiguriert",
                              "CLOUD_MEMORY_URL + CLOUD_MEMORY_TOKEN in .env setzen")

        ok, msg = c.ping()
        outbox  = c.outbox.size()
        flush_t = c.outbox.last_flush_time()
        flush_s = flush_t.strftime("%H:%M:%S") if flush_t else "nie"

        if not ok:
            return TestResult("cloud", "fail", f"Verbindung fehlgeschlagen: {msg}",
                              "CLOUD_MEMORY_URL und CLOUD_MEMORY_TOKEN in .env prüfen")

        outbox_hint = f"  ·  Outbox: {outbox} ausstehend" if outbox > 0 else "  ·  Outbox leer"
        summary = f"Verbunden  ·  {c.save_count} Saves  ·  Flush: {flush_s}{outbox_hint}"
        if outbox > 0:
            return TestResult("cloud", "warn", summary,
                              "Outbox-Einträge werden beim nächsten Ping automatisch gesendet")
        return TestResult("cloud", "ok", summary)

    # ── LLM ──────────────────────────────────────────────────────────────────

    def _test_llm(self) -> TestResult:
        a = self._api_mgr
        if a is None:
            return TestResult("llm", "warn", "APIManager nicht übergeben",
                              "SystemTest mit api_mgr=api_mgr instanziieren")
        label = a.provider_label
        if a.simulation:
            return TestResult("llm", "warn",
                              f"SIM-Modus  ·  kein gültiger API-Key  ({label})",
                              "GEMINI_API_KEY (oder ANTHROPIC_/OPENAI_API_KEY) in .env setzen")
        try:
            resp = a.chat("Antworte nur mit dem Wort 'OK'.", max_tokens=5)
            if resp and len(resp.strip()) > 0:
                return TestResult("llm", "ok",
                                  f"Provider: {label}  ·  Test-Antwort erhalten")
            return TestResult("llm", "warn",
                              f"Provider: {label}  ·  Leere Antwort",
                              "API-Key und Kontingent prüfen")
        except NotImplementedError:
            return TestResult("llm", "warn",
                              f"Provider: {label}  ·  Stub nicht implementiert",
                              "_call_local() in api_manager.py mit HTTP-Call befüllen")
        except Exception as e:
            return TestResult("llm", "fail", f"Fehler: {e}",
                              f"API-Key oder Netzwerk prüfen ({a.provider})")

    # ── STT ──────────────────────────────────────────────────────────────────

    def _test_stt(self) -> TestResult:
        s = self._stt
        if s is None:
            return TestResult("stt", "fail", "WhisperEngine nicht übergeben",
                              "SystemTest mit stt=stt instanziieren")
        mode = getattr(s, "mode_label", "unbekannt")
        return TestResult("stt", "ok", f"WhisperEngine geladen  ·  Modus: {mode}")

    # ── TTS ──────────────────────────────────────────────────────────────────

    def _test_tts(self) -> TestResult:
        t = self._tts
        if t is None:
            return TestResult("tts", "fail", "TTSEngine nicht übergeben",
                              "SystemTest mit tts=tts instanziieren")
        # ab Bundle 8: TTSEngine ist Wrapper um Backend (WindowsTTS / LinuxTTS).
        # Status API returns backend, voice, ready, platform.
        try:
            status = t.get_status()
        except Exception as e:
            return TestResult("tts", "fail", f"get_status() fehlgeschlagen: {e}",
                              "TTSEngine.get_status() prüfen")
        if not status.get("ready", False):
            backend = status.get("backend", "?")
            return TestResult("tts", "fail",
                              f"Backend '{backend}' nicht bereit",
                              "pip install pyttsx3 / Windows SAPI5 prüfen")
        backend = status.get("backend", "?")
        voice   = status.get("voice", "unbekannt")
        return TestResult("tts", "ok", f"{backend}  ·  Stimme: \"{voice}\"")

    # ── Vision ────────────────────────────────────────────────────────────────

    def _test_vision(self) -> TestResult:
        try:
            import mss  # noqa: F401
        except ImportError:
            return TestResult("vision", "fail", "mss nicht installiert",
                              "pip install mss Pillow")
        vision_dir = os.path.join(_ROOT, "temp", "vision")
        try:
            os.makedirs(vision_dir, exist_ok=True)
            probe = os.path.join(vision_dir, "_probe.tmp")
            with open(probe, "w") as f:
                f.write("ok")
            os.remove(probe)
        except OSError as e:
            return TestResult("vision", "fail", f"temp/vision/ nicht schreibbar: {e}",
                              "Schreibrechte für temp/vision/ prüfen")
        return TestResult("vision", "ok", "mss installiert  ·  temp/vision/ schreibbar")

    # ── Mic ───────────────────────────────────────────────────────────────────

    def _test_mic(self) -> TestResult:
        try:
            import sounddevice as sd  # noqa: F401
            devices = sd.query_devices()
            inputs  = [d for d in devices if d.get("max_input_channels", 0) > 0]
            if not inputs:
                return TestResult("mic", "fail", "Kein Eingabegerät gefunden",
                                  "Mikrofon anschließen oder Gerätetreiber prüfen")
            default_dev = sd.query_devices(kind="input")
            name = default_dev.get("name", "unbekannt") if isinstance(default_dev, dict) else str(default_dev)
            return TestResult("mic", "ok",
                              f"Eingabegerät: \"{name}\"  ·  {len(inputs)} Gerät(e) verfügbar")
        except Exception as e:
            return TestResult("mic", "fail", f"sounddevice-Fehler: {e}",
                              "pip install sounddevice; Audiogeräte und Treiber prüfen")

    # ── Filesystem ───────────────────────────────────────────────────────────

    def _test_filesystem(self) -> TestResult:
        dirs = {
            "temp":    os.path.join(_ROOT, "temp"),
            "logs":    os.path.join(_ROOT, "logs"),
            "backups": os.path.join(_ROOT, "backups"),
        }
        missing      = []
        not_writable = []
        for label, path in dirs.items():
            if not os.path.isdir(path):
                missing.append(label)
                continue
            try:
                probe = os.path.join(path, "_probe.tmp")
                with open(probe, "w") as f:
                    f.write("ok")
                os.remove(probe)
            except OSError:
                not_writable.append(label)

        if not_writable:
            return TestResult("filesystem", "fail",
                              f"Nicht schreibbar: {', '.join(not_writable)}/",
                              "Schreibrechte prüfen oder Ordner neu anlegen")
        if missing:
            return TestResult("filesystem", "warn",
                              f"Ordner fehlen: {', '.join(missing)}/",
                              "Werden beim nächsten Start automatisch erstellt")
        return TestResult("filesystem", "ok",
                          "temp/  logs/  backups/  — vorhanden und schreibbar")

    # ── Memory ────────────────────────────────────────────────────────────────

    def _test_memory(self) -> TestResult:
        h = self._history
        p = self._profile
        if h is None or p is None:
            return TestResult("memory", "warn", "History oder Profil nicht übergeben",
                              "SystemTest mit history=history, profile=profile instanziieren")
        count        = getattr(h, "count", 0)
        is_empty     = getattr(p, "is_empty", True)
        profile_info = "leer (kein Nutzerprofil)" if is_empty else "vorhanden"
        return TestResult("memory", "ok",
                          f"Historie: {count} Einträge  ·  Profil: {profile_info}")

    # ── Skills ────────────────────────────────────────────────────────────────

    def _test_skills(self) -> TestResult:
        sr = self._skills
        if sr is None:
            return TestResult("skills", "warn", "Skill-Registry nicht übergeben",
                              "SystemTest mit skill_registry_module=skill_registry instanziieren")
        count = sr.skill_count()
        names = sr.list_names()
        if count == 0:
            return TestResult("skills", "warn", "Keine Skills registriert",
                              "skills/ Verzeichnis prüfen, discover_skills() aufgerufen?")
        return TestResult("skills", "ok",
                          f"{count} Skills: {', '.join(names)}")

    # ── Session ───────────────────────────────────────────────────────────────

    def _test_session(self) -> TestResult:
        s = self._session
        if s is None:
            return TestResult("session", "warn", "SessionState nicht übergeben",
                              "SystemTest mit session_state=state instanziieren")
        path = getattr(s, "_path", None)
        if path and not os.path.exists(os.path.dirname(path)):
            return TestResult("session", "fail", "temp/ Verzeichnis nicht vorhanden",
                              "Verzeichnis temp/ erstellen")

        unclean = s.is_unclean()
        if unclean:
            data = s.load()
            ts   = (data or {}).get("timestamp", "?")[:19]
            return TestResult("session", "warn",
                              f"Unclean-Flag aktiv (Session seit: {ts})",
                              "Normal während laufender Session — wird beim Exit zurückgesetzt")

        return TestResult("session", "ok", "Kein unclean-Flag  ·  Letzter Exit sauber")

    # ── Backup ────────────────────────────────────────────────────────────────

    def _test_backup(self) -> TestResult:
        b = self._backup
        if b is None:
            return TestResult("backup", "warn", "AutoBackup nicht übergeben",
                              "SystemTest mit auto_backup=_auto_backup instanziieren")
        count  = b.snapshot_count()
        last_t = b.last_snapshot_time()
        last_s = last_t.strftime("%Y-%m-%d %H:%M") if last_t else "noch keiner in dieser Sitzung"
        if count == 0:
            return TestResult("backup", "warn",
                              "Noch kein Snapshot vorhanden  ·  AutoBackup alle 6h",
                              "Jetzt mit 'system backup' einen manuellen Snapshot erstellen")
        return TestResult("backup", "ok",
                          f"{count} Snapshots  ·  Letzter Auto-Backup: {last_s}")

    # ── ENV ───────────────────────────────────────────────────────────────────

    def _test_env(self) -> TestResult:
        def _has_placeholder(val: str) -> bool:
            v = val.lower()
            return any(p in v for p in _PLACEHOLDER_PATTERNS)

        essential = {
            "CLOUD_MEMORY_URL":   "Cloud-URL",
            "CLOUD_MEMORY_TOKEN": "Cloud-Token",
        }
        api_keys = ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"]

        missing_vars      = []
        placeholder_vars  = []

        for var, label in essential.items():
            val = os.environ.get(var, "").strip()
            if not val:
                missing_vars.append(var)
            elif _has_placeholder(val):
                placeholder_vars.append(var)

        active_key = next(
            (k for k in api_keys
             if os.environ.get(k, "").strip()
             and not _has_placeholder(os.environ.get(k, ""))),
            None,
        )
        if active_key is None:
            missing_vars.append("(mind. ein API-Key)")

        if missing_vars:
            return TestResult(
                "env", "fail",
                f"Fehlende Variablen: {', '.join(missing_vars)}",
                ".env öffnen und fehlende Werte eintragen",
            )
        if placeholder_vars:
            return TestResult(
                "env", "warn",
                f"Platzhalter erkannt: {', '.join(placeholder_vars)}",
                "Echte URLs/Tokens in .env eintragen",
            )
        return TestResult("env", "ok",
                          f"Alle ENV-Vars gesetzt  ·  Aktiver API-Key: {active_key}")

    # ── GitHub-Backup ─────────────────────────────────────────────────────────

    def _test_github(self) -> TestResult:
        g = self._github
        if g is None:
            return TestResult("github", "warn", "GitHubBackup nicht übergeben",
                              "SystemTest mit github_backup=_github_backup instanziieren")
        result = g.self_test()
        return TestResult(
            name     = "github",
            status   = result["status"],
            summary  = result["summary"],
            fix_hint = result.get("fix_hint", ""),
        )

    # ── Tenant check ──────────────────────────────────────────────────────────

    def _test_tenant(self) -> TestResult:
        tm = self._tenant_mgr
        if tm is None:
            return TestResult(
                "tenant", "warn",
                "TenantManager nicht übergeben",
                "SystemTest mit tenant_mgr=tenant_mgr instanziieren",
            )
        result = tm.self_test()
        return TestResult(
            name     = "tenant",
            status   = result["status"],
            summary  = result["summary"],
            fix_hint = result.get("fix_hint", ""),
        )

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def _test_cleanup(self) -> TestResult:
        from tools.cleanup_manager import CleanupManager
        cleaner = CleanupManager()
        info    = cleaner.self_test()
        return TestResult(
            name     = "cleanup",
            status   = info.get("status", "ok"),
            summary  = info.get("summary", ""),
        )

    # ── Platform-Agnostik ─────────────────────────────────────────────────────

    def _test_platform(self) -> TestResult:
        import sys
        platform = sys.platform
        lines: list[str] = []
        warnings_found: list[str] = []

        # TTS-Backend prüfen
        try:
            from core.text_to_speech.tts_engine import TTSEngine
            engine = TTSEngine()
            tts_status = engine.get_status()
            engine.shutdown()
            tts_ready = tts_status.get("ready", False)
            tts_label = tts_status.get("backend", "?")
            if tts_ready:
                lines.append(f"TTS: {tts_label} (ok)")
            else:
                warnings_found.append(f"TTS: {tts_label} nicht bereit")
        except Exception as e:
            warnings_found.append(f"TTS: Fehler — {e}")

        # Window-Control-Backend prüfen
        try:
            from tools.pc_control import PCControl
            wc_status = PCControl.get_status()
            wc_ready  = wc_status.get("available", False)
            wc_label  = wc_status.get("backend", "?")
            if wc_ready:
                lines.append(f"WinCtrl: {wc_label} (ok)")
            else:
                warnings_found.append(f"WinCtrl: {wc_label} — Stub aktiv")
        except Exception as e:
            warnings_found.append(f"WinCtrl: Fehler — {e}")

        # Audio-In (sounddevice) prüfen
        try:
            from core.speech_to_text.whisper_engine import _SD_AVAILABLE
            if _SD_AVAILABLE:
                lines.append("Audio-In: sounddevice (ok)")
            else:
                hint = (
                    "sudo apt install portaudio19-dev && pip install sounddevice"
                    if platform.startswith("linux")
                    else "pip install sounddevice"
                )
                warnings_found.append(f"Audio-In: sounddevice fehlt → {hint}")
        except Exception as e:
            warnings_found.append(f"Audio-In: Fehler — {e}")

        summary = f"Platform: {platform}  |  " + "  |  ".join(lines)
        if warnings_found:
            return TestResult(
                name     = "platform",
                status   = "warn",
                summary  = summary,
                fix_hint = " | ".join(warnings_found),
            )
        return TestResult(
            name    = "platform",
            status  = "ok",
            summary = summary,
        )

    # ── Report ───────────────────────────────────────────────────────────────

    def _test_report(self) -> TestResult:
        from tools.report import self_test as report_self_test
        result = report_self_test()
        return TestResult(
            name     = "report",
            status   = result["status"],
            summary  = result["summary"],
            fix_hint = result.get("fix_hint", ""),
        )

    # ── Scraper ───────────────────────────────────────────────────────────────

    def _test_scraper(self) -> TestResult:
        from tools.scraper import self_test as scraper_self_test
        result = scraper_self_test()
        return TestResult(
            name     = "scraper",
            status   = result["status"],
            summary  = result["summary"],
            fix_hint = result.get("fix_hint", ""),
        )

    # ── Coding-Scratchpad ─────────────────────────────────────────────────────

    def _test_coding(self) -> TestResult:
        from workspaces.coding.sandbox import is_available, run_code
        from workspaces.coding.buffer import LANGUAGES

        # Python must always be available
        ok, hint = is_available("python")
        if not ok:
            return TestResult("coding", "fail", "Python-Interpreter nicht gefunden", hint)

        # Quick-Smoke-Test: einfaches Python-Snippet ausführen
        result = run_code("python", "print('zuki-coding-ok')", timeout=5)
        if not result.success or "zuki-coding-ok" not in result.stdout:
            return TestResult(
                "coding", "fail",
                f"Sandbox-Ausführung fehlgeschlagen: {result.format_output()[:80]}",
                "temp/sandbox/ Verzeichnis prüfen; Python-Pfad in .env setzen",
            )

        # Optional: which additional interpreters are available
        available = ["python"]
        missing   = []
        for lang in sorted(LANGUAGES - {"python", "pine"}):
            avail, _ = is_available(lang)
            (available if avail else missing).append(lang)

        pine_note = "pine→TradingView"
        summary   = (
            f"Sandbox OK  ·  Verfügbar: {', '.join(available + [pine_note])}"
            + (f"  ·  Nicht installiert: {', '.join(missing)}" if missing else "")
        )
        status = "ok" if not missing else "warn"
        hint   = (
            f"Fehlende Interpreter: {', '.join(missing)} — optional, nur bei Bedarf installieren"
            if missing else ""
        )
        return TestResult("coding", status, summary, hint)

    # ── Knowledge-Base ────────────────────────────────────────────────────────

    def _test_knowledge(self) -> TestResult:
        from knowledge.loader import self_test as kb_self_test
        result = kb_self_test()
        return TestResult(
            name     = "knowledge",
            status   = result["status"],
            summary  = result["summary"],
            fix_hint = result.get("fix_hint", ""),
        )

    # ── Router-Agent ──────────────────────────────────────────────────────────

    def _test_router(self) -> TestResult:
        r = self._router
        if r is None:
            return TestResult(
                "router", "warn",
                "RouterAgent nicht übergeben",
                "SystemTest mit router_agent=router instanziieren",
            )
        info    = r.self_test()
        enabled = info.get("enabled", False)
        count   = info.get("decision_count", 0)
        log_ok  = info.get("log_exists", False)
        last    = info.get("last_decision")

        if not enabled:
            return TestResult(
                "router", "warn",
                "SIM-Modus aktiv — Router deaktiviert (kein API-Key)",
                "Einen echten API-Key in .env eintragen für LLM-Routing",
            )

        last_str = f"  ·  Letzte Entscheidung: {last['skills']}" if last else ""
        log_str  = "  ·  Log vorhanden" if log_ok else "  ·  Noch kein Log"
        return TestResult(
            "router", "ok",
            f"Aktiv  ·  {count} Entscheidungen{last_str}{log_str}",
        )
