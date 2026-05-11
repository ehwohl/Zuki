import sys
import os
import warnings
import logging
import atexit
import threading
import time

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

# ui wird in run() nach load_env() initialisiert (damit ZUKI_UI aus .env wirkt).
# Modul-Level-Fallback damit Hilfsfunktionen (listen, shutdown …) immer
# auf ein gültiges Objekt treffen, auch wenn sie vor run() aufgerufen werden.
ui: UIRenderer = _get_renderer()

ENV_FILES = [
    os.path.join(ROOT, ".env"),
    os.path.join(ROOT, "persona", "config", ".env"),
]

from core.llm_manager import LLMManager
from core.api_manager import APIManager
from core.speech_to_text.whisper_engine import WhisperEngine
from core.text_to_speech.tts_engine import TTSEngine
from core.news_manager import NewsManager
from core.calendar_manager import get_todays_events
from memory.history_manager import HistoryManager
from memory.user_profile import UserProfile
from skills.broker.scraper import fetch_news
from skills import registry as skill_registry
from core import vision_manager as vision
from tools.backup_manager import create_snapshot, format_snapshot_list, AutoBackup
from tools.cloud_memory import CloudMemory
from tools.github_backup import GitHubBackup
from tools.instance_guard import acquire as _guard_acquire, release as _guard_release
from tools.session_state import SessionState
from tools.system_test import SystemTest
from core.tenant import get_tenant_manager

LISTEN_TRIGGERS  = {"hör zu", "hoer zu"}
EXIT_TRIGGERS    = {"exit", "quit", "beenden"}
BROKER_TRIGGERS  = {"broker"}
BROKER_EXIT      = {"main", "exit broker"}
VISION_TRIGGERS  = {"vision", "screenshot", "schau hin", "was siehst du"}
SAVE_TRIGGERS    = {"save", "speichern", "merken"}
CLOUD_TEST       = {"cloud test", "cloud status", "cloud ping"}
TENANT_CMD       = "tenant"

SCRAPER_INTERVAL = int(os.getenv("SCRAPER_INTERVAL", "600"))  # default 10 min


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


def _scraper_loop(simulation: bool, stop_event: threading.Event) -> None:
    """
    Hintergrund-Thread: prüft alle SCRAPER_INTERVAL Sekunden ob neue News
    geholt werden sollen.

    SIM  → nur Log-Eintrag (kein Terminal-Output)
    LIVE → fetch_news() aufrufen
    """
    log.info(f"Scraper-Thread gestartet (Intervall: {SCRAPER_INTERVAL}s)")
    while not stop_event.wait(timeout=SCRAPER_INTERVAL):
        if simulation:
            log.debug("[DEBUG] Scraper-Check aktiv — SIM-Modus, kein echter Fetch")
        else:
            log.info("[SCRAPER] Starte automatischen News-Fetch...")
            try:
                count = fetch_news()
                log.info(f"[SCRAPER] {count} neue Artikel abgerufen")
            except Exception as e:
                log.warning(f"[SCRAPER] Fehler beim Fetch: {e}")
    log.info("Scraper-Thread beendet")


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
        tts_voice     = tts._voice_name,
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


# ── Hauptschleife ──────────────────────────────────────────────────────────────

def run():
    global ui
    load_env(ENV_FILES)
    ui = _get_renderer()

    # ── Single-Instance-Guard — verhindert Mehrfachstart ─────────────────────
    if not _guard_acquire():
        ui.error_msg(
            "Zuki läuft bereits in einem anderen Fenster.\n"
            "  Bitte das bestehende Fenster nutzen oder zuerst mit 'exit' beenden."
        )
        return
    atexit.register(_guard_release)

    # ── Session-State: unclean-Exit erkennen ──────────────────────────────────
    # Zuerst registrieren → als letztes aufgerufen (LIFO) → nach shutdown()
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

    # ── Tenant-Manager — früh initialisieren ──────────────────────────────────
    tenant_mgr = get_tenant_manager()
    _migration_needed = not tenant_mgr.migration_done()

    # ── Lokale Datei-Migration (Profil-Umbenennung, vor UserProfile-Init) ─────
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
    news     = NewsManager()
    api_mgr  = APIManager()

    # ── Vision-System initialisieren (Cleanup alter Frames) ───────────────────
    vision.init()   # loggt intern — kein Terminal-Output

    # ── Scraper-Hintergrund-Thread ─────────────────────────────────────────────
    _stop_scraper = threading.Event()
    _scraper_thread = threading.Thread(
        target=_scraper_loop,
        args=(llm.simulation, _stop_scraper),
        daemon=True,
        name="scraper-bg",
    )
    _scraper_thread.start()
    atexit.register(_stop_scraper.set)

    # ── Auto-Backup-Thread ─────────────────────────────────────────────────────
    _auto_backup = AutoBackup()
    _auto_backup.start()

    # ── GitHub-Backup-Thread ───────────────────────────────────────────────────
    _github_backup = GitHubBackup()
    _github_backup.start()

    # ── Skill-Discovery ────────────────────────────────────────────────────────
    skill_registry.discover_skills()
    log.info(f"Skills geladen: {skill_registry.list_names()}")

    # ── Startup-Dashboard — Screen clearen für saubere Anzeige ───────────────
    os.system("cls" if sys.platform == "win32" else "clear")
    display_startup_dashboard(llm, api_mgr, stt, tts, history, profile, tenant_mgr)

    broker_mode   = False   # activated by 'broker' command
    last_response = ""      # letzte Zuki-Antwort — für manuelles / Auto-Speichern

    # ── Cloud-Gedächtnis — unabhängig vom LLM-Simulations-Modus ─────────────
    cloud = CloudMemory()
    if cloud.enabled:
        ok, msg = cloud.ping()
        if ok:
            ui.system_msg(f"[☁] Cloud-Gedächtnis aktiv  ·  {msg}")
        else:
            ui.error_msg(f"[☁] Cloud-Verbindung fehlgeschlagen: {msg}")

    # ── Profil mit Cloud verbinden (für asynchronen Bio-Sync) ─────────────────
    profile.set_cloud(cloud)

    # ── Cloud-Migration (einmalig, nach Cloud-Init) ────────────────────────────
    if _migration_needed:
        log.info("[TENANT-MIGRATION] Starte Cloud-Migration...")
        if cloud.enabled:
            _mig_status = cloud.migrate_to_tenant("self")
            log.info(f"[TENANT-MIGRATION] Cloud-Ergebnis: {_mig_status}")
        tenant_mgr.mark_migration_done()
        ui.system_msg("[TENANT-MIGRATION] Abgeschlossen — Daten auf Tenant-Struktur umgestellt.")

    # ── Bio-Recovery: lokales Profil leer → aus Cloud anbieten ───────────────
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

    # ── Session-State-Helper (Closure über lokale Variablen) ─────────────────
    def _save_state() -> None:
        state.save({
            "broker_mode":      broker_mode,
            "cloud_auto_save":  cloud.auto_save,
            "cloud_session_id": cloud._session_id,
            "cloud_save_count": cloud.save_count,
            "last_response":    last_response[:500],
        })

    # ── Session-Recovery anwenden ─────────────────────────────────────────────
    if _restore_answer and _prev_state:
        if _prev_state.get("broker_mode"):
            broker_mode     = True
            news_count      = news.scan()
            calendar_events = get_todays_events()
            log.info("[SESSION-RESTORE] Broker-Modus wiederhergestellt")
        if _prev_state.get("cloud_auto_save") and cloud.enabled:
            cloud.enable_auto_save()
            log.info("[SESSION-RESTORE] Auto-Save wiederhergestellt")
        log.info(f"[SESSION-RESTORE] Session wiederhergestellt | {_prev_state.get('timestamp', '')}")
        ui.system_msg("[SESSION] Letzte Session wiederhergestellt.")

    while True:
        try:
            user_input = ui.user_prompt()
            cmd = user_input.strip().lower()

            if not user_input:
                continue

            # ── Exit ───────────────────────────────────────────────────────────
            if cmd in EXIT_TRIGGERS:
                break

            # ── Broker aktivieren ──────────────────────────────────────────────
            if cmd in BROKER_TRIGGERS:
                if not broker_mode:
                    news_count      = news.scan()
                    calendar_events = get_todays_events()
                    broker_mode     = True
                    log.info("Broker-Modus aktiviert")
                    ui.system_msg("Automatische News-Überwachung ist bereit.")
                    _save_state()
                ui.print_broker_status(
                    news_count      = news.count,
                    watchlist_hits  = news.watchlist_hits,
                    sentiment       = news.overall_sentiment,
                    calendar_events = calendar_events,
                )
                continue

            # ── Broker deaktivieren ────────────────────────────────────────────
            if cmd in BROKER_EXIT:
                broker_mode = False
                log.info("Broker-Modus deaktiviert")
                ui.print_broker_deactivated()
                _save_state()
                continue

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
                # Schritt 1: Screenshot aufnehmen
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
                    # SIM: kein echter API-Key → Platzhalter
                    ui.speak_zuki(
                        f"[VISION] Screenshot erstellt: {frame_path}\n"
                        f"(SIM: Für echte Bildanalyse GEMINI_API_KEY in .env setzen.)"
                    )
                    continue

                # Schritt 2: User fragen was analysiert werden soll
                ui.speak_zuki(
                    f"Screenshot erstellt  ({frame_path})\n"
                    f"Was soll ich auf diesem Bild analysieren?"
                )
                vision_question = ui.user_prompt()

                if not vision_question or vision_question.strip().lower() in EXIT_TRIGGERS:
                    continue

                # Schritt 3: Bild + Frage an Gemini / Claude / GPT-4o senden
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

                # Vision-Interaktion in History (kompakt)
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
            # HINWEIS: Der LLM-Simulations-Modus hat KEINEN Einfluss auf Cloud-Saves.
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

            # ── Tenant-Befehle ─────────────────────────────────────────────────
            if cmd == TENANT_CMD or cmd.startswith(TENANT_CMD + " "):
                _parts = cmd.split()

                if len(_parts) == 1:
                    # tenant → aktuellen + alle bekannten anzeigen
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

            # ── Skill-Dispatch ─────────────────────────────────────────────────
            skill = skill_registry.get_skill_for(cmd)
            if skill:
                history.append("user", user_input)
                ui.thinking()
                log.info(f"[SKILL-INVOKE] {skill.name} | cmd={cmd[:60]}")
                response = skill.handle({
                    "user_input": user_input,
                    "cmd":        cmd,
                    "api_mgr":   api_mgr,
                    "llm":       llm,
                    "profile":   profile,
                })
                if response is not None:
                    history.append("assistant", response)
                    last_response = response
                    _save_state()
                    if cloud.auto_save:
                        cloud.save(response, source="auto")
                    ui.speak_zuki(response)
                    ui.speaking()
                    tts.speak(response)
                continue

            # ── Report (nur im Broker-Modus) ───────────────────────────────────
            if news.is_report_trigger(user_input):
                if not broker_mode:
                    ui.speak_zuki("Broker-Modus nicht aktiv. Bitte zuerst 'broker' eingeben.")
                    continue
                history.append("user", user_input, source="broker")
                ui.thinking()
                if not news.has_news:
                    response = "Keine News für heute in der Inbox gefunden."
                elif llm.simulation:
                    response = news.build_sim_report()
                else:
                    ui.system_msg(f"[🗞] {news.count} Artikel werden ausgewertet...")
                    try:
                        response = llm.chat(
                            [{"role": "user", "content": news.build_prompt()}],
                            max_tokens=2048,
                        )
                    except Exception as e:
                        log.error(f"LLM News-Fehler: {e}")
                        response = "Auswertung fehlgeschlagen. Details: logs/zuki.log"
                history.append("assistant", response, source="broker")
                ui.speak_zuki(response)
                ui.speaking()
                tts.speak(response)
                continue

            # ── Normale Antwort ────────────────────────────────────────────────
            history.append("user", user_input)

            # Lern-Logik: Profil-Extraktion aus jeder User-Eingabe
            learned = profile.extract_and_update(user_input)
            for fact in learned:
                ui.system_msg(f"[MEM] Gelernt: {fact}")
                log.info(f"Profil-Update: {fact}")

            ui.thinking()

            # Profil als Kontext-Präfix injizieren (nur wenn Daten vorhanden)
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
