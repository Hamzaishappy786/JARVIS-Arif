"""Volume control for Arif via pycaw (Windows Core Audio API). Mirrors brightness.py's shape."""
from pycaw.pycaw import AudioUtilities


def _endpoint():
    return AudioUtilities.GetSpeakers().EndpointVolume


def get_volume() -> int:
    return round(_endpoint().GetMasterVolumeLevelScalar() * 100)


def set_volume(level: int) -> str:
    level = max(0, min(100, level))
    _endpoint().SetMasterVolumeLevelScalar(level / 100, None)
    return f"volume set to {level}%"


def adjust_volume(delta: int) -> str:
    current = get_volume()
    level = max(0, min(100, current + delta))
    _endpoint().SetMasterVolumeLevelScalar(level / 100, None)
    return f"volume changed from {current}% to {level}%"


def mute(_args: dict = None) -> str:
    _endpoint().SetMute(1, None)
    return "muted"


def unmute(_args: dict = None) -> str:
    _endpoint().SetMute(0, None)
    return "unmuted"
