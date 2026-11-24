from pipeline.common.cache import (
    file_hash, keyframe_inputs, narration_inputs, stable_hash, video_inputs,
)

MODEL = "test-image-model"
PARAMS = {"steps": 4, "width": 768, "height": 1344}


def keyframe_hashes(board):
    return {
        s["id"]: stable_hash(keyframe_inputs(board, s, model=MODEL, params=PARAMS))
        for s in board["shots"]
    }


def test_hash_ignores_key_order():
    assert stable_hash({"a": 1, "b": [1, 2]}) == stable_hash({"b": [1, 2], "a": 1})


def test_hash_changes_when_value_changes():
    assert stable_hash({"seed": 1}) != stable_hash({"seed": 2})


def test_changing_one_prompt_changes_only_that_shot(board):
    before = keyframe_hashes(board)
    board["shots"][2]["image_prompt"] += " at sunset"
    after = keyframe_hashes(board)
    changed = [sid for sid in before if before[sid] != after[sid]]
    assert changed == [board["shots"][2]["id"]]


def test_style_block_change_invalidates_every_keyframe(board):
    before = keyframe_hashes(board)
    board["style_block"] += ", oil paint"
    after = keyframe_hashes(board)
    assert all(before[s] != after[s] for s in before)


def test_character_description_change_only_hits_shots_with_that_character(board):
    before = keyframe_hashes(board)
    board["characters"][0]["description"] = "a different description"
    after = keyframe_hashes(board)
    cid = board["characters"][0]["id"]
    for s in board["shots"]:
        assert (before[s["id"]] != after[s["id"]]) == (cid in s["characters"])


def test_new_keyframe_means_new_video(board, tmp_path):
    shot = board["shots"][0]
    img = tmp_path / "kf.png"
    img.write_bytes(b"first image")
    v1 = stable_hash(video_inputs(shot, keyframe_hash=file_hash(img), model="wan", params={}))
    img.write_bytes(b"second image")
    v2 = stable_hash(video_inputs(shot, keyframe_hash=file_hash(img), model="wan", params={}))
    assert v1 != v2


def test_narration_hash_changes_with_text_only_for_that_shot(board):
    before = [stable_hash(narration_inputs(board, s)) for s in board["shots"]]
    board["shots"][4]["narration"]["text"] = "new line"
    after = [stable_hash(narration_inputs(board, s)) for s in board["shots"]]
    assert [i for i in range(len(before)) if before[i] != after[i]] == [4]


def test_subtitle_change_does_not_regenerate_audio(board):
    shot = board["shots"][0]
    h1 = stable_hash(narration_inputs(board, shot))
    shot["narration"]["subtitle_en"] = "edited subtitle"
    assert stable_hash(narration_inputs(board, shot)) == h1
