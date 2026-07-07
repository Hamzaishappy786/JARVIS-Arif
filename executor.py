"""
Pure dispatcher — routes each action to its dedicated module.
No business logic lives here.
"""
from datetime import datetime

import addition
import deletion
import mover
import navigator
import apps
import brightness as brightness_mod

from config import LOG_FILE
from guard import ActionError


def _brightness_dispatch(args: dict) -> str:
    if "level" in args:
        return brightness_mod.set_brightness(int(args["level"]))
    if "delta" in args:
        return brightness_mod.adjust_brightness(int(args["delta"]))
    raise ActionError("set_brightness requires 'level' or 'delta' in args.")


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
    "close_app":      apps.close_app,
    "close_all":      apps.close_all,
    "set_brightness": _brightness_dispatch,
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
