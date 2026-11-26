"""Cloudflare Workers AI: text-to-image (FLUX models).

Models differ in what they accept, and sending a field a model ignores is
worse than useless: it puts a fake guarantee into the cache key. ImageModel
records what each model *verifiably* supports (from the model schema API and
our own probes, logged as stage "probe" in runs.jsonl), and text_to_image()
refuses requests a model cannot honour.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

import requests

from ..common import config
from ..common.retry import PermanentError

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai"
TIMEOUT_S = 120


@dataclass(frozen=True)
class ImageModel:
    id: str
    multipart: bool        # request body is multipart/form-data (else JSON)
    supports_size: bool    # honours width/height
    max_references: int    # reference images it can condition on (0 = text only)
    seed_honoured: bool    # same seed -> same image
    output: str            # image format it returns
    licence: str


MODELS = {
    # schema API 2026-11-25: input is {prompt, steps<=8} only
    "@cf/black-forest-labs/flux-1-schnell": ImageModel(
        "@cf/black-forest-labs/flux-1-schnell", multipart=False, supports_size=False,
        max_references=0, seed_honoured=False, output="jpeg", licence="Apache-2.0"),
    # multipart; probe 2026-11-25: width/height honoured (1024x576 JPEG returned), same "seed"
    # gave two different compositions -> not honoured. References: see FAILURES/EXPERIMENTS.
    "@cf/black-forest-labs/flux-2-klein-4b": ImageModel(
        "@cf/black-forest-labs/flux-2-klein-4b", multipart=True, supports_size=True,
        max_references=4, seed_honoured=False, output="jpeg", licence="Apache-2.0"),
}


def model_info(model: str) -> ImageModel:
    try:
        return MODELS[model]
    except KeyError:
        raise PermanentError(f"unknown image model {model!r}; known: {sorted(MODELS)}") from None


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.get_secret('CLOUDFLARE_API_TOKEN')}"}


def _base() -> str:
    return API.format(account=config.get_secret("CLOUDFLARE_ACCOUNT_ID"))


def search_models(term: str) -> list[str]:
    r = requests.get(f"{_base()}/models/search", params={"search": term},
                     headers=_headers(), timeout=30)
    r.raise_for_status()
    return sorted(m["name"] for m in r.json().get("result", []))


def image_format(data: bytes) -> str:
    if data[:2] == b"\xff\xd8":
        return "jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return "unknown"


def text_to_image(*, model: str, prompt: str, params: dict, out_path: Path,
                  references: list[Path] = ()) -> dict:
    """Run a FLUX model and write the image. Returns info for logging.

    params may hold width/height/steps; references are image files to condition on.
    Anything the model cannot honour is refused rather than silently ignored.
    """
    info = model_info(model)
    if references and len(references) > info.max_references:
        raise PermanentError(f"{model} takes at most {info.max_references} reference images")
    if not info.supports_size and ({"width", "height"} & set(params)):
        raise PermanentError(f"{model} does not accept width/height")

    url = f"{_base()}/run/{model}"
    if info.multipart:
        files = {"prompt": (None, prompt)}
        files |= {k: (None, str(v)) for k, v in params.items()}
        for i, ref in enumerate(references):
            files[f"input_image_{i}"] = (Path(ref).name, Path(ref).read_bytes(), "image/jpeg")
        r = requests.post(url, files=files, headers=_headers(), timeout=TIMEOUT_S)
    else:
        r = requests.post(url, json={"prompt": prompt, **params}, headers=_headers(),
                          timeout=TIMEOUT_S)
    if r.status_code >= 400:  # keep Cloudflare's explanation (e.g. a rejected field) in the log
        raise requests.HTTPError(f"HTTP {r.status_code}: {r.text[:400]}", response=r)
    if r.headers.get("content-type", "").startswith("image/"):
        data = r.content
    else:
        result = r.json().get("result") or {}
        if not result.get("image"):
            raise RuntimeError(f"no image in response: {str(r.json())[:300]}")
        data = base64.b64decode(result["image"])
    fmt = image_format(data)
    if fmt != info.output:
        raise PermanentError(f"{model} returned {fmt}, expected {info.output}")
    Path(out_path).write_bytes(data)
    return {"bytes": len(data), "format": fmt}
