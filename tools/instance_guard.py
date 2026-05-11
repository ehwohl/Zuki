"""
instance_guard.py — Verhindert mehrfaches Starten von Zuki
────────────────────────────────────────────────────────────
Methode: Socket-Lock auf 127.0.0.1:Port
  → Erster Start belegt den Port → andere Instanzen scheitern sofort
  → Beim Beenden gibt das OS den Port automatisch frei (auch bei Absturz)
  → Kein manuelles Aufräumen nötig
"""

import socket
import os
from core.logger import get_logger

log = get_logger("instance_guard")

_PORT    = 65432          # interner Lock-Port — nach außen nicht erreichbar
_HOST    = "127.0.0.1"
_socket  = None           # hält die Verbindung offen solange Zuki läuft


def acquire() -> bool:
    """
    Versucht den Lock zu belegen.
    Returns True  → diese Instanz darf starten
    Returns False → eine andere Instanz läuft bereits
    """
    global _socket
    _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    _socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        _socket.bind((_HOST, _PORT))
        log.debug(f"Instance-Lock belegt auf Port {_PORT}")
        return True
    except OSError:
        _socket.close()
        _socket = None
        return False


def release() -> None:
    """Gibt den Lock frei — wird automatisch via atexit aufgerufen."""
    global _socket
    if _socket:
        try:
            _socket.close()
        except Exception:
            pass
        _socket = None
        log.debug("Instance-Lock freigegeben")


def already_running_pid() -> int | None:
    """
    Prüft ob der Lock-Port belegt ist ohne ihn selbst zu belegen.
    Returns PID wenn bekannt, sonst None.
    Nützlich für Diagnose-Ausgaben.
    """
    test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        test.connect((_HOST, _PORT))
        test.close()
        return -1    # Port belegt, PID unbekannt (kein PID-Protokoll)
    except ConnectionRefusedError:
        return None  # Port frei → keine andere Instanz
    finally:
        test.close()
