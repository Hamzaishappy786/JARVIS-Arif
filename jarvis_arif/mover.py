import shutil
from pathlib import Path

from .guard import require_allowed


def move(args: dict) -> str:
    src, dst = args["path"], args["target"]
    require_allowed(src)
    require_allowed(dst)
    shutil.move(src, dst)
    return f"moved {src} -> {dst}"


def copy(args: dict) -> str:
    src, dst = args["path"], args["target"]
    require_allowed(src)
    require_allowed(dst)
    if Path(src).is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        shutil.copy2(src, dst)
    return f"copied {src} -> {dst}"
