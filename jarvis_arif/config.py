"""Central configuration for Arif. Load once, import everywhere."""
import os
from pathlib import Path
from dotenv import load_dotenv

# All runtime data stays inside the project directory
_PROJECT_DIR = Path(__file__).parent.parent   # D:\JARVIS-ARIF
DATA_DIR     = _PROJECT_DIR                   # kept as alias used by other modules

# Load .env from project root
load_dotenv(_PROJECT_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

GROQ_LLM_MODEL = "llama-3.1-8b-instant"

# Piper TTS model — lives in models/ inside the project
_MODEL_NAME       = "ur_PK-fasih-medium.onnx"
_model_base       = _PROJECT_DIR / "models" / _MODEL_NAME
PIPER_MODEL_PATH  = str(_model_base)
PIPER_CONFIG_PATH = str(_model_base.parent / (_MODEL_NAME + ".json"))

TEMP_AUDIO_DIR = _PROJECT_DIR / "temp_audio"
TEMP_AUDIO_DIR.mkdir(exist_ok=True)

SCREENSHOT_DIR = _PROJECT_DIR / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

LOG_DIR = _PROJECT_DIR / "logs"
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

CONFIRM_REQUIRED_ACTIONS = {
    "delete", "move", "close_app", "close_all",
    "sleep_pc", "hibernate_pc", "logoff_pc", "restart_pc", "shutdown_pc",
}
