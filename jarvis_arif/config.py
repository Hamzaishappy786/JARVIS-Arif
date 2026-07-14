"""Central configuration for Arif. Load once, import everywhere."""
import os
from pathlib import Path
from dotenv import load_dotenv

# User data lives in ~/.jarvis_arif/ so it survives package upgrades
DATA_DIR = Path.home() / ".jarvis_arif"
DATA_DIR.mkdir(exist_ok=True)

# Load .env from user data dir, then CWD as fallback
load_dotenv(DATA_DIR / ".env")
load_dotenv(Path.cwd() / ".env", override=False)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing. Add it to ~/.jarvis_arif/.env")

GROQ_LLM_MODEL = "llama-3.3-70b-versatile"

# Piper TTS — look in ~/.jarvis_arif/models/ first, then project dir
_MODEL_NAME = "ur_PK-fasih-medium.onnx"
_user_model = DATA_DIR / "models" / _MODEL_NAME
_proj_model = Path(__file__).parent.parent / "models" / _MODEL_NAME
_model_base  = _user_model if _user_model.exists() else _proj_model
PIPER_MODEL_PATH  = str(_model_base)
PIPER_CONFIG_PATH = str(_model_base.parent / (_MODEL_NAME + ".json"))

TEMP_AUDIO_DIR = DATA_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

SCREENSHOT_DIR = DATA_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE              = LOG_DIR / "actions.log"
CONVERSATION_LOG_FILE = LOG_DIR / "conversation.txt"
HISTORY_FILE          = LOG_DIR / "history.json"

# Weather (OpenWeatherMap) — degrade gracefully if the key is missing, not core to the assistant
OPEN_WEATHER_API_KEY = os.getenv("OPEN_WEATHER_API_KEY", "")
DEFAULT_CITY = "Lahore"

RECORD_HOTKEY = "f9"
DEFAULT_CWD   = str(Path.home())
SAMPLE_RATE   = 16000
CHANNELS      = 1

ALLOWED_ROOTS = [
    str(Path.home()),
    "C:/",
    "D:/",
]

CONFIRM_REQUIRED_ACTIONS = {"delete", "move", "close_app", "close_all"}
