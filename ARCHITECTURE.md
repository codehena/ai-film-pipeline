# Architecture

## The idea in one sentence
`storyboard.json` is the only contract between stages. Each stage reads it (plus earlier stages' outputs), writes files to `outputs/<stage>/`, and logs every model call to `runs.jsonl`.

```
storyboard.json ──validate──┬──> narration ──────────────┐
                            ├──> keyframes ──> shots ────┼──> assemble ──> outputs/cuts/*.mp4
                            └──> music ──────────────────┘
                     every model call ──> runs.jsonl
```

## Contracts

| Stage | Reads from storyboard | Reads files | Writes |
|---|---|---|---|
| validate | everything | `schema/storyboard.schema.json` | nothing (fails fast) |
| narration | `voice`, `language.narration`, `shots[].narration.text` | – | `outputs/narration/<shot>_<hash>.wav` |
| keyframes | `style_block`, `characters`, `shots[].image_prompt`, `seed` | reference sheet | `outputs/keyframes/<shot>_<hash>.png` |
| shots | `shots[].motion_prompt`, `video`, `duration_s`, `seed` | that shot's keyframe | `outputs/shots/<shot>_<hash>.mp4` |
| music | `music_cues` | – | `outputs/music/` |
| assemble | everything | all of the above | `outputs/cuts/` (9:16 and 16:9) |

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

## Failure handling (`pipeline/common/retry.py`, `modelcall.py`)
- `with_retry()`: up to 3 attempts with backoff of 2 s, 4 s, 8 s plus jitter.
- Retried: timeouts, connection errors, HTTP 429 and 5xx. Not retried: 4xx such as a bad key or a bad request.
- Models write to a `.part` file, which is renamed only on success, so a crash never leaves a broken file that looks cached.
- After the last failed attempt, the shot's `video.fallback` (Ken Burns or a still) is written as `<shot>_<hash>.fallback.<ext>`. It is not a cache hit, so the next run tries the real model again.

## Logging (`pipeline/common/runlog.py`)
`runs.jsonl` gets one line per attempt: `ts, run_id, stage, shot, provider, model, params, seed, input_hash, status (ok | error | cache_hit | fallback), attempt, latency_s, gpu_s, cost_usd_list, output, error`.

## GPU stages
Wan 2.2 and ACE-Step run in Kaggle notebooks (`notebooks/`). The local stage writes a job file listing only uncached shots, and imports the results and their log lines afterwards.
