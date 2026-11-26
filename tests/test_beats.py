"""Visual beats and per-shot appearance: timing, keyframes, isolation from narration."""
import copy

import pytest

from pipeline import beats, keyframes, narration
from pipeline.common.storyboard import StoryboardError, validate


@pytest.fixture
def listing(board):
    """A shot whose line lists four things, like s02."""
    shot = board["shots"][1]
    shot["narration"]["text"] = "ንቦች አበቦች ላይ ሲያንዣብቡ፣ ወፎች ሲዘምሩ፣ ጥጃዎች ሲዘሉ፣ ዶሮዎች ሲሯሯጡ ማየት"
    shot["beats"] = [{"from_word": 4, "image_prompt": "birds singing"},
                     {"from_word": 6, "image_prompt": "calves jumping"},
                     {"from_word": 8, "image_prompt": "chickens pecking"}]
    return board


def test_units_are_the_shot_then_its_beats(listing):
    shot = listing["shots"][1]
    units = beats.visual_units(shot)
    assert [u["id"] for u in units] == [shot["id"], f"{shot['id']}-b1", f"{shot['id']}-b2", f"{shot['id']}-b3"]
    assert units[0] is shot                                   # existing cache names stay valid
    assert units[2]["motion_prompt"] == shot["motion_prompt"]  # inherited
    assert units[2]["seed"] == shot["seed"]


def test_word_starts_follow_character_share():
    f = beats.word_starts("ab cd፣ efgh")
    assert f == [0.0, 0.25, 0.5]                              # punctuation does not count


def test_each_picture_lands_just_before_its_word(listing):
    shot = listing["shots"][1]
    bounds = beats.unit_bounds(shot, (10.0, 22.0), (10.2, 21.0))
    frac = beats.word_starts(shot["narration"]["text"])
    for (start, _), b in zip(bounds[1:], shot["beats"]):
        assert start == pytest.approx(10.2 + 10.8 * frac[b["from_word"]] - beats.LEAD_S)
    assert bounds[0][0] == 10.0 and bounds[-1][1] == 22.0
    assert all(a[1] == b[0] for a, b in zip(bounds, bounds[1:]))   # contiguous, no gaps


def test_beats_never_get_shorter_than_the_minimum(listing):
    shot = listing["shots"][1]
    shot["beats"] = [{"from_word": 1, "image_prompt": "a"}, {"from_word": 2, "image_prompt": "b"}]
    bounds = beats.unit_bounds(shot, (0.0, 3.0), (0.1, 2.9))
    assert all(e - s >= beats.MIN_BEAT_S - 1e-9 for s, e in bounds)


def test_visual_fields_never_touch_the_narration(listing, tmp_path):
    before = [narration.audio_path(listing, s, tmp_path) for s in listing["shots"]]
    v = copy.deepcopy(listing)
    v["shots"][1]["beats"][0]["image_prompt"] = "different birds"
    v["shots"][3]["video"]["safe_box"] = [0.2, 0.1, 0.8, 0.4]
    v["shots"][3]["appearance"] = {c: "someone else" for c in v["shots"][3]["characters"]}
    after = [narration.audio_path(v, s, tmp_path) for s in v["shots"]]
    assert before == after


def test_each_beat_gets_its_own_cached_keyframe(listing, tmp_path):
    calls = []

    def gen(*, model, prompt, params, out_path, references=()):
        calls.append(prompt)
        out_path.write_bytes(b"\xff\xd8" + str(len(calls)).encode())
    done = keyframes.run(listing, [listing["shots"][1]["id"]], generate=gen, out_base=tmp_path,
                         log_path=tmp_path / "runs.jsonl")
    assert len(done) == 4 and any("chickens pecking" in p for p in calls)
    n = len(calls)
    listing["shots"][1]["beats"][1]["image_prompt"] = "calves running"
    keyframes.run(listing, [listing["shots"][1]["id"]], generate=gen, out_base=tmp_path,
                  log_path=tmp_path / "runs.jsonl")
    assert len(calls) == n + 1                                # only the edited beat re-rolls


def test_appearance_changes_only_that_shot(board):
    shot = next(s for s in board["shots"] if s["characters"])
    cid = shot["characters"][0]
    shot["appearance"] = {cid: "a boy in swim shorts"}
    assert "a boy in swim shorts" in keyframes.shot_prompt(board, shot)
    other = next(s for s in board["shots"] if s["characters"] and s is not shot)
    assert "a boy in swim shorts" not in keyframes.shot_prompt(board, other)


def test_character_prompts_keep_faces_turned_away(board):
    shot = next(s for s in board["shots"] if s["characters"])
    assert keyframes.FRAMING in keyframes.shot_prompt(board, shot)


@pytest.mark.parametrize("beats_list,needle", [
    ([{"from_word": 6, "image_prompt": "a"}, {"from_word": 4, "image_prompt": "b"}], "must increase"),
    ([{"from_word": 99, "image_prompt": "a"}], "must increase"),
    ([{"from_word": 2, "image_prompt": "a", "characters": ["ghost"]}], "'ghost' is not defined"),
])
def test_beat_rules(listing, schema, beats_list, needle):
    listing["shots"][1]["beats"] = beats_list
    with pytest.raises(StoryboardError, match=needle):
        validate(listing, schema)
