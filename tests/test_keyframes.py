"""Keyframe stage with a fake image model: caching, references and contracts, offline."""
import pytest

from pipeline import keyframes
from pipeline.common.retry import PermanentError
from pipeline.common.runlog import read_log

JPEG = b"\xff\xd8\xff\xe0fake-jpeg"


@pytest.fixture
def fake():
    calls = []

    def generate(*, model, prompt, params, out_path, references=()):
        calls.append({"prompt": prompt, "params": params, "refs": [r.name for r in references]})
        out_path.write_bytes(JPEG + str(len(calls)).encode())
    generate.calls = calls
    return generate


def run(board, tmp_path, fake, only=None):
    return keyframes.run(board, only, generate=fake, out_base=tmp_path,
                         log_path=tmp_path / "runs.jsonl")


def ref_calls(fake):
    return [c for c in fake.calls if "reference sheet" in c["prompt"]]


def test_references_first_then_every_shot(board, tmp_path, fake):
    done = run(board, tmp_path, fake)
    chars_used = {c for s in board["shots"] for c in s["characters"]}
    assert len(ref_calls(fake)) == len(chars_used)
    assert len(done) == len(board["shots"])
    assert len(fake.calls) == len(chars_used) + len(board["shots"])


def test_rerun_costs_nothing(board, tmp_path, fake):
    run(board, tmp_path, fake)
    n = len(fake.calls)
    run(board, tmp_path, fake)
    assert len(fake.calls) == n
    assert "cache_hit" in [r["status"] for r in read_log(tmp_path / "runs.jsonl")]


def test_shots_with_a_character_are_conditioned_on_its_sheet(board, tmp_path, fake):
    run(board, tmp_path, fake)
    for shot, call in zip(board["shots"], [c for c in fake.calls if c not in ref_calls(fake)]):
        assert len(call["refs"]) == len(shot["characters"])
        assert all(r.startswith("ref-") for r in call["refs"])


def test_take_number_rerolls_only_that_shot(board, tmp_path, fake):
    run(board, tmp_path, fake)
    n = len(fake.calls)
    board["shots"][2]["seed"] += 1
    run(board, tmp_path, fake)
    assert len(fake.calls) == n + 1


def test_new_character_description_remakes_its_sheet_and_its_shots_only(board, tmp_path, fake):
    run(board, tmp_path, fake)
    n = len(fake.calls)
    cid = board["characters"][0]["id"]
    board["characters"][0]["description"] += ", wearing a woven cap"
    run(board, tmp_path, fake)
    with_char = sum(1 for s in board["shots"] if cid in s["characters"])
    assert len(fake.calls) == n + 1 + with_char


def test_keyframe_path_is_the_contract(board, tmp_path, fake):
    done = run(board, tmp_path, fake)
    for shot in board["shots"]:
        assert keyframes.keyframe_path(board, shot, tmp_path) == done[shot["id"]]


def test_prompt_carries_story_style_characters_and_no_text_rule(board):
    board["characters"][0]["description"] = "a boy in a green shirt"
    shot = next(s for s in board["shots"] if s["characters"])
    p = keyframes.shot_prompt(board, shot)
    assert shot["image_prompt"].rstrip(".") in p and board["style_block"] in p
    assert "a boy in a green shirt" in p and "No text" in p


def test_only_fields_the_model_honours_are_sent(board, tmp_path, fake):
    board["image"]["model"] = "@cf/black-forest-labs/flux-1-schnell"   # no size, no references
    run(board, tmp_path, fake)
    assert all(c["params"] == {} and c["refs"] == [] for c in fake.calls)
    assert not ref_calls(fake)


def test_unknown_model_fails_fast(board, tmp_path, fake):
    board["image"]["model"] = "@cf/nobody/imaginary"
    with pytest.raises(PermanentError, match="unknown image model"):
        run(board, tmp_path, fake)


def test_overlong_prompt_is_refused(board):
    board["style_block"] = "x" * 3000
    with pytest.raises(PermanentError, match="chars"):
        keyframes.shot_prompt(board, board["shots"][0])
