"""Sleep the PC via Windows power API."""
from ._power_utils import run


def sleep_pc(_args: dict = None) -> str:
    run("rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0")
    return "sleeping"
