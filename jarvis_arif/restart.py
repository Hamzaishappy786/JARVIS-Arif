"""Restart the PC and relaunch Arif automatically via Windows startup registry."""
from ._power_utils import run, register_startup


def restart_pc(args: dict = None) -> str:
    delay = int((args or {}).get("seconds", 10))
    register_startup()
    run("shutdown", "/r", "/t", str(delay))
    return f"restarting in {delay}s — Arif will relaunch automatically"
