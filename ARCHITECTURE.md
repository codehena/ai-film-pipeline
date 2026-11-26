# Architecture

## The idea in one sentence
`storyboard.json` is the only contract between stages. Each stage reads it (plus earlier stages' outputs), writes files to `outputs/<stage>/`, and logs every model call to `runs.jsonl`.

```
storyboard.json ──validate──┬──> narration ──────────────┐
                            ├──> keyframes ──> shots ────┼──> assemble ──> outputs/cuts/*.mp4
                            └──> music ──────────────────┘
                     every model call ──> runs.jsonl
```

## Why it is shaped this way (engineering decisions)
**1. One contract, independent stages, joined only by hashes.** Each stage's output is named by the hash of exactly the inputs that change it (`common/cache.py`):

```
narration  = hash(text, voice, style, model)                -> outputs/narration/
keyframe   = hash(image_prompt, style_block, character descriptions,
                  reference-image file hashes, seed, model)  -> outputs/keyframes/
motion     = hash(motion_prompt, keyframe FILE hash, seed, model) -> outputs/shots/
music      = hash(music cue captions, bpm, key, model)      -> outputs/music/
final cut  = hash(file hashes of all of the above + timeline + recipe) -> outputs/cuts/
```

So swapping the narration (say, a future re-read) re-renders **only the final cut**. Keyframes, motion clips and music are untouched, because none of them depends on the voice. A new keyframe invalidates only its own motion clip. Nothing is regenerated "just in case", and the free quotas go to what actually changed.

**2. Measure, then fix the cheapest real cause.** When the draft 4 delivery felt stiffer, the cut was measured against the raw read first (DESIGN.md). The measurable cause was edit spacing (+1.0 s after the proverb, the breath after ይናፍቀኛል shortened, 0–0.5 s rounding slack), and it was fixed at **0 API calls** (Option A). The unmeasurable remainder, intonation, would need a re-read (Option B, 1 TTS call). With the TTS and ASR quotas exhausted and a deadline the next day, we shipped Option A rather than block the picture work on a quota reset. The audio stays swappable (point 1).

**3. Quotas shape the unit of work.** At 10 TTS requests/day, the whole narration is read in **one** call (continuous mode) instead of one per line (F-09). At 20 text requests/day, `asr-check` caches per segment and saves after every line (F-12). A daily cap fails fast with the reset time instead of retrying (`QuotaExhausted`).

**4. Corrections are data, not hand-edited outputs.** A wrong split is fixed in `narration_splits.json` (committed, keyed to one specific read), never by editing a generated WAV. Every fix is reproducible and reviewable in git. The same goes for pronunciation: a mispronounced word is fixed with `voice.pronunciations` in `storyboard.json` (written word → the spelling the TTS model is given, `cache.spoken_text`). Only the spoken audio changes: the written line, the English subtitles and every line without a mapped word keep their cache keys.

**5. Fallbacks keep a film possible at every step.** No keyframe: the stage stops with a clear error. No motion clip: a Ken Burns pan-and-zoom on the keyframe. No chosen score, or a chosen one that isn't on disk (a clean clone: Kaggle outputs aren't in git): the placeholder pad, with a printed warning. A complete film can always be rendered from whatever exists, and `py -m pipeline film` ends in the final cut.

## Contracts

| Stage | Reads from storyboard | Reads files | Writes |
|---|---|---|---|
| validate | everything | `schema/storyboard.schema.json` | nothing (fails fast) |
| narration | `voice`, `language.narration`, `shots[].narration.text` | – | `outputs/narration/<shot>_<hash>.wav` |
| keyframes | `style_block`, `characters`, `shots[].image_prompt`, `seed` | reference sheet | `outputs/keyframes/<shot>_<hash>.png` |
| shots | `shots[].motion_prompt`, `video`, `duration_s`, `seed` | that shot's keyframe | `outputs/shots/<shot>_<hash>.mp4` |
| music | `music_cues` | – | `outputs/music/` |
| retime | `shots[].narration.speech_metadata` pauses, `music_cues` | narration audio | `storyboard.json`: each spoken shot's `duration_s` = pause before + line + pause after, rounded up to 0.1 s, plus cue times on shot boundaries (validated before writing, LF line endings) |
| assemble | everything | all of the above | `outputs/cuts/` (radio now; 9:16 and 16:9 later) |

## Validation (`pipeline/common/storyboard.py`)
Before any stage runs:
1. **JSON Schema** (Draft 2020-12): required fields, types, enums such as `shot_size`, 8–12 shots, `additionalProperties: false` so a typo like `imagePrompt` is caught.
2. **Python rules**: unique shot and character ids, total length (shots + end card) between 60 and 90 s, every character used in a shot is defined, music cues fit inside the film.

`TODO` strings are reported as warnings, not errors, so the placeholder storyboard still runs.

## Caching (`pipeline/common/cache.py`)
- For each shot and stage, `*_inputs()` builds a dict of everything that affects the output (prompt, style block, character descriptions, seed, model, parameters, upstream file hash).
- `stable_hash()` = SHA-256 of canonical JSON (sorted keys), first 12 hex chars.
- The output file is named `<shot>_<hash>.<ext>`. If it exists, the call is skipped and logged as `cache_hit`.
- A video's inputs include its keyframe's **file hash**, so a new keyframe automatically invalidates that shot's video and nothing else.
- What is deliberately *not* in a hash: `subtitle_en` does not affect narration audio, and `reason` affects nothing that is generated.

### Spoken text vs. delivery cues (`speech_metadata`)
Each line's `narration` keeps three things apart:

| Field | Meaning | Changing it… |
|---|---|---|
| `text` | only the words spoken (no stage directions) | new TTS call for that shot |
| `speech_metadata.style` | delivery override; falls back to `voice.style` | new TTS call for that shot |
| `speech_metadata.pause_before_s` / `pause_after_s` | timing in the edit | re-time the cut only, **no** TTS call |

### Narration modes (`voice.mode`)
| | `per_line` | `continuous` |
|---|---|---|
| TTS calls for a full read | one per spoken shot | **1** |
| Editing one line | 1 call (that shot) | 1 call (the whole read) |
| Voice and pacing | can drift between calls (each call is independent) | one take, consistent throughout |
| Per-line `speech_metadata.style` | used | ignored (one read, one style) |
| Files | `<shot>_<hash>.wav` | `full_<hash>.wav` → `<shot>_<hash>.cont.wav` + `full_<hash>.split.json` |

Continuous mode asks the model for a clear pause between paragraphs, then `common/silence.py` finds the pauses (20 ms RMS windows below −40 dBFS, at least 0.25 s long). It places each line break with an order-preserving alignment that weighs pause length against distance from the line's expected end, computed from its share of the words. So a pause *inside* a two-sentence line is not mistaken for a break. The split report flags any line whose time share is under 0.5× or over 2× its word share. `audio_path()` hides the mode, so `assemble` and `retime` work the same either way.

**Split corrections and checks.** A pause inside a line can look exactly like a line break, so an in-band ratio does not prove a split is right (FAILURES.md F-12).
- `py -m pipeline asr-check` transcribes every segment with a Gemini text model and prints it next to the script. It is cached per segment file hash and logged as stage `qa`.
- Verified corrections go in **`narration_splits.json`** (committed), keyed to one read (`full_<hash>`), so they never apply to a different take. `narration` applies them at no TTS cost and validates them: inside the read, no overlaps, known shot ids.
- Every segment gets 0.1 s of padding (at most half the gap to its neighbour), so a soft first syllable is not clipped.

`voice.style_mode` decides how style reaches the model. `speech_metadata` uses the SDK's `Part.speech_metadata.style` field, so the style is never part of the spoken string. `prompt_prefix` is the older "Read this in a … style:" approach, and `none` sends the words only. Comparing these modes is an experiment (EXPERIMENTS.md).

## Loudness (`pipeline/common/loudness.py`)
Every delivered cut is normalised to **−14 LUFS integrated, true peak ≤ −1 dBTP**, in passes whose numbers are all logged to `<cut>.loudness.json`:
1. Render the mix with no loudness processing, then measure it.
2. Pre-gain by `−14 − measured + 2 dB`, and limit peaks at −3.5 dBFS **at 4× the sample rate** (192 kHz). At 48 kHz, peaks between samples overshot the ceiling by about 0.9 dB (F-13). If the final gain still wouldn't fit under the ceiling with 0.3 dB margin, push more level into the limiter and repeat, up to 4 rounds, each recorded in the report. The mix's peaks sit about 20 dB above its loudness, so without this the target is out of reach under the ceiling (FAILURES.md F-11, EXPERIMENTS.md EXP-04).
3. Measure again, then apply `loudnorm` with those measurements and `linear=true`: a plain gain change.
4. Measure the delivered MP4. The stage prints a WARNING, and the report lists `problems`, if it is more than 0.5 LU off target, over the ceiling, or the final pass was not linear.

**Subtitles:** each line's `subtitle_en` becomes one or more cues. A line that won't fit on two ~40-character rows is split at sentence and clause breaks into consecutive cues, timed in proportion to their length (F-14).

A change to this recipe bumps `assemble.RECIPE_VERSION`, so a new cut gets a new hash and the old one stays as evidence.

## Failure handling (`pipeline/common/retry.py`, `modelcall.py`)
- `with_retry()`: up to 3 attempts with backoff of 2 s, 4 s, 8 s plus jitter.
- Retried: timeouts, connection errors, HTTP 429 and 5xx. Not retried: 4xx such as a bad key or a bad request.
- Models write to a `.part` file, which is renamed only on success, so a crash never leaves a broken file that looks cached.
- After the last failed attempt, the shot's `video.fallback` (Ken Burns or a still) is written as `<shot>_<hash>.fallback.<ext>`. It is not a cache hit, so the next run tries the real model again.

## Logging (`pipeline/common/runlog.py`)
`runs.jsonl` gets one line per attempt: `ts, run_id, stage, shot, provider, model, params, seed, input_hash, status (ok | error | cache_hit | fallback), attempt, latency_s, gpu_s, cost_usd_list, output, error`.

## Keyframes (`pipeline/keyframes.py`, `providers/cloudflare.py`)
- **`ImageModel` registry:** records what each FLUX model *verifiably* honours (size, references, seed) from the schema API and our probe. Requests a model can't honour are refused rather than silently ignored, because an ignored field in a cache key is a false promise.
- **One reference sheet per character first.** Every shot of that character is conditioned on it and repeats the same description text. The sheet's **file** hash is in each shot's key, so a new sheet re-makes exactly that character's shots.
- **One square 1024² master per shot.** `video.focus` chooses where the 16:9 and 9:16 crops centre. The seed is not honoured by the model, so `seed` is a take number: change it to re-roll one shot on purpose.
- **Separate template versions** for sheets and shots, so a shot-prompt change never silently remakes the sheets.

## Final cut (`assemble --mode final`, `pipeline/render.py`)
- **Each shot** is the imported motion clip if one exists, otherwise a Ken Burns move on its keyframe, or on another shot's keyframe for an insert (`video.still`). The move comes from the shot's `motion_prompt` ("push-in", "pull-back", "pan left to right", "static").
- **Shot boundaries** are whole frames rounded on cumulative times, so there is no drift against the narration. Per-shot segments are cached in `outputs/cuts/parts/` by everything that changes their pixels.
- **One audio master serves both ratios:** the same chain as the radio cut, with the chosen score in place of the pad.
- **Subtitles per ratio:** 40 characters per row for 16:9, 26 for 9:16, lifted above the bottom ~20% of the vertical frame. The end card is drawn as a centred card.
- **The final cut's cache key** includes card/subtitle styles and output size (F-17).

## Beats and head-safe framing (`pipeline/beats.py`, `render.crop_window` / `fit_move`, `pipeline/framing.py`)
- **A shot is one or more *visual units*.** Unit 0 is the shot itself, so old cache names stay valid. Beat k is `<shot>-b<k>`, with its own keyframe, segment and Wan clip contract.
- **A beat starts 0.15 s before its word** (`from_word`), estimated from the cached narration by character share. Narration never reads visual fields, so swapping the audio later re-times beats automatically and regenerates nothing.
- **`video.safe_box`** must be inside every crop and every Ken Burns moment. When it can't fit: vertically keep the top (heads), sideways centre.
- **Shot prompt templates are versioned per kind** (character vs scene), so changing the character template never re-rolls a scene-only keyframe.
- **A motion clip's key excludes the shot duration:** a narration retime never invalidates Wan clips.
- **`py -m pipeline framing`** draws all of this on the keyframes for review before rendering.
- **Segments are cached by their actual framing** (`render.still_plan`: window, fitted move, vertical centre), not by its inputs, so a framing-rule change can never leave a stale segment (F-24).
- **Prompt rule for cultural objects:** describe the shape and parts (a jebena: spherical base, tall bottle-like neck, side spout, loop handle), never only the name, and never name what to avoid (EXP-11).

## GPU stages
Wan 2.2 and ACE-Step run in Kaggle notebooks (`notebooks/`, see its README for the round trip). `shots/music --export` writes a job bundle that lists only what is missing. `--import` copies back only files whose names match the current contract (a clip tied to an old keyframe is ignored) and merges the notebook's log lines without duplicates. The music hash ignores cue *times*, so retiming never invalidates the score.

**What actually ran (2026-11-25):**
- **ACE-Step** produced 3 candidates on a T4, and c1 was chosen (EXP-13).
- **Wan 2.2 TI2V-5B** loads after a RAM patch but runs out of GPU memory at step 0 on a T4 (F-26, EXP-12), so the clip contract is in place and unused.
- **Notebook environments:** each model gets its own Python 3.11 venv, with the torch trio pinned (F-25).
