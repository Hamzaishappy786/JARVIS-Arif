"""Log off the current Windows session."""
from ._power_utils import run, unregister_startup


def logoff_pc(_args: dict = None) -> str:
    unregister_startup()
    run("shutdown", "/l")
    return "logging off"
