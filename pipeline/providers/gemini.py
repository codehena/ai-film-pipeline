"""Gemini API: text generation and text-to-speech (TTS).

TTS returns raw 16-bit PCM audio (mime type like "audio/L16;codec=pcm;rate=24000").
We wrap it in a WAV header so FFmpeg and media players can read it.
"""
from __future__ import annotations

import re
import wave
from pathlib import Path

from ..common import config

API_VERSION = "v1beta"
_client = None


def client():
    global _client
    if _client is None:
        from google import genai
        from google.genai import types

        # The SDK defaults to the stable v1 API, which rejects speechConfig / speechMetadata.
        # Speech generation lives on v1beta (FAILURES.md F-06).
        _client = genai.Client(
            api_key=config.get_secret("GEMINI_API_KEY"),
            http_options=types.HttpOptions(api_version=API_VERSION),
        )
    return _client


def list_models() -> list[str]:
    return sorted(m.name.removeprefix("models/") for m in client().models.list())


def generate_text(model: str, prompt: str) -> str:
    return client().models.generate_content(model=model, contents=prompt).text or ""


def transcribe(model: str, wav_path: Path, language: str = "Amharic") -> str:
    """Speech-to-text with a Gemini text model (used to check narration, not to make it)."""
    from google.genai import types

    response = client().models.generate_content(model=model, contents=[
        types.Part.from_bytes(data=Path(wav_path).read_bytes(), mime_type="audio/wav"),
        f"Transcribe this short {language} speech exactly, in its own script. Output only the words.",
    ])
    return (response.text or "").strip()


def build_tts_contents(text: str, style: str | None, style_mode: str):
    """How the delivery instruction reaches the model, kept apart from the spoken words.

    style_mode:
      "speech_metadata": the SDK's Part.speech_metadata.style field (style is never spoken)
      "prompt_prefix":   the documented fallback, "<style>: <text>" in one string
      "none":            words only
    """
    from google.genai import types

    if not style or style_mode == "none":
        return text
    if style_mode == "speech_metadata":
        part = types.Part(text=text, speech_metadata=types.SpeechMetadata(style=style))
        return [types.Content(role="user", parts=[part])]
    if style_mode == "prompt_prefix":
        return f"Read the following aloud in this style: {style}.\n\n{text}"
    raise ValueError(f"unknown style_mode {style_mode!r}")


def synthesize(
    *, model: str, text: str, voice_name: str, style: str | None, style_mode: str,
    language_code: str | None, out_path: Path,
) -> dict:
    """Speak `text` and write a WAV file. Returns info about the audio for logging."""
    from google.genai import types

    speech = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
        ),
        language_code=language_code,
    )
    response = client().models.generate_content(
        model=model,
        contents=build_tts_contents(text, style, style_mode),
        config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=speech),
    )
    candidate = (response.candidates or [None])[0]
    parts = candidate.content.parts if candidate and candidate.content else None
    if not parts or not parts[0].inline_data or not parts[0].inline_data.data:
        reason = getattr(candidate, "finish_reason", None)
        raise RuntimeError(f"TTS response contained no audio (finish_reason={reason})")
    blob = parts[0].inline_data
    return save_audio(blob.data, blob.mime_type or "", out_path)


def save_audio(data: bytes, mime: str, out_path: Path) -> dict:
    """Newer TTS models return a complete WAV file; older ones return raw PCM (audio/L16)."""
    if data[:4] == b"RIFF":
        Path(out_path).write_bytes(data)
    else:
        write_wav(out_path, data, _sample_rate(mime))
    with wave.open(str(out_path), "rb") as w:
        rate, frames = w.getframerate(), w.getnframes()
    return {"mime": mime, "sample_rate": rate, "duration_s": round(frames / rate, 3)}


def _sample_rate(mime: str) -> int:
    m = re.search(r"rate=(\d+)", mime)
    return int(m.group(1)) if m else 24000


def write_wav(path: Path, pcm: bytes, rate: int) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
