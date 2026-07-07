"""Central configuration for Arif. Load once, import everywhere."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing. Put it in .env at the project root.")

# Groq model (intent parsing only -- STT runs locally to save API usage)
GROQ_LLM_MODEL = "llama-3.3-70b-versatile"

# Local HF Whisper model for Urdu speech -> English text (runs on GPU if available)
WHISPER_MODEL_ID = "openai/whisper-small"

# Piper TTS
PIPER_MODEL_PATH = str(BASE_DIR / "models" / "ur_PK-fasih-medium.onnx")
PIPER_CONFIG_PATH = str(BASE_DIR / "models" / "ur_PK-fasih-medium.onnx.json")

# Scratch space
TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "actions.log"
CONVERSATION_LOG_FILE = LOG_DIR / "conversation.txt"

# Push-to-talk hotkey (hold to record, release to stop)
RECORD_HOTKEY = "f9"

# Where Arif "is" before it has navigated anywhere ("Tum kahan pe ho" on a fresh start).
DEFAULT_CWD = str(Path.home())

# Only these directories (and their subfolders) may be touched by file actions.
# Edit this list to match where you actually want Arif operating.
ALLOWED_ROOTS = [
    str(Path.home() / "Desktop"),
    str(Path.home() / "Downloads"),
    str(Path.home() / "Documents"),
    "D:/JARVIS-ARIF-Workspace",  # dedicated sandbox folder, create it if you want one
]

# Actions that must be voice-confirmed before executing.
CONFIRM_REQUIRED_ACTIONS = {"delete", "move", "close_app", "close_all"}

# Audio recording settings
SAMPLE_RATE = 16000
CHANNELS = 1
