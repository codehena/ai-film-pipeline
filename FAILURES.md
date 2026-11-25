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
---

### F-10: `retime` rewrote storyboard.json with Windows line endings
- **Date:** 2026-11-25
- **Stage / model:** retime (local)
- **What happened:** the first real `retime` (after the 11:01 EAT continuous read) wrote `storyboard.json` with CRLF line endings. `Path.write_text` in text mode on Windows turns every `\n` into `\r\n`, while `.gitattributes` stores LF. Git warned on every touch, and the working-copy diff became noisy.
- **What fixed it / workaround:** `write_text(..., newline="\n")`, plus a test assertion that the written file contains no `\r\n`. Re-running `retime` now leaves the file byte-identical (checked 2026-11-25 18:21 EAT: 0 CRLF, 300 LF).
- **Lesson:** any code that writes a tracked text file on Windows must pick its line endings explicitly. (The same bug was fixed earlier in `runlog.py`.)

---

### F-11: The radio cut missed the loudness target (−15.9 LUFS instead of −14)
- **Date:** 2026-11-25
- **Stage / model:** assemble --mode radio / FFmpeg `loudnorm`
- **What happened:** verifying the draft 3 cut (`radio_633140d7a506.mp4`) measured **−15.88 LUFS** integrated and **−0.80 dBTP** true peak. The target is −14 LUFS with true peak ≤ −1. Draft 2 had also missed, at −14.77 / −0.79.
- **Root cause (measured):** the raw mix (narration plus ducked pad) is **−23.54 LUFS with true peak −3.61 dBTP**, so its peaks sit 20 dB above its loudness. Reaching −14 needs +9.5 dB, which would put peaks near +6 dBTP. Single-pass `loudnorm` therefore silently falls back to "dynamic" mode and stops short of the target.
- **What I tried:** each attempt was measured on the real mix in a scratch folder (EXPERIMENTS.md EXP-04).
  1. Two-pass linear `loudnorm` alone: still dynamic, final −14.42.
  2. A −3 dBFS limiter before it: did nothing, because the peaks were already below −3.
  3. Pre-gain to −14 plus a limiter at −1.5 or −2 dBFS: −14.2 to −14.3, but true peaks between samples overshot and the final pass stayed dynamic.
- **What fixed it:** `common/loudness.py`, in three steps:
  - measure the raw mix
  - pre-gain by (−14 − measured + 2 dB) and limit at −3.5 dBFS
  - measure again, then apply `loudnorm` with those measurements and `linear=true`

  Result: **−14.0 LUFS, −1.58 dBTP, final pass linear**. FFmpeg's independent `ebur128` meter agrees: −13.9 LUFS, −1.6 dB. Every step's numbers go to `radio_<hash>.loudness.json`, and the stage prints a WARNING if the delivered file misses the target. The end-to-end test now requires a problem-free loudness report.
- **Lesson:** "I ran loudnorm" is not "the file is at −14 LUFS". Measure the delivered file, and make missing the target loud.

---

### F-12: The continuous-read split put words in the wrong shot, and the ratio check didn't catch all of it
- **Date:** 2026-11-25
- **Stage / model:** narration (continuous) / `common/silence.py`
- **What happened:** the draft 4 read (`full_64173211a953.wav`) split with s03 = 1.32 s for 10 words (×0.26, flagged) and s04 = 8.42 s (×1.65).
- **What I tried:**
  1. **Tuning the splitter (rejected).** A stronger position penalty fixed draft 4 but moved several breaks in the draft 3 read, which had been clean. That just trades one guess for another.
  2. **Transcribing the speech chunks between 16 and 27 s** with a Gemini text model. This showed the *real* error: 16.22–17.54 s was "አንዳንዴም ይናፍቀኛል", the **end of s02**. s02 had been cut at its own internal "፤" pause even though its ratio looked perfect (×1.03), and s03/s04 were shifted by one chunk. Lines chained with "፣" made a comma breath and a line break look alike.
- **What fixed it:**
  - `narration_splits.json` (committed) holds verified span corrections **keyed to one specific read**, so they never leak onto a new take. `narration` applies them at no TTS cost, and the split report marks them "corrected".
  - `py -m pipeline asr-check` transcribes every segment, so all 10 boundaries were checked, not just the flagged one. After the correction, every segment starts and ends on its own line's words.
  - Each segment now gets 0.1 s of padding (capped at half the gap), because "**እን**ደሚባለው" came back without its first syllable, which hinted at a clipped soft onset.
- **Side snags:**
  - `gemini-3.8-flash` and `3.7-flash` returned 503 "high demand", so I used `gemini-3.5-flash`.
  - Its free tier hit **20 requests/day** (the error names `gemini-3.6-flash`, so the quota seems shared).
  - `asr-check` saved its cache only at the end, so **7 finished transcripts were lost** when the quota hit. It now saves after every line (tested).
- **Lesson:** a ratio check can say "suspicious", but not "correct". Hearing the words back is the evidence. Corrections should be data tied to their source, not hand-edited outputs.

---

### F-13: The loudness recipe from F-11 failed on the next mix
- **Date:** 2026-11-25
- **Stage / model:** assemble / `common/loudness.py`
- **What happened:** the draft 4 cut came out at −14.16 LUFS / −0.95 dBTP, but the final pass **fell back to dynamic**, which the new check reported as a WARNING. The Iapetus mix starts much louder (−19.8 LUFS vs −23.5), so the fixed +2 dB of extra pre-gain was wrong for it.
- **Root cause:** after the −3.5 dBFS limiter, true peaks came out at −2.6 dB. Peaks *between samples* overshot the ceiling by about 0.9 dB, leaving only 1.3 dB of room for the +2.1 dB final gain.
- **What I tried:** an adaptive loop that pushes more level into the limiter until the final gain fits. It did not converge in 4 rounds (needed 1.57 dB vs 1.30 allowed) and squashed the voice more each round.
- **What fixed it:** limiting at **4× the sample rate** (192 kHz), plus the adaptive loop as a safety net. The overshoot dropped to 0.00 dB, and both the draft 3 and draft 4 mixes reach target in **one round** with a linear final pass (−14.00 / −14.01 LUFS). Recipe v3. Unit tests cover one round, more rounds, and the round cap.
- **Lesson:** a fix tuned on one example is a guess. Re-test it on a second, different input before calling it done.

---

### F-14: Draft 4's richer lines made unreadable subtitles
- **Date:** 2026-11-25
- **Stage / model:** assemble (subtitles)
- **What happened:** the wrapper kept each line to two subtitle rows by widening them. s02 ended up with 61-character rows and s10 with **75**, while the guideline is about 40.
- **What fixed it:** `split_caption()` splits a long subtitle into consecutive cues at sentence and clause breaks, each timed in proportion to its length, with no words dropped or reordered (tested). The draft 4 cut now has 15 cues and its widest row is 43 characters. Recipe v4.

---

### F-15: FLUX.2 klein edited the reference sheet instead of drawing the scene
- **Date:** 2026-11-25
- **Stage / model:** keyframes / `@cf/black-forest-labs/flux-2-klein-4b`
- **What happened:** with both boys' reference sheets attached, s04 ("two boys walking to the spring") came back as a **character sheet**: front and back poses on a plain background, with both shirts recoloured yellow (taken from "yellow water container").
- **Cause:** klein "unifies generation and editing". With input images, a plain scene prompt was read as an edit of the reference.
- **What fixed it:** shots that use references now open with an explicit instruction: a completely new illustration of the scene, using the references only for how the boys look. The next s04 showed both boys exactly as on their sheets, by the water. Keyframes `s04_f272050fa9c7` (bad) and `s04_5feab1d8798e` (good) are both kept as evidence.
- **Side bug:** one shared prompt-template version made the change also remake both reference sheets (2 wasted calls). The sheet and shot templates now have separate versions (tested).

### F-16: s09's coffee cup kept its handle, three times
- **Date:** 2026-11-25
- **Stage / model:** keyframes / FLUX.2 klein
- **What happened:**
  - Take 1, "small white handleless sini cup": a Western mug with a handle.
  - Take 2, "a small round bowl", without the word *handle*: one cup right, one with a handle, and the style drifted towards realism.
  - Take 3, the jebena alone: a pot with **two** spouts, plus unrelated men in the background.
- **Lesson:** a negated word ("handleless") still pulls its object in. Describing the shape helps, but not reliably.
- **What fixed it (fallback after 3 attempts, per the brief):** s09 is now an **insert** from s08, whose jebena and sini cups were right: a slow push-in on the jebena as the proverb is spoken (`video.still: {from: s08, zoom: [1.5, 1.9]}`). It costs no extra calls and is consistent by construction, since it is the same scene.

### F-17: The first final render had a corner end card, 3-row vertical subtitles, and a stale cached 16:9 cut
- **Date:** 2026-11-25
- **Stage / model:** assemble --mode final (FFmpeg / libass)
- **How it was found:** extracting frames from both exports and looking at them. The numbers (duration, loudness) were all fine.
- **What happened, and the fixes:**
  1. **The end card sat in the top-left corner.** FFmpeg reads `force_style` alignment in legacy SSA numbering, where 5 is top-left. Middle-centre is **10**.
  2. **One 9:16 subtitle wrapped to 3 rows**, because the clause had no punctuation to split at. Such clauses are now split between words, and rows are balanced.
  3. **After the card fix, the 16:9 cut was served from the cache unchanged.** Its cache key covered the card *text* but not the card/subtitle *style* or the output size. The key now includes them, and a test proves that a style change produces a new cut.
- **Lesson:** a cache key must cover everything that changes the delivered pixels, not just the content. And look at the frames, not only the numbers.

### F-18: Work stopped mid-turn (by hand) while building the final cut
- **Date:** 2026-11-25
- **What happened:** the session was stopped while code for the final assembly was being written, with no render running.
- **What I did:** audited before continuing:
  - `git status`, branches and log
  - searched for `*.part.*` and zero-byte files: none
  - confirmed every keyframe the storyboard points to exists and decodes (12/12, 1024×1024)
  - ran the full test suite: 140 passed
  - committed the uncommitted work in focused pieces
- **Why nothing was half-written:** model outputs are written to a `.part` file and renamed only on success (`run_model_step`), and FFmpeg segments follow the same pattern. A stop leaves either a complete file or nothing.
