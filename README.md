# AI Film Pipeline: The Heritage Short

A small studio in code. One file, [`storyboard.json`](storyboard.json), describes a 60–90 second family-history film: shots, prompts, narration, music cues. Each pipeline stage reads that file, writes its outputs and logs every model call to [`runs.jsonl`](runs.jsonl). Change one shot and only that shot is regenerated.

> **Status (2026-11-26, submitted):** the film *ገጠር – Geter* (70.3 s) renders in 16:9 and 9:16 from `storyboard.json`:
> - Amharic narration (Gemini TTS, one continuous read) with English subtitles
> - keyframes (Cloudflare FLUX.2 klein, with character reference sheets and word-timed beats) and head-safe Ken Burns motion
> - the ACE-Step score (candidate c1, generated on Kaggle) ducked under the voice, −14 LUFS
> - the AI end card
>
> Wan 2.2 motion clips were tried on a free Kaggle T4 and didn't fit in memory (FAILURES.md F-26), so every shot keeps its Ken Burns move. A pronunciation pass from user test 2 is prepared on branch `feat/pronunciation-pass` (DESIGN.md).

## Quick start

**Windows (PowerShell)**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env        # then put your real keys in .env
py -m pipeline validate
py -m pytest
```

**Mac / Linux**
```bash
make setup && source .venv/bin/activate
cp .env.example .env          # then put your real keys in .env
make validate && make test
```

You also need **FFmpeg** on your PATH for the assembly stage (Windows: `winget install --id Gyan.FFmpeg -e`).

## One command: make the film

```
py -m pipeline film        # Windows
make film                  # Mac / Linux
```
Runs validate → narration → keyframes → shots → music → assemble (final), and writes `outputs/cuts/final-16x9_<hash>.mp4` and `final-9x16_<hash>.mp4`. Anything whose inputs have not changed is reused from `outputs/` (logged as `cache_hit`).

**From a clean clone** (`outputs/` is not in git, so the media is regenerated):
- **You need:** the keys in `.env` (Gemini, Cloudflare) and FFmpeg on your PATH.
- **Narration and keyframes are regenerated** from the storyboard: 1 TTS request and 16 image calls (2 reference sheets, 9 shots, 5 beats; s09 reuses s08) on the free tiers (COSTS.md). These models aren't deterministic, so a fresh clone gets a new recording and new pictures, not byte-identical ones. On one machine, the input-hash cache is what makes re-runs identical.
- **Split corrections** in `narration_splits.json` are pinned to the exact recording they were verified on (`audio_hash`), so a new recording gets the automatic split. Check it with `py -m pipeline asr-check`.
- **The score and motion clips are GPU stages on Kaggle** (`notebooks/README.md`). Until the score is imported, `film` warns and uses the placeholder pad, and every shot without a clip uses its Ken Burns move. The film always renders (ARCHITECTURE.md, point 5).

## Commands

| Command | What it does |
|---|---|
| `py -m pipeline validate` | Check `storyboard.json` against the schema and the extra rules |
| `py -m pipeline smoke` | Call each provider once and log latency |
| `py -m pipeline <stage> [--shot s03]` | Run one stage, optionally for one shot |
| `py -m pipeline narration --shot s03` | Re-voice one line (per_line mode: only that shot calls TTS) |
| `py -m pipeline audition --shot s01 --voices Charon,Iapetus` | Speak one line in several voices to choose by ear (`outputs/auditions/`) |
| `py -m pipeline asr-check` | Transcribe each narration segment to check the split and the pronunciation (Gemini text model, cached) |
| `py -m pipeline retime` | Set every `duration_s` from the measured narration (review with `git diff`) |
| `py -m pipeline keyframes [--shot s04]` | Reference sheets, then one square keyframe per shot (cached; change a shot's `seed` to re-roll it) |
| `py -m pipeline shots --export DIR` / `--import DIR` | Kaggle round trip for Wan 2.2 clips (`notebooks/README.md`) |
| `py -m pipeline music --export DIR` / `--import DIR` | Kaggle round trip for ACE-Step score candidates |
| `py scripts/score_previews.py` | one listening preview per imported score candidate (narration + ducked score, same audio chain as the final cut) in `outputs/previews/`, to choose `score.chosen` by ear |
| `py -m pipeline framing [--shot s04]` | Draw safe boxes and 16:9/9:16 crops on the keyframes (`outputs/qa/framing.png`) before rendering |
| `py -m pipeline assemble --mode final` | The film in every storyboard aspect ratio (16:9 and 9:16) |
| `py -m pipeline assemble --mode radio` | Radio cut: narration + ducked placeholder pad + subtitles on black, plus a timing report |
| `py -m pipeline film` | Run every stage in order and render the final film in 16:9 and 9:16 (cached work is skipped) |

**Narration modes** (`voice.mode` in `storyboard.json`): `continuous` reads the whole story in one TTS call (one voice and flow, 1 request) and splits it at the pauses. `per_line` makes one call per shot. The free tier allows 10 TTS requests a day (FAILURES.md F-09).

Tested models (2026-11-25/26):
- narration: `gemini-3.8-flash-tts` on API **v1beta** (it is not returned by `models.list`; see FAILURES.md F-06)
- QA: `gemini-3.5-flash`
- images: `@cf/black-forest-labs/flux-2-klein-4b` (FLUX.1 schnell in the smoke test)
- music: ACE-Step 1.5 turbo on a Kaggle T4

## Stages

| Stage | Model | Runs on | Output |
|---|---|---|---|
| narration | Gemini Flash TTS | Gemini API (free tier) | `outputs/narration/` |
| keyframes | FLUX (schnell / klein) | Cloudflare Workers AI | `outputs/keyframes/` |
| shots | Wan 2.2 TI2V-5B, Ken Burns fallback | Kaggle GPU / FFmpeg | `outputs/shots/` |
| music | ACE-Step 1.5 | Kaggle GPU | `outputs/music/` |
| assemble | FFmpeg | your machine | `outputs/cuts/` |

How the pieces fit together: [ARCHITECTURE.md](ARCHITECTURE.md). Measured cost: [COSTS.md](COSTS.md).

## Repository map

```
storyboard.json   the contract          schema/      its JSON Schema
pipeline/         one script per stage  pipeline/common/  shared helpers
tests/            offline tests         notebooks/   Kaggle GPU notebooks
runs.jsonl        one line per model call
scripts/          helper tools (score previews)
narration_splits.json  verified split corrections, pinned to one recording
DESIGN.md  ARCHITECTURE.md  EXPERIMENTS.md  FAILURES.md  COSTS.md  ETHICS.md  REPORT.md
```

## Roadmap
- [x] Skeleton: schema, validation, caching, retries, logging, tests
- [x] Step 2: smoke test, narration, radio cut, real story, user test 1 (DESIGN.md)
- [x] Step 3a: reference sheets, keyframes, Ken Burns final cut in 16:9 and 9:16
- [x] Step 3b: ACE-Step score: 3 candidates generated on Kaggle T4 (`notebooks/acestep_score.ipynb`)
- [x] Step 4: final edit (ducking, subtitles, loudness, end card, 9:16 + 16:9), score c1 chosen (EXP-13), user test 2 (DESIGN.md)
- [ ] Wan 2.2 clips: tried on Kaggle T4, out of memory (FAILURES.md F-26); shots keep their Ken Burns moves, and clips from a ≥ 24 GB GPU slot in through the same contract
- [ ] Pronunciation pass from user test 2: prepared on `feat/pronunciation-pass`, needs one TTS re-read

## Secrets
Real keys go only in `.env`, which is git-ignored. `.env.example` lists the names with placeholder values. `tests/test_secrets.py` fails if a real-looking key appears in any repository file.
