# Failures

What broke, what I tried, what fixed it (or how I worked around it). Write these down as they happen.

## Template

### F-01: short title
- **Date:**
- **Stage / model:**
- **What happened:** (paste the error message)
- **What I tried:**
- **What fixed it / workaround:**
- **Lesson:**

---

### F-01: Git and FFmpeg not installed on the development machine
- **Date:** 2026-11-25
- **Stage / model:** setup
- **What happened:** `git` and `ffmpeg` were not found in PowerShell; `python` opened the Microsoft Store prompt instead of running Python.
- **What I tried:** checked with `Get-Command`; found Python 3.13 available through the `py` launcher.
- **What fixed it / workaround:** use `py` instead of `python`; install Git and FFmpeg with `winget`.
- **Lesson:** check the toolchain before writing pipeline code; document `py` vs `python3` in the README.

---

### F-02: Git commit failed due to missing author identity
- **Date:** 2026-11-25
- **Stage / model:** setup / git
- **What happened:** `git commit` failed with `Author identity unknown` and `fatal: unable to auto-detect email address` in PowerShell.
- **What I tried:** ran `git commit -m "chore: add verified pipeline skeleton and offline tests"` after staging files.
- **What fixed it / workaround:** set global Git `user.name` and `user.email` with `git config --global`, then re-ran `git commit` and verified a clean working tree with `git status`.
- **Lesson:** configure Git author identity right after initializing a repository before making the first commit.

---

### F-03: Rotated Cloudflare Workers AI token after early screenshot exposure
- **Date:** 2026-11-25
- **Stage / model:** setup / cloudflare-workers-ai
- **What happened:** an early Cloudflare Workers AI token value was exposed during setup prior to running live pipeline checks.
- **What I tried:** checked `.gitignore` / `.env` handling so secrets stay local and out of version control.
- **What fixed it / workaround:** revoked the exposed token, generated a scoped replacement token, saved it in `.env`, and verified environment presence without printing secret values.
- **Lesson:** rotate any exposed credential immediately rather than reusing it, and verify `.env` stays ignored before live API calls.
---

### F-04: Git push failed with HTTP 400 due to literal angle brackets in remote URL
- **Date:** 2026-11-25
- **Stage / model:** setup / git
- **What happened:** `git push -u origin master` failed with `fatal: unable to access 'https://github.com/<codehena>/ai-film-pipeline.git/': The requested URL returned error: 400`.
- **What I tried:** added `origin` using `<codehena>` placeholder brackets in the repository URL and ran `git push -u origin master`.
- **What fixed it / workaround:** updated the remote URL with `git remote set-url origin https://github.com/codehena/ai-film-pipeline.git` without angle brackets, then re-ran `git push -u origin master`.
- **Lesson:** replace placeholder brackets (`<...>`) completely when copying remote URLs before pushing.

---

### F-05: FFmpeg and Git "not found" right after installing them
- **Date:** 2026-11-25
- **Stage / model:** setup / assemble (FFmpeg)
- **What happened:** after `winget install` of Git and FFmpeg, a terminal that was already open still reported `git` / `ffmpeg` as not recognised.
- **What I tried:** reloading PATH from the registry in the session made both visible, which showed the binaries were installed but the old terminal's PATH was stale.
- **What fixed it / workaround:** `config.find_tool()` looks for FFmpeg in this order: an `FFMPEG_PATH` override in `.env`, then PATH, then winget's own install folders. A missing binary now gives a clear `missing tool:` message with the fix. The smoke test found FFmpeg 9.1 through the winget fallback even with the stale PATH.
- **Lesson:** open a new terminal after installing tools, and don't let the pipeline depend on PATH alone.

---

### F-06: Gemini TTS rejected every request: wrong API version, unlisted model, new audio format
- **Date:** 2026-11-25
- **Stage / model:** smoke / Gemini TTS
- **What happened:** `models.list` returned 28 models and none had "tts" in its name. Probing five likely ids all failed with the same `400 INVALID_ARGUMENT: Unknown name "speechConfig" at 'generation_config'` (and `"speechMetadata"`), before the model id was even checked.
- **What I tried:** stripped the request to a minimal TTS call and printed the SDK's default API version: `v1`.
- **What fixed it / workaround:** created the client with `HttpOptions(api_version="v1beta")`. On v1beta, `gemini-3.8-flash-tts` works although `models.list` does not list it. `gemini-3.8-flash-preview-tts` returned 404, and `gemini-3.8-flash` returned 503 (high demand). The 3.8 TTS model returns `audio/wav` (with a header) where older models returned raw PCM, so `save_audio()` checks for the `RIFF` header instead of always wrapping the data. First Amharic line: 3.48 s of audio in 3.01 s.
- **Lesson:** the model list is not the whole truth. Probe candidates and log every probe in `runs.jsonl`, and check what format the bytes actually are, not what the docs say.

---

### F-07: Smoke test reported success while TTS was silently skipped
- **Date:** 2026-11-25
- **Stage / model:** smoke
- **What happened:** the first smoke run found no TTS model, skipped the TTS step without recording it, and exited 0.
- **What fixed it / workaround:** a missing TTS model is now recorded as `FAILED` and the command exits 1.
- **Lesson:** "nothing to do" must still be reported, or a broken stage looks green.

---

### F-08: Free-tier TTS rate limit (3 requests/minute) stopped narration at shot 7
- **Date:** 2026-11-25
- **Stage / model:** narration / gemini-3.8-flash-tts
- **What happened:** the first full narration run generated s01–s06, then s07 failed 3 times with `429 RESOURCE_EXHAUSTED ... limit: 3, model: gemini-3.8-flash-tts ... Please retry in 26.5s` (`retryDelay: '26s'`). The CLI crashed with a long traceback.
- **What I tried:** read the three `error` lines in `runs.jsonl`. All three attempts were about 0.3 s long and inside the same minute, because my backoff (2 s, then 4 s) was far shorter than the 26 s the server asked for.
- **What fixed it / workaround:**
  - `retry.server_retry_delay()` reads the server's wait (Gemini `retryDelay`, "retry in N s", or an HTTP `Retry-After` header) and waits that long plus 1 s, capped at 120 s.
  - Narration now gets 4 attempts.
  - The CLI prints a short `stage failed:` message and reminds you that finished shots are cached (`--debug` shows the traceback).
  - Re-running resumed at s07: s01–s06 were cache hits, and s07–s10 were generated with no further 429s.
- **Lesson:** use the wait time the server sends instead of guessing. Caching turned a crash into a resume, at no extra quota.

---

### F-09: Daily TTS cap of 10 requests hit during the voice audition, and my logs hid it
- **Date:** 2026-11-25
- **Stage / model:** auditions / gemini-3.8-flash-tts
- **What happened:** auditioning 5 male voices on the new opening line ran for more than 10 minutes. Most attempts returned `429 ... limit: 10, model: gemini-3.8-flash-tts, description: Generate content requests per day limit`. Each retry waited my 120 s cap. Only Charon and Iapetus got through (one each, minutes apart), so the daily window seems to let a request through now and then rather than resetting all at once (observed, not confirmed).
- **Second problem:** `runs.jsonl` cut error text at 500 characters, which dropped the words "per day". At first I read the 429s as the per-minute limit from F-08.
- **What I tried:** read the full error text, stopped the audition (more retries could not succeed), and counted today's TTS requests in `runs.jsonl`: smoke tests, probes and 10 narration lines had used the budget.
- **What fixed it / workaround:**
  - Logged errors now keep the quota metric, limit, description and `retryDelay` (`modelcall._short_error`).
  - **Design change:** a `continuous` narration mode reads the whole story in **one** TTS call and splits it at the pauses (`common/silence.py`). A full re-voice now costs 1 request instead of 10. This also answers my own feedback that the voice should stay the same throughout (EXP-02).
  - The live continuous read waits for quota. **Reset time confirmed from the log:** with the fuller error text, the next attempt (01:35 UTC) recorded `retryDelay: '23084s'`, i.e. 6.4 h, which ends at 08:00 UTC: midnight Pacific time, **11:00 EAT**.
  - **Follow-up bug:** my retry still waited its 120 s cap three times against that 6.4 h wait, which was pointless. Now, when the server asks for longer than the cap, `with_retry` stops at once with `QuotaExhausted` and says when the quota resets (`tests/test_retry.py::test_long_server_wait_fails_fast_instead_of_retrying`).
- **Lesson:** at 10 requests a day, the unit of work has to be the whole narration, not the line. And a log that cuts off the reason for an error is a log that misleads.