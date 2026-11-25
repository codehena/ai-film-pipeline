"""Find pauses in a narration WAV and split it into one segment per line.

Used by continuous narration: the whole story is read in ONE TTS call (one
voice, one flow, one request), then cut back into per-shot segments.

Why not "just cut at the N-1 longest silences"? A line can contain its own
pause (two sentences), which may be longer than the pause between lines. So
each boundary is matched to where that line SHOULD end, from its share of the
words, and the alignment trades silence length against distance from that
expected position (dynamic programming, so the boundaries stay in order).

Pure Python on 16-bit mono PCM: no FFmpeg, testable offline.
"""
from __future__ import annotations

import math
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

WINDOW_S = 0.02          # 20 ms analysis windows
SILENCE_DBFS = -40.0     # quieter than this counts as silence
MIN_SILENCE_S = 0.25     # shorter dips are breaths inside a word, not pauses
DISTANCE_PENALTY = 0.25  # seconds of silence "worth" one second of misplacement


class SplitError(Exception):
    """The recording could not be split into the expected number of lines."""


@dataclass
class Silence:
    start: float
    end: float

    @property
    def length(self) -> float:
        return self.end - self.start

    @property
    def mid(self) -> float:
        return (self.start + self.end) / 2


def read_pcm(path: Path) -> tuple[array, int]:
    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise SplitError("expected 16-bit mono WAV")
        rate = w.getframerate()
        samples = array("h")
        samples.frombytes(w.readframes(w.getnframes()))
    return samples, rate


def find_silences(samples: array, rate: int) -> list[Silence]:
    win = max(1, int(rate * WINDOW_S))
    silences: list[Silence] = []
    run_start = None
    n_windows = math.ceil(len(samples) / win)
    for i in range(n_windows):
        chunk = samples[i * win:(i + 1) * win]
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk)) if chunk else 0.0
        db = 20 * math.log10(rms / 32768) if rms > 0 else -120.0
        if db < SILENCE_DBFS:
            if run_start is None:
                run_start = i
        elif run_start is not None:
            silences.append(Silence(run_start * win / rate, i * win / rate))
            run_start = None
    if run_start is not None:
        silences.append(Silence(run_start * win / rate, len(samples) / rate))
    return [s for s in silences if s.length >= MIN_SILENCE_S]


def align_boundaries(silences: list[Silence], expected: list[float]) -> list[Silence]:
    """Pick one silence per expected boundary time, in order, maximising
    sum(silence length - DISTANCE_PENALTY * |mid - expected|)."""
    k, n = len(expected), len(silences)
    if n < k:
        raise SplitError(f"found {n} pauses but need {k} line breaks")
    NEG = float("-inf")
    # best[i][j]: best score using boundaries 0..i with boundary i at silence j
    best = [[NEG] * n for _ in range(k)]
    back = [[-1] * n for _ in range(k)]
    for j in range(n):
        best[0][j] = silences[j].length - DISTANCE_PENALTY * abs(silences[j].mid - expected[0])
    for i in range(1, k):
        running, arg = NEG, -1
        for j in range(n):
            if j - 1 >= 0 and best[i - 1][j - 1] > running:
                running, arg = best[i - 1][j - 1], j - 1
            if running > NEG:
                gain = silences[j].length - DISTANCE_PENALTY * abs(silences[j].mid - expected[i])
                best[i][j], back[i][j] = running + gain, arg
    j = max(range(n), key=lambda x: best[k - 1][x])
    if best[k - 1][j] == NEG:
        raise SplitError("could not place every line break in order")
    chosen = []
    for i in range(k - 1, -1, -1):
        chosen.append(silences[j])
        j = back[i][j]
    return chosen[::-1]


def split_lines(path: Path, word_counts: list[int]) -> list[tuple[float, float]]:
    """(start, end) of the speech for each line, silence trimmed."""
    if len(word_counts) == 1:
        samples, rate = read_pcm(path)
        sil = find_silences(samples, rate)
        total = len(samples) / rate
        start = sil[0].end if sil and sil[0].start <= 0.01 else 0.0
        end = sil[-1].start if sil and sil[-1].end >= total - 0.01 else total
        return [(start, end)]
    samples, rate = read_pcm(path)
    total = len(samples) / rate
    silences = find_silences(samples, rate)
    lead = silences[0].end if silences and silences[0].start <= 0.01 else 0.0
    tail = silences[-1].start if silences and silences[-1].end >= total - 0.01 else total
    interior = [s for s in silences if s.start > lead and s.end < tail]
    speech = tail - lead
    words = sum(word_counts)
    cumulative, expected = 0, []
    for wc in word_counts[:-1]:
        cumulative += wc
        expected.append(lead + speech * cumulative / words)
    cuts = align_boundaries(interior, expected)
    starts = [lead] + [c.end for c in cuts]
    ends = [c.start for c in cuts] + [tail]
    return list(zip(starts, ends))


def write_segment(src: Path, start: float, end: float, out: Path) -> None:
    with wave.open(str(src), "rb") as w:
        rate, width, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
        w.setpos(int(start * rate))
        frames = w.readframes(max(0, int((end - start) * rate)))
    with wave.open(str(out), "wb") as o:
        o.setnchannels(ch); o.setsampwidth(width); o.setframerate(rate)
        o.writeframes(frames)
