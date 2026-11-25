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
