"""Screen capture for Arif. Saves PNGs under DATA_DIR/screenshots/."""
import os
import subprocess
import time
from datetime import datetime

from PIL import ImageGrab

from .config import SCREENSHOT_DIR


def _get_console_hwnd():
    """Return the HWND of the current console window, or None."""
    try:
        import ctypes
        return ctypes.windll.kernel32.GetConsoleWindow()
    except Exception:
        return None


def take_screenshot(_args: dict) -> str:
    import ctypes

    hwnd = _get_console_hwnd()
    SW_MINIMIZE = 6
    SW_RESTORE  = 9

    # Minimize the console so it doesn't appear in the screenshot
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
        time.sleep(0.4)   # let the animation finish

    try:
        img = ImageGrab.grab()
        path = SCREENSHOT_DIR / f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        img.save(path)
    finally:
        # Always restore the console, even if the capture failed
        if hwnd:
            time.sleep(0.15)
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(hwnd)

    # Open the screenshots folder so the user sees the new file
    subprocess.Popen(["explorer", str(SCREENSHOT_DIR)])

    return f"screenshot saved to {path}"
