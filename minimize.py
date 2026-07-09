"""
Minimize one specific app window or all visible windows.
Uses pygetwindow to find windows by title match.
"""
import pygetwindow as gw

from app_paths import APPS


def _resolve(name: str) -> tuple[str, str | None]:
    """
    Return (query, exe_stem) after applying alias resolution.
    exe_stem is the filename-without-extension of the known .exe (e.g. "code" for VS Code).
    """
    from pathlib import Path
    from apps import _ALIASES, _find_app

    query = name.lower().strip()

    # Apply the same alias map used by open_app
    if query in _ALIASES:
        query = _ALIASES[query]

    # Get the exe stem from app_paths so we can match window titles like
    # "executor.py — Visual Studio Code"
    match = _find_app(query)
    exe_stem = Path(match[1]).stem.lower() if match else None

    return query, exe_stem


def _find_windows(name: str) -> list:
    """Return all windows whose title contains the app name or exe stem."""
    query, exe_stem = _resolve(name)

    matched = []
    for win in gw.getAllWindows():
        title = win.title.lower().strip()
        if not title:
            continue
        if query in title:
            matched.append(win)
        elif exe_stem and exe_stem in title:
            matched.append(win)

    return matched


def minimize_app(args: dict) -> str:
    name = args.get("name", "").strip()
    if not name:
        return "no app name provided"

    windows = _find_windows(name)
    if not windows:
        return f"no open window found matching '{name}'"

    done = 0
    for win in windows:
        try:
            win.minimize()
            done += 1
        except Exception:
            pass
    return f"minimized {done} window(s) matching '{name}'"


def minimize_all(_args: dict) -> str:
    done = 0
    for win in gw.getAllWindows():
        if win.title.strip():
            try:
                win.minimize()
                done += 1
            except Exception:
                pass
    return f"minimized {done} window(s)"
