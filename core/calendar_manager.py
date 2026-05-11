import os
from datetime import date

from core.logger import get_logger

log = get_logger("calendar")

CALENDAR_FILE = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "skills", "broker", "calendar.txt"
))


def get_todays_events() -> list[str]:
    """
    Parse calendar.txt and return events matching today's date.
    Format per line: YYYY-MM-DD - Event description
    Returns empty list if file missing, empty, or no match today.
    """
    if not os.path.exists(CALENDAR_FILE):
        log.debug("calendar.txt nicht gefunden")
        return []

    today = date.today().isoformat()
    events = []

    try:
        with open(CALENDAR_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or " - " not in line:
                    continue
                entry_date, _, event = line.partition(" - ")
                if entry_date.strip() == today:
                    events.append(event.strip())
    except OSError as e:
        log.warning(f"Kalender konnte nicht gelesen werden: {e}")

    if events:
        log.info(f"Kalender-Treffer: {events}")
    return events
