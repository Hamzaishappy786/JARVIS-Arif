"""Arif's main loop — push-to-talk or always-on mic, with full JSON + txt history."""
import sys
import json
import os
from pathlib import Path

# ── Must happen before ANY other import ───────────────────────────────────────
from .startup import suppress_warnings, show_banner, show_ready, Spinner, choose_mode
suppress_warnings()
show_banner()

_spinner = Spinner("Loading Arif").start()

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from datetime import datetime
from .recorder     import record_on_hotkey
from .vad_recorder import record_on_vad
from .stt          import transcribe_and_translate
from .intent       import parse_intent, is_goodbye
from .executor     import execute
from .tts          import speak
from .config       import CONVERSATION_LOG_FILE, HISTORY_FILE
from . import navigator
from .navigator    import path_to_urdu, find_candidates

_spinner.stop()
show_ready()

# ─────────────────────────────────────────────────────────────────────────────

YES_WORDS = ["yes", "haan", "han", "ji haan", "ji", "sure", "ok", "okay",
             "bilkul", "yup", "yep"]

# Colour shortcuts (ANSI)
_C  = "\033[38;5;51m"    # cyan
_O  = "\033[38;5;214m"   # orange
_G  = "\033[38;5;82m"    # green
_R  = "\033[38;5;196m"   # red
_GR = "\033[38;5;242m"   # grey
_W  = "\033[97m"
_B  = "\033[1m"
_RS = "\033[0m"


# ── History ───────────────────────────────────────────────────────────────────

def _append_history(entry: dict):
    """Append one turn to history.json (creates the file if missing)."""
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    history.append(entry)
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def log_turn(speaker: str, text: str, **extra):
    """Write to both conversation.txt and history.json."""
    if not text:
        return
    ts = datetime.now().isoformat(timespec="seconds")
    # .txt
    with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {speaker}: {text}\n")
    # .json
    entry = {"timestamp": ts, "speaker": speaker, "text": text}
    entry.update(extra)
    _append_history(entry)


# ── Speech helpers ────────────────────────────────────────────────────────────

def say(text: str, action: str = "", result: str = ""):
    log_turn("Arif", text, action=action, result=result)
    speak(text)


def listen(mode: str) -> str:
    path = record_on_hotkey() if mode == "ptt" else record_on_vad()
    if not path:
        return ""
    text = transcribe_and_translate(path)
    log_turn("You", text, mode=mode)
    return text


# ── Confirmation gate ─────────────────────────────────────────────────────────

def confirm(prompt_urdu: str, mode: str) -> bool:
    say(prompt_urdu)
    print()
    print(f"  {_C}┌─────────────────────────────────────────┐{_RS}")
    print(f"  {_C}│{_W}{_B}           CONFIRMATION REQUIRED          {_RS}{_C}│{_RS}")
    print(f"  {_C}├─────────────────────────────────────────┤{_RS}")
    print(f"  {_C}│  {_O}[1]{_W} Yes  {_GR}/ {_O}[2]{_W} No  {_GR}/ {_O}[3]{_W} Voice F9  {_GR}        {_C}│{_RS}")
    print(f"  {_C}└─────────────────────────────────────────┘{_RS}")
    print(f"  {_O}>{_RS} ", end="", flush=True)

    while True:
        choice = input().strip().lower()
        if choice in ("1", "y", "yes", "haan", "han", "ji", "bilkul", "yup"):
            return True
        elif choice in ("2", "n", "no", "nahi", "nahin", "nope", "nah"):
            return False
        elif choice in ("3", "v", "voice", "f9"):
            print(f"  {_GR}[Hold F9 and speak…]{_RS}")
            text = listen("ptt").lower()
            print(f"  {_GR}[voice heard]{_RS} {text}")
            return any(w in text for w in YES_WORDS)
        else:
            print(f"  Enter {_O}1{_RS}, {_O}2{_RS}, or {_O}3{_RS}: ", end="", flush=True)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    mode = choose_mode()          # "ptt" or "vad"
    say("میں تیار ہوں۔")

    mode_label = f"{_O}[F9]{_RS}" if mode == "ptt" else f"{_C}[mic on]{_RS}"

    while True:
        try:
            if mode == "ptt":
                print(f"\n  Hold {_O}{_B}[F9]{_RS} to talk to Arif…")
            # vad_recorder prints its own prompt

            english_text = listen(mode)
            if not english_text.strip():
                continue
            print(f"  {_C}[heard]{_RS}   {english_text}")

            action = parse_intent(english_text, navigator.get_current_dir())
            print(f"  {_GR}[action]{_RS}  {action}")

            # Name-verification gate for folder/file actions
            act_name_early = action.get("action", "")
            if act_name_early in ("create_folder", "create_file", "delete"):
                item_path = action.get("args", {}).get("path", "")
                item_name = Path(item_path).name if item_path else "?"
                kind = "فائل" if act_name_early == "create_file" else "فولڈر"
                verb = "مٹانا" if act_name_early == "delete" else "بنانا"
                print(f"\n  {_O}[{kind} ka naam]{_RS}  {_W}{_B}{item_name}{_RS}")
                prompt_name = f"{verb} ہے: {item_name} — کیا یہی نام ہے {kind} کا؟"
                if not confirm(prompt_name, mode):
                    say("ٹھیک ہے، منسوخ کر دیا۔", action="cancelled")
                    continue

            if action.get("needs_confirmation"):
                prompt = f"کیا آپ واقعی چاہتے ہیں کہ میں یہ کروں: {action.get('reply_urdu', '')}؟"
                if not confirm(prompt, mode):
                    say("ٹھیک ہے، منسوخ کر دیا۔", action="cancelled")
                    continue

            result = execute(action)
            print(f"  {_G}[result]{_RS}  {result}")

            act_name = action.get("action", "")
            if act_name == "where_am_i":
                reply = path_to_urdu(result)
            else:
                reply = action.get("reply_urdu", "ہو گیا۔")

            say(reply, action=act_name, result=result)

        except KeyboardInterrupt:
            print(f"\n\n  {_O}{_B}خدا حافظ — Shutting down Arif.{_RS}\n")
            say("خدا حافظ۔")
            sys.exit(0)
        except Exception as e:
            print(f"  {_R}[error]{_RS} {e}")
            say("معاف کیجیے، کچھ مسئلہ ہو گیا۔")


if __name__ == "__main__":
    main()
