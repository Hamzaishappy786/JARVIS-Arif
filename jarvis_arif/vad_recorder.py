"""
Always-on microphone recorder using energy-based Voice Activity Detection.
Continuously listens; when speech is detected it records until silence,
then saves and returns the WAV path — same interface as recorder.py.
"""
import time
import numpy as np
import sounddevice as sd
import soundfile as sf

from .config import TEMP_AUDIO_DIR, SAMPLE_RATE, CHANNELS
from .startup import TermWave

_wave = TermWave(color="white")

# ── VAD tuning ────────────────────────────────────────────────────────────────
FRAME_MS        = 30          # analysis window (ms)
FRAME_SAMPLES   = int(SAMPLE_RATE * FRAME_MS / 1000)   # ~480 samples
ENERGY_THRESH   = 350         # RMS threshold — raise if too sensitive to noise
SILENCE_TIMEOUT = 1.5         # seconds of quiet before cutting the clip
MIN_SPEECH_SEC  = 0.3         # ignore clips shorter than this (noise bursts)


def _rms(frame: np.ndarray) -> float:
    return float(np.sqrt(np.mean(frame.astype(np.float32) ** 2)))


def record_on_vad() -> str | None:
    """
    Blocks until speech is detected, records until silence, returns WAV path.
    Prints a live indicator so the user knows Arif is listening.
    """
    print("  \033[38;5;51m[mic on]\033[0m  Arif is listening… (speak freely)\n")

    buffer: list[np.ndarray] = []       # accumulates speech frames
    recording   = False
    silence_sec = 0.0
    speech_sec  = 0.0

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                        dtype="int16", blocksize=FRAME_SAMPLES) as stream:
        while True:
            frame, _ = stream.read(FRAME_SAMPLES)
            energy = _rms(frame)

            if energy > ENERGY_THRESH:
                if not recording:
                    recording   = True
                    silence_sec = 0.0
                    buffer      = []
                    print("  \033[38;5;214m●\033[0m  Recording…", end="\r", flush=True)
                buffer.append(frame.copy())
                speech_sec  += FRAME_MS / 1000
                silence_sec  = 0.0
            else:
                if recording:
                    buffer.append(frame.copy())       # include trailing silence
                    silence_sec += FRAME_MS / 1000
                    if silence_sec >= SILENCE_TIMEOUT:
                        # End of utterance
                        print(" " * 40, end="\r")     # clear the recording indicator
                        if speech_sec < MIN_SPEECH_SEC:
                            # Too short — noise, reset and keep listening
                            recording   = False
                            speech_sec  = 0.0
                            silence_sec = 0.0
                            buffer      = []
                            continue

                        audio    = np.concatenate(buffer, axis=0)
                        out_path = TEMP_AUDIO_DIR / f"input_{int(time.time())}.wav"
                        sf.write(str(out_path), audio, SAMPLE_RATE)
                        return str(out_path)
