import os
from pathlib import Path

from config import DEFAULT_CWD
from guard import require_allowed

# Shared state: last folder Arif navigated to.
_current_dir = DEFAULT_CWD


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
