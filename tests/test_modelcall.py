import pytest

from pipeline.common.modelcall import run_model_step
from pipeline.common.retry import PermanentError, TransientError
from pipeline.common.runlog import read_log


def step(tmp_path, produce, inputs=None, **kw):
    return run_model_step(
        stage="keyframes", shot="s01", provider="fake", model="fake-model",
        params={"steps": 4}, seed=1, inputs=inputs or {"prompt": "a"}, ext="png",
        produce=produce, out_base=tmp_path / "outputs", log_path=tmp_path / "runs.jsonl",
        sleep=lambda s: None, **kw,
    )


def writer(calls):
    def produce(path):
        calls.append(path)
        path.write_bytes(b"image")
    return produce


def test_second_run_is_a_cache_hit(tmp_path):
    calls = []
    first = step(tmp_path, writer(calls))
    second = step(tmp_path, writer(calls))
    assert first == second and first.exists()
    assert len(calls) == 1
    assert [r["status"] for r in read_log(tmp_path / "runs.jsonl")] == ["ok", "cache_hit"]


def test_changed_inputs_call_the_model_again(tmp_path):
    calls = []
    a = step(tmp_path, writer(calls), inputs={"prompt": "a"})
    b = step(tmp_path, writer(calls), inputs={"prompt": "b"})
    assert a != b and len(calls) == 2


def test_retry_then_success_logs_each_attempt(tmp_path):
    tries = []

    def flaky(path):
        tries.append(1)
        if len(tries) == 1:
            raise TransientError("429")
        path.write_bytes(b"ok")

    out = step(tmp_path, flaky)
    assert out.exists()
    assert [r["status"] for r in read_log(tmp_path / "runs.jsonl")] == ["error", "ok"]


def test_failure_uses_fallback_and_is_not_cached(tmp_path):
    def down(path):
        raise TransientError("503")

    def ken_burns(path):
        path.write_bytes(b"fallback clip")

    out = step(tmp_path, down, fallback=ken_burns)
    assert ".fallback." in out.name and out.exists()
    statuses = [r["status"] for r in read_log(tmp_path / "runs.jsonl")]
    assert statuses == ["error", "error", "error", "fallback"]
    # next run tries the real model again (fallback is not a cache hit)
    calls = []
    real = step(tmp_path, writer(calls), fallback=ken_burns)
    assert len(calls) == 1 and ".fallback." not in real.name


def test_failure_without_fallback_raises_and_leaves_no_partial_file(tmp_path):
    def half_then_crash(path):
        path.write_bytes(b"half")
        raise PermanentError("bad prompt")

    with pytest.raises(PermanentError):
        step(tmp_path, half_then_crash)
    assert list((tmp_path / "outputs" / "keyframes").iterdir()) == []


def test_empty_output_counts_as_failure(tmp_path):
    with pytest.raises(PermanentError):
        step(tmp_path, lambda path: path.write_bytes(b""))
