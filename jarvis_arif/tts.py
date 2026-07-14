"""Urdu text-to-speech via Piper — local playback and/or raw WAV bytes for remote clients."""
import io
import time
import wave

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from .config  import PIPER_MODEL_PATH, PIPER_CONFIG_PATH, TEMP_AUDIO_DIR
from .startup import TermWave

_voice     = PiperVoice.load(PIPER_MODEL_PATH, config_path=PIPER_CONFIG_PATH)
_arif_wave = TermWave(color="orange")


def synthesize_to_bytes(text: str) -> bytes:
    """Synthesize Urdu text and return raw WAV bytes (no playback)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        _voice.synthesize_wav(text, wav_file)
    return buf.getvalue()


def speak(text: str):
    """Synthesize and play locally on the PC speakers."""
    wav_bytes = synthesize_to_bytes(text)
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        rate  = wf.getframerate()
        audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
    _arif_wave.start()
    sd.play(audio, rate)
    sd.wait()
    _arif_wave.stop()
