import math
import wave
from array import array

import pytest

from pipeline.common.silence import (
    Silence, SplitError, align_boundaries, find_silences, split_lines, write_segment,
)

RATE = 24000


def tone(seconds, freq=220.0, amp=6000):
    return array("h", (int(amp * math.sin(2 * math.pi * freq * i / RATE))
                       for i in range(int(seconds * RATE))))


def silence(seconds):
    return array("h", bytes(2 * int(seconds * RATE)))


def write(path, parts):
    samples = array("h")
    for p in parts:
        samples.extend(p)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(RATE)
        w.writeframes(samples.tobytes())
    return path


def test_find_silences_reports_gaps():
    samples = tone(1.0) + silence(0.6) + tone(1.0)
    found = find_silences(samples, RATE)
    assert len(found) == 1
    assert found[0].start == pytest.approx(1.0, abs=0.03)
    assert found[0].length == pytest.approx(0.6, abs=0.05)


def test_short_dips_are_not_pauses():
    samples = tone(1.0) + silence(0.1) + tone(1.0)
    assert find_silences(samples, RATE) == []


def test_alignment_prefers_expected_position_over_longest_pause():
    # a 0.8 s pause mid-line (far from the expected break) vs a 0.5 s pause at the break
    sil = [Silence(2.6, 3.4), Silence(6.0, 6.5)]
    chosen = align_boundaries(sil, expected=[6.2])
    assert chosen == [sil[1]]


def test_alignment_keeps_boundaries_in_order():
    sil = [Silence(1, 1.5), Silence(3, 3.5), Silence(5, 5.5)]
    assert align_boundaries(sil, expected=[3.1, 5.2]) == [sil[1], sil[2]]


def test_too_few_pauses_is_an_error():
    with pytest.raises(SplitError):
        align_boundaries([Silence(1, 2)], expected=[1.5, 3.0])


def test_split_with_a_long_pause_inside_the_first_line(tmp_path):
    # line 1 = two sentences (3 s + 3 s) with a 0.7 s inner pause; lines 2 and 3 = 2 s each.
    # Breaks between lines are only 0.5 s: shorter than the inner pause.
    wav = write(tmp_path / "full.wav", [
        silence(0.4), tone(3), silence(0.7), tone(3),   # line 1 (12 words)
        silence(0.5), tone(2),                          # line 2 (4 words)
        silence(0.5), tone(2), silence(0.6),            # line 3 (4 words)
    ])
    spans = split_lines(wav, [12, 4, 4])
    assert len(spans) == 3
    (a0, a1), (b0, b1), (c0, c1) = spans
    assert a0 == pytest.approx(0.4, abs=0.03) and a1 == pytest.approx(7.1, abs=0.03)
    assert b0 == pytest.approx(7.6, abs=0.03) and b1 == pytest.approx(9.6, abs=0.03)
    assert c0 == pytest.approx(10.1, abs=0.03) and c1 == pytest.approx(12.1, abs=0.03)


def test_write_segment_cuts_the_right_length(tmp_path):
    wav = write(tmp_path / "full.wav", [tone(2), silence(1), tone(2)])
    out = tmp_path / "seg.wav"
    write_segment(wav, 3.0, 5.0, out)
    with wave.open(str(out)) as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(2.0, abs=0.001)
