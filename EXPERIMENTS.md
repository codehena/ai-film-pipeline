# Experiments

Aim for about ten. Change **one thing** at a time and keep the seed fixed. Point to the `runs.jsonl` lines (by `run_id` / `input_hash`) as evidence.

## Template

### EXP-01: short title
- **Date:**
- **Hypothesis:** If I …, then … because …
- **Change:** (exactly one thing)
- **Held fixed:** seed, model, …
- **Result:** (what you saw or heard, with numbers where possible)
- **Evidence:** runs.jsonl `run_id=…`, files `outputs/…`
- **Decision:** keep / revert / try next

---

### EXP-01: Does the planned shot timing fit the measured Amharic narration?
- **Date:** 2026-11-25
- **Hypothesis:** if Amharic TTS speaks at about the rate I assumed (130–150 words per minute), then draft 1's shot durations (80 s in total) will hold every line with its pauses.
- **Change:** generated all 10 lines with `gemini-3.8-flash-tts` (voice Kore, `style_mode: speech_metadata`, calm and unhurried style), then built the radio cut.
- **Held fixed:** text, voice, style, pauses.
- **Result:**
  - 99 Amharic words took 68.64 s of speech: **1.44 words/s, or 87 words per minute**, well below the assumed 130–150 (and the brief's English rule of thumb of 2–2.5 words/s).
  - **8 of 10 lines overran** their shot. The worst was s03, the list of village sounds: an 11.8 s line in a 9 s slot. Drift built up to +5.6 s by s03.
  - Amharic words are long (whole phrases join into one word), and the calm style slows delivery further.
- **Evidence:**
  - `runs.jsonl` stage `narration`, 10 `ok` lines: input hashes `6f25c9f7bd79` (s01) … `eccc9b5226b4` (s10)
  - timing report `outputs/cuts/radio_35007642475a.timing.md`
- **Decision:** keep the words and set each `duration_s` to the measured recommendation (pause before + line + pause after, rounded up to 0.5 s).
  - Draft 2 is 85 s and every line fits (`radio_4e62d2e01523`).
  - The change made **0 new TTS calls**: all 10 lines were cache hits, because durations and pauses are not part of the narration hash.
  - Open question for user test 1: s03 is now a 13 s shot. Does the list drag, or does it build the place?
- **Also moved:** the music cue boundary from 40 s to 58 s (the start of s08), so the warmer theme returns when the story turns to home, coffee and the proverb.

---

### EXP-02: One continuous TTS read vs. one call per line (consistency and flow)
- **Date:** 2026-11-25. **Status:** built and tested offline; live run waiting for the daily quota (F-09).
- **What prompted it:** my own listen to radio cut draft 2. The opening (s01) sounded right ("a cool voice"), but the delivery changed in later lines. Two causes:
  - s01, s05, s09 and s10 each had a different `speech_metadata.style` override.
  - Every line was a separate, independent TTS call, and the model has no memory of the previous line.
- **Hypothesis:** if the whole story is read in **one** call with **one** style (s01's "soft and slow, like waking up"), the voice and pacing stay consistent from start to finish and the story flows, at 1 request instead of 10.
- **Change:** `voice.mode: continuous` (whole narration in one call, paragraphs separated by a pause request), plus a splitter that cuts the read into per-shot segments. Per-line style overrides removed in draft 3.
- **Held fixed:** text (draft 3), voice, style, model.
- **How to judge it:**
  - by ear: same listeners, per_line vs continuous radio cut, blind if possible
  - the split report's `time_vs_word_share` per line
  - number of requests in `runs.jsonl`
- **Offline evidence so far:** `tests/test_silence.py` shows the splitter places breaks correctly even when a pause inside a line (0.7 s) is longer than the pauses between lines (0.5 s). `tests/test_narration.py` shows that a re-run makes 0 calls and any edit makes 1.
- **Result:** TODO after the live run.

### EXP-03: Which male voice carries the opening best?
- **Date:** 2026-11-25. **Status:** 2 of 5 takes recorded (quota).
- **Hypothesis:** a calm male voice reading the same opening line with the same style will suit the story better than Kore (a female voice), because the narrator is a man telling his own childhood.
- **Change:** `py -m pipeline audition --shot s01`. Only `voice_name` varies (text, style and model are fixed).
- **Takes so far:** `outputs/auditions/s01-Charon_b8edc8220fe3.wav` (7.92 s), `outputs/auditions/s01-Iapetus_c97084de6c9e.wav` (8.04 s). Algieba, Umbriel and Orus were blocked by the daily cap.
- **Result / decision:** TODO: listen and choose. Charon is set provisionally in `storyboard.json`.
