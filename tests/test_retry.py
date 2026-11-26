import pytest
import requests

from pipeline.common.retry import PermanentError, TransientError, is_transient, with_retry


def no_sleep(_seconds):
    pass


def http_error(code):
    response = requests.Response()
    response.status_code = code
    return requests.HTTPError(f"HTTP {code}", response=response)


def test_transient_failures_are_retried_until_success():
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TransientError("rate limited")
        return "done"

    seen = []
    result = with_retry(flaky, attempts=3, sleep=no_sleep,
                        on_attempt=lambda n, lat, err: seen.append((n, err is None)))
    assert result == "done"
    assert seen == [(1, False), (2, False), (3, True)]


def test_permanent_failure_is_not_retried():
    calls = []

    def broken():
        calls.append(1)
        raise PermanentError("bad request")

    with pytest.raises(PermanentError):
        with_retry(broken, attempts=3, sleep=no_sleep)
    assert len(calls) == 1


def test_gives_up_after_max_attempts():
    calls = []

    def always_down():
        calls.append(1)
        raise TransientError("503")

    with pytest.raises(TransientError):
        with_retry(always_down, attempts=3, sleep=no_sleep)
    assert len(calls) == 3


def test_backoff_doubles():
    waits = []

    def always_down():
        raise TransientError("x")

    with pytest.raises(TransientError):
        with_retry(always_down, attempts=3, base_delay_s=2, sleep=waits.append)
    assert len(waits) == 2
    assert 2 <= waits[0] < 2.6 and 4 <= waits[1] < 4.6


@pytest.mark.parametrize("code,expected", [(429, True), (500, True), (503, True),
                                           (400, False), (401, False), (404, False)])
def test_http_status_classification(code, expected):
    assert is_transient(http_error(code)) is expected


GEMINI_429 = ("429 RESOURCE_EXHAUSTED. {'error': {'message': 'Quota exceeded ... "
              "Please retry in 26.519281487s.', 'details': [{'@type': "
              "'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '26s'}]}}")


def test_server_retry_delay_is_read_from_gemini_error():
    from pipeline.common.retry import server_retry_delay
    assert server_retry_delay(TransientError(GEMINI_429)) == 26.0
    assert server_retry_delay(TransientError("Please retry in 7.5s")) == 7.5
    assert server_retry_delay(TransientError("no hint here")) is None
    assert server_retry_delay(TransientError("retry in 9999s")) == 120.0  # capped


def test_retry_waits_as_long_as_the_server_asks():
    waits, calls = [], []

    def limited():
        calls.append(1)
        if len(calls) == 1:
            raise TransientError(GEMINI_429)
        return "ok"

    assert with_retry(limited, sleep=waits.append) == "ok"
    assert waits[0] >= 27  # 26 s asked + 1 s margin, not the 2 s default


def test_long_server_wait_fails_fast_instead_of_retrying():
    from pipeline.common.retry import QuotaExhausted
    calls, waits = [], []
    daily = TransientError("429 ... per day limit exceeded ... 'retryDelay': '23084s'")

    def capped():
        calls.append(1)
        raise daily

    with pytest.raises(QuotaExhausted, match="6.4 h") as info:
        with_retry(capped, attempts=4, sleep=waits.append)
    assert len(calls) == 1 and waits == []
    assert info.value.__cause__ is daily


def test_retry_after_header_is_honoured():
    from pipeline.common.retry import server_retry_delay
    err = http_error(429)
    err.response.headers["Retry-After"] = "12"
    assert server_retry_delay(err) == 12.0


def test_timeouts_are_transient():
    assert is_transient(requests.Timeout())
    assert is_transient(TimeoutError())
    assert not is_transient(ValueError())
