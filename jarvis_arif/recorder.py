"""Push-to-talk microphone recording. Hold RECORD_HOTKEY to talk, release to stop."""
import time

import numpy as np
import sounddevice as sd
import soundfile as sf
import keyboard

from .config import TEMP_AUDIO_DIR, RECORD_HOTKEY, SAMPLE_RATE, CHANNELS
from .startup import TermWave

_wave = TermWave(color="orange")


def record_on_hotkey() -> str | None:
    """Blocks until RECORD_HOTKEY is pressed, records while held, saves a wav, returns its path."""
    keyboard.wait(RECORD_HOTKEY)

    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    stream = sd.InputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16", callback=callback
    )
    _wave.start()
    with stream:
        while keyboard.is_pressed(RECORD_HOTKEY):
            time.sleep(0.02)
    _wave.stop()

    if not frames:
        return None

    audio = np.concatenate(frames, axis=0)
    out_path = TEMP_AUDIO_DIR / f"input_{int(time.time())}.wav"
    sf.write(str(out_path), audio, SAMPLE_RATE)
    return str(out_path)
