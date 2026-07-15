"""Turns English text into a structured action dict, via Groq JSON mode."""
import json

from groq import Groq

from .config import GROQ_API_KEY, GROQ_LLM_MODEL, ALLOWED_ROOTS, CONFIRM_REQUIRED_ACTIONS
from .usage import record

_client = Groq(api_key=GROQ_API_KEY)

VALID_ACTIONS = {
    "create_folder", "create_file", "delete", "move", "copy",
    "open_app", "close_app", "close_all", "minimize_app", "minimize_all",
    "list", "open_folder", "where_am_i", "set_brightness", "goodbye", "none",
    "set_volume", "open_website", "get_weather", "set_reminder",
    "take_screenshot", "dictate", "show_limits",
    "sleep_pc", "hibernate_pc", "logoff_pc", "restart_pc", "shutdown_pc",
}

# Farewell phrases — detected locally before hitting the LLM
GOODBYE_PHRASES = [
    "khuda hafiz", "khuda haafiz", "allah hafiz", "allah haafiz",
    "goodbye", "bye", "khudahafiz", "allahhafiz", "good bye",
    "band karo", "shut down", "close arif", "exit",
]


def is_goodbye(text: str) -> bool:
    t = text.lower().strip()
    return any(phrase in t for phrase in GOODBYE_PHRASES)


# Wake-phrase greeting ("Yaar Arif") — detected locally before hitting the LLM.
# Whisper translates Urdu speech to English, so "یار عارف" may come through as
# any of several renderings; this list is a first draft, extend after testing
# against real recordings.
WAKE_PHRASES = [
    "hey arif", "hey aarif", "yaar arif", "friend arif", "dear arif",
    "hi arif", "hello arif", "buddy arif", "yo arif", "arif yaar",
]


def is_wake_phrase(text: str) -> bool:
    t = text.lower().strip()
    return any(phrase in t for phrase in WAKE_PHRASES)

_SYSTEM_PROMPT_BASE = f"""Arif Windows voice assistant intent parser. Output ONLY raw JSON, no prose.

{{"action":"<one of {sorted(VALID_ACTIONS)}>","args":{{...}},"needs_confirmation":true/false,"reply_urdu":"<short Urdu>"}}

ACTIONS & ARGS:
create_folder/create_file/delete/move/copy → "path" (full absolute path, join with cwd if relative); move/copy also "target"
open_app/close_app/minimize_app → "name" (plain app name); open_app always needs_confirmation=true
minimize_all/close_all/list/where_am_i/take_screenshot/dictate/show_limits/goodbye → empty args
set_brightness → {{"level":0-100}} OR {{"delta":-100..100}}; triggered by: roshni/brightness/screen/light/display
set_volume      → {{"level":0-100}} OR {{"delta":-100..100}} OR {{"mute":true/false}}; triggered by: awaaz/volume/sound/voice/speaker
NEVER mix set_brightness and set_volume — they are completely different. awaaz→volume, roshni→brightness.
open_website → {{"name":"<spoken site name verbatim>"}} — do NOT build a URL
get_weather  → {{}} or {{"city":"<name>"}}
set_reminder → {{"seconds":<int>,"message":"<text>"}}

Power commands (all need needs_confirmation=true):
sleep_pc → "so jao"/"sleep karo"/suspend; empty args
hibernate_pc → "hibernate"/"deep sleep"; empty args
logoff_pc → "log off"/"sign out"/"session band"; empty args
restart_pc → "restart"/"dobara chalao"; optional {{"seconds":10}}
shutdown_pc → "shutdown"/"band karo PC"/"power off"; optional {{"seconds":10}}

RULES:
- needs_confirmation=true for: {sorted(CONFIRM_REQUIRED_ACTIONS)}, ambiguous commands, 2+ files affected
- path always absolute; if no location given, use CWD (provided below)
- reply_urdu: short, natural Urdu script. Use ک not ك, ی not ي, ہ not ه (Urdu not Arabic codepoints)
- History below = prior turns for pronoun context only; always output fresh JSON for current command
- Output raw JSON only."""


def parse_intent(english_text: str, current_dir: str = "", history: list[dict] | None = None) -> dict:
    cwd_line = (
        f"\n\nCURRENT WORKING DIRECTORY (use this as base for any relative path): {current_dir}"
        if current_dir else ""
    )
    system_prompt = _SYSTEM_PROMPT_BASE + cwd_line

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-4:])   # last 2 turns (4 messages) is enough for context
    messages.append({"role": "user", "content": english_text})

    record("llm")
    resp = _client.chat.completions.create(
        model=GROQ_LLM_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=200,   # JSON response is never longer than this
    )
    data = json.loads(resp.choices[0].message.content)

    data.setdefault("action", "none")
    data.setdefault("args", {})
    data.setdefault("needs_confirmation", data["action"] in CONFIRM_REQUIRED_ACTIONS)
    data.setdefault("reply_urdu", "معاف کیجیے، سمجھ نہیں آیا۔")

    if data["action"] not in VALID_ACTIONS:
        data["action"] = "none"

    return data
