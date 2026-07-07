import shutil
from pathlib import Path

from config import ActionError
from guard import require_allowed


def delete(args: dict) -> str:
    path = args["path"]
    require_allowed(path)
    p = Path(path)
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()
    else:
        raise ActionError(f"Nothing found at '{path}'.")
    return f"deleted {path}"
