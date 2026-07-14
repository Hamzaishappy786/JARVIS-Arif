# Arif: Urdu Voice Assistant (JARVIS-style)

> **Current focus:** This repo has ONE goal — build "Arif", a voice assistant that
> takes spoken Urdu commands and performs actions on the user's Windows PC (file/folder
> operations, closing apps, etc.), then replies with Urdu voice. Only work on Arif.

<p align="center">⬇️ ⬇️ ⬇️ CLICK ME ⬇️ ⬇️ ⬇️</p>

<p align="center">➡️ ➡️ ➡️ &nbsp;&nbsp;&nbsp;&nbsp; <a href="https://pypi.org/project/jarvis-arif/"><img src="https://img.shields.io/pypi/v/jarvis-arif?style=for-the-badge&logo=pypi&label=pip+install+jarvis-arif"/></a> &nbsp;&nbsp;&nbsp;&nbsp; ⬅️ ⬅️ ⬅️</p>

<p align="center">⬆️ ⬆️ ⬆️ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ⬆️ ⬆️ ⬆️</p>

## About the user / interaction style
- The user speaks **Urdu** (romanized meaning like "falani folder mein chale jao",
  "falana folder bana do", "meri saari files close kar do").
- The wake word / assistant name is **"Arif"**.
- Arif replies back in **Urdu voice**.
- Platform: **Windows 11**, primary language Python. Shell is PowerShell.

## Pipeline (voice command → action → voice reply)

```
[Mic] → [Wake word "Arif"] → [Record until silence (VAD)]
     → [STT + translate Urdu→English]   (Whisper)
     → [Intent parsing → structured action JSON]   (Groq LLM)
     → [Confirmation gate for risky actions]
     → [Executor runs the action on Windows]
     → [Compose Urdu reply] → [TTS Piper → .wav] → [Play audio]
     → loop
```

### Stage details
1. **Wake word** — detect "Arif" before recording (openWakeWord / Porcupine), so the
   system isn't parsing everything it hears.
2. **Record** — capture mic audio; use Voice Activity Detection (VAD, e.g. webrtcvad
   or silero-vad) to stop recording when the user stops speaking.
3. **STT + translation** — convert Urdu speech directly to **English text**.
   - **Whisper** handles this in one step via its `translate` task (non-English speech →
     English text). Options: local `faster-whisper` (GPU) OR **Groq's hosted
     `whisper-large-v3`** audio endpoint (much faster, no local compute). Prefer Groq's
     audio API to keep latency low.
4. **Intent parsing** — send the English text to **Groq** (chat completions). Groq must
   return a **structured JSON action** (use JSON mode / tool-calling), NOT free prose,
   so the executor can act reliably. See "Action schema" below.
5. **Confirmation gate** — destructive/ambiguous actions (delete, overwrite, move,
   close apps, actions spanning 2+ files) require a spoken Urdu confirmation before
   running. Read-only/create actions can run directly.
6. **Executor** — perform the action with Python: `os`, `shutil`, `pathlib`,
   `subprocess`, `psutil` (list/kill processes), `pygetwindow`/`pywin32` (windows).
7. **TTS** — synthesize the Urdu reply with **Piper** (`ur_PK-fasih-medium`) to a `.wav`,
   then play it. Working code already validated (see below).

## Action schema (Groq output contract)
Groq should return an object the executor can dispatch on, e.g.:
```json
{
  "action": "create_folder | delete | move | copy | open_app | close_app | close_all | list | open_folder | none",
  "args": { "path": "...", "target": "...", "name": "..." },
  "needs_confirmation": true,
  "reply_urdu": "<short Urdu sentence to speak back>"
}
```
Keep the list of valid `action` values and their args as the single source of truth the
executor and the Groq system prompt both reference.

## Safety rules (important)
- **Confirm before destructive actions**: delete, overwrite, move, mass-close apps, or
  anything touching 2+ files.
- **Allowlist directories**: restrict file operations to user-approved roots; refuse
  paths outside them.
- Never run shell/exec content that came from the transcription without validation.
- Log every executed action (timestamp, transcript, action, result) for auditability.
- Support a **dry-run** mode during development.

## Known-good building blocks
### Piper TTS (Urdu) — verified working
```python
from piper import PiperVoice
import wave

model_path = "ur_PK-fasih-medium.onnx"
config_path = "ur_PK-fasih-medium.onnx.json"
voice = PiperVoice.load(model_path, config_path=config_path)

text = "آپ کا کیا حال ہے؟"
with wave.open("saul_urdu_response.wav", "wb") as wav_file:
    voice.synthesize_wav(text, wav_file)
```

## Tech stack (planned)
- **Python** (Windows)
- Mic capture: `sounddevice` / `pyaudio`; VAD: `webrtcvad` or `silero-vad`
- Wake word: `openWakeWord` or `pvporcupine`
- STT+translate: Groq `whisper-large-v3` audio API (or local `faster-whisper`)
- LLM intent: **Groq** chat completions (JSON mode / tool calling)
- TTS: **Piper** (`ur_PK-fasih-medium`)
- Audio playback: `sounddevice` / `simpleaudio`
- System actions: `os`, `shutil`, `pathlib`, `subprocess`, `psutil`, `pygetwindow`

## Config / secrets
- Groq API key via environment variable (e.g. `GROQ_API_KEY`) or `.env` — never hardcode.

## Conventions
- Keep the pipeline **modular**: separate files/modules per stage (wake, stt, intent,
  executor, tts) so each can be tested in isolation.
- Test each stage standalone before wiring the full loop.

## Status
- [x] Piper Urdu TTS validated
- [x] Project scaffolded: config.py, recorder.py, stt.py, intent.py, executor.py, tts.py, main.py
- [x] Isolated venv at `.venv/` created with `--system-site-packages` (reuses the machine's
      existing torch==1.12.1+cu113 install instead of downloading a second copy; do NOT
      `pip install` into the global Python directly -- it's shared with other tools like
      aider-chat and got its versions clobbered once already, then restored)
- [x] STT moved off Groq entirely -- runs locally via HF `openai/whisper-small` on the GTX 1050
      (task="translate", Urdu audio -> English text in one step, confirmed on cuda:0).
      Only intent.py still calls Groq (for the LLM intent-parsing step), to conserve API usage.
      transformers/tokenizers are pinned venv-local (4.40.0 / 0.19.1) because the global
      transformers install is independently broken (tokenizers/protobuf/tensorflow version
      rot from other tools) -- stt.py sets USE_TF=0, USE_FLAX=0, and
      PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python to route around that global rot.
- [x] Groq JSON-mode intent parsing and executor smoke-tested individually and pass
- [ ] Full interactive loop (`main.py`, hold F9 to talk) — needs a live human+mic to verify;
      not testable headlessly

## Run it
```
D:\JARVIS-ARIF\.venv\Scripts\python.exe main.py
```
Hold **F9**, speak in Urdu, release. Ctrl+C to quit.
