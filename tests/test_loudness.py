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
