import os
from pathlib import Path

from config import DEFAULT_CWD
from guard import require_allowed

# Shared state: last folder Arif navigated to.
_current_dir = DEFAULT_CWD

# Known folder friendly names in Urdu
_KNOWN = {
    "desktop":   "ڈیسک ٹاپ",
    "downloads": "ڈاؤن لوڈز",
    "documents": "دستاویزات",
    "pictures":  "تصاویر",
    "music":     "موسیقی",
    "videos":    "ویڈیوز",
    "users":     None,   # skip — not meaningful on its own
}


def path_to_urdu(raw_path: str) -> str:
    """
    Convert a Windows path to a short natural Urdu location sentence.
    e.g. C:\\Users\\gamer        → "میں C ڈرائیو کے gamer فولڈر میں ہوں"
         C:\\Users\\gamer\\Desktop → "میں C ڈرائیو کے ڈیسک ٹاپ پر ہوں"
         D:\\JARVIS-ARIF          → "میں D ڈرائیو کے JARVIS-ARIF فولڈر میں ہوں"
    """
    p = Path(raw_path)
    parts = list(p.parts)          # e.g. ['C:\\', 'Users', 'gamer', 'Desktop']

    # Drive letter
    drive = parts[0].rstrip("\\:/").upper() if parts else "C"

    # Skip uninformative middle segments (Users) and find the last meaningful part
    meaningful = [
        part for part in parts[1:]
        if _KNOWN.get(part.lower()) is not None   # known with a nice name
        or part.lower() not in _KNOWN             # unknown name → keep it
    ]

    if not meaningful:
        return f"میں {drive} ڈرائیو پر ہوں"

    last = meaningful[-1]
    urdu_name = _KNOWN.get(last.lower(), last)   # translate if known, else keep original

    # "par" for known special folders, "mein" for generic folders
    postfix = "پر" if last.lower() in _KNOWN else "فولڈر میں"

    return f"میں {drive} ڈرائیو کے {urdu_name} {postfix} ہوں"


def find_candidates(name: str, search_dir: str) -> list[str]:
    """Return paths of folders in search_dir whose names fuzzy-match name."""
    import difflib
    try:
        entries = [e for e in os.scandir(search_dir) if e.is_dir()]
        folder_names = [e.name for e in entries]
        path_map = {e.name: e.path for e in entries}
        matches = difflib.get_close_matches(name, folder_names, n=5, cutoff=0.4)
        return [path_map[m] for m in matches]
    except Exception:
        return []


def get_current_dir() -> str:
    return _current_dir


def open_folder(args: dict) -> str:
    global _current_dir
    path = args["path"]
    require_allowed(path)
    os.startfile(path)
    _current_dir = str(Path(path).resolve())
    return f"opened {path}"


def where_am_i(_args: dict) -> str:
    return _current_dir


def list_dir(args: dict) -> str:
    path = args.get("path", _current_dir)
    require_allowed(path)
    items = os.listdir(path)
    preview = ", ".join(items[:20])
    return f"{len(items)} items: {preview}"
