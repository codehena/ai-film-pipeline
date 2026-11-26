"""Smoke test: call each provider once and log latency to runs.jsonl.

Answers "what works today?" before any real generation:
  1. Which Gemini and Cloudflare models can this key see?
  2. Does a Gemini text call work?
  3. Does Gemini TTS speak Amharic? (writes outputs/smoke/tts_am.wav: listen to it)
  4. Does a Cloudflare FLUX image call work? (writes outputs/smoke/flux.<ext>)
  5. Is FFmpeg reachable?

Every step is independent: one failure is logged and reported, the rest still run.
Nothing here is cached; each run makes real calls (all on free tiers).
"""
from __future__ import annotations

import re
import subprocess
import time

from .common import config
from .common.modelcall import logged_call
from .providers import cloudflare, gemini

TTS_TEST_TEXT = "ሰላም። ይህ የድምፅ ሙከራ ነው።"  # "Hello. This is a voice test."
TTS_TEST_STYLE = "calm, warm, unhurried"
DEFAULT_VOICE = "Kore"
# Not returned by models.list, but callable on v1beta (found 2026-11-25, see FAILURES.md F-06)
TTS_CANDIDATES = [
    "gemini-3.8-flash-tts",
    "gemini-2.5-flash-preview-tts",
]
IMAGE_PROMPT = "a clay coffee pot on a wooden stool, warm morning light, hand-painted look"
IMAGE_PARAMS = {"steps": 4}


def _version_key(name: str) -> tuple:
    nums = re.findall(r"\d+(?:\.\d+)?", name)
    return (float(nums[0]) if nums else 0.0, "preview" not in name, name)


def pick(models: list[str], must: list[str], avoid: list[str] = ()) -> str | None:
    """Newest model whose name contains every word in `must` and none in `avoid`."""
    ok = [m for m in models if all(w in m for w in must) and not any(w in m for w in avoid)]
    return max(ok, key=_version_key) if ok else None


def _step(results: dict, label: str, fn) -> object:
    start = time.perf_counter()
    try:
        value = fn()
        results[label] = ("ok", time.perf_counter() - start, value)
        return value
    except Exception as e:  # report and continue: smoke tests every provider
        results[label] = ("FAILED", time.perf_counter() - start, f"{type(e).__name__}: {e}"[:300])
        return None


def run(text_model: str | None = None, tts_model: str | None = None,
        image_model: str | None = None) -> dict:
    out = config.output_dir("smoke")
    results: dict = {}

    gem_models = _step(results, "gemini: list models", lambda: logged_call(
        gemini.list_models, stage="smoke", shot=None, provider="gemini",
        model="models.list", params={})) or []
    cf_models = _step(results, "cloudflare: search flux models", lambda: logged_call(
        lambda: cloudflare.search_models("flux"), stage="smoke", shot=None,
        provider="cloudflare", model="models.search", params={"search": "flux"})) or []

    text_model = text_model or pick(gem_models, ["flash-lite"], ["tts", "image", "live"]) \
        or pick(gem_models, ["flash"], ["tts", "image", "live"])
    tts_model = tts_model or pick(gem_models, ["flash", "tts"])
    image_model = image_model or pick(cf_models, ["flux-1-schnell"]) \
        or "@cf/black-forest-labs/flux-1-schnell"

    if text_model:
        _step(results, f"gemini text: {text_model}", lambda: logged_call(
            lambda: gemini.generate_text(text_model, "Reply with the single word OK."),
            stage="smoke", shot=None, provider="gemini", model=text_model, params={}))

    # TTS models are not always listed by models.list, so probe likely ids in order.
    # Every probe is logged, so runs.jsonl records which ids exist and which do not.
    candidates = [tts_model] if tts_model else TTS_CANDIDATES
    wav = out / "tts_am.wav"
    params = {"voice": DEFAULT_VOICE, "style": TTS_TEST_STYLE,
              "style_mode": "speech_metadata", "language_code": "am"}
    tts_model = None
    for cand in candidates:
        label = f"gemini tts (Amharic): {cand}"
        _step(results, label, lambda cand=cand: logged_call(
            lambda: gemini.synthesize(model=cand, text=TTS_TEST_TEXT,
                                      voice_name=DEFAULT_VOICE, style=TTS_TEST_STYLE,
                                      style_mode="speech_metadata", language_code="am",
                                      out_path=wav),
            stage="smoke", shot=None, provider="gemini", model=cand, params=params,
            output=config.rel(wav)))
        if results[label][0] == "ok":
            tts_model = cand
            break
    if tts_model is None:
        results["gemini tts: no working model"] = ("FAILED", 0.0, f"tried {candidates}")

    img = out / "flux.png"
    _step(results, f"cloudflare image: {image_model}", lambda: logged_call(
        lambda: cloudflare.text_to_image(model=image_model, prompt=IMAGE_PROMPT,
                                         params=IMAGE_PARAMS, out_path=img),
        stage="smoke", shot=None, provider="cloudflare", model=image_model,
        params=IMAGE_PARAMS, seed=None, output=config.rel(img)))

    def ffmpeg_version():
        exe = config.find_tool("ffmpeg")
        first = subprocess.run([exe, "-version"], capture_output=True, text=True).stdout
        return f"{first.splitlines()[0]}  ({exe})"
    _step(results, "ffmpeg", ffmpeg_version)

    print("\nSmoke test results")
    for label, (status, seconds, value) in results.items():
        print(f"  [{status:6}] {label}  ({seconds:.2f} s)")
        if status != "ok" or label == "ffmpeg":
            print(f"           {value}")
    print("\nModels visible to your Gemini key (tts / flash):")
    for m in gem_models:
        if "tts" in m or "flash" in m:
            print(f"  {m}")
    print("Cloudflare FLUX models:", ", ".join(cf_models) or "(none listed)")
    print("\nChosen: text =", text_model, "| tts =", tts_model, "| image =", image_model)
    print("Listen to outputs/smoke/tts_am.wav; ask a native speaker if the Amharic sounds right.")
    return results
