import pytest

from pipeline.common import loudness

STDERR = """[Parsed_loudnorm_0 @ 000001]
{
	"input_i" : "-23.54",
	"input_tp" : "-3.61",
	"input_lra" : "4.70",
	"input_thresh" : "-33.90",
	"output_i" : "-15.80",
	"output_tp" : "-1.00",
	"output_lra" : "3.80",
	"output_thresh" : "-26.04",
	"normalization_type" : "dynamic",
	"target_offset" : "1.80"
}
[out#0/null @ 000002] video:0KiB audio:...
"""


def test_parse_loudnorm_reads_the_json_block():
    stats = loudness.parse_loudnorm(STDERR)
    assert stats["input_i"] == "-23.54" and stats["normalization_type"] == "dynamic"


def test_parse_loudnorm_without_json_is_an_error():
    with pytest.raises(loudness.LoudnessError):
        loudness.parse_loudnorm("ffmpeg said nothing useful")


def report(**kw):
    base = {"final_i": -14.0, "final_tp": -1.46, "final_pass": "linear"}
    return base | kw


def test_on_target_has_no_problems():
    assert loudness.problems(report()) == []


@pytest.mark.parametrize("kw,needle", [
    ({"final_i": -15.88}, "integrated loudness"),     # the single-pass result we measured (F-11)
    ({"final_tp": -0.80}, "true peak"),
    ({"final_pass": "dynamic"}, "not linear"),
])
def test_misses_are_reported(kw, needle):
    assert any(needle in p for p in loudness.problems(report(**kw)))


def test_small_deviation_is_tolerated():
    assert loudness.problems(report(final_i=-14.4, final_tp=-0.95)) == []


def _fake_ffmpeg(monkeypatch, mids):
    """measure() returns raw stats first, then one limited result per round."""
    seq = [{"input_i": "-20.0", "input_tp": "-1.2", "input_lra": "4", "input_thresh": "-30",
            "target_offset": "0"}] + [
        {"input_i": str(i), "input_tp": str(tp), "input_lra": "4", "input_thresh": "-26",
         "target_offset": "0"} for i, tp in mids]
    calls = iter(seq)
    monkeypatch.setattr(loudness, "measure", lambda ff, path: next(calls))
    monkeypatch.setattr(loudness, "_run", lambda cmd: '{"normalization_type" : "linear"}')


def test_one_round_when_the_final_gain_fits(monkeypatch, tmp_path):
    _fake_ffmpeg(monkeypatch, [(-15.0, -3.5)])                 # needs +1.0, allowed 2.2
    r = loudness.normalize("ffmpeg", tmp_path / "a.wav", tmp_path / "b.wav")
    assert len(r["rounds"]) == 1 and r["pre_gain_db"] == 8.0   # -14 - (-20) + 2


def test_more_level_into_the_limiter_until_it_fits(monkeypatch, tmp_path):
    _fake_ffmpeg(monkeypatch, [(-16.5, -3.5), (-15.5, -3.5)])  # needs 2.5 > 2.2, then 1.5 fits
    r = loudness.normalize("ffmpeg", tmp_path / "a.wav", tmp_path / "b.wav")
    assert len(r["rounds"]) == 2
    assert r["rounds"][1]["pre_gain_db"] > r["rounds"][0]["pre_gain_db"]


def test_rounds_are_capped(monkeypatch, tmp_path):
    _fake_ffmpeg(monkeypatch, [(-17.0, -3.5)] * loudness.MAX_ROUNDS)
    r = loudness.normalize("ffmpeg", tmp_path / "a.wav", tmp_path / "b.wav")
    assert len(r["rounds"]) == loudness.MAX_ROUNDS
