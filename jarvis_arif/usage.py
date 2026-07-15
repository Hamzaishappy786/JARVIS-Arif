"""Local API call tracker. Logs every LLM and Whisper call with a timestamp.

Stored in ~/.jarvis_arif/usage.json as:
  {"llm": ["2026-07-15T10:30:00", ...], "whisper": ["2026-07-15T10:30:00", ...]}
"""
import json
from datetime import datetime, timezone, timedelta
from .config import DATA_DIR

_USAGE_FILE = DATA_DIR / "usage.json"


def _load() -> dict:
    if _USAGE_FILE.exists():
        try:
            return json.loads(_USAGE_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"llm": [], "whisper": []}


def _save(data: dict):
    _USAGE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def record(kind: str):
    """Record one API call. kind = 'llm' or 'whisper'."""
    data = _load()
    data.setdefault(kind, []).append(datetime.now(timezone.utc).isoformat())
    _save(data)


def get_stats() -> dict:
    """Return counts for today and the last 60 seconds for both services."""
    data  = _load()
    now   = datetime.now(timezone.utc)
    today = now.date().isoformat()
    minute_ago = now - timedelta(seconds=60)

    result = {}
    for kind in ("llm", "whisper"):
        calls = []
        for ts in data.get(kind, []):
            try:
                calls.append(datetime.fromisoformat(ts))
            except ValueError:
                pass
        result[kind] = {
            "today": sum(1 for c in calls if c.date().isoformat() == today),
            "last_minute": sum(1 for c in calls if c >= minute_ago),
        }
    return result
