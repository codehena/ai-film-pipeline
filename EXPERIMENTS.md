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
- **Result (live, 2026-11-25 11:01 EAT, run `r20261125-110104`):**
  - **1 request** (latency 24.3 s), giving `full_62660579a53d.wav` (64.68 s).
  - The splitter found all 10 lines on the first try. Each line's time share was ×0.72 to ×1.26 of its word share (all inside the ×0.5–×2.0 band, none flagged), and 13.44 s of pauses were trimmed (`full_62660579a53d.split.json`).
  - Speech: 94 words in 51.24 s = **110 words per minute**, against 87 for the per-line Kore read in EXP-01. That comparison is confounded (voice, style and text all changed), so it is not evidence for continuous mode by itself.
  - `retime` then cut the film from 76.5 s to **65.5 s**, and every line fits.
- **Decision:** keep `continuous` as the mode. It meets the quota constraint (1 of 10 daily requests), and the split is clean. TODO: my by-ear verdict on whether it sounds like one voice telling one story, which is the actual hypothesis.
- **Watch:** 65.5 s is close to the 60 s minimum. If listeners want any line cut, the film may fall under 60 s, and pauses or a shot would have to be added back.

### EXP-03: Which male voice carries the opening best?
- **Date:** 2026-11-25. **Status:** 2 of 5 takes recorded (quota).
- **Hypothesis:** a calm male voice reading the same opening line with the same style will suit the story better than Kore (a female voice), because the narrator is a man telling his own childhood.
- **Change:** `py -m pipeline audition --shot s01`. Only `voice_name` varies (text, style and model are fixed).
- **Takes so far:** `outputs/auditions/s01-Charon_b8edc8220fe3.wav` (7.92 s), `outputs/auditions/s01-Iapetus_c97084de6c9e.wav` (8.04 s). Algieba, Umbriel and Orus were blocked by the daily cap.
- **Result / decision (2026-11-25):** I listened to both takes and chose **Iapetus** for the narration (`voice.voice_name`). TODO: in my own words, what made Iapetus right (warmth, pace, how close it is to the "cool" opening I liked).
- **Caveat:** only 2 of the 5 planned voices could be heard (the daily cap), so this is the best of two, not of five. Algieba, Umbriel and Orus can be auditioned after the quota resets if Iapetus doesn't hold up over the whole read.

### EXP-04: How to actually reach −14 LUFS on the radio mix
- **Date:** 2026-11-25
- **Hypothesis:** single-pass `loudnorm=I=-14:TP=-1` reaches the target. Verifying the draft 3 cut showed it did not (−15.88 LUFS, FAILURES.md F-11), so the new hypothesis is that the mix's peak-to-loudness ratio, not the filter, is the limit.
- **Change:** one variable at a time, on the same raw mix (`radio_633140d7a506.narration.wav` plus the pad and ducking, rendered without normalisation), each result measured with `loudnorm` in measure-only mode.

| Variant | After limiter: I / TP | Final I (LUFS) | Final TP (dBTP) | Final pass |
|---|---|---|---|---|
| A: single-pass loudnorm (old recipe) | – | −15.80 | −1.00 | dynamic |
| B: two-pass, linear requested | – | −14.42 | −1.00 | dynamic (fallback) |
| C: limiter −3 dBFS + two-pass | −15.00 / −1.00 | −14.42 | −1.00 | dynamic |
| D: +9.54 dB, limiter −1.5 dBFS + two-pass | −15.19 / −0.77 | −14.33 | −1.00 | dynamic |
| E: +11 dB, limiter −3 dBFS + two-pass | −15.09 / −2.08 | −14.05 | −1.00 | dynamic |
| **F: +11.5 dB, limiter −3.5 dBFS + two-pass** | −15.12 / −2.58 | **−14.00** | **−1.46** | **linear** |
| G: +12 dB, limiter −4 dBFS + two-pass | −15.17 / −3.08 | −14.00 | −1.91 | linear |

- **Raw mix:** −23.54 LUFS, true peak −3.61 dBTP, so peaks sit 20 dB above the loudness. To get −14 under a −1 ceiling, the peaks must come down by about 7 dB, which only a limiter after pre-gain can do.
- **Result:** F is the gentlest setting where the final pass is a plain linear gain with real headroom. G limits harder for no gain in loudness.
  - Built into `common/loudness.py` as pre-gain = target − measured + 2 dB, then the −3.5 dBFS limiter.
  - On the real cut `radio_e4cfcbb9f085.mp4`: **−14.0 LUFS, −1.58 dBTP, linear**. The independent `ebur128` meter reads −13.9 LUFS, −1.6 dB.
- **Cost:** the radio render went from 9.5 s to 36 s because of the extra measurement passes. That's acceptable for a correct, auditable level.
- **Decision:** keep F. Re-check by ear that the limiting (about 7 dB on peaks) doesn't make the voice sound squashed; that's part of user test 1.
