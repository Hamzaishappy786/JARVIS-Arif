"""
Android-connected Arif TCP server.
Receives WAV audio from phone → STT → intent → confirm via phone buttons → execute → reply.

Protocol  PC → Phone:
  {"type": "confirm", "message": "<urdu question>", "item": "<name>"}  +  WAV (question audio)
  {"type": "response", "text": "<urdu reply>", "action": "...", "result": "..."}  +  WAV (reply audio)

Protocol  Phone → PC:
  WAV audio (user speech)
  {"answer": "yes"} or {"answer": "no"}  (only during a confirm exchange)
"""
import sys
import os
import json
import socket
import struct
import time
import threading
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from .startup import suppress_warnings, show_banner, show_ready, Spinner
suppress_warnings()
show_banner()

_spinner = Spinner("Loading Arif (Android mode)").start()

from datetime import datetime
from .config    import TEMP_AUDIO_DIR, CONVERSATION_LOG_FILE, HISTORY_FILE
from .stt       import transcribe_and_translate
from .intent    import parse_intent, is_goodbye
from .executor  import execute
from .tts       import synthesize_to_bytes
from . import navigator
from .navigator import path_to_urdu, find_candidates

_spinner.stop()
show_ready()

HOST = "0.0.0.0"
PORT = 5050

# ── Terminal waveform animation ───────────────────────────────────────────────

_WAVE_CHARS = "▁▂▃▄▅▆▇█▇▆▅▄▃▂▁"

class _TermWave:
    """Scrolling Unicode bar waveform shown in terminal while phone mic is active."""

    def __init__(self):
        self._stop   = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        seq = (_WAVE_CHARS * 4)   # long enough to scroll
        offset = 0
        while not self._stop.is_set():
            segment = seq[offset: offset + 28]
            sys.stdout.write(
                f"  \033[38;5;214m🎙\033[0m  \033[38;5;51m{segment}\033[0m   \r"
            )
            sys.stdout.flush()
            offset = (offset + 1) % len(_WAVE_CHARS)
            time.sleep(0.07)

    def start(self):
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=0.5)
        sys.stdout.write(" " * 60 + "\r")
        sys.stdout.flush()

_wave = _TermWave()


# ── Low-level packet helpers ──────────────────────────────────────────────────

def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Client disconnected")
        buf += chunk
    return buf


def _recv_packet(sock: socket.socket) -> bytes:
    length = struct.unpack(">I", _recv_exact(sock, 4))[0]
    return _recv_exact(sock, length)


def _send_packet(sock: socket.socket, payload: bytes):
    sock.sendall(struct.pack(">I", len(payload)) + payload)


def _send_json(sock: socket.socket, obj: dict):
    _send_packet(sock, json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def _send_audio(sock: socket.socket, text: str):
    _send_packet(sock, synthesize_to_bytes(text))


# ── Logging ───────────────────────────────────────────────────────────────────

def _log(speaker: str, text: str, **extra):
    if not text:
        return
    ts = datetime.now().isoformat(timespec="seconds")
    with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {speaker} (mobile): {text}\n")
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            history = []
    entry = {"timestamp": ts, "speaker": speaker, "text": text, "channel": "android"}
    entry.update(extra)
    history.append(entry)
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Folder-picker via phone list ─────────────────────────────────────────────

def _ask_pick(sock: socket.socket, message: str, options: list[str]) -> int:
    """
    Send a pick-list to the phone, wait for {"pick": index}.
    Returns the chosen index, or -1 if cancelled.
    """
    _send_json(sock, {"type": "pick", "message": message, "options": options})
    _send_audio(sock, message)

    reply_bytes = _recv_packet(sock)
    try:
        reply = json.loads(reply_bytes.decode("utf-8"))
        return int(reply.get("pick", -1))
    except Exception:
        return -1


# ── Confirm via phone buttons ─────────────────────────────────────────────────

def _ask_confirm(sock: socket.socket, message: str, item: str = "") -> bool:
    """
    Send confirm question to phone (JSON + audio), wait for {"answer":"yes/no"}.
    Returns True if user tapped Yes.
    """
    _send_json(sock, {"type": "confirm", "message": message, "item": item})
    _send_audio(sock, message)

    reply_bytes = _recv_packet(sock)
    try:
        reply = json.loads(reply_bytes.decode("utf-8"))
        return reply.get("answer", "no").lower() in ("yes", "haan", "ji", "1")
    except Exception:
        return False


# ── Client handler ────────────────────────────────────────────────────────────

def _handle_client(conn: socket.socket, addr):
    print(f"  \033[38;5;82m[connected]\033[0m  {addr}")
    try:
        while True:
            # Step 1: receive packet — may be a control signal or audio
            raw = _recv_packet(conn)

            # Check for control packets (valid JSON sent before the audio)
            try:
                ctrl = json.loads(raw.decode("utf-8"))
                if ctrl.get("type") == "start_speaking":
                    _wave.start()
                    continue
            except (UnicodeDecodeError, ValueError):
                pass  # not JSON → it's the audio WAV

            wav_bytes = raw
            _wave.stop()   # clears the scrolling waveform line

            tmp_path  = TEMP_AUDIO_DIR / f"mobile_{int(time.time())}.wav"
            tmp_path.write_bytes(wav_bytes)

            english_text = transcribe_and_translate(str(tmp_path))
            print(f"  \033[38;5;51m[heard]\033[0m   {english_text}")
            _log("You", english_text)

            if is_goodbye(english_text):
                farewell = "اللہ حافظ۔"
                _send_json(conn, {"type": "response", "text": farewell, "action": "goodbye", "result": ""})
                _send_audio(conn, farewell)
                _log("Arif", farewell, action="goodbye")
                print(f"\n  \033[38;5;214m\033[1mاللہ حافظ — Shutting down Arif.\033[0m\n")
                conn.close()
                sys.exit(0)

            if not english_text.strip():
                reply = "معاف کیجیے، سمجھ نہیں آیا۔"
                _send_json(conn, {"type": "response", "text": reply, "action": "none", "result": ""})
                _send_audio(conn, reply)
                continue

            action   = parse_intent(english_text, navigator.get_current_dir())
            act_name = action.get("action", "")
            print(f"  \033[38;5;242m[action]\033[0m  {action}")

            # Step 2: folder-picker gate for open_folder
            if act_name == "open_folder":
                target_path = action.get("args", {}).get("path", "")
                target_name = Path(target_path).name

                if Path(target_path).exists():
                    if not _ask_confirm(conn, f"کیا یہ فولڈر کھولوں: {target_name}؟", target_name):
                        cancel = "ٹھیک ہے، منسوخ کر دیا۔"
                        _send_json(conn, {"type": "response", "text": cancel, "action": "cancelled", "result": ""})
                        _send_audio(conn, cancel)
                        _log("Arif", cancel, action="cancelled")
                        continue
                else:
                    search_dirs = list(dict.fromkeys([
                        navigator.get_current_dir(),
                        str(Path(target_path).parent),
                    ]))
                    candidates = []
                    for d in search_dirs:
                        for c in find_candidates(target_name, d):
                            if c not in candidates:
                                candidates.append(c)

                    if not candidates:
                        reply = f"کوئی فولڈر نہیں ملا جس کا نام '{target_name}' سے ملتا ہو۔"
                        _send_json(conn, {"type": "response", "text": reply, "action": "not_found", "result": ""})
                        _send_audio(conn, reply)
                        _log("Arif", reply)
                        continue

                    folder_names = [Path(c).name for c in candidates]
                    idx = _ask_pick(conn, "کونسا فولڈر کھولوں؟", folder_names)

                    if idx < 0 or idx >= len(candidates):
                        cancel = "ٹھیک ہے، منسوخ کر دیا۔"
                        _send_json(conn, {"type": "response", "text": cancel, "action": "cancelled", "result": ""})
                        _send_audio(conn, cancel)
                        _log("Arif", cancel, action="cancelled")
                        continue

                    action["args"]["path"] = candidates[idx]

                action["needs_confirmation"] = False

            # Step 3a: name-verification gate (folder/file create or delete)
            if act_name in ("create_folder", "create_file", "delete"):
                item_path = action.get("args", {}).get("path", "")
                item_name = Path(item_path).name if item_path else "?"
                kind  = "فائل" if act_name == "create_file" else "فولڈر"
                verb  = "مٹانا" if act_name == "delete" else "بنانا"
                question = f"{verb} ہے: {item_name} — کیا یہی نام ہے {kind} کا؟"
                if not _ask_confirm(conn, question, item_name):
                    cancel = "ٹھیک ہے، منسوخ کر دیا۔"
                    _send_json(conn, {"type": "response", "text": cancel, "action": "cancelled", "result": ""})
                    _send_audio(conn, cancel)
                    _log("Arif", cancel, action="cancelled")
                    continue

            # Step 2b: general confirmation gate
            if action.get("needs_confirmation"):
                question = f"کیا آپ واقعی چاہتے ہیں کہ میں یہ کروں: {action.get('reply_urdu', '')}؟"
                if not _ask_confirm(conn, question):
                    cancel = "ٹھیک ہے، منسوخ کر دیا۔"
                    _send_json(conn, {"type": "response", "text": cancel, "action": "cancelled", "result": ""})
                    _send_audio(conn, cancel)
                    _log("Arif", cancel, action="cancelled")
                    continue

            # Step 3: execute
            result = execute(action)
            print(f"  \033[38;5;82m[result]\033[0m  {result}")

            if act_name == "where_am_i":
                reply = path_to_urdu(result)
            else:
                reply = action.get("reply_urdu", "ہو گیا۔")

            _log("Arif", reply, action=act_name, result=result)
            _send_json(conn, {"type": "response", "text": reply, "action": act_name, "result": result})
            _send_audio(conn, reply)

    except ConnectionError as e:
        print(f"  \033[38;5;196m[disconnected]\033[0m  {addr}: {e}")
    except Exception as e:
        print(f"  \033[38;5;196m[error]\033[0m  {e}")
        try:
            err = "معاف کیجیے، سرور پر کچھ مسئلہ ہو گیا۔"
            _send_json(conn, {"type": "response", "text": err, "action": "error", "result": str(e)})
            _send_audio(conn, err)
        except Exception:
            pass
    finally:
        conn.close()


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(1)
        print(f"  \033[38;5;82m[server]\033[0m  Listening on port {PORT} — open Android app and connect.\n")
        while True:
            conn, addr = srv.accept()
            _handle_client(conn, addr)


if __name__ == "__main__":
    main()
