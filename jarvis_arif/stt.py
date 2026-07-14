"""Speech-to-English via Groq Whisper large-v3 (translations endpoint)."""
from groq import Groq
from .config import GROQ_API_KEY

_client = Groq(api_key=GROQ_API_KEY)


def transcribe_and_translate(audio_path: str) -> str:
    with open(audio_path, "rb") as f:
        result = _client.audio.translations.create(
            file=(audio_path, f),
            model="whisper-large-v3",
            response_format="text",
            prompt="The speaker is using Urdu. Translate to English.",
        )
    return str(result).strip()


def transcribe_urdu_native(audio_path: str) -> str:
    """Native-Urdu-script transcription (no translation) -- used only for dictation,
    where the literal Urdu text (not an English gloss) must be typed into a document."""
    with open(audio_path, "rb") as f:
        result = _client.audio.transcriptions.create(
            file=(audio_path, f),
            model="whisper-large-v3",
            language="ur",
            response_format="text",
        )
    return str(result).strip()
