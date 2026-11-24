"""run_model_step(): the one function every stage uses to call a model.

It combines caching, retries, logging and fallback:

1. Hash the inputs. If outputs/<stage>/<shot>_<hash>.<ext> exists -> cache hit,
   log it, return it. No model call.
2. Otherwise call produce(tmp_path) with retries. Every attempt is logged.
   The model writes to a temporary ".part" file that is renamed only on
   success, so a crash never leaves a half-written file that looks cached.
3. If every attempt fails and a fallback is given, the fallback writes
   <shot>_<hash>.fallback.<ext> instead. That name is NOT the cache name, so
   the next run tries the real model again.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from . import config
from .cache import stable_hash
from .retry import DEFAULT_ATTEMPTS, PermanentError, with_retry
from .runlog import log_call


def _short_error(exc: BaseException) -> str:
    return f"{type(exc).__name__}: {exc}"[:500]


def run_model_step(
    *,
    stage: str,
    shot: str,
    provider: str,
    model: str,
    params: dict,
    seed: int | None,
    inputs: dict,
    ext: str,
    produce: Callable[[Path], None],
    fallback: Callable[[Path], None] | None = None,
    cost_usd_list: float | None = None,
    attempts: int = DEFAULT_ATTEMPTS,
    out_base: Path | None = None,
    log_path: Path | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> Path:
    input_hash = stable_hash(inputs)
    ext = ext.lstrip(".")
    folder = config.output_dir(stage, out_base)
    out = folder / f"{shot}_{input_hash}.{ext}"
    tmp = folder / f"{shot}_{input_hash}.part.{ext}"

    common = dict(
        stage=stage, shot=shot, provider=provider, model=model, params=params,
        seed=seed, input_hash=input_hash, log_path=log_path,
    )

    if out.exists():
        log_call(**common, status="cache_hit", attempt=0, latency_s=0.0, output=config.rel(out))
        return out

    def attempt() -> None:
        tmp.unlink(missing_ok=True)
        produce(tmp)
        if not tmp.exists() or tmp.stat().st_size == 0:
            raise PermanentError("model call returned no output file")

    def on_attempt(n: int, latency: float, err: BaseException | None) -> None:
        if err is None:
            log_call(**common, status="ok", attempt=n, latency_s=latency,
                     cost_usd_list=cost_usd_list, output=config.rel(out))
        else:
            log_call(**common, status="error", attempt=n, latency_s=latency,
                     error=_short_error(err))

    try:
        with_retry(attempt, attempts=attempts, on_attempt=on_attempt, sleep=sleep)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        if fallback is None:
            raise
        fb = folder / f"{shot}_{input_hash}.fallback.{ext}"
        start = time.perf_counter()
        fallback(fb)
        log_call(**common, status="fallback", attempt=attempts,
                 latency_s=time.perf_counter() - start, output=config.rel(fb),
                 error=_short_error(exc))
        return fb

    tmp.replace(out)
    return out
