"""Urdu text-to-speech via Piper — local playback and/or raw WAV bytes for remote clients."""
import io
import wave

import numpy as np
import sounddevice as sd
from piper import PiperVoice

from .config  import PIPER_MODEL_PATH, PIPER_CONFIG_PATH
from .startup import TermWave

_voice     = PiperVoice.load(PIPER_MODEL_PATH, config_path=PIPER_CONFIG_PATH)
_arif_wave = TermWave(color="white")

# LLMs often output Arabic Unicode lookalikes instead of proper Urdu codepoints.
# Piper (trained on Urdu text) doesn't recognise them as words and spells them
# letter-by-letter.  Map every Arabic lookalike → its Urdu equivalent.
_ARABIC_TO_URDU = str.maketrans({
    "ك": "ک",   # Arabic kaf  U+0643  → Urdu kaf   U+06A9
    "ي": "ی",   # Arabic ye   U+064A  → Urdu ye    U+06CC
    "ه": "ہ",   # Arabic he   U+0647  → Urdu gol-he U+06C1
    "ى": "ی",   # Arabic alef maqsura U+0649 → Urdu ye
    "ة": "ت",   # Arabic taa marbuta  U+0629 → plain te
    "ك": "ک",
    "ي": "ی",
    "ه": "ہ",
})


def _normalise(text: str) -> str:
    """Remap Arabic lookalike characters to proper Urdu codepoints."""
    return text.translate(_ARABIC_TO_URDU)


def synthesize_to_bytes(text: str) -> bytes:
    """Synthesize Urdu text and return raw WAV bytes (no playback)."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        _voice.synthesize_wav(_normalise(text), wav_file)
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
