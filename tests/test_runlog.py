import json

import pytest

from pipeline.common.runlog import REQUIRED_FIELDS, log_call, read_log


def call(log, **overrides):
    fields = dict(
        stage="narration", shot="s01", provider="gemini", model="tts-model",
        params={"voice": "x"}, seed=None, input_hash="abc123abc123",
        status="ok", attempt=1, latency_s=1.23456, log_path=log,
    )
    fields.update(overrides)
    return log_call(**fields)


def test_one_line_per_call_with_all_fields(tmp_path):
    log = tmp_path / "runs.jsonl"
    call(log)
    call(log, status="cache_hit", attempt=0, latency_s=0)
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    for line in lines:
        record = json.loads(line)
        assert set(REQUIRED_FIELDS) <= set(record)
    assert json.loads(lines[0])["latency_s"] == 1.235


def test_non_latin_text_is_kept_readable(tmp_path):
    log = tmp_path / "runs.jsonl"
    call(log, error="ሰላም")
    assert "ሰላም" in log.read_text(encoding="utf-8")
    assert read_log(log)[0]["error"] == "ሰላም"


def test_unknown_status_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        call(tmp_path / "runs.jsonl", status="maybe")
