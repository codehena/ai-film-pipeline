"""Retry temporary failures with exponential backoff.

Retried (temporary): timeouts, connection drops, HTTP 429 (rate limit), HTTP 5xx.
Not retried (needs a human): HTTP 400/401/403/404, bad input, missing keys.

If the server says how long to wait (Gemini's RetryInfo "retryDelay": "26s",
"Please retry in 26.5s", or an HTTP Retry-After header), we wait that long
instead of our own short backoff (FAILURES.md F-08: free-tier TTS allows
3 requests per minute, so 2-4-8 s backoff retried inside the blocked minute).
"""
from __future__ import annotations

import random
import re
import time
from typing import Callable, TypeVar

T = TypeVar("T")

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY_S = 2.0  # waits 2 s, then 4 s, then 8 s ... plus a little jitter
MAX_SERVER_DELAY_S = 120.0  # never wait longer than this on a server's say-so

_DELAY_PATTERNS = (
    re.compile(r"retryDelay['\"]?\s*:\s*['\"](\d+(?:\.\d+)?)s"),
    re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE),
)


def server_retry_delay(exc: BaseException) -> float | None:
    """Seconds the server asked us to wait, if it said so."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None) or {}
    try:
        if headers.get("Retry-After"):
            return min(float(headers["Retry-After"]), MAX_SERVER_DELAY_S)
    except (TypeError, ValueError):
        pass
    text = str(exc)
    for pattern in _DELAY_PATTERNS:
        m = pattern.search(text)
        if m:
            return min(float(m.group(1)), MAX_SERVER_DELAY_S)
    return None


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
    # google-genai APIError (and similar SDK errors) carry the HTTP status as .code
    code = getattr(exc, "code", None)
    if isinstance(code, int) and 400 <= code < 600:
        return code == 429 or code >= 500
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
            backoff = base_delay_s * 2 ** (attempt - 1)
            asked = server_retry_delay(exc)
            wait = max(backoff, asked + 1.0) if asked is not None else backoff
            if asked is not None:
                print(f"    rate limited: server asked to wait {asked:.0f} s; waiting {wait:.0f} s")
            sleep(wait + random.uniform(0, 0.5))
        else:
            if on_attempt:
                on_attempt(attempt, time.perf_counter() - start, None)
            return result
    raise AssertionError("unreachable")
