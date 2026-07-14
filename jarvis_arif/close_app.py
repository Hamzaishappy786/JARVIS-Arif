"""
Close a specific app or all visible windows.
Uses psutil to match running process names and pygetwindow for close_all.
"""
import psutil
import pygetwindow as gw

from .app_paths import APPS


def _running_processes() -> list[dict]:
    """Return list of {pid, name, exe} for all running processes."""
    procs = []
    for proc in psutil.process_iter(["pid", "name", "exe"]):
        try:
            procs.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return procs


def _find_running(name: str) -> list[dict]:
    """
    Find running processes that match the given app name.
    Checks against:
      1. Process name  (e.g. "chrome.exe")
      2. Exe path basename
      3. The exe path stored in app_paths.APPS for that name
    """
    query = name.lower().strip()
    procs = _running_processes()
    matched = []

    # Look up the known exe path from our registry
    known_exe = None
    if query in APPS:
        known_exe = APPS[query].lower()
    else:
        # partial match in APPS keys
        for key in APPS:
            if query in key or key in query:
                known_exe = APPS[key].lower()
                break

    for p in procs:
        proc_name = (p.get("name") or "").lower()
        proc_exe  = (p.get("exe")  or "").lower()

        if query in proc_name:
            matched.append(p)
        elif query in proc_exe:
            matched.append(p)
        elif known_exe and known_exe in proc_exe:
            matched.append(p)

    return matched


def close_app(args: dict) -> str:
    name = args.get("name", "").strip()
    if not name:
        return "no app name provided"

    matched = _find_running(name)
    if not matched:
        return f"no running process found matching '{name}'"

    closed = 0
    for p in matched:
        try:
            proc = psutil.Process(p["pid"])
            proc.terminate()
            closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return f"closed {closed} process(es) matching '{name}'"


def close_all(_args: dict) -> str:
    closed = 0
    for win in gw.getAllWindows():
        if win.title.strip():
            try:
                win.close()
                closed += 1
            except Exception:
                pass
    return f"closed {closed} window(s)"
