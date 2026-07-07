"""TCP server for the JARVIS-Arif Android app.
Receives audio from the phone over WiFi, runs the full pipeline, sends the Urdu reply back.
Run this instead of main.py when using the mobile app.

Protocol (both directions): [4-byte big-endian uint32 length][payload bytes]
  Phone → PC : WAV audio bytes
  PC → Phone : UTF-8 JSON  {"heard":..., "action":..., "result":..., "reply_urdu":...,
                             "needs_confirmation": bool}
"""
import os
import sys
import json
import socket
import struct
import time

# Same env fixes as stt.py (must be set before importing transformers)
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from datetime import datetime
from config import TEMP_AUDIO_DIR, CONVERSATION_LOG_FILE
from stt import transcribe_and_translate
from intent import parse_intent
from executor import execute

HOST = "0.0.0.0"
PORT = 5050

YES_WORDS = ["yes", "haan", "han", "ji haan", "ji", "sure", "ok", "okay"]


def _log(speaker: str, text: str):
    if not text:
        return
    with open(CONVERSATION_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {speaker} (mobile): {text}\n")


def _recv_exact(sock: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("Client disconnected")
        buf += chunk
    return buf


def _recv_audio(sock: socket.socket) -> str:
    """Receive one length-prefixed audio blob, save as WAV, return path."""
    length = struct.unpack(">I", _recv_exact(sock, 4))[0]
    audio_bytes = _recv_exact(sock, length)
    path = str(TEMP_AUDIO_DIR / f"mobile_{int(time.time())}.wav")
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return path


def _send_json(sock: socket.socket, data: dict):
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    sock.sendall(struct.pack(">I", len(payload)) + payload)


def _handle_client(conn: socket.socket, addr):
    print(f"[server] connected: {addr}")
    try:
        while True:
            # ── Step 1: receive audio ─────────────────────────────────────────
            audio_path = _recv_audio(conn)

            english_text = transcribe_and_translate(audio_path)
            print(f"[heard]  {english_text}")
            _log("You", english_text)

            if not english_text.strip():
                _send_json(conn, {"reply_urdu": "معاف کیجیے، سمجھ نہیں آیا۔", "action": "none",
                                  "result": "", "heard": "", "needs_confirmation": False})
                continue

            action = parse_intent(english_text)
            print(f"[action] {action}")

            # ── Step 2: confirmation gate ─────────────────────────────────────
            if action.get("needs_confirmation"):
                confirm_prompt = f"کیا آپ واقعی چاہتے ہیں کہ میں یہ کروں: {action.get('reply_urdu', '')}؟"
                _send_json(conn, {
                    "heard": english_text,
                    "action": action.get("action"),
                    "result": "",
                    "reply_urdu": confirm_prompt,
                    "needs_confirmation": True,
                })
                # Wait for the user's yes/no audio
                confirm_path = _recv_audio(conn)
                confirm_text = transcribe_and_translate(confirm_path).lower()
                _log("You", confirm_text)
                if not any(w in confirm_text for w in YES_WORDS):
                    _send_json(conn, {"reply_urdu": "ٹھیک ہے، منسوخ کر دیا۔", "action": "cancelled",
                                      "result": "", "heard": confirm_text, "needs_confirmation": False})
                    continue

            # ── Step 3: execute ───────────────────────────────────────────────
            result = execute(action)
            print(f"[result] {result}")

            if action.get("action") == "where_am_i":
                reply_urdu = f"میں اس وقت اس مقام پر ہوں: {result}"
            else:
                reply_urdu = action.get("reply_urdu", "ہو گیا۔")

            _log("Arif", reply_urdu)
            _send_json(conn, {
                "heard": english_text,
                "action": action.get("action"),
                "result": result,
                "reply_urdu": reply_urdu,
                "needs_confirmation": False,
            })

    except ConnectionError as e:
        print(f"[server] disconnected: {addr} ({e})")
    except Exception as e:
        print(f"[server] error: {e}")
        try:
            _send_json(conn, {"reply_urdu": "معاف کیجیے، سرور پر کچھ مسئلہ ہو گیا۔",
                              "action": "error", "result": str(e), "heard": "",
                              "needs_confirmation": False})
        except Exception:
            pass
    finally:
        conn.close()
        print(f"[server] connection closed: {addr}")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as srv:
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PORT))
        srv.listen(1)
        print(f"JARVIS-Arif TCP server ready on port {PORT}")
        print("Open the Android app, enter this PC's WiFi IP, and connect.")
        while True:
            conn, addr = srv.accept()
            _handle_client(conn, addr)


if __name__ == "__main__":
    main()
