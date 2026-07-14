from pathlib import Path
from .config import ALLOWED_ROOTS


class ActionError(Exception):
    pass


def is_allowed(path: str) -> bool:
    try:
        resolved = Path(path).resolve()
    except Exception:
        return False
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(Path(root).resolve())
            return True
        except ValueError:
            continue
    return False


def require_allowed(path: str):
    if not is_allowed(path):
        raise ActionError(f"Path '{path}' is outside the allowed folders.")
