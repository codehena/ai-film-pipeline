# Costs

All numbers are **measured** from `runs.jsonl` unless marked as an estimate. Free-tier limits change often, so each one below records what I actually found and when.

## Free-tier limits found
| Provider | Limit found | How I found it | Date |
|---|---|---|---|
| Gemini API, `gemini-3.8-flash-tts` | **3 requests per minute** per model (`GenerateRequestsPerMinutePerProjectPerModel-FreeTier`, quotaValue 3) | 429 error during narration (FAILURES.md F-08) | 2026-11-25 |
| Gemini API, `gemini-3.5-flash` (text; used for `asr-check`) | **20 requests per day** (the error names `gemini-3.6-flash`, so the quota seems shared); 503 "high demand" seen on 3.8/3.7 flash | 429 during asr-check (F-12) | 2026-11-25 |
| Gemini API, `gemini-3.8-flash-tts` | **10 requests per day** ("Generate content requests per day limit", limit 10); resets 08:00 UTC = 11:00 EAT (`retryDelay` 23084 s at 01:35 UTC) | 429 errors during the voice audition (F-09) | 2026-11-25 |
| Cloudflare Workers AI | Not hit: **43** FLUX.2 klein images on 2026-11-25 with 0 errors (free daily neuron allowance; per-image neurons aren't reported by the API) | `runs.jsonl` stages `keyframes`, `probe` | 2026-11-25 |
| Kaggle GPU | 2× Tesla T4 (14.6 GB VRAM each), about 31 GB host RAM per session; weekly GPU-hour quota (check the Kaggle settings page) | Kaggle session, `nvidia-smi`, `free -g` | 2026-11-25 |

## Per stage (Phase 1: radio cut)
| Stage | Model | Calls | Median latency | GPU minutes | List-price equivalent |
|---|---|---|---|---|---|
| smoke | Gemini text, TTS; Cloudflare FLUX.1 schnell | 1 each per run | TTS 3.0 s, text 0.8 s, FLUX 3.6–4.6 s | – | TODO |
| narration (per_line, drafts 1–2) | `gemini-3.8-flash-tts` | 10 ok + 3 rate-limited (429) | **4.2 s** (min 3.3, max 13.8) | – | TODO (free tier: USD 0) |
| narration (continuous, draft 3) | `gemini-3.8-flash-tts`, Iapetus | **1** ok (after the reset; 4 attempts before it hit the daily cap) | **24.3 s** for the whole 64.7 s read | – | TODO (free tier: USD 0) |
| assemble (radio), single-pass loudnorm | FFmpeg 9.1, local | 3 renders | 9.5–12.4 s per cut | – | 0 |
| assemble (radio), two-pass loudness | FFmpeg 9.1, local | 1 render | **36.0 s** per 65.5 s cut (4 measure/render passes) | – | 0 |
| narration (continuous, draft 4) | `gemini-3.8-flash-tts`, Iapetus | **1** ok | 64.9 s read; split corrected at no TTS cost | – | TODO (free tier: USD 0) |
| qa: asr-check | `gemini-3.5-flash` | 21 ok, 8 errors (503 or quota) | a few s per segment | – | TODO (free tier: USD 0) |
| assemble (radio), recipe v3/v4 (oversampled limiter, split subtitles) | FFmpeg 9.1, local | 3 renders | **38.7–41.1 s** per 71 s cut | – | 0 |
| assemble (radio), Option A spacing (draft 4b) | FFmpeg 9.1, local | 1 render | **22.4 s** per 70.3 s cut; 0 model calls | – | 0 |
| keyframes (2 sheets + 10 shots + retakes) | FLUX.2 klein 4B (Cloudflare) | **19** ok + 2 probe, 0 errors | **16.8 s** (12.1–25.8) | – | TODO (free tier: USD 0) |
| keyframes, draft 4c (beats, ensera, swimming, friends, ceremony, gojo bet) | FLUX.2 klein 4B | **14** ok (11 + s06 retake + 2 s10 retakes), 0 errors | **18.1 s** median | – | TODO (free tier: USD 0) |
| assemble (final, 16:9 + 9:16) | FFmpeg 9.1, local | 5 renders | first render 110 s (16:9) + 72 s (9:16), building every Ken Burns segment at 4×; re-renders with cached segments 13–42 s | – | 0 |
| shots | Wan 2.2 TI2V-5B (Kaggle T4) | 4 attempts, 0 clips (OOM, F-26) | about 8 min to failure (≈4 min loading weights) | ≈ 33 GPU-min spent, 0 output | 0 (free tier) |
| music | ACE-Step 1.5 turbo + 5Hz LM 1.7B (Kaggle T4, fp16) | 3 ok, 0 errors | **60 s** per 75 s candidate (≈51 s LM codes + ≈3 s diffusion + ≈4 s VAE); ≈1.5 min model load once | ≈ 4.5 GPU-min | 0 (free tier) |

**Narration throughput:** 68.6 s of Amharic speech from 10 calls, at 87 words per minute (EXP-01). At 3 requests per minute, a full 10-line re-voice takes at least about 3.5 minutes of wall-clock time on the free tier. Caching means a single-line edit is one call.

**The real budget is per day.** At 10 TTS requests a day, per-line mode spends the **whole day's quota** on one full read. Continuous mode (EXP-02) reads the whole story in **1** request, so a day's quota covers a full read, a few voice auditions and several re-takes. Each audition take costs 1 request.

**What caching saved:** changing all 10 shot durations (draft 1 → draft 2) cost **0 TTS calls** (10 `cache_hit` lines) and one 12 s FFmpeg render. For draft 3, retiming, the loudness fix and the character descriptions together cost **0 TTS calls**: the one continuous read was reused every time, and an unchanged radio cut is a logged `cache_hit` (0 s).

**Quota used for the whole draft 3 radio cut: 1 of 10 daily TTS requests.** Draft 4 used 1 more (2 of 10 on 2026-11-25). The split correction, re-cut, retime and 3 re-renders used 0. Under per-line mode the same read would have taken all 10.

## How list-price equivalents were calculated
TODO: the price source and date for each provider.

## Frontier comparison (if available)
TODO

**Draft 4c render cost:** 15 visual units (10 shots + 5 beats) per ratio. A full rebuild of both ratios took 276 s (16:9) + 265 s (9:16) locally, with 0 model calls, because every Ken Burns segment is rendered at 4× for smoothness. Unchanged segments are cached, so later re-renders only rebuild what changed.
**s08 fix (draft 4d):** 2 keyframe generations (attempt 1: jebena wrong; attempt 2 kept), 0 TTS/ASR calls. s09 changed with it at no generation cost (insert from s08). The new segment cache key (framing plan, F-24) forced one full rebuild of both ratios: 164 s (16:9) + 262 s (9:16), local FFmpeg only.
**Score chosen (2026-11-26):** 3 listening previews (local FFmpeg, about 30 s each) and one final re-render of both ratios with the chosen score: **139 s** total, all picture segments cached, 0 model calls.
