"""Turns English text into a structured action dict, via Groq JSON mode."""
import json

from groq import Groq

from .config import GROQ_API_KEY, GROQ_LLM_MODEL, ALLOWED_ROOTS, CONFIRM_REQUIRED_ACTIONS

_client = Groq(api_key=GROQ_API_KEY)

VALID_ACTIONS = {
    "create_folder", "create_file", "delete", "move", "copy",
    "open_app", "close_app", "close_all", "minimize_app", "minimize_all",
    "list", "open_folder", "where_am_i", "set_brightness", "goodbye", "none",
    "set_volume", "open_website", "get_weather", "set_reminder",
    "take_screenshot", "dictate",
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

_SYSTEM_PROMPT_BASE = f"""You are the intent-parsing brain for "Arif", a Windows voice assistant.
You receive an English translation of a spoken Urdu command and must output ONLY a JSON object
(no prose, no markdown fences) with this exact shape:

{{
  "action": one of {sorted(VALID_ACTIONS)},
  "args": {{"path": "...", "target": "...", "name": "..."}},
  "needs_confirmation": true or false,
  "reply_urdu": "a short natural Urdu sentence (in Urdu script) to speak back to the user"
}}

Rules:
- "args" only includes the keys relevant to the action; omit keys you don't need.
- "path" (and "target", for move/copy) must always be ONE FULL ABSOLUTE PATH, already joined
  with any folder/file name mentioned. IMPORTANT: if no explicit location is given, build
  the path inside the CURRENT WORKING DIRECTORY shown below. For example if the user says
  "delete Hamza" and cwd is C:/Users/gamer/Desktop/Harris, output
  "path": "C:/Users/gamer/Desktop/Harris/Hamza".
  The "name" key is ONLY used for open_app/close_app (the app name, not a path component).
- For open_app: set "name" to the plain app name the user said (e.g. "chrome", "discord",
  "android studio"). Always set needs_confirmation: true and reply_urdu should say something
  like "کیا میں [app name] کھولوں؟" so the user can confirm with haan/nahi.
- For minimize_app: set "name" to the app the user wants minimized. Use minimize_all (empty args)
  when they say "sab minimize karo" / "minimize everything" / "sab chupa do".
- Paths must resolve within these allowed roots: {ALLOWED_ROOTS}. If the user's target isn't
  clearly one of these, still fill your best-guess absolute path under the most relevant root.
- Set "needs_confirmation": true for any of: {sorted(CONFIRM_REQUIRED_ACTIONS)}, or when the
  command affects 2+ files/folders, or the request is ambiguous.
- Brightness commands -- about SCREEN LIGHT ("roshni kam karo", "light teez karo", "brightness
  badha do", "screen dark karo", "poori roshni karo", "roshni 50 karo", or the English words
  "brightness"/"screen light"/"display") -- map to "action": "set_brightness".
  Use "args": {{"level": <0-100>}} for an absolute value, OR "args": {{"delta": <-100 to 100>}} for
  a relative change (e.g. "kam karo" → delta: -30, "zyada karo" → delta: +30, "bilkul band" →
  level: 0, "poori/max" → level: 100, "thodi kam" → delta: -15, "thodi zyada" → delta: +15).
  Never set both level and delta at once -- pick one based on the phrase.
- Questions asking where Arif currently is (e.g. "tum kahan pe ho", "kahan ho", "where are you",
  "abhi kis folder mein ho") map to "action": "where_am_i" with empty args. Do not guess a path
  for reply_urdu here -- the real path is filled in after execution, not by you.
- For "list" / "show contents" / "kya hai andar": use "action": "list" with empty args -- the
  executor will list the current working directory automatically.
- Volume commands -- about SOUND/SPEAKER LEVEL ("awaaz kam karo", "zyada karo", "mute karo",
  "un-mute karo", "awaaz 50 karo", "chup karo", or the English words "volume"/"sound"/"voice"/
  "speaker") -- map to "action": "set_volume". Use "args": {{"level": <0-100>}} for an absolute
  value, OR "args": {{"delta": <-100 to 100>}} for a relative change, OR "args": {{"mute": true}}
  / "args": {{"mute": false}}. Never combine multiple keys -- pick exactly one based on the phrase.
- IMPORTANT: set_brightness (screen light) and set_volume (sound level) are DIFFERENT actions --
  never conflate them. If the command mentions "awaaz"/"volume"/"sound"/"voice"/"speaker", it is
  ALWAYS set_volume, never set_brightness, even if the phrasing otherwise resembles a brightness
  example above. If it mentions "roshni"/"brightness"/"light"/"screen", it is ALWAYS
  set_brightness, never set_volume.
- Opening a website/page ("YouTube kholo", "Google kholo", "whatsapp web kholo") maps to
  "action": "open_website" with "args": {{"name": "<site name or plain text exactly as said>"}}.
  Do not build a URL yourself -- pass the raw spoken name through unchanged.
- Weather questions ("aaj ka mausam kya hai", "kal ka mausam", "garmi hai kya", "baarish hogi kya")
  map to "action": "get_weather" with "args": {{}} (defaults to the configured city), or
  "args": {{"city": "<name>"}} if the user explicitly names a different city. Note: only current
  conditions are available right now, so treat "kal" (tomorrow) phrasing the same as "aaj" (today).
- Reminder/alarm requests ("5 minute baad yaad dilana", "10 minute mein alarm laga do") map to
  "action": "set_reminder". Convert the spoken duration to seconds in
  "args": {{"seconds": <int>, "message": "<what to remind about>"}}. If no explicit message content
  is given, default the message to a generic Urdu reminder phrase.
- Screenshot requests ("screenshot lo", "tasveer le lo screen ki") map to "action": "take_screenshot"
  with "args": {{}}.
- Dictation/typing requests ("yeh likhna hai...", "notepad mein likh do", "type kar do yeh") map to
  "action": "dictate" with "args": {{}} -- the actual text to type is NOT extracted here; it comes
  from a separate native-Urdu re-transcription of the same audio, handled after execution. Just
  detect the trigger phrase and set reply_urdu to something like "ٹھیک ہے، لکھ رہا ہوں۔".
- If you cannot map the command to a real action, use "action": "none" and explain in reply_urdu.
- reply_urdu must always be filled, in Urdu script, short and natural (not a translation dump).
  CRITICAL: use proper Urdu Unicode — ک (U+06A9) not ك, ی (U+06CC) not ي, ہ (U+06C1) not ه.
  Never use Arabic lookalike codepoints; the Urdu TTS engine will mispronounce them.
- Prior turns may be included below as conversation history -- use them to resolve pronouns/context
  in the CURRENT command (e.g. "usko wahi wapas le jao" referring to something mentioned earlier),
  but always output a fresh JSON action for the current command only.
- Output raw JSON only, nothing else.
"""


def parse_intent(english_text: str, current_dir: str = "", history: list[dict] | None = None) -> dict:
    cwd_line = (
        f"\n\nCURRENT WORKING DIRECTORY (use this as base for any relative path): {current_dir}"
        if current_dir else ""
    )
    system_prompt = _SYSTEM_PROMPT_BASE + cwd_line

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": english_text})

    resp = _client.chat.completions.create(
        model=GROQ_LLM_MODEL,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    data = json.loads(resp.choices[0].message.content)

    data.setdefault("action", "none")
    data.setdefault("args", {})
    data.setdefault("needs_confirmation", data["action"] in CONFIRM_REQUIRED_ACTIONS)
    data.setdefault("reply_urdu", "معاف کیجیے، سمجھ نہیں آیا۔")

    if data["action"] not in VALID_ACTIONS:
        data["action"] = "none"

    return data
