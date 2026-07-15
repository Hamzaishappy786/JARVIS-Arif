"""Shut down the PC."""
from ._power_utils import run, unregister_startup


def shutdown_pc(args: dict = None) -> str:
    delay = int((args or {}).get("seconds", 10))
    unregister_startup()
    run("shutdown", "/s", "/t", str(delay))
    return f"shutting down in {delay}s"
