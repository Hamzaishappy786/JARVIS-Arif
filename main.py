"""Arif's main loop: hold hotkey -> listen -> understand -> (confirm) -> act -> reply -> repeat."""
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from recorder import record_on_hotkey
from stt import transcribe_and_translate
from intent import parse_intent
from executor import execute
from tts import speak
from config import CONVERSATION_LOG_FILE

YES_WORDS = ["yes", "haan", "han", "ji haan", "ji", "sure", "ok", "okay"]


def log_turn(speaker: str, text: str):
    """Appends one line to the conversation transcript -- works for English or Urdu text."""
    if not text:
        return
    with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {speaker}: {text}\n")


def say(text: str):
    log_turn("Arif", text)
    speak(text)


def listen() -> str:
    """Records, transcribes+translates, and logs what the user said. Returns the text."""
    path = record_on_hotkey()
    if not path:
        return ""
    text = transcribe_and_translate(path)
    log_turn("You", text)
    return text


def ask_yes_no_urdu() -> bool:
    text = listen().lower()
    return any(w in text for w in YES_WORDS)


def main():
    print("Arif is ready.")
    say("میں تیار ہوں۔")

    while True:
        try:
            english_text = listen()
            print(f"[heard] {english_text}")
            if not english_text.strip():
                continue

            action = parse_intent(english_text)
            print(f"[action] {action}")

            if action.get("needs_confirmation"):
                say(f"کیا آپ واقعی چاہتے ہیں کہ میں یہ کروں: {action.get('reply_urdu', '')}؟")
                if not ask_yes_no_urdu():
                    say("ٹھیک ہے، منسوخ کر دیا۔")
                    continue

            result = execute(action)
            print(f"[result] {result}")

            if action.get("action") == "where_am_i":
                say(f"میں اس وقت اس مقام پر ہوں: {result}")
            else:
                say(action.get("reply_urdu", "ہو گیا۔"))

        except KeyboardInterrupt:
            print("\nShutting down Arif.")
            say("خدا حافظ۔")
            sys.exit(0)
        except Exception as e:
            print(f"[error] {e}")
            say("معاف کیجیے، کچھ مسئلہ ہو گیا۔")


if __name__ == "__main__":
    main()
