"""voice.pronunciations: respellings reach the TTS model only, and only where they apply."""
import copy

import pytest

from pipeline import narration
from pipeline.common.cache import narration_inputs, spoken_text, stable_hash
from pipeline.common.storyboard import StoryboardError, validate


def with_map(board, mapping):
    board = copy.deepcopy(board)
    board["voice"]["pronunciations"] = mapping
    return board


def test_whole_words_only_with_ethiopic_punctuation_as_boundary(board):
    b = with_map(board, {"ጥጃዎች": "ጥጆች"})
    assert spoken_text(b, "ወፎች ሲዘምሩ፣ ጥጃዎች ሲዘሉ፣") == "ወፎች ሲዘምሩ፣ ጥጆች ሲዘሉ፣"
    assert spoken_text(b, "ጥጃዎች።") == "ጥጆች።"
    assert spoken_text(b, "የጥጃዎችን") == "የጥጃዎችን"          # inside a longer word: untouched


def test_no_map_or_no_match_keeps_text_and_cache_key(board):
    shot = board["shots"][0]
    shot["narration"]["text"] = "ያደግኩት ገጠር ነው።"
    before = stable_hash(narration_inputs(board, shot))
    assert stable_hash(narration_inputs(with_map(board, {}), shot)) == before
    assert stable_hash(narration_inputs(with_map(board, {"ጥጃዎች": "ጥጆች"}), shot)) == before


def test_a_mapped_word_changes_only_that_lines_key(board):
    a, b = board["shots"][0], board["shots"][1]
    a["narration"]["text"], b["narration"]["text"] = "ጥጃዎች ሲዘሉ", "ያደግኩት ገጠር ነው።"
    mapped = with_map(board, {"ጥጃዎች": "ጥጆች"})
    assert stable_hash(narration_inputs(mapped, a)) != stable_hash(narration_inputs(board, a))
    assert stable_hash(narration_inputs(mapped, b)) == stable_hash(narration_inputs(board, b))


def test_continuous_read_sends_respelled_text_but_storyboard_keeps_written(board, tmp_path):
    board["voice"]["mode"] = "continuous"
    for i, s in enumerate(board["shots"]):
        s["narration"]["text"] = " ".join(["word"] * (3 + i))
    board["shots"][1]["narration"]["text"] = "ጥጃዎች ሲዘሉ ማየት"
    board = with_map(board, {"ጥጃዎች": "ጥጆች"})
    sent = []

    def tts(*, text, out_path, **kw):
        sent.append(text)
        from tests.test_narration import paragraph_reader
        paragraph_reader([])(text=text, out_path=out_path)

    narration.run(board, synthesize=tts, out_base=tmp_path / "out", log_path=tmp_path / "runs.jsonl")
    assert len(sent) == 1
    assert "ጥጆች ሲዘሉ ማየት" in sent[0] and "ጥጃዎች" not in sent[0]
    assert board["shots"][1]["narration"]["text"] == "ጥጃዎች ሲዘሉ ማየት"


def test_schema_accepts_a_map_and_rejects_empty_spellings(board, schema):
    validate(with_map(board, {"ጥጃዎች": "ጥጆች"}), schema)
    with pytest.raises(StoryboardError):
        validate(with_map(board, {"ጥጃዎች": ""}), schema)
