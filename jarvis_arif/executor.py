"""
Pure dispatcher — routes each action to its dedicated module.
No business logic lives here.
"""
from datetime import datetime

from . import addition
from . import deletion
from . import mover
from . import navigator
from . import apps
from . import close_app as close_app_mod
from . import minimize as minimize_mod
from . import brightness as brightness_mod
from . import volume as volume_mod
from . import website
from . import weather
from . import reminder
from . import screenshot
from . import dictation

from .config import LOG_FILE
from .guard import ActionError


def _brightness_dispatch(args: dict) -> str:
    if "level" in args:
        return brightness_mod.set_brightness(int(args["level"]))
    if "delta" in args:
        return brightness_mod.adjust_brightness(int(args["delta"]))
    raise ActionError("set_brightness requires 'level' or 'delta' in args.")


def _volume_dispatch(args: dict) -> str:
    if "mute" in args:
        return volume_mod.mute() if args["mute"] else volume_mod.unmute()
    if "level" in args:
        return volume_mod.set_volume(int(args["level"]))
    if "delta" in args:
        return volume_mod.adjust_volume(int(args["delta"]))
    raise ActionError("set_volume requires 'level', 'delta', or 'mute' in args.")


_ROUTES = {
    "create_folder":  addition.create_folder,
    "create_file":    addition.create_file,
    "delete":         deletion.delete,
    "move":           mover.move,
    "copy":           mover.copy,
    "open_folder":    navigator.open_folder,
    "where_am_i":     navigator.where_am_i,
    "list":           navigator.list_dir,
    "open_app":       apps.open_app,
    "close_app":      close_app_mod.close_app,
    "close_all":      close_app_mod.close_all,
    "minimize_app":   minimize_mod.minimize_app,
    "minimize_all":   minimize_mod.minimize_all,
    "set_brightness": _brightness_dispatch,
    "set_volume":     _volume_dispatch,
    "open_website":   website.open_website,
    "get_weather":    weather.get_weather,
    "set_reminder":   reminder.set_reminder,
    "take_screenshot": screenshot.take_screenshot,
    "dictate":        dictation.dictate,
    "none":           lambda _: "no-op",
}


def _log(entry: str):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {entry}\n")


def execute(action: dict) -> str:
    """Dispatch the action dict from intent.parse_intent. Returns a short result string."""
    name = action.get("action", "none")
    args = action.get("args", {})

    handler = _ROUTES.get(name)
    if handler is None:
        result = f"unknown action '{name}'"
    else:
        try:
            result = handler(args)
        except ActionError as e:
            result = f"BLOCKED: {e}"
        except Exception as e:
            result = f"ERROR: {e}"

    _log(f"action={name} args={args} -> {result}")
    return result
