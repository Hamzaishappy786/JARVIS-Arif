import os
import subprocess

import psutil
import pygetwindow as gw


def open_app(args: dict) -> str:
    name = args["name"]
    if os.path.exists(name):
        os.startfile(name)
    else:
        subprocess.Popen(name, shell=True)
    return f"opened app {name}"


def close_app(args: dict) -> str:
    app_name = args["name"].lower()
    closed = 0
    for proc in psutil.process_iter(["pid", "name"]):
        if app_name in (proc.info["name"] or "").lower():
            proc.terminate()
            closed += 1
    return f"closed {closed} process(es) matching '{app_name}'"


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
