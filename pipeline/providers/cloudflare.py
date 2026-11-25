"""Cloudflare Workers AI: text-to-image (FLUX models)."""
from __future__ import annotations

import base64
from pathlib import Path

import requests

from ..common import config

API = "https://api.cloudflare.com/client/v4/accounts/{account}/ai"
TIMEOUT_S = 120


def _headers() -> dict:
    return {"Authorization": f"Bearer {config.get_secret('CLOUDFLARE_API_TOKEN')}"}


def _base() -> str:
    return API.format(account=config.get_secret("CLOUDFLARE_ACCOUNT_ID"))


def search_models(term: str) -> list[str]:
    r = requests.get(f"{_base()}/models/search", params={"search": term},
                     headers=_headers(), timeout=30)
    r.raise_for_status()
    return sorted(m["name"] for m in r.json().get("result", []))


def text_to_image(*, model: str, prompt: str, params: dict, out_path: Path) -> dict:
    """Run a FLUX model and write the image. Returns info for logging."""
    r = requests.post(f"{_base()}/run/{model}", json={"prompt": prompt, **params},
                      headers=_headers(), timeout=TIMEOUT_S)
    r.raise_for_status()
    if r.headers.get("content-type", "").startswith("image/"):
        data = r.content
    else:
        result = r.json().get("result") or {}
        if not result.get("image"):
            raise RuntimeError(f"no image in response: {str(r.json())[:300]}")
        data = base64.b64decode(result["image"])
    Path(out_path).write_bytes(data)
    return {"bytes": len(data)}
