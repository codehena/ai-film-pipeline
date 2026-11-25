# Costs

All numbers are **measured** from `runs.jsonl` unless marked as an estimate. Free-tier limits change often, so each one below records what I actually found and when.

## Free-tier limits found
| Provider | Limit found | How I found it | Date |
|---|---|---|---|
| Gemini API, `gemini-3.8-flash-tts` | **3 requests per minute** per model (`GenerateRequestsPerMinutePerProjectPerModel-FreeTier`, quotaValue 3) | 429 error during narration (FAILURES.md F-08) | 2026-11-25 |
| Gemini API, `gemini-3.8-flash-tts` | **10 requests per day** ("Generate content requests per day limit", limit 10) | 429 errors during the voice audition (F-09) | 2026-11-25 |
| Gemini API, text models | TODO (no limit hit yet) | | |
| Cloudflare Workers AI | TODO (daily neurons) | | |
| Kaggle GPU | TODO (hours/week) | | |

## Per stage (Phase 1: radio cut)
| Stage | Model | Calls | Median latency | GPU minutes | List-price equivalent |
|---|---|---|---|---|---|
| smoke | Gemini text, TTS; Cloudflare FLUX.1 schnell | 1 each per run | TTS 3.0 s, text 0.8 s, FLUX 3.6–4.6 s | – | TODO |
| narration | `gemini-3.8-flash-tts` | 10 ok + 3 rate-limited (429) | **4.2 s** (min 3.3, max 13.8) | – | TODO (free tier: USD 0) |
| assemble (radio) | FFmpeg 9.1, local | 2 renders | **12.2 s** per 85 s cut | – | 0 |
| keyframes | FLUX | – | – | – | – |
| shots | Wan 2.2 TI2V-5B | – | – | – | – |
| music | ACE-Step 1.5 | – | – | – | – |

**Narration throughput:** 68.6 s of Amharic speech from 10 calls, at 87 words per minute (EXP-01). At 3 requests per minute, a full 10-line re-voice takes at least about 3.5 minutes of wall-clock time on the free tier. Caching means a single-line edit is one call.

**The real budget is per day.** At 10 TTS requests a day, per-line mode spends the **whole day's quota** on one full read. Continuous mode (EXP-02) reads the whole story in **1** request, so a day's quota covers a full read, a few voice auditions and several re-takes. Each audition take costs 1 request.

**What caching saved:** changing all 10 shot durations (draft 1 → draft 2) cost **0 TTS calls** (10 `cache_hit` lines) and one 12 s FFmpeg render.

## How list-price equivalents were calculated
TODO: the price source and date for each provider.

## Frontier comparison (if available)
TODO
