"""Fire-and-forget reminders. Daemon thread sleeps then speaks -- no persistence across restarts."""
import threading
import time

from .tts import speak


def set_reminder(args: dict) -> str:
    seconds = int(args.get("seconds", 0))
    message = args.get("message", "یاد دہانی کا وقت ہو گیا ہے")
    if seconds <= 0:
        return "invalid reminder duration"

    def _fire():
        time.sleep(seconds)
        speak(message)

    threading.Thread(target=_fire, daemon=True).start()
    return f"reminder set for {seconds}s: {message}"
