"""Stage: keyframes. Reference sheets first, then one square master image per shot.

    py -m pipeline keyframes            # every shot (cached shots cost nothing)
    py -m pipeline keyframes --shot s04 # one shot (its references are made if missing)

Reads:  storyboard.json -> image (model, size), style_block, characters, shots[].image_prompt, seed
Writes: outputs/keyframes/ref-<character>_<hash>.jpg   one reference sheet per character
        outputs/keyframes/<shot>_<hash>.jpg            one square master per shot

Consistency: every shot of a character is conditioned on that character's
reference sheet (if the model takes references) and repeats the exact same
description text. The reference sheet's FILE hash is part of each shot's cache
key, so a new reference sheet re-makes exactly the shots of that character.

Determinism: neither FLUX model on Workers AI honours a seed (probe 2026-11-25),
so the same request gives a new image every time. Reproducibility therefore comes
from the cache: outputs are kept and reused, never silently re-rolled. The shot's
`seed` is used as a *take number*: change it to deliberately re-roll that shot.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .common import MissingInput, config
from .common.cache import file_hash, keyframe_inputs, stable_hash
from .common.modelcall import run_model_step
from .common.retry import PermanentError
from .common.storyboard import select_shots
from .providers import cloudflare

STAGE = "keyframes"
EXT = "jpg"
PROMPT_VERSION = 1  # bump when the prompt templates below change
MAX_PROMPT_CHARS = 2048
NEGATIVE = "No text, no letters, no signature, no watermark, no border"
REF_TEMPLATE = ("Character reference sheet of {desc}. Full body, front view and back view "
                "side by side, standing, plain warm off-white background, even soft light")


@dataclass(frozen=True)
class ImageConfig:
    """The `image` block of the storyboard, plus what the chosen model can honour."""
    model: str
    width: int
    height: int
    reference_sheets: bool

    @classmethod
    def from_storyboard(cls, storyboard: dict) -> "ImageConfig":
        i = storyboard["image"]
        cfg = cls(i["model"], i["width"], i["height"], i.get("reference_sheets", True))
        cloudflare.model_info(cfg.model)  # fail fast on an unknown model
        return cfg

    @property
    def info(self) -> cloudflare.ImageModel:
        return cloudflare.model_info(self.model)

    def request_params(self) -> dict:
        """Only fields the model honours (a field it ignores would be a fake cache key)."""
        return {"width": self.width, "height": self.height} if self.info.supports_size else {}

    def use_references(self) -> bool:
        return self.reference_sheets and self.info.max_references > 0


def _clip(prompt: str) -> str:
    if len(prompt) > MAX_PROMPT_CHARS:
        raise PermanentError(f"prompt is {len(prompt)} chars; the model takes {MAX_PROMPT_CHARS}")
    return prompt


def reference_prompt(storyboard: dict, character: dict) -> str:
    desc = REF_TEMPLATE.format(desc=character["description"])
    return _clip(f"{desc}. Style: {storyboard['style_block']}. {NEGATIVE}.")


def shot_prompt(storyboard: dict, shot: dict) -> str:
    chars = {c["id"]: c for c in storyboard["characters"]}
    parts = [shot["image_prompt"].rstrip(".")]
    if shot["characters"]:
        who = "; ".join(chars[c]["description"] for c in shot["characters"])
        parts.append(f"Characters (stylised, faces simplified, seen from behind or at a distance): {who}")
    parts.append(f"Style: {storyboard['style_block']}")
    parts.append(NEGATIVE)
    return _clip(". ".join(parts) + ".")


def _params(cfg: ImageConfig) -> dict:
    return cfg.request_params() | {"prompt_version": PROMPT_VERSION}


def reference_inputs(storyboard: dict, character: dict, cfg: ImageConfig) -> dict:
    return {"stage": "keyframes-ref", "model": cfg.model, "params": _params(cfg),
            "prompt": reference_prompt(storyboard, character)}


def _folder(out_base: Path | None) -> Path:
    return (out_base or config.OUTPUTS) / STAGE


def reference_path(storyboard: dict, character: dict, out_base: Path | None = None) -> Path:
    cfg = ImageConfig.from_storyboard(storyboard)
    h = stable_hash(reference_inputs(storyboard, character, cfg))
    return _folder(out_base) / f"ref-{character['id']}_{h}.{EXT}"


def _shot_references(storyboard: dict, shot: dict, cfg: ImageConfig,
                     out_base: Path | None) -> list[Path]:
    if not cfg.use_references():
        return []
    chars = {c["id"]: c for c in storyboard["characters"]}
    refs = [reference_path(storyboard, chars[c], out_base) for c in shot["characters"]]
    return refs[: cfg.info.max_references]


def shot_inputs(storyboard: dict, shot: dict, cfg: ImageConfig, refs: list[Path]) -> dict:
    missing = [r.name for r in refs if not r.exists()]
    if missing:
        raise MissingInput(f"{shot['id']}: reference sheet(s) {missing} not made yet; "
                           "run `py -m pipeline keyframes`")
    return keyframe_inputs(storyboard, shot, model=cfg.model, params=_params(cfg),
                           reference_hashes=[file_hash(r) for r in refs])


def keyframe_path(storyboard: dict, shot: dict, out_base: Path | None = None) -> Path:
    """Where this shot's keyframe lives. Motion and assembly use this, so the hash is the contract."""
    cfg = ImageConfig.from_storyboard(storyboard)
    refs = _shot_references(storyboard, shot, cfg, out_base)
    h = stable_hash(shot_inputs(storyboard, shot, cfg, refs))
    return _folder(out_base) / f"{shot['id']}_{h}.{EXT}"


def run(storyboard: dict, only: list[str] | None = None, *, generate=None,
        out_base: Path | None = None, log_path: Path | None = None) -> dict[str, Path]:
    """Make (or reuse) the reference sheets the selected shots need, then their keyframes."""
    generate = generate or cloudflare.text_to_image
    cfg = ImageConfig.from_storyboard(storyboard)
    shots = select_shots(storyboard, only)
    chars = {c["id"]: c for c in storyboard["characters"]}
    common = dict(provider="cloudflare", model=cfg.model, ext=EXT, out_base=out_base,
                  log_path=log_path)
    # the model ignores seeds; log that honestly next to the take number
    logged = cfg.request_params() | {"prompt_version": PROMPT_VERSION,
                                     "seed_honoured": cfg.info.seed_honoured}

    if cfg.use_references():
        needed = sorted({c for s in shots for c in s["characters"]})
        for cid in needed:
            char = chars[cid]
            before = reference_path(storyboard, char, out_base).exists()
            path = run_model_step(
                stage=STAGE, shot=f"ref-{cid}", params=logged, seed=None,
                inputs=reference_inputs(storyboard, char, cfg),
                produce=lambda p, char=char: generate(
                    model=cfg.model, prompt=reference_prompt(storyboard, char),
                    params=cfg.request_params(), out_path=p),
                **common)
            print(f"  ref-{cid}: {'cached' if before else 'generated'}  {config.rel(path)}")

    done: dict[str, Path] = {}
    for shot in shots:
        refs = _shot_references(storyboard, shot, cfg, out_base)
        before = keyframe_path(storyboard, shot, out_base).exists()
        path = run_model_step(
            stage=STAGE, shot=shot["id"], params=logged | {"references": len(refs)},
            seed=shot["seed"], inputs=shot_inputs(storyboard, shot, cfg, refs),
            produce=lambda p, shot=shot, refs=refs: generate(
                model=cfg.model, prompt=shot_prompt(storyboard, shot),
                params=cfg.request_params(), out_path=p, references=refs),
            **common)
        print(f"  {shot['id']}: {'cached' if before else 'generated'}  refs {len(refs)}  "
              f"{config.rel(path)}")
        done[shot["id"]] = path
    return done
