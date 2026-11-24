# AI Film Pipeline: The Heritage Short

A small studio in code. One file, [`storyboard.json`](storyboard.json), describes a 60–90 second family-history film: shots, prompts, narration, music cues. Each pipeline stage reads that file, writes its outputs and logs every model call to [`runs.jsonl`](runs.jsonl). Change one shot and only that shot is regenerated.

> **Status:** starter skeleton. Validation, caching, retries and logging work and are tested. The generation stages are stubs (see "Roadmap").

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
Runs validate → narration → keyframes → shots → music → assemble. Anything whose inputs have not changed is reused from `outputs/` (logged as `cache_hit`).

## Commands

| Command | What it does |
|---|---|
| `py -m pipeline validate` | Check `storyboard.json` against the schema and the extra rules |
| `py -m pipeline smoke` | Call each provider once and log latency |
| `py -m pipeline <stage> [--shot s03]` | Run one stage, optionally for one shot |
| `py -m pipeline film` | Run everything in order |

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
DESIGN.md  ARCHITECTURE.md  EXPERIMENTS.md  FAILURES.md  COSTS.md  ETHICS.md
```

## Roadmap
- [x] Skeleton: schema, validation, caching, retries, logging, tests
- [ ] Step 2: smoke test, narration, radio cut (Phase 1 checkpoint)
- [ ] Step 3: reference sheet, keyframes, Wan 2.2 shots, ACE-Step score
- [ ] Step 4: final edit (ducking, subtitles, loudness, end card, 9:16 + 16:9)

## Secrets
Real keys go only in `.env`, which is git-ignored. `.env.example` lists the names with placeholder values. `tests/test_secrets.py` fails if a real-looking key appears in any repository file.
