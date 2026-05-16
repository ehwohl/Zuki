import sys
import os
import warnings
import logging
import atexit

# ── Suppress all third-party warnings permanently ─────────────────────────────
warnings.filterwarnings("ignore")
for _lib in ("whisper", "torch", "urllib3", "numba", "sounddevice", "httpx", "httpcore"):
    logging.getLogger(_lib).setLevel(logging.CRITICAL)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, ROOT)

from core.logger import get_logger
from core.ui_factory import get_renderer as _get_renderer
from core.ui_renderer import UIRenderer

log = get_logger("main")

# ui is initialized in run() after load_env() so ZUKI_UI from .env takes effect.
# Module-level fallback so helpers (listen, shutdown, …) always
# have a valid object even if called before run().
ui: UIRenderer = _get_renderer()

ENV_FILES = [
    os.path.join(ROOT, ".env"),
    os.path.join(ROOT, "workspaces", "os", "voice", "config", ".env"),
]

from core.llm_manager import LLMManager
from core.api_manager import APIManager
from core.speech_to_text.whisper_engine import WhisperEngine
from core.text_to_speech.tts_engine import TTSEngine
from memory.history_manager import HistoryManager
from memory.user_profile import UserProfile
from workspaces import registry as skill_registry
from core import vision_manager as vision
from tools.backup_manager import create_snapshot, format_snapshot_list, AutoBackup
from tools.cloud_memory import CloudMemory
from tools.github_backup import GitHubBackup
from tools.instance_guard import acquire as _guard_acquire, release as _guard_release
from tools.session_state import SessionState
from tools.system_test import SystemTest
from core.tenant import get_tenant_manager
from core.router_agent import RouterAgent
from tools.cleanup_manager import CleanupManager
import ui_bridge

LISTEN_TRIGGERS  = {"hör zu", "hoer zu"}
EXIT_TRIGGERS    = {"exit", "quit", "beenden"}
VISION_TRIGGERS  = {"vision", "screenshot", "schau hin", "was siehst du"}
SAVE_TRIGGERS    = {"save", "speichern", "merken"}
CLOUD_TEST       = {"cloud test", "cloud status", "cloud ping"}
TENANT_CMD       = "tenant"


# ── Tenant Guard ───────────────────────────────────────────────────────────────

def _tenant_guard(skill, tenant_mgr) -> bool:
    """
    Checks whether a skill is running in the correct tenant.
    Returns True if the skill may proceed, False if it should abort.

    Controlled via ENV SKILL_TENANT_GUARD:
      warn (default) — warns + prompts (continue / tenant <name> / no)
      auto           — warns + automatically prompts for tenant name, creates + switches,
                       skill then runs directly in the new tenant
      off            — guard disabled for all skills

    CONVENTION: Called before EVERY skill invocation (fast-path + router).
    Skills with tenant_aware=False (test/utility skills) are skipped.
    """
    if not getattr(skill, "tenant_aware", True):
        return True

    guard_mode = os.getenv("SKILL_TENANT_GUARD", "warn").lower()
    if guard_mode == "off":
        return True

    current = tenant_mgr.current() if tenant_mgr else "self"
    if current != "self":
        return True   # bereits in Kunden-Tenant — alles gut

    # ── In self-tenant: warn ───────────────────────────────────────────────────
    if guard_mode == "auto":
        ui.speak_zuki(
            f"⚠️  Tenant-Warnung: Aktiver Workspace ist 'self' (Privat).\n"
            f"    Für welchen Kunden/Projekt soll dieser Skill laufen?\n"
            f"    Tenant-Name eingeben (z. B. 'client-eboli') oder Enter für 'self':"
        )
        answer = ui.user_prompt().strip()
        if answer and answer.lower() not in {"self", "weiter", ""}:
            tenant_name = answer.lower().replace(" ", "-")
            tenant_mgr.create(tenant_name, {})
            tenant_mgr.switch(tenant_name)
            ui.system_msg(f"[Tenant] Gewechselt zu '{tenant_name}' — Skill läuft jetzt dort.")
            log.info(f"[TENANT-GUARD] Auto-Switch zu '{tenant_name}'")
        else:
            log.info("[TENANT-GUARD] User bleibt in 'self'")
        return True   # in jedem Fall fortfahren (entweder im neuen oder self Tenant)

    else:  # warn (Standard)
        ui.speak_zuki(
            f"⚠️  Tenant-Warnung: Aktiver Workspace ist 'self' (Privat).\n"
            f"    Für Kundendaten empfehlen wir einen eigenen Tenant.\n\n"
            f"    weiter          → trotzdem in 'self' fortfahren\n"
            f"    tenant <Name>   → Tenant anlegen + wechseln, Befehl danach wiederholen\n"
            f"    nein            → abbrechen"
        )
        answer = ui.user_prompt().strip().lower()

        if answer in {"weiter", "w", "ja", "j", "yes", "y"}:
            log.info("[TENANT-GUARD] User hat 'weiter' in self-Tenant gewählt")
            return True

        if answer.startswith("tenant "):
            tenant_name = answer[7:].strip().replace(" ", "-")
            if tenant_name:
                tenant_mgr.create(tenant_name, {})
                tenant_mgr.switch(tenant_name)
                ui.system_msg(
                    f"[Tenant] '{tenant_name}' erstellt und aktiviert.\n"
                    f"    Befehl bitte erneut eingeben — läuft jetzt unter '{tenant_name}'."
                )
                log.info(f"[TENANT-GUARD] Tenant '{tenant_name}' erstellt + gewechselt")
            return False   # Skill nicht starten — User tippt Befehl neu

        log.info("[TENANT-GUARD] Skill abgebrochen")
        return False


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_env(paths: list[str]) -> None:
    for path in paths:
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())
        log.debug(f".env geladen: {path}")


def listen(stt: WhisperEngine) -> str | None:
    ui.listening()
    log.info("Mikrofon aktiviert")
    try:
        transcript = stt.transcribe_microphone()
        ui.thinking()
        log.info(f"Transkript: {transcript}")
        return transcript or None
    except Exception as e:
        log.error(f"Mikrofon-Fehler: {e}")
        ui.error_msg("Mikrofon nicht erreichbar. Details: logs/zuki.log")
        return None



def _check_vision() -> bool:
    """True wenn mss importierbar ist (Vision einsatzbereit)."""
    try:
        import mss  # noqa: F401
        return True
    except ImportError:
        return False


def display_startup_dashboard(llm, api_mgr, stt, tts, history, profile, tenant_mgr=None) -> None:
    """
    Kompaktes Startup-Dashboard — zeigt Profil, Tenant, System-Status
    und Befehlsreferenz in einer Box.
    """
    tenant_name = tenant_mgr.current() if tenant_mgr else "self"
    ui.print_dashboard(
        simulation    = llm.simulation,
        api_provider  = api_mgr.provider_label,
        name          = profile._data.get("name", ""),
        level         = profile.level,
        memory_count  = history.count,
        whisper_mode  = stt.mode_label,
        tts_voice     = tts.get_status().get("voice", ""),
        vision_ok     = _check_vision(),
        tenant_name   = tenant_name,
    )
    log.info(
        f"Dashboard: {llm.system_prompt_info}  |  "
        f"API-Provider: {api_mgr.provider_label}  |  "
        f"Gedächtnis: {history.count}  |  "
        f"Tenant: {tenant_name}"
    )


def shutdown(stt: WhisperEngine, tts: TTSEngine) -> None:
    log.info("Graceful shutdown eingeleitet")
    try:
        ui.speaking()
        tts.speak("Auf Wiedersehen, Sir.")
    except Exception:
        pass
    stt.shutdown()
    tts.shutdown()
    log.info("Shutdown abgeschlossen")
    ui.system_msg("Zuki offline. Auf Wiedersehen, Sir.")


# ── Main loop ──────────────────────────────────────────────────────────────────

def run():
    global ui
    load_env(ENV_FILES)
    ui = _get_renderer()

    # ── Single-instance guard — prevents duplicate startup ────────────────────
    if not _guard_acquire():
        ui.error_msg(
            "Zuki läuft bereits in einem anderen Fenster.\n"
            "  Bitte das bestehende Fenster nutzen oder zuerst mit 'exit' beenden."
        )
        return
    atexit.register(_guard_release)

    # ── Session state: detect unclean exit ────────────────────────────────────
    # Registered first → called last (LIFO) → after shutdown()
    state = SessionState()
    atexit.register(state.clear)

    _restore_answer = False
    _prev_state: dict | None = None
    if state.is_unclean():
        _prev_state = state.load()
        if _prev_state:
            ui.system_msg(
                f"Letzte Session unsauber beendet "
                f"({_prev_state.get('timestamp', '')[:19]}):\n"
                f"      Modus:       {'Broker' if _prev_state.get('broker_mode') else 'Standard'}\n"
                f"      Cloud-Saves: {_prev_state.get('cloud_save_count', 0)}\n"
                f"      Auto-Save:   {'an' if _prev_state.get('cloud_auto_save') else 'aus'}\n"
                f"    Wiederherstellen? (ja / nein)"
            )
            answer = ui.user_prompt()
            if answer.strip().lower() in {"ja", "j", "yes", "y"}:
                _restore_answer = True
                log.info(f"[SESSION-RESTORE] Wiederherstellung bestätigt | ts={_prev_state.get('timestamp')}")
            else:
                state.clear()
                _prev_state = None
                log.info("[SESSION-CLEAR] Wiederherstellung abgelehnt — State verworfen")

    # ── Tenant manager — initialize early ─────────────────────────────────────
    tenant_mgr = get_tenant_manager()
    _migration_needed = not tenant_mgr.migration_done()

    # ── Local file migration (profile rename, before UserProfile init) ─────────
    if _migration_needed:
        import shutil as _shutil
        _old_profile = os.path.join(ROOT, "memory", "user_profile.txt")
        _new_profile = os.path.join(ROOT, "memory", "user_profile_self.txt")
        if os.path.exists(_old_profile) and not os.path.exists(_new_profile):
            try:
                _shutil.copy2(_old_profile, _new_profile)
                log.info("[TENANT-MIGRATION] user_profile.txt → user_profile_self.txt")
            except OSError as _e:
                log.warning(f"[TENANT-MIGRATION] Profil-Kopie fehlgeschlagen: {_e}")

    log.info("Zuki startet")

    try:
        llm = LLMManager()
    except Exception as e:
        log.error(f"LLMManager Fehler: {e}")
        ui.error_msg("Sprachmodell nicht verfügbar. Details: logs/zuki.log")
        sys.exit(1)

    try:
        stt = WhisperEngine(language="de")
    except Exception as e:
        log.error(f"WhisperEngine Fehler: {e}")
        ui.error_msg("Spracherkennung nicht verfügbar. Details: logs/zuki.log")
        sys.exit(1)

    try:
        tts = TTSEngine()
    except Exception as e:
        log.error(f"TTSEngine Fehler: {e}")
        ui.error_msg("Sprachausgabe nicht verfügbar. Details: logs/zuki.log")
        sys.exit(1)

    atexit.register(shutdown, stt, tts)
    history  = HistoryManager()
    profile  = UserProfile()
    api_mgr  = APIManager()

    # ── Initialize vision system (clean up stale frames) ──────────────────────
    vision.init()   # loggt intern — kein Terminal-Output

    # ── Auto-Backup-Thread ─────────────────────────────────────────────────────
    _auto_backup = AutoBackup()
    _auto_backup.start()

    # ── GitHub-Backup-Thread ───────────────────────────────────────────────────
    _github_backup = GitHubBackup()
    _github_backup.start()

    # ── Skill-Discovery ────────────────────────────────────────────────────────
    skill_registry.discover_skills()
    log.info(f"Skills geladen: {skill_registry.list_names()}")

    # ── Router-Agent ───────────────────────────────────────────────────────────
    router = RouterAgent(api_mgr)

    # ── Startup dashboard — clear screen for clean display ────────────────────
    os.system("cls" if sys.platform == "win32" else "clear")
    display_startup_dashboard(llm, api_mgr, stt, tts, history, profile, tenant_mgr)

    last_response = ""      # last Zuki response — for manual / auto save

    # ── Cloud memory — independent of LLM simulation mode ────────────────────
    cloud = CloudMemory()
    if cloud.enabled:
        ok, msg = cloud.ping()
        if ok:
            ui.system_msg(f"[☁] Cloud-Gedächtnis aktiv  ·  {msg}")
        else:
            ui.error_msg(f"[☁] Cloud-Verbindung fehlgeschlagen: {msg}")

    # ── Connect profile to cloud (for async bio sync) ─────────────────────────
    profile.set_cloud(cloud)

    # ── Cloud migration (one-time, after cloud init) ───────────────────────────
    if _migration_needed:
        log.info("[TENANT-MIGRATION] Starte Cloud-Migration...")
        if cloud.enabled:
            _mig_status = cloud.migrate_to_tenant("self")
            log.info(f"[TENANT-MIGRATION] Cloud-Ergebnis: {_mig_status}")
        tenant_mgr.mark_migration_done()
        ui.system_msg("[TENANT-MIGRATION] Abgeschlossen — Daten auf Tenant-Struktur umgestellt.")

    # ── Bio recovery: local profile empty → offer restore from cloud ──────────
    if profile.is_empty and cloud.enabled:
        log.info("[BIO-CHECK] Lokales Profil leer — prüfe Cloud-Backup")
        bio = cloud.get_latest_bio()
        if bio:
            ui.system_msg(
                f"Lokales Profil leer.\n"
                f"      Cloud-Backup vorhanden vom {bio['saved_at'][:10]}.\n"
                f"    Wiederherstellen? (ja / nein)"
            )
            answer = ui.user_prompt()
            if answer.strip().lower() in {"ja", "j", "yes", "y"}:
                profile._data = bio["data"]
                profile._save()
                log.info(f"[BIO-RESTORE] Profil aus Cloud wiederhergestellt | {bio['saved_at'][:10]}")
                ui.system_msg(f"[Profil] Wiederhergestellt: {profile.get_summary()}")
            else:
                log.info("[BIO-RESTORE] Wiederherstellung abgelehnt")

    # ── Session state helper (closure over local variables) ───────────────────
    def _save_state() -> None:
        state.save({
            "cloud_auto_save":  cloud.auto_save,
            "cloud_session_id": cloud._session_id,
            "cloud_save_count": cloud.save_count,
            "last_response":    last_response[:500],
        })

    # ── Context builder for skill dispatch ────────────────────────────────────
    def _make_context(user_input: str, cmd: str) -> dict:
        return {
            "user_input": user_input,
            "cmd":        cmd,
            "api_mgr":   api_mgr,
            "llm":       llm,
            "profile":   profile,
            "tts":       tts,
            "stt":       stt,
        }

    # ── UI bridge command handler — routes React terminal commands ────────────
    # Mirrors the three-stage dispatch of the main loop:
    #   1. Exact trigger match (0 LLM tokens)
    #   2. Router agent (LLM routing, skipped in simulation mode)
    #   3. LLM fallback (full conversation context)
    def _ui_command_handler(text: str, workspace: str, _tenant: str) -> None:
        _cmd = text.strip().lower()

        # Interactive prompt intercept — if a skill (e.g. interview) is blocking on
        # user_prompt(), feed the answer directly instead of routing through stages.
        if callable(getattr(ui, 'feed_input', None)) and ui.feed_input(text):
            return

        # Stage 1: exact trigger match
        _skill = skill_registry.get_skill_for(_cmd)
        if _skill:
            _resp = _skill.handle(_make_context(text, _cmd))
            if _resp:
                ui_bridge.emit_response(_resp, workspace=workspace)
            return

        # Stage 2: router agent
        _routable = skill_registry.get_all_descriptions()
        if _routable and not api_mgr.simulation:
            try:
                _chosen = router.route(text, _routable)
                if _chosen:
                    _responses = []
                    for _sname in _chosen:
                        _first_trigger = next(
                            (s["triggers"][0] for s in _routable if s["name"] == _sname),
                            _sname,
                        )
                        _sk = skill_registry.get_skill_for(_first_trigger)
                        if _sk is None:
                            _sk = next(
                                (inst for inst in set(skill_registry._registry.values())
                                 if inst.name == _sname),
                                None,
                            )
                        if _sk:
                            _r = _sk.handle(_make_context(text, _cmd))
                            if _r:
                                _responses.append(_r)
                    if _responses:
                        ui_bridge.emit_response("\n\n".join(_responses), workspace=workspace)
                        return
            except Exception as _e:
                log.warning(f"[UI-CMD] Router-Fehler: {_e}")

        # Stage 3: LLM fallback
        try:
            _ctx = history.get_context()
            _summary = profile.get_summary()
            if _summary:
                _ctx = [
                    {"role": "user",      "content": f"[Nutzerprofil] {_summary}"},
                    {"role": "assistant", "content": "Verstanden, ich berücksichtige Ihr Profil."},
                ] + _ctx
            _ctx.append({"role": "user", "content": text})
            _resp = llm.chat(_ctx)
            if _resp:
                ui_bridge.emit_response(_resp, workspace=workspace)
        except Exception as _e:
            log.error(f"[UI-CMD] LLM-Fehler: {_e}")
            ui_bridge.emit_response(
                "Fehler bei der Verarbeitung — Details: logs/zuki.log",
                workspace=workspace,
            )

    # ── Start WebSocket bridge ────────────────────────────────────────────────
    ui_bridge.start(command_handler=_ui_command_handler)

    # ── n8n Webhook Receiver (disabled by default — set N8N_WEBHOOK_ENABLED=true) ──
    if os.getenv("N8N_WEBHOOK_ENABLED", "false").lower() == "true":
        from workspaces.broker import webhook_receiver as _wh_recv
        _wh_port = int(os.getenv("N8N_WEBHOOK_PORT", "8766"))

        def _n8n_handler(msg_type: str, payload: dict) -> None:
            _routable = skill_registry.get_all_descriptions()
            _chosen   = router.route(f"n8n:{msg_type}", _routable)
            for _sname in _chosen:
                _sk = skill_registry.get_skill_for(
                    next(
                        (s["triggers"][0] for s in _routable if s["name"] == _sname),
                        _sname,
                    )
                )
                if _sk is not None:
                    _sk.handle(_make_context(f"n8n:{msg_type}", msg_type))

        _wh_recv.start(_wh_port, _n8n_handler)
        log.info("[MAIN] n8n webhook active on port %d", _wh_port)

    # ── Apply session recovery ─────────────────────────────────────────────────
    if _restore_answer and _prev_state:
        if _prev_state.get("cloud_auto_save") and cloud.enabled:
            cloud.enable_auto_save()
            log.info("[SESSION-RESTORE] Auto-Save wiederhergestellt")
        log.info(f"[SESSION-RESTORE] Session wiederhergestellt | {_prev_state.get('timestamp', '')}")
        ui.system_msg("[SESSION] Letzte Session wiederhergestellt.")

    # Web mode: the bridge handles all input — no stdin loop needed.
    # Main thread sleeps so daemon threads stay alive.
    if callable(getattr(ui, 'is_waiting_for_input', None)):
        import threading as _threading
        log.info("[MAIN] Web-Modus — Hauptschleife deaktiviert, Bridge übernimmt.")
        _threading.Event().wait()
        return

    while True:
        try:
            user_input = ui.user_prompt()
            cmd = user_input.strip().lower()

            if not user_input:
                continue

            # ── Exit ───────────────────────────────────────────────────────────
            if cmd in EXIT_TRIGGERS:
                break

            # ── Voice ──────────────────────────────────────────────────────────
            if cmd in LISTEN_TRIGGERS:
                transcript = listen(stt)
                if not transcript:
                    ui.speak_zuki("Ich habe leider nichts verstanden.")
                    continue
                ui.voice_echo(transcript)
                user_input = transcript

            # ── Vision ─────────────────────────────────────────────────────────
            if cmd in VISION_TRIGGERS:
                # Step 1: capture screenshot
                ui.thinking()
                try:
                    frame_path = vision.capture_active_screen()
                except RuntimeError as e:
                    ui.error_msg(f"Vision nicht verfügbar: {e}")
                    continue
                except OSError as e:
                    log.error(f"Vision Capture Fehler: {e}")
                    ui.error_msg("Screenshot fehlgeschlagen. Details: logs/zuki.log")
                    continue

                if api_mgr.simulation:
                    # SIM: no real API key → placeholder response
                    ui.speak_zuki(
                        f"[VISION] Screenshot erstellt: {frame_path}\n"
                        f"(SIM: Für echte Bildanalyse GEMINI_API_KEY in .env setzen.)"
                    )
                    continue

                # Step 2: ask the user what to analyze
                ui.speak_zuki(
                    f"Screenshot erstellt  ({frame_path})\n"
                    f"Was soll ich auf diesem Bild analysieren?"
                )
                vision_question = ui.user_prompt()

                if not vision_question or vision_question.strip().lower() in EXIT_TRIGGERS:
                    continue

                # Step 3: send image + question to Gemini / Claude / GPT-4o
                ui.system_msg(
                    f"[VISION] Analysiere mit {api_mgr.provider_label}..."
                )
                ui.thinking()
                response = api_mgr.chat_vision(
                    image_path = frame_path,
                    question   = vision_question,
                    system     = llm.system_prompt,
                    max_tokens = 1024,
                )

                # Record vision interaction in history (compact)
                history.append("user",      f"[Vision-Frage] {vision_question}")
                history.append("assistant", response)
                last_response = response
                _save_state()

                ui.speak_zuki(response)
                ui.speaking()
                tts.speak(response)
                continue

            # ── Cloud-Test ─────────────────────────────────────────────────────
            if cmd in CLOUD_TEST:
                ui.system_msg("[☁] Verbindungstest läuft...")
                ok, msg = cloud.ping()
                if ok:
                    ui.system_msg(f"[☁] {msg}")
                else:
                    ui.error_msg(
                        f"[☁] Verbindung fehlgeschlagen: {msg}\n"
                        f"    → CLOUD_MEMORY_URL und CLOUD_MEMORY_TOKEN in .env prüfen"
                    )
                continue

            # ── Cloud-Speichern ────────────────────────────────────────────────
            # NOTE: LLM simulation mode has NO effect on cloud saves.
            if cmd in SAVE_TRIGGERS:
                if not last_response:
                    ui.speak_zuki("Noch keine Antwort zum Speichern vorhanden.")
                else:
                    ui.system_msg("[☁] Speichere in Cloud...")
                    status = cloud.save(last_response, source="manual")
                    if status.startswith("ok"):
                        ui.system_msg(
                            f"[☁] Gespeichert  ·  {status}  "
                            f"·  #{cloud.save_count}  ·  Session {cloud._session_id}"
                        )
                    else:
                        ui.error_msg(f"[☁] Speichern fehlgeschlagen: {status}")
                    if cloud.should_ask_auto():
                        cloud.mark_prompted()
                        ui.speak_zuki(
                            f"Du hast nun {cloud.save_count}× manuell gespeichert.\n"
                            f"Soll ich für diese Sitzung alle wichtigen Kernpunkte\n"
                            f"direkt in deinem Cloud-Gedächtnis speichern? (ja / nein)"
                        )
                        answer = ui.user_prompt()
                        if answer.strip().lower() in {"ja", "yes", "j", "y"}:
                            cloud.enable_auto_save()
                            ui.system_msg("[☁] Auto-Save für diese Sitzung aktiviert.")
                        else:
                            ui.system_msg("[☁] Verstanden — weiterhin manuell mit 'save'.")
                        _save_state()
                continue

            # ── Tenant commands ────────────────────────────────────────────────
            if cmd == TENANT_CMD or cmd.startswith(TENANT_CMD + " "):
                _parts = cmd.split()

                if len(_parts) == 1:
                    # tenant → show current + all known tenants
                    _known = tenant_mgr.list_known()
                    ui.system_msg(
                        f"[TENANT] Aktiver Workspace: {tenant_mgr.current()}"
                        f"  ·  Bekannte: {', '.join(_known)}"
                    )

                elif _parts[1] == "list":
                    _known = tenant_mgr.list_known()
                    ui.system_msg(f"[TENANT] Bekannte Tenants: {', '.join(_known)}")

                elif _parts[1] == "switch" and len(_parts) > 2:
                    _name = _parts[2]
                    if tenant_mgr.switch(_name):
                        profile.reload()
                        log.info(f"[TENANT] Gewechselt zu: {_name}")
                        ui.system_msg(
                            f"[TENANT] Workspace gewechselt zu: {_name}  "
                            f"·  Profil neu geladen."
                        )
                    else:
                        ui.error_msg(
                            f"Tenant '{_name}' unbekannt.\n"
                            f"    Erst anlegen mit: tenant create {_name}"
                        )

                elif _parts[1] == "create" and len(_parts) > 2:
                    _name = _parts[2]
                    if tenant_mgr.create(_name):
                        ui.system_msg(
                            f"[TENANT] Tenant '{_name}' erstellt  "
                            f"·  require_dsgvo=True (Business-Default)"
                        )
                    else:
                        ui.error_msg(
                            f"Tenant '{_name}' existiert bereits oder Name ungültig."
                        )

                elif _parts[1] == "delete" and len(_parts) > 2:
                    _name = _parts[2]
                    if _name == "self":
                        ui.error_msg("[TENANT] 'self' kann nicht gelöscht werden.")
                    elif _name == tenant_mgr.current():
                        ui.error_msg(
                            f"[TENANT] Aktiven Tenant '{_name}' nicht löschbar — "
                            f"zuerst wechseln: tenant switch self"
                        )
                    else:
                        ui.speak_zuki(
                            f"Tenant '{_name}' wirklich löschen?\n"
                            f"Profil-Daten werden entfernt. (ja / nein)"
                        )
                        _ans = ui.user_prompt()
                        if _ans.strip().lower() in {"ja", "j", "yes", "y"}:
                            # Lokale Profildatei löschen
                            import shutil as _shutil
                            _pfile = os.path.join(
                                ROOT, "memory", f"user_profile_{_name}.txt"
                            )
                            if os.path.exists(_pfile):
                                try:
                                    os.remove(_pfile)
                                except OSError:
                                    pass
                            if tenant_mgr.delete(_name):
                                ui.system_msg(f"[TENANT] Tenant '{_name}' gelöscht.")
                            else:
                                ui.error_msg(f"Löschen fehlgeschlagen für '{_name}'.")
                        else:
                            ui.system_msg("[TENANT] Abgebrochen.")

                else:
                    ui.error_msg(
                        "Tenant-Befehle:\n"
                        "    tenant                 → Aktiver Workspace\n"
                        "    tenant list            → Alle bekannten\n"
                        "    tenant switch <name>   → Wechseln\n"
                        "    tenant create <name>   → Neu anlegen\n"
                        "    tenant delete <name>   → Löschen (mit Bestätigung)"
                    )
                continue

            # ── System-Befehle ─────────────────────────────────────────────────
            if cmd == "system backup":
                ui.system_msg("Erstelle Snapshot...")
                snap = create_snapshot()
                if snap["error"]:
                    ui.error_msg(f"Backup fehlgeschlagen: {snap['error']}")
                else:
                    response = (
                        f"[BACKUP] Snapshot erstellt.\n"
                        f"  Pfad    : {snap['path']}\n"
                        f"  Dateien : {snap['files']}\n"
                        f"  Größe   : {snap['size_kb']} KB\n\n"
                        f"Vorhandene Snapshots:\n{format_snapshot_list()}"
                    )
                    ui.speak_zuki(response)
                continue

            # ── GitHub-Backup-Befehle ──────────────────────────────────────────
            if cmd == "system github init":
                ui.system_msg("[GitHub] Initialisiere Repo...")
                result = _github_backup.cmd_init()
                ui.speak_zuki(result)
                continue

            if cmd == "system github commit":
                ui.system_msg("[GitHub] Commit + Push...")
                result = _github_backup.cmd_commit()
                ui.speak_zuki(result)
                continue

            if cmd == "system github status":
                result = _github_backup.cmd_status()
                ui.speak_zuki(result)
                continue

            # ── System-Test ────────────────────────────────────────────────────
            if cmd == "system test" or cmd.startswith("system test "):
                parts   = cmd.split()
                subname = parts[2] if len(parts) > 2 else None
                tester  = SystemTest(
                    cloud                = cloud,
                    api_mgr              = api_mgr,
                    stt                  = stt,
                    tts                  = tts,
                    history              = history,
                    profile              = profile,
                    skill_registry_module = skill_registry,
                    session_state        = state,
                    auto_backup          = _auto_backup,
                    github_backup        = _github_backup,
                    tenant_mgr           = tenant_mgr,
                    router_agent         = router,
                )
                if subname is None:
                    results = tester.run_all()
                    ui.print_system_test(results)
                elif subname in tester.available_names():
                    result = tester.run_one(subname)
                    ui.print_system_test([result])
                else:
                    available = "  ".join(tester.available_names())
                    ui.error_msg(
                        f"Unbekannter Test: '{subname}'\n"
                        f"    Verfügbar: {available}"
                    )
                continue

            # ── Cleanup-Befehle ────────────────────────────────────────────────
            if cmd == "cleanup" or cmd.startswith("cleanup "):
                _parts   = cmd.split()
                _subname = _parts[1] if len(_parts) > 1 else None
                _cleaner = CleanupManager()
                _results = {}

                _current_tenant = tenant_mgr.current() if tenant_mgr else "self"

                if _subname is None:
                    # Hilfe-Übersicht
                    ui.speak_zuki(
                        "Cleanup-Befehle:\n"
                        f"  (Aktiver Tenant: {_current_tenant})\n\n"
                        "  cleanup vision          → Screenshots löschen\n"
                        "  cleanup chats           → Chat-History dieses Tenants löschen\n"
                        "  cleanup old             → Alte Backup-Snapshots löschen (behält 3)\n"
                        "  cleanup cloud           → Cloud-Memories dieses Tenants bereinigen\n"
                        "  cleanup all             → vision + chats + old (mit Bestätigung)\n\n"
                        "  cleanup kunde           → Alle Kunden-Dokumente auflisten\n"
                        "  cleanup kunde <Name>    → Dokumente für diesen Kunden anzeigen\n"
                        "  cleanup kunde <Name> !  → Dokumente für diesen Kunden löschen\n"
                        "  cleanup kunde all       → Alle Kunden-Dokumente löschen"
                    )
                    continue

                elif _subname == "vision":
                    _results["vision"] = _cleaner.cleanup_vision()

                elif _subname == "chats":
                    ui.speak_zuki(
                        f"Chat-History für Tenant '{_current_tenant}' löschen?\n"
                        f"Andere Tenants bleiben unberührt. (ja / nein)"
                    )
                    _ans = ui.user_prompt()
                    if _ans.strip().lower() in {"ja", "j", "yes", "y"}:
                        _results["chats"] = _cleaner.cleanup_chats(
                            history_mgr=history, tenant_id=_current_tenant
                        )
                    else:
                        ui.system_msg("[Cleanup] Abgebrochen.")
                        continue

                elif _subname == "old":
                    _results["old backups"] = _cleaner.cleanup_old_backups()

                elif _subname == "cloud":
                    if not cloud.enabled:
                        ui.error_msg(
                            "Cloud nicht konfiguriert — CLOUD_MEMORY_URL + TOKEN in .env prüfen."
                        )
                        continue
                    ui.speak_zuki(
                        "Cloud-Memories für diesen Tenant bereinigen?\n"
                        "Geschützte Einträge (Bio, system) bleiben erhalten. (ja / nein)"
                    )
                    _ans = ui.user_prompt()
                    if _ans.strip().lower() in {"ja", "j", "yes", "y"}:
                        ui.system_msg("[Cleanup] Cloud-Bereinigung läuft...")
                        _results["cloud"] = cloud.cleanup_cloud()
                    else:
                        ui.system_msg("[Cleanup] Abgebrochen.")
                        continue

                elif _subname == "all":
                    ui.speak_zuki(
                        "Komplett-Cleanup: Screenshots, Chat-History und alte Backups löschen?\n"
                        "Cloud-Daten werden NICHT automatisch bereinigt. (ja / nein)"
                    )
                    _ans = ui.user_prompt()
                    if _ans.strip().lower() in {"ja", "j", "yes", "y"}:
                        _results["vision"]      = _cleaner.cleanup_vision()
                        _results["chats"]       = _cleaner.cleanup_chats(
                            history_mgr=history, tenant_id=_current_tenant
                        )
                        _results["old backups"] = _cleaner.cleanup_old_backups()
                    else:
                        ui.system_msg("[Cleanup] Abgebrochen.")
                        continue

                elif _subname == "kunde":
                    # cleanup kunde | cleanup kunde <Name> | cleanup kunde <Name> ! | cleanup kunde all
                    _kunde_parts = cmd.split(None, 2)   # ["cleanup", "kunde", rest]
                    _kunde_arg   = _kunde_parts[2].strip() if len(_kunde_parts) > 2 else ""
                    _delete_flag = _kunde_arg.endswith("!")
                    _kunde_name  = _kunde_arg.rstrip("!").strip()
                    _delete_all  = _kunde_name.lower() == "all"

                    if _delete_all:
                        # Alle Kunden-Dokumente löschen
                        _files = _cleaner.list_client_files()
                        if not _files:
                            ui.system_msg("[Cleanup] Keine Kunden-Dokumente vorhanden.")
                            continue
                        _list_str = "\n".join(f"  • {f['filename']} ({f['size_kb']} KB)" for f in _files)
                        ui.speak_zuki(
                            f"Alle {len(_files)} Kunden-Dokument(e) löschen?\n"
                            f"{_list_str}\n\n(ja / nein)"
                        )
                        _ans = ui.user_prompt()
                        if _ans.strip().lower() in {"ja", "j", "yes", "y"}:
                            _results["kunde"] = _cleaner.cleanup_client()
                        else:
                            ui.system_msg("[Cleanup] Abgebrochen.")
                            continue

                    elif _delete_flag and _kunde_name:
                        # cleanup kunde <Name> ! → sofort löschen
                        _files = _cleaner.list_client_files(_kunde_name)
                        if not _files:
                            ui.system_msg(f"[Cleanup] Keine Dokumente für '{_kunde_name}' gefunden.")
                            continue
                        _list_str = "\n".join(f"  • {f['filename']} ({f['size_kb']} KB)" for f in _files)
                        ui.speak_zuki(
                            f"{len(_files)} Dokument(e) für '{_kunde_name}' löschen?\n"
                            f"{_list_str}\n\n(ja / nein)"
                        )
                        _ans = ui.user_prompt()
                        if _ans.strip().lower() in {"ja", "j", "yes", "y"}:
                            _results["kunde"] = _cleaner.cleanup_client(_kunde_name)
                        else:
                            ui.system_msg("[Cleanup] Abgebrochen.")
                            continue

                    else:
                        # Nur auflisten (cleanup kunde oder cleanup kunde <Name>)
                        _files = _cleaner.list_client_files(_kunde_name)
                        if not _files:
                            _hint = f" für '{_kunde_name}'" if _kunde_name else ""
                            ui.system_msg(f"[Cleanup] Keine Kunden-Dokumente{_hint} vorhanden.")
                            continue
                        _lines = [f"Kunden-Dokumente{' für ' + _kunde_name if _kunde_name else ''} ({len(_files)}):"]
                        for f in _files:
                            _lines.append(f"  • {f['filename']} ({f['size_kb']} KB)")
                        _lines.append(f"\nLöschen: cleanup kunde {_kunde_name or '<Name>'} !")
                        ui.speak_zuki("\n".join(_lines))
                        continue

                else:
                    ui.error_msg(
                        f"Unbekannter Cleanup-Befehl: '{_subname}'\n"
                        "    Verfügbar: vision  chats  old  cloud  kunde  all"
                    )
                    continue

                if _results:
                    ui.print_cleanup_result(_results)
                    _save_state()
                continue

            # ── Skill-Dispatch (Schnellpfad: exakter Trigger-Match) ───────────
            skill = skill_registry.get_skill_for(cmd)
            if skill:
                if not _tenant_guard(skill, tenant_mgr):
                    continue
                history.append("user", user_input)
                ui.thinking()
                log.info(f"[SKILL-INVOKE] {skill.name} | cmd={cmd[:60]}")
                response = skill.handle(_make_context(user_input, cmd))
                if response is not None:
                    history.append("assistant", response)
                    last_response = response
                    _save_state()
                    if cloud.auto_save:
                        cloud.save(response, source="auto")
                    cloud.save_skill_conversation(skill.name, response)
                    ui.speak_zuki(response)
                    ui.speaking()
                    tts.speak(response)
                continue

            # ── Router agent: no trigger match → LLM decides ──────────────────
            _routable = skill_registry.get_all_descriptions()
            if _routable and not api_mgr.simulation:
                ui.thinking()
                _chosen_names = router.route(user_input, _routable)
                if _chosen_names:
                    ui.print_router_decision(_chosen_names, user_input)
                    history.append("user", user_input)
                    _responses = []
                    for _sname in _chosen_names:
                        _sk = skill_registry.get_skill_for(
                            next((s["triggers"][0] for s in _routable if s["name"] == _sname), _sname)
                        )
                        if _sk is None:
                            # Trigger-map lookup as fallback
                            from workspaces import registry as _sr
                            _sk = next(
                                (inst for inst in set(_sr._registry.values()) if inst.name == _sname),
                                None,
                            )
                        if _sk is None:
                            continue
                        if not _tenant_guard(_sk, tenant_mgr):
                            continue
                        log.info(f"[ROUTER-INVOKE] {_sname} | input={user_input[:60]}")
                        _r = _sk.handle(_make_context(user_input, cmd))
                        if _r is not None:
                            _responses.append(_r)
                            cloud.save_skill_conversation(_sname, _r)

                    if _responses:
                        response = "\n\n".join(_responses)
                        history.append("assistant", response)
                        last_response = response
                        _save_state()
                        if cloud.auto_save:
                            cloud.save(response, source="auto")
                        ui.speak_zuki(response)
                        ui.speaking()
                        tts.speak(response)
                        continue
                    # Router selected skills but all returned None → fall through to LLM

            # ── Normale Antwort ────────────────────────────────────────────────
            history.append("user", user_input)

            # Learning: extract profile facts from every user input
            learned = profile.extract_and_update(user_input)
            for fact in learned:
                ui.system_msg(f"[MEM] Gelernt: {fact}")
                log.info(f"Profil-Update: {fact}")

            ui.thinking()

            # Inject profile as context prefix (only when data is present)
            context = history.get_context()
            profile_summary = profile.get_summary()
            if profile_summary:
                context = [
                    {"role": "user", "content": f"[Nutzerprofil] {profile_summary}"},
                    {"role": "assistant", "content": "Verstanden, ich berücksichtige Ihr Profil."},
                ] + context

            try:
                response = llm.chat(context)
            except Exception as e:
                log.error(f"LLM-Fehler: {e}")
                ui.speak_zuki("Entschuldigung — keine Antwort möglich. Details: logs/zuki.log")
                continue

            history.append("assistant", response)
            last_response = response
            _save_state()
            if cloud.auto_save:
                cloud.save(response, source="auto")
            ui.speak_zuki(response)
            ui.speaking()
            tts.speak(response)

        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    run()
