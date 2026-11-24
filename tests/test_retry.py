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


def test_timeouts_are_transient():
    assert is_transient(requests.Timeout())
    assert is_transient(TimeoutError())
    assert not is_transient(ValueError())
