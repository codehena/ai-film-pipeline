"""Retry temporary failures with exponential backoff.

Retried (temporary): timeouts, connection drops, HTTP 429 (rate limit), HTTP 5xx.
Not retried (needs a human): HTTP 400/401/403/404, bad input, missing keys.
"""
from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY_S = 2.0  # waits 2 s, then 4 s, then 8 s ... plus a little jitter


class TransientError(Exception):
    """A temporary problem worth retrying (raise this from your own code)."""


class PermanentError(Exception):
    """A problem retrying will not fix."""


def is_transient(exc: BaseException) -> bool:
    if isinstance(exc, TransientError):
        return True
    if isinstance(exc, PermanentError):
        return False
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    try:
        import requests
    except ImportError:
        return False
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return True
    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        code = exc.response.status_code
        return code == 429 or code >= 500
    return False


def with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay_s: float = DEFAULT_BASE_DELAY_S,
    on_attempt: Callable[[int, float, BaseException | None], None] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call fn() up to `attempts` times. on_attempt(n, latency_s, error) runs after each try."""
    for attempt in range(1, attempts + 1):
        start = time.perf_counter()
        try:
            result = fn()
        except Exception as exc:
            latency = time.perf_counter() - start
            if on_attempt:
                on_attempt(attempt, latency, exc)
            if attempt == attempts or not is_transient(exc):
                raise
            sleep(base_delay_s * 2 ** (attempt - 1) + random.uniform(0, 0.5))
        else:
            if on_attempt:
                on_attempt(attempt, time.perf_counter() - start, None)
            return result
    raise AssertionError("unreachable")
