"""Urdu text-to-speech via Piper, played straight to the speakers."""
import time
import wave

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from config import PIPER_MODEL_PATH, PIPER_CONFIG_PATH, TEMP_AUDIO_DIR

_voice = PiperVoice.load(PIPER_MODEL_PATH, config_path=PIPER_CONFIG_PATH)


def speak(text: str):
    out_path = TEMP_AUDIO_DIR / f"reply_{int(time.time())}.wav"
    with wave.open(str(out_path), "wb") as wav_file:
        _voice.synthesize_wav(text, wav_file)

    with wave.open(str(out_path), "rb") as wf:
        rate = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)

    sd.play(audio, rate)
    sd.wait()
