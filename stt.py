"""Speech-to-English via a local HuggingFace Whisper model. Runs on GPU if available.
Kept local (instead of Groq) so every utterance doesn't burn a Groq API call --
only the intent-parsing step (intent.py) still talks to Groq.
"""
import os

# Force torch-only backend -- the global env also has a broken TensorFlow install
# (unrelated protobuf conflict) that transformers would otherwise try to import.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
# Global tensorboard's compiled protobufs are older than the global protobuf package;
# pure-Python protobuf avoids the C++ descriptor-pool crash (we never use tensorboard).
os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")

import torch
from transformers import pipeline

from config import WHISPER_MODEL_ID

_device = 0 if torch.cuda.is_available() else -1
_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

_pipe = pipeline(
    "automatic-speech-recognition",
    model=WHISPER_MODEL_ID,
    device=_device,
    torch_dtype=_dtype,
)


def transcribe_and_translate(audio_path: str) -> str:
    result = _pipe(audio_path, generate_kwargs={"task": "translate"})
    return result["text"].strip()
