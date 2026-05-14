"""
github_backup.py — Off-Site Code-Backup via privatem GitHub-Repo
─────────────────────────────────────────────────────────────────
Auto-Commit alle INTERVAL Stunden wenn Code-Änderungen vorliegen.
Push zu Remote als Off-Site-Sicherung.

Wichtig: Nur Code-Backup. .env / logs / temp / backups werden
nie committet (→ .gitignore).

Bei Offline: Commit lokal, Push beim nächsten Cycle (Git puffert nativ).

ENV-Vars:
  GITHUB_REPO_URL         https://github.com/<user>/<repo>.git
  GITHUB_TOKEN            Personal Access Token (scope: repo)
  GITHUB_AUTOBACKUP       on|off  (Standard: on)
  GITHUB_INTERVAL_HOURS   Standard: 6

Status-API:
  last_commit_time()         -> datetime | None
  last_push_time()           -> datetime | None
  commits_today()            -> int
  has_uncommitted_changes()  -> bool
  is_configured()            -> bool
  self_test()                -> dict

Befehle (via main.py):
  system github init    → einmaliges Setup
  system github commit  → manueller Commit + Push
  system github status  → Branch, letzter Commit, Änderungen

Log-Marker: [GITHUB-INIT], [GITHUB-COMMIT], [GITHUB-PUSH],
            [GITHUB-SKIP], [GITHUB-FAIL]
"""

import os
import subprocess
import threading
import atexit
from datetime import datetime, date

from core.logger import get_logger

log = get_logger("github_backup")

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

_PLACEHOLDER_PATTERNS = ["your-", "<user>", "<repo>", "example", "placeholder", "token-here"]


# ── Git-Subprocess-Helfer ─────────────────────────────────────────────────────

def _run_git(args: list[str], cwd: str = ROOT) -> tuple[bool, str]:
    """Führt git-Befehl aus. Gibt (success, output) zurück."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except FileNotFoundError:
        return False, "git nicht gefunden — ist Git installiert und im PATH?"
    except subprocess.TimeoutExpired:
        return False, "git Timeout nach 30s"
    except Exception as e:
        return False, str(e)


# ── GitHubBackup-Klasse ───────────────────────────────────────────────────────

class GitHubBackup:
    """
    Off-Site Code-Backup via privatem GitHub-Repository.

    Threading-Pattern identisch zu AutoBackup (backup_manager.py):
      stop_event = threading.Event()
      thread = threading.Thread(target=_loop, args=(stop_event,), daemon=True)
      atexit.register(stop_event.set)
    """

    DEFAULT_INTERVAL = 6 * 3600  # 6 Stunden

    def __init__(self, interval: int | None = None):
        self._repo_url = os.environ.get("GITHUB_REPO_URL", "").strip()
        self._token    = os.environ.get("GITHUB_TOKEN", "").strip()
        self._enabled  = os.environ.get("GITHUB_AUTOBACKUP", "on").strip().lower() == "on"

        hours = float(os.environ.get("GITHUB_INTERVAL_HOURS", "6") or "6")
        self._interval = interval if interval is not None else int(hours * 3600)

        self._stop  = threading.Event()
        self._thread: threading.Thread | None = None

        self._last_commit: datetime | None = None
        self._last_push:   datetime | None = None
        self._started_at:  datetime | None = None

        self._commits_today: int  = 0
        self._commit_date:   date = date.today()

    # ── Konfigurationsprüfung ─────────────────────────────────────────────────

    def is_configured(self) -> bool:
        """True wenn GITHUB_REPO_URL + GITHUB_TOKEN gesetzt und kein Platzhalter."""
        if not self._repo_url or not self._token:
            return False
        combined = (self._repo_url + self._token).lower()
        return not any(p in combined for p in _PLACEHOLDER_PATTERNS)

    def _auth_url(self) -> str:
        """Baut HTTPS-URL mit eingebettetem Token für Push (niemals loggen)."""
        if not self._repo_url or not self._token:
            return self._repo_url
        if self._repo_url.startswith("https://"):
            return f"https://{self._token}@{self._repo_url[8:]}"
        return self._repo_url

    def _safe_output(self, text: str) -> str:
        """Entfernt Token aus Ausgabe-Strings (Log-Safety)."""
        if self._token and self._token in text:
            return text.replace(self._token, "***")
        return text

    # ── Status-API ────────────────────────────────────────────────────────────

    def last_commit_time(self) -> datetime | None:
        return self._last_commit

    def last_push_time(self) -> datetime | None:
        return self._last_push

    def commits_today(self) -> int:
        if date.today() != self._commit_date:
            self._commits_today = 0
            self._commit_date   = date.today()
        return self._commits_today

    def has_uncommitted_changes(self) -> bool:
        ok, output = _run_git(["status", "--porcelain"])
        return bool(output.strip()) if ok else False

    # ── Thread-Start / Stop ───────────────────────────────────────────────────

    def start(self) -> None:
        """Startet den Hintergrund-Thread. Idempotent."""
        if not self.is_configured():
            log.info("[GITHUB-SKIP] GITHUB_REPO_URL/GITHUB_TOKEN nicht konfiguriert — Auto-Backup inaktiv")
            return
        if not self._enabled:
            log.info("[GITHUB-SKIP] GITHUB_AUTOBACKUP=off — Auto-Backup deaktiviert")
            return
        if self._thread and self._thread.is_alive():
            return

        self._started_at = datetime.now()
        self._thread = threading.Thread(
            target=self._loop,
            args=(self._stop,),
            daemon=True,
            name="github-backup-bg",
        )
        self._thread.start()
        atexit.register(self._stop.set)
        log.info(f"[GITHUB-INIT] Auto-Backup Thread gestartet | Intervall: {self._interval}s")

    def stop(self) -> None:
        self._stop.set()

    # ── Thread-Loop ───────────────────────────────────────────────────────────

    def _loop(self, stop_event: threading.Event) -> None:
        log.info(f"[GITHUB-INIT] Erster Auto-Commit in {self._interval}s")
        while not stop_event.wait(timeout=self._interval):
            self._auto_commit_push()
        log.info("[GITHUB-INIT] Thread beendet")

    def _auto_commit_push(self) -> None:
        log.info("[GITHUB-COMMIT] Auto-Commit Cycle gestartet...")
        ok, msg = self._do_commit()
        if not ok:
            if "keine Änderungen" in msg or "nothing to commit" in msg.lower():
                log.info(f"[GITHUB-SKIP] {msg}")
            else:
                log.error(f"[GITHUB-FAIL] Commit fehlgeschlagen: {msg}")
            return
        self._do_push()

    # ── Commit / Push ─────────────────────────────────────────────────────────

    def _do_commit(self) -> tuple[bool, str]:
        """Commit wenn Änderungen vorliegen. Gibt (success, message) zurück."""
        ok, status = _run_git(["status", "--porcelain"])
        if not ok:
            return False, f"git status fehlgeschlagen: {status}"
        if not status.strip():
            return False, "keine Änderungen seit letztem Commit"

        ok2, out2 = _run_git(["add", "-A"])
        if not ok2:
            return False, f"git add fehlgeschlagen: {out2}"

        # Re-check whether anything is actually staged after add
        ok3, staged = _run_git(["diff", "--cached", "--name-only"])
        if not staged.strip():
            return False, "keine Änderungen nach git add (alles in .gitignore?)"

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        commit_msg = f"[Zuki Auto-Backup] {timestamp}"
        ok4, out4 = _run_git(["commit", "-m", commit_msg])
        if not ok4:
            if "nothing to commit" in out4.lower():
                return False, "keine Änderungen seit letztem Commit"
            return False, f"git commit fehlgeschlagen: {out4}"

        self._last_commit = datetime.now()
        if date.today() == self._commit_date:
            self._commits_today += 1
        else:
            self._commits_today = 1
            self._commit_date   = date.today()

        log.info(f"[GITHUB-COMMIT] Commit erstellt: {commit_msg}")
        return True, out4

    def _do_push(self) -> bool:
        """Push zu Remote. Gibt True bei Erfolg zurück."""
        # Aktuellen Branch ermitteln
        ok_br, branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        branch = branch.strip() if ok_br else "main"

        ok, out = _run_git(["push", self._auth_url(), f"HEAD:{branch}"])
        if ok:
            self._last_push = datetime.now()
            log.info(f"[GITHUB-PUSH] Push erfolgreich → {branch}")
            return True
        else:
            log.warning(f"[GITHUB-FAIL] Push fehlgeschlagen (offline?): {self._safe_output(out)}")
            return False

    def _has_commits(self) -> bool:
        ok, _ = _run_git(["log", "--oneline", "-1"])
        return ok

    # ── Public commands ───────────────────────────────────────────────────────

    def cmd_init(self) -> str:
        """
        Einmaliges Setup: git init, remote setzen, initial commit + push.
        Sicher bei bereits initialisiertem Repo.
        """
        lines = []

        # Git bereits initialisiert?
        git_dir = os.path.join(ROOT, ".git")
        if os.path.isdir(git_dir):
            lines.append("Git bereits initialisiert — kein git init nötig.")
        else:
            ok, out = _run_git(["init"])
            if not ok:
                return f"[GITHUB-FAIL] git init fehlgeschlagen: {out}"
            lines.append("git init — OK")

        # .gitignore prüfen
        gitignore_path = os.path.join(ROOT, ".gitignore")
        if os.path.exists(gitignore_path):
            lines.append(".gitignore vorhanden — OK")
        else:
            lines.append("[WARN] .gitignore fehlt — .env könnte committet werden!")

        # Konfiguration prüfen
        if not self.is_configured():
            return (
                "[GITHUB-FAIL] GITHUB_REPO_URL oder GITHUB_TOKEN nicht konfiguriert.\n"
                "  → .env ausfüllen, dann 'system github init' erneut aufrufen."
            )

        # Git config: set user email + name if empty (required for commits)
        ok_name, _ = _run_git(["config", "user.name"])
        if not ok_name or not _:
            _run_git(["config", "user.name", "Zuki Auto-Backup"])
        ok_email, _ = _run_git(["config", "user.email"])
        if not ok_email or not _:
            _run_git(["config", "user.email", "zuki@localhost"])

        # Set remote (without token in the stored URL — display only)
        ok_remote, _ = _run_git(["remote", "get-url", "origin"])
        if ok_remote:
            _run_git(["remote", "set-url", "origin", self._repo_url])
            lines.append(f"Remote-URL aktualisiert: {self._repo_url}")
        else:
            ok2, out2 = _run_git(["remote", "add", "origin", self._repo_url])
            if not ok2:
                return f"[GITHUB-FAIL] git remote add fehlgeschlagen: {out2}"
            lines.append(f"Remote hinzugefügt: {self._repo_url}")

        # Initial Commit (nur wenn Änderungen oder noch keine Commits)
        ok_s, status = _run_git(["status", "--porcelain"])
        if (ok_s and status.strip()) or not self._has_commits():
            ok3, out3 = _run_git(["add", "-A"])
            if not ok3:
                lines.append(f"git add fehlgeschlagen: {out3}")
            else:
                ok4, out4 = _run_git(["commit", "-m", "[Zuki] Initial Commit"])
                if ok4:
                    self._last_commit = datetime.now()
                    lines.append("Initial Commit erstellt.")
                elif "nothing to commit" in out4.lower():
                    lines.append("Kein neuer Commit nötig (nichts verändert).")
                else:
                    lines.append(f"Commit-Hinweis: {out4}")
        else:
            lines.append("Kein neuer Commit nötig.")

        # Push
        push_ok = self._do_push()
        if push_ok:
            lines.append("Push zu Remote — erfolgreich.")
        else:
            lines.append("[WARN] Push fehlgeschlagen — GITHUB_TOKEN und Repo-URL prüfen.")
            lines.append("       Nächster Auto-Commit-Cycle versucht Push erneut.")

        return "\n".join(f"  {l}" for l in lines)

    def cmd_commit(self) -> str:
        """Manueller Commit + Push jetzt."""
        ok, msg = self._do_commit()
        if not ok:
            if "keine Änderungen" in msg:
                return f"[GITHUB-SKIP] Kein Commit nötig — {msg}"
            return f"[GITHUB-FAIL] {msg}"
        push_ok = self._do_push()
        push_status = (
            "Push OK" if push_ok
            else "Push fehlgeschlagen (offline?) — wird beim nächsten Cycle erneut versucht"
        )
        return f"[GITHUB-COMMIT] Committed  ·  {push_status}"

    def cmd_status(self) -> str:
        """Kurzer Status-Output: Branch, letzter Commit, uncommitted Änderungen."""
        if not self.is_configured():
            return "[GITHUB] Nicht konfiguriert — GITHUB_REPO_URL + GITHUB_TOKEN in .env setzen"

        ok_br, branch   = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        branch          = branch.strip() if ok_br else "unbekannt"

        ok_log, last_log = _run_git(["log", "--oneline", "-1"])
        last_commit_s   = last_log.strip() if ok_log else "(keine Commits vorhanden)"

        ok_st, status   = _run_git(["status", "--porcelain"])
        changed = len([l for l in status.strip().splitlines() if l.strip()]) if ok_st else 0

        push_t   = self._last_push.strftime("%Y-%m-%d %H:%M")   if self._last_push   else "noch kein Push in dieser Sitzung"
        commit_t = self._last_commit.strftime("%Y-%m-%d %H:%M") if self._last_commit  else "noch kein Auto-Commit in dieser Sitzung"

        auto_status = "aktiv" if (self._thread and self._thread.is_alive()) else "inaktiv"

        return (
            f"Branch          : {branch}\n"
            f"  Letzter Commit  : {last_commit_s}\n"
            f"  Auto-Commit     : {commit_t}\n"
            f"  Letzter Push    : {push_t}\n"
            f"  Commits heute   : {self.commits_today()}\n"
            f"  Uncommitted     : {changed} Datei(en)\n"
            f"  Auto-Backup     : {auto_status}  (Intervall: {self._interval // 3600}h)\n"
            f"  Repo-URL        : {self._repo_url}"
        )

    # ── self_test — for SystemTest integration ────────────────────────────────

    def self_test(self) -> dict:
        """
        Gibt dict zurück: {"status": "ok"|"warn"|"fail", "summary": str, "fix_hint": str}
        Wird von SystemTest._test_github() aufgerufen.
        """
        if not self.is_configured():
            return {
                "status":   "warn",
                "summary":  "GitHub-Backup nicht konfiguriert",
                "fix_hint": "GITHUB_REPO_URL + GITHUB_TOKEN in .env setzen",
            }

        # .env in Git-History? (kritisch!)
        ok_hist, hist_out = _run_git(["log", "--all", "--full-history", "--", ".env"])
        if ok_hist and hist_out.strip():
            return {
                "status":   "fail",
                "summary":  ".env in Git-History gefunden — SOFORT entfernen!",
                "fix_hint": "BFG Repo-Cleaner oder git filter-repo nutzen, dann force-push",
            }

        # Remote erreichbar?
        ok_remote, remote_out = _run_git(["ls-remote", "--exit-code", self._auth_url(), "HEAD"])
        if not ok_remote:
            return {
                "status":   "fail",
                "summary":  f"Remote nicht erreichbar: {self._safe_output(remote_out)[:80]}",
                "fix_hint": "PAT abgelaufen? Repo-URL falsch? Netzwerk prüfen.",
            }

        # Letzter Commit
        last_s = (
            self._last_commit.strftime("%Y-%m-%d %H:%M")
            if self._last_commit
            else "noch keiner in dieser Sitzung"
        )

        changes = self.has_uncommitted_changes()
        uncommitted_note = "  ·  Uncommitted Änderungen" if changes else ""

        return {
            "status":   "warn" if changes else "ok",
            "summary":  f"Konfiguriert  ·  Remote erreichbar  ·  Letzter Commit: {last_s}{uncommitted_note}",
            "fix_hint": "Manuell committen mit 'system github commit'" if changes else "",
        }
