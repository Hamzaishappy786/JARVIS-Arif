from pathlib import Path

from guard import require_allowed


def create_folder(args: dict) -> str:
    path = args["path"]
    require_allowed(path)
    Path(path).mkdir(parents=True, exist_ok=True)
    return f"created folder {path}"


def create_file(args: dict) -> str:
    path = args["path"]
    require_allowed(path)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.touch(exist_ok=True)
    return f"created file {path}"
