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
- **Update (F-13), the same day:** on the louder draft 4 mix, F's fixed +2 dB didn't hold, and the final pass fell back to dynamic. The 48 kHz limiter let true peaks overshoot its ceiling by +0.88 dB; **limiting at 4× (192 kHz)** made the overshoot 0.00 dB. With that, both mixes reach −14.0 LUFS in one round with a linear pass, so recipe v3 replaced F. Lesson: test a recipe on a second mix before trusting it.

### EXP-05: Can a speech recogniser check the split (and the pronunciation)?
- **Date:** 2026-11-25
- **Hypothesis:** transcribing each narration segment with a Gemini text model shows whether each segment holds exactly its own line, which the time/word ratio cannot prove.
- **Change:** `py -m pipeline asr-check` (`gemini-3.5-flash`) on the draft 4 segments, before and after the split correction in `narration_splits.json`. Only the segments changed.
- **Result:**
  - The chunk transcripts located the true breaks (F-12). After the correction, all 10 segments start and end on their own line's words.
  - Lines transcribed closely: s03 0.97, s10 0.99, and s01, s02, s05, s07, s09 at about 0.8.
  - Lines that came back garbled: s04 (twice, in separate checks), s06 and s08. s08's ቄጠማው ሲጎዘጎዝ was heard as prayer words, and s02's ጥጃዎች ሲዘሉ as ልጆች ሲጫወቱ.
  - The recogniser also mangled a common word (እናቶች heard as a name), so a garbled line is *a place to listen*, not proof of a bad pronunciation.
- **Evidence:** `runs.jsonl` stage `qa` (21 ok calls); `outputs/narration/asr_64173211a953.json`; `narration_splits.json`.
- **Decision:** keep `asr-check` as the split check after every new read. Pronunciation goes to a native ear: the words above are listed in DESIGN.md for the follow-up check.
- **Cost:** 20 free text requests/day. One full check is 10 requests, so it is cached per segment file and saves after each line.

### EXP-06: Does letting the cut follow the read's own spacing make it feel more natural?
- **Date:** 2026-11-25
- **Hypothesis:** the draft 4 cut feels stiffer than draft 3 partly because the edit re-spaced the lines, not because of the voice:
  - +1.00 s after the proverb
  - +0.36 s before it
  - −0.46 s off the breath after ይናፍቀኛል
  - 0–0.5 s of rounding slack per line

  If every gap matches the read, the cut should flow like the voice did.
- **Change:**
  - `retime` rounds to 0.1 s
  - `pause_before` / `pause_after` set from the read's gaps (DESIGN.md, "Option A")
- **Held fixed:** the read (`full_64173211a953.wav`), words, voice, loudness recipe, subtitles.
- **Result (measured):** every between-line gap is now within ±0.08 s of the read (it was −0.46 to +1.00 s). The film runs 70.3 s, and the cut is `radio_4fa2a5146bca.mp4`. Cost: 0 model calls and one 22 s render.
- **Result (by ear):** TODO, from the blind check against `radio_71461dcbe940.mp4`.
- **Decision:** keep the spacing rule either way, because it removes edit-made artefacts. If the delivery still feels stiff, the remaining cause is intonation inside the lines, and EXP-07 would be a targeted re-read (Option B).

### EXP-07: Keyframes on Cloudflare FLUX: what is controllable, and how to keep two boys consistent
- **Date:** 2026-11-25
- **Questions:**
  1. Which inputs does each model honour?
  2. Do reference sheets keep the boys consistent across shots?
- **Measured:**
  - **Model schemas** (Cloudflare API): FLUX.1 schnell takes only `prompt` and `steps`. FLUX.2 klein 4B takes multipart form data.
  - **Probe** (2 klein calls, stage `probe` in `runs.jsonl`): `width`/`height` are honoured (1024×576 JPEG). The same `seed` gave two completely different compositions, so **the seed is ignored**. Determinism comes from the cache (keep and reuse outputs); the storyboard `seed` acts as a take number.
  - **References:** klein accepts `input_image_0..1`. Plain scene prompt plus references: it edited the sheet (F-15). With the "new scene, references only for appearance" prompt, s04–s07 all show the green-shirt and red-shirt boys matching their sheets (contact sheet checked by eye).
- **Result:**
  - **19 keyframe-stage images:** 2 sheets ×2 (one wasted pair, F-15), 10 shots, 1 bad s04, 2 extra s08/s09 takes, and 3 s09 takes in all
  - **0 errors,** median 16.8 s per image
  - Cultural fixes from looking at the frames: s08 cauldron → jebena on a brazier, sini cups, women in netela; s09 → insert (F-16)
- **Decision:** klein with reference sheets, the explicit scene prompt, and one 1024² master per shot cropped to both 16:9 and 9:16 around `video.focus`.

### EXP-08: Can one square keyframe serve both 16:9 and 9:16?
- **Date:** 2026-11-25
- **Hypothesis:** keyframes are composed with the subject centred (style block), so one 1024×1024 master can be cropped to 1024×576 (16:9) and 576×1024 (9:16) without losing the subject. That halves image calls and keeps both versions identical in content.
- **Result (frames checked from both exports):**
  - s04 keeps both boys whole in 9:16.
  - The s09 insert lands on the jebena in both formats.
  - Vertical subtitles sit above the bottom area that phone apps cover.
  - Both crops are upscaled 1.25× to 720p, with the Ken Burns move rendered at 4× for smoothness.
- **Decision:** keep. Exports `final-16x9_79e1e669fdc0.mp4` and `final-9x16_73291dad58e1.mp4` (70.30 s, −14.0 LUFS, linear pass).

### EXP-09: Do word-timed beats make the pictures follow the voice?
- **Date:** 2026-11-25
- **Hypothesis:** if each named thing gets its own picture landing just before its word, the film stops "catching up" (F-20). Estimating word times by character share is accurate enough that no speech recognition is needed.
- **Change:**
  - 5 beats: s02 → birds, calves, hens; s03 → mothers washing; s10 → the gojo bet farmland
  - each beat starts 0.15 s before its word
  - narration unchanged
- **Result:**
  - Every beat's picture starts 0.15 s before its estimated word time.
  - 15 visual units in place of 10.
  - Narration cache hits throughout (0 TTS calls).
  - Frames checked in both exports.
  - TODO, by ear: does each picture *feel* on time? If one is late, adjust its `from_word`.
- **Decision:** keep. Tune `from_word` from the author's viewing rather than adding an ASR dependency.

### EXP-10: Safe boxes vs. centred crops for 16:9
- **Date:** 2026-11-25
- **Hypothesis:** keeping an explicit head box inside every crop (and every zoom) removes cut heads in 16:9 without hurting 9:16.
- **Result:**
  - On the old keyframes, the overlay showed the 16:9 crop cutting heads in s04, s05 and s07. With boxes, all heads sit inside both crops at every zoom (`outputs/qa/framing.png`).
  - In 9:16, s08's four seated women can't all fit (the box is wider than the frame), so the crop centres on the jebena, as designed.
  - The new character prompt (medium-wide, space above heads) also helped: most new keyframes already placed heads inside the 16:9 band.
- **Decision:** safe boxes for every shot with people; the framing sheet is part of the review before a render.

### EXP-11: Naming a cultural object vs. describing its shape
- **Date:** 2026-11-25
- **Hypothesis:** FLUX.2 klein knows the *words* for Ethiopian objects (jebena, sini, netela, habesha kemis) but not their *shapes*. Describing the shape and parts will get them right where names alone didn't.
- **Evidence across takes:**

| Shot / take | Prompt style | Result |
|---|---|---|
| s08 v1 (morning) | names only ("black clay jebena", "white netela shawls") | cauldron-like pot; lace veils over the head |
| s08 now, attempt 1 | names + described garments, tray, straw ring, popcorn | attire and ceremony right; jebena a squat teapot |
| s08 now, attempt 2 | + jebena geometry (spherical base, tall bottle-like neck, side spout, loop handle) | a recognisable jebena; kept |
| s09 takes 1–2 (morning) | "handleless" / "bowl-shaped" cup | handles kept appearing (F-16) |

- **Result:** describing shape and parts worked, on the second attempt. Naming the thing to avoid ("handleless", and the reason "teapot" was left out) does the opposite.
- **Decision:** for every culturally specific object, the prompt describes its shape. Recorded as a prompt rule in ARCHITECTURE.md.
