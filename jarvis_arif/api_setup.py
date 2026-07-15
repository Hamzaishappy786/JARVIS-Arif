"""
Pre-flight check for GROQ_API_KEY.
Runs BEFORE config.py is imported so the RuntimeError never surfaces.
If the key is missing, speaks a prompt via Piper, collects the key, and
writes it to .env in the project root.
"""
import os
import sys
import io
import time
import wave
from pathlib import Path

from dotenv import load_dotenv, set_key

_PROJECT_DIR = Path(__file__).parent.parent
_ENV_FILE    = _PROJECT_DIR / ".env"
_MODEL_DIR   = _PROJECT_DIR / "models"
_MODEL_NAME  = "ur_PK-fasih-medium.onnx"
_MODEL_PATH  = _MODEL_DIR / _MODEL_NAME
_CONFIG_PATH = _MODEL_DIR / (_MODEL_NAME + ".json")


def _speak(text: str):
    """Speak text via Piper without importing jarvis_arif.config."""
    try:
        import numpy as np
        import sounddevice as sd
        from piper import PiperVoice
        voice = PiperVoice.load(str(_MODEL_PATH), config_path=str(_CONFIG_PATH))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            voice.synthesize_wav(text, wf)
        buf.seek(0)
        with wave.open(buf, "rb") as wf:
            rate  = wf.getframerate()
            audio = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        sd.play(audio, rate)
        sd.wait()
    except Exception:
        pass   # if TTS fails, the text prompt is still shown


def ensure_groq_key():
    """
    Load .env and verify GROQ_API_KEY exists.
    If missing: speak a prompt, wait, collect input, save to .env.
    Returns immediately if the key is already set.
    """
    load_dotenv(_ENV_FILE)
    if os.getenv("GROQ_API_KEY", "").strip():
        return   # all good

    # ── Key is missing ────────────────────────────────────────────────────────
    _C  = "\033[38;5;51m"
    _O  = "\033[38;5;214m"
    _W  = "\033[97m"
    _BD = "\033[1m"
    _RS = "\033[0m"

    print(f"\n  {_O}{_BD}⚠  GROQ API key not found.{_RS}\n")
    _speak("GROQ کی API key کی ضرورت ہے")
    time.sleep(0.5)

    print(f"  {_C}Get your free key at:{_RS} {_W}https://console.groq.com/keys{_RS}\n")
    print(f"  {_O}Enter your GROQ API key:{_RS} ", end="", flush=True)
    key = input().strip()

    if not key:
        print(f"\n  {_O}No key entered — exiting.{_RS}\n")
        sys.exit(1)

    # Save to .env
    _ENV_FILE.touch(exist_ok=True)
    set_key(str(_ENV_FILE), "GROQ_API_KEY", key)
    os.environ["GROQ_API_KEY"] = key

    print(f"\n  {_C}✓{_RS}  Key saved to {_W}.env{_RS} — starting Arif…\n")
    time.sleep(0.5)
