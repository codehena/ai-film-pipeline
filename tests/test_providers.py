"""Offline tests for provider helpers and tool lookup (no network)."""
import io
import wave

import pytest

from pipeline.common import config
from pipeline.common.retry import is_transient
from pipeline.providers import gemini
from pipeline.smoke import pick


class FakeApiError(Exception):
    def __init__(self, code):
        self.code = code


@pytest.mark.parametrize("code,expected", [(429, True), (503, True), (400, False), (404, False)])
def test_sdk_errors_with_code_attribute(code, expected):
    assert is_transient(FakeApiError(code)) is expected


def pcm(seconds=0.5, rate=24000):
    return b"\x00\x00" * int(seconds * rate)


def test_raw_pcm_is_wrapped_in_wav(tmp_path):
    info = gemini.save_audio(pcm(), "audio/L16;codec=pcm;rate=24000", tmp_path / "a.wav")
    assert info["sample_rate"] == 24000 and info["duration_s"] == 0.5


def test_complete_wav_is_not_wrapped_twice(tmp_path):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm(1.0))
    out = tmp_path / "b.wav"
    info = gemini.save_audio(buf.getvalue(), "audio/wav", out)
    assert out.read_bytes() == buf.getvalue()
    assert info["duration_s"] == 1.0


def test_style_is_kept_out_of_spoken_text():
    contents = gemini.build_tts_contents("ሰላም", "calm, warm", "speech_metadata")
    part = contents[0].parts[0]
    assert part.text == "ሰላም"
    assert part.speech_metadata.style == "calm, warm"
    assert gemini.build_tts_contents("ሰላም", "calm", "none") == "ሰላም"


def test_pick_prefers_newest_matching_model():
    models = ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash", "x-tts"]
    assert pick(models, ["flash-lite"]) == "gemini-3.5-flash-lite"
    assert pick(models, ["flash"], ["lite"]) == "gemini-3.8-flash"
    assert pick(models, ["nothing"]) is None


def test_find_tool_respects_env_override(tmp_path, monkeypatch):
    fake = tmp_path / "ffmpeg.exe"
    fake.write_bytes(b"")
    monkeypatch.setenv("FFMPEG_PATH", str(fake))
    assert config.find_tool("ffmpeg") == str(fake)
    monkeypatch.setenv("FFMPEG_PATH", str(tmp_path / "missing.exe"))
    with pytest.raises(config.MissingTool):
        config.find_tool("ffmpeg")


def test_image_requests_a_model_cannot_honour_are_refused(tmp_path):
    from pipeline.common.retry import PermanentError
    from pipeline.providers import cloudflare
    with pytest.raises(PermanentError, match="width/height"):
        cloudflare.text_to_image(model="@cf/black-forest-labs/flux-1-schnell", prompt="x",
                                 params={"width": 512}, out_path=tmp_path / "a.jpg")
    with pytest.raises(PermanentError, match="reference"):
        cloudflare.text_to_image(model="@cf/black-forest-labs/flux-1-schnell", prompt="x",
                                 params={}, out_path=tmp_path / "a.jpg", references=[tmp_path / "r.jpg"])


def test_image_format_sniffing():
    from pipeline.providers.cloudflare import image_format
    assert image_format(b"\xff\xd8\xff\xe0") == "jpeg"
    assert image_format(b"\x89PNG\r\n\x1a\n....") == "png"
    assert image_format(b"GIF89a") == "unknown"
