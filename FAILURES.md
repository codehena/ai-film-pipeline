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

---

### F-19: The 16:9 film cut the boys' heads (s04, s05 through the eyes, s07)
- **Date:** 2026-11-25
- **Stage:** assemble --mode final / `render.crop_window`
- **Reported by:** the author, watching `final-16x9_79e1e669fdc0.mp4`.
- **Root cause (measured with a crop overlay):**
  - 16:9 kept the middle 56% of each square keyframe, centred vertically. Standing figures have their heads in the top quarter, so a centred crop removed them.
  - The Ken Burns zoom-in then tightened the crop by another 10%, with no check that heads stayed in frame.
- **What fixed it:**
  1. **`video.safe_box`:** the heads, faces or key action that must stay in frame. The crop keeps the box plus a 5% margin. If the box can't fit, it keeps the box's *top* (heads over feet) and centres sideways.
  2. **`fit_move()`:** clamps the zoom and drift so the box stays visible for the whole move.
  3. **The character prompt asks for medium-wide framing** with space above the heads (template v3).
  4. **`py -m pipeline framing`:** draws every crop and box on the keyframes. The boxes for s04–s08 and s10 were read off it, and the sheet was re-checked after.
- **Regression tests** (`tests/test_framing.py`) reproduce the measured bug, and cover both ratios, overflow, clamping and image edges.

### F-20: Pictures arrived after the words they illustrate
- **Date:** 2026-11-25
- **Reported by:** the author: "visuals stay static and catch up after the narration mentions something".
- **Root cause:** a content mismatch, not slow cutting. Each shot had one picture for its whole line:
  - **s02 (12.5 s):** the voice lists bees, birds, calves and chickens, but the picture showed bees only.
  - **The calves and chickens were in s03's picture,** which arrived *after* the line about them.
  - **s10 (12.9 s):** one image for two ideas.
- **What fixed it:** `shots[].beats`. Each beat is its own picture landing 0.15 s before the word it shows (`from_word`), with timing from the cached narration by character share. That means no model call, and narration text and audio are unchanged (tested). Measured in the new cut: all 5 beats land 0.15 s before ወፎች, ጥጃዎች, ዶሮዎች, እናቶች and እነዚህ.

### F-21: Two keyframes needed retakes (s06 swimming, s10 coffee ceremony)
- **Date:** 2026-11-25
- **s06:** attempt 1, with reference sheets plus a per-shot "in shorts" appearance, still showed the boys swimming in their shirts. The sheets show the shirts, and they win over the text. **Attempt 2, without references:** two boys from behind in khaki/blue shorts, with the green and red shirts folded on the rock. Kept.
- **s10:**
  - Attempt 1 showed both boys and other children **facing the camera with clear faces**, outside the recorded consent (ETHICS.md, "Option 1").
  - Attempt 2 had them from behind, but the brother wore his everyday red shirt (pulled from his sheet).
  - **Attempt 3, without references**, with both outfits described: from behind, white holiday tunics with green/red tibeb borders, beside the jebena. Kept, and the 3-attempt cap was reached.
- **Lesson:** reference sheets lock *clothes* as well as identity. When a shot needs different clothes, leave the references out and carry identity through colours and position.

### F-22: Two broken commits nearly slipped through (process)
- **Date:** 2026-11-25
- **What happened:**
  1. A patch script stopped halfway (an anchor matched twice), but the next command committed anyway. The schema then referenced a `#/$defs/box` that didn't exist.
  2. Later, `pytest ... | tail -1` hid a failing exit code from `set -e`, and a commit went in with a red test.
- **What fixed it:**
  - Both commits were local and unpushed, so each was repaired and amended.
  - Since then, every patch-then-commit step is chained with `&&`, and the test suite's exit code is captured *before* the pipe and checked. The commit only runs on 0.
  - The red test had found a real flaw: one shot-template version re-keyed scene-only keyframes too. Versions are now per template kind (character vs scene), so s01/s02/s08 kept their images (tested).
- **Lesson:** a commit gate that a pipe can bypass is not a gate.

### F-23: s08's coffee ceremony didn't look Ethiopian (clothing and jebena)
- **Date:** 2026-11-25
- **Reported by:** the author, watching `final-16x9_cf2f2882d313.mp4`.
- **What happened:**
  - The women wore lace veils over their heads, which read as Arabic-style dress rather than habesha wear.
  - The jebena and sini cups didn't look like a real Ethiopian *buna* ceremony.
- **Cause:** the prompt named the garments ("white netela shawls") without describing them, and the model filled the gap with a generic veil.
- **What I tried:**
  - **Attempt 1:** named and described each element: *habesha kemis* (white handwoven cotton with *tibeb* borders at hem and cuffs), *netela* over the shoulders not the face, braided hair, a straw ring, *rekebot*, popcorn, incense, *qetema*. The attire and ceremony came out right, but the jebena came out as a squat teapot.
  - **Attempt 2:** kept attempt 1's prompt and described the jebena's geometry: a spherical base, a tall thin neck like a bottle neck, a spout beside the neck, a loop handle. The word "teapot" was deliberately left out (F-16: a negated word pulls its object in). **Kept.**
- **Knock-on:** s09 is an insert from s08, so it changed with it. Its focus, safe box and zoom were retargeted on the new jebena, with no extra generation.
- **Lesson:** for cultural objects, describe the *shape and parts*, not just the name. The model knows the words but not the objects.

### F-24: The framing rules could leave stale segments in the cache
- **Date:** 2026-11-25
- **Found while:** fixing s08's crop. Heads plus the jebena (56% of the height) fit a 16:9 window (56.25%), but box + 5% margin didn't. The rule then fell back to "keep the top" and cut the jebena's body. **Fix:** shrink the margin before cutting into the box (tested).
- **The risk it exposed:** a segment's cache key held the crop *inputs* (focus, safe box), not the crop *computed*. A change to the rules could therefore silently reuse old segments with the old framing.
- **Fix:** `render.still_plan()` computes exactly what a segment shows (window, fitted move, vertical centre), and segments are keyed by that. Tested both ways: a rule change that moves pixels rebuilds the segment, and one that doesn't keeps the cache. The new key format meant one full rebuild.

### F-25: Kaggle environments: six install failures before ACE-Step ran
- **Date:** 2026-11-25 (Kaggle, 2× Tesla T4, system Python 3.13)
- **What happened, in order:**
  1. `python -m acestep.infer` doesn't exist. The entry point was guessed from memory. **Fix:** read the repo (`cli.py` is an interactive wizard) and call the Python API that `run_generate_test.py` uses (`AceStepHandler.initialize_service`, `LLMHandler.initialize`, `generate_music`).
  2. Installing ACE-Step's requirements into Kaggle's system Python downgraded numpy to 1.26. That broke jax and, through diffusers, Wan's import (`numpy.dtypes ... StringDType`). `flash-attn` failed to compile, so the rest of the list (e.g. `loguru`) never installed. **Fix:** Factory reset; one isolated Python 3.11 venv per model (`uv venv /tmp/ace`, `/tmp/wan`), with flash-attn filtered out.
  3. The venvs stayed empty: Kaggle's image makes `uv pip install` target the system Python even with `VIRTUAL_ENV` set. **Fix:** pass `--python <venv>/bin/python` on every install, and a smoke test that asserts `sys.prefix`.
  4. `torchaudio 2.11` was resolved next to `torch 2.10` (`undefined symbol torch_dtype_float4_e2m1fn_x2`). **Fix:** pin the matching trio (`2.10.0 / 0.25.0 / 2.10.0`) and `torchcodec 0.10`.
  5. Matplotlib in the venv rejected the notebook's `MPLBACKEND=module://matplotlib_inline...`, which subprocesses inherit. **Fix:** `MPLBACKEND=Agg`.
  6. In the Wan venv, an unpinned requirement pulled `torch 2.15` (CUDA 13) over the pinned 2.5.1. **Fix:** a constraints file (`-c`) holding the torch trio and `numpy<2`.
- **Result:** ACE-Step ran. 3 candidates × 75 s, about 60 s each (it switches itself to fp16 on pre-Ampere GPUs).
- **Lesson:** never install a model's requirements into a shared interpreter. Give each model its own venv, address it explicitly, pin the torch trio together, and make every setup cell end in an import-level smoke test that fails fast.

### F-26: Wan 2.2 TI2V-5B does not fit a Kaggle T4 (memory). Shipped with Ken Burns.
- **Date:** 2026-11-25
- **Setup:** isolated venv (torch 2.5.1+cu124). `flash_attention` patched to Wan's SDPA fallback, because flash-attn can't build for sm_75. Unused modes (`speech2video`, `animate`) made optional imports.
- **What happened, in order:**
  1. **Two clips in parallel (one per T4): system RAM out of memory.** The kernel restarted. Each process holds the T5 encoder (`--t5_cpu`, about 11 GB) plus the DiT in host RAM, against about 31 GB available.
  2. **One clip: RAM out of memory again.** The DiT loads in fp32 (about 20 GB) before `--convert_model_dtype`. **Fix:** patched `WanModel.from_pretrained(..., torch_dtype=param_dtype, low_cpu_mem_usage=True)`. Measured peak RAM 22/31 GB, so this worked.
  3. **GPU out of memory at denoising step 0** (T4 = 14.6 GB), at both 50 and 20 steps. A 1280×704×121 clip is about 27k tokens. Without flash-attn, and with bf16 (which sm_75 lacks), SDPA falls back to the math kernel. That kernel builds the full attention matrix (about 35 GB). **Next idea, not confirmed:** an fp16 memory-efficient SDPA wrapper was written, but the logs don't show whether it was active in the last run. The size can't be lowered: ti2v-5B only accepts 1280×704 or 704×1280.
- **Decision:** stop. Each attempt cost about 8 minutes before failing. Even if one worked, the estimate is 30–60 min per clip on a T4, so 2–4 clips by the deadline, not 14. Also, every clip would need checking against the consent terms, because video models redraw figures and can turn heads toward the camera.
- **Workaround (by design, ARCHITECTURE.md §5):** every shot keeps its Ken Burns move. The clip contract (`shots --export/--import`) is unchanged, so clips from a bigger GPU (A100/L4, or a hosted endpoint) slot in shot by shot without touching anything else.
- **Lesson:** check the model's minimum VRAM against the free GPU *before* building the pipeline around it. The fallback-first architecture is why this failure cost minutes of film quality and not the film.
