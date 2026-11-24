"""runs.jsonl: one JSON line per model call (and per cache hit / fallback).

This file is the evidence graders read: which model, which parameters and seed,
how long it took, what it cost, and what it produced. COSTS.md is computed from it.

status values:
  ok         the model call succeeded
  error      one attempt failed (it may be retried)
  cache_hit  inputs unchanged, output reused, no model call made
  fallback   all attempts failed, a fallback (e.g. Ken Burns) was used
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from . import config

RUN_ID = time.strftime("r%Y%m%d-%H%M%S")

REQUIRED_FIELDS = (
    "ts", "run_id", "stage", "shot", "provider", "model", "params", "seed",
    "input_hash", "status", "attempt", "latency_s", "gpu_s", "cost_usd_list",
    "output", "error",
)
STATUSES = ("ok", "error", "cache_hit", "fallback")


def log_call(
    *,
    stage: str,
    shot: str | None,
    provider: str,
    model: str,
    params: dict,
    seed: int | None,
    input_hash: str | None,
    status: str,
    attempt: int,
    latency_s: float,
    gpu_s: float | None = None,
    cost_usd_list: float | None = None,
    output: str | None = None,
    error: str | None = None,
    log_path: Path | None = None,
) -> dict:
    if status not in STATUSES:
        raise ValueError(f"unknown status {status!r}")
    record = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": RUN_ID,
        "stage": stage,
        "shot": shot,
        "provider": provider,
        "model": model,
        "params": params,
        "seed": seed,
        "input_hash": input_hash,
        "status": status,
        "attempt": attempt,
        "latency_s": round(latency_s, 3),
        "gpu_s": gpu_s,
        "cost_usd_list": cost_usd_list,
        "output": output,
        "error": error,
    }
    with open(log_path or config.RUNS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def read_log(log_path: Path | None = None) -> list[dict]:
    path = Path(log_path or config.RUNS_LOG)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
