# Report: ገጠር – Geter (Heritage Short)

<!-- Drafted on 2026-11-26 by my coding agent from the evidence in this repository. I rewrite it in my own words before submitting; the AI interview checks that it is mine. -->

**Repository:** https://github.com/codehena/ai-film-pipeline (`master`). One command runs the pipeline end to end: `py -m pipeline film` (README).

## 1. What I set out to make, and for whom
A 70-second film about growing up side by side with my brother in the green Ethiopian countryside, narrated in Amharic with English subtitles, in 16:9 and 9:16.
- **Audience:** my classmates (a shared screen in class), and Ethiopians who grew up rural or miss that life (phones, when I post it). DESIGN.md, "Audience and intent".
- **Intent:** the viewer should feel warmth, reflection and nostalgia. Someone who grew up in the *geter* should recognise their own childhood home.
- **Constraint I set myself:** my brother is shown stylised, from behind or at a distance, with no clear faces, and he is never named. His consent is recorded in ETHICS.md.

## 2. What I learned from my audience
**User test 1** (radio cut, 3 listeners, DESIGN.md) changed the *words*:
- My best friend gave a richer sensory opening (bees, birds, calves, chickens). It became s02, and later the word-timed beats.
- My brother said there were too many ነበር endings. I cut them from 8 to 4 and chained clauses across shots. He also asked to say that a rural childhood is loved and never forgotten; that became the s10 close.
- My female friend said the flow broke near the end, and her line became s08.

**User test 2** (near-final cut, same 3 people, DESIGN.md):
- The pictures and the score now carry the story: "music and visuals fit the story well", "no issues on the visuals". Football (s05) was the most nostalgic moment for my brother.
- All three pointed at the **pronunciation** of the narration: two explicitly, one called the sound "somehow bearable". This is the one thing I'm still acting on: a reproducible pronunciation pass through `storyboard.json`, after the TTS quota resets.
- One listener wanted real motion. I didn't act on that, and section 3 explains why.
- **Caveat:** my brother is in the story and all three had heard the radio cut, so a fresh viewer would be a stronger test.

## 3. The hardest problem, and how I solved it
**Clear Amharic narration on a free tier of 10 TTS requests a day.**
- **Per-line reads hit the limits.** Reading each line separately hit the 3-per-minute and 10-per-day caps (F-08, F-09). It also made the voice drift between lines.
- **A continuous read fixed the budget and the voice.** I switched to one continuous read of the whole story (EXP-02): 1 request instead of 10, and one consistent voice.
- **The continuous read had to be cut into shots.** Splitting it by silence put words in the wrong shots (F-12). I fixed the split with a reviewed corrections file (`narration_splits.json`) and checked it with a speech recogniser (`asr-check`, EXP-05).
- **The pauses had to sound natural.** The cut now follows the read's own spacing instead of forcing pauses (Option A, EXP-06).
- **The audience result:** the narration is now one voice and on time. Test 2 shows pronunciation is the remaining gap, so that's what I'm fixing now.

**A second hard problem: real motion.**
- I prepared Kaggle notebooks for Wan 2.2 TI2V-5B on the free T4.
- I fixed six environment failures along the way (F-25).
- I cut peak RAM from over 31 GB to 22 GB by loading the model in bf16.
- The model still ran out of GPU memory at the first denoising step (F-26, EXP-12).
- I stopped after about 33 GPU-minutes. Each attempt cost 8 minutes, and even a working run would have given 2–4 clips by the deadline, not 14.
- The pipeline was designed so a missing clip falls back to a Ken Burns move (ARCHITECTURE.md §5). So the film stayed complete, and clips from a bigger GPU can still slot in through the same contract.

## 4. Suggested practices, tested honestly
**One that beat my instinct: make the radio cut first and test it with real people before generating pictures.**
- My instinct was to start with images.
- Testing the sound-only cut first meant that test 1 changed the *script* (s02, s08, s10, ነበር 8 → 4) while changes were still cheap: 0 images to throw away.
- The pictures were then written for the final words, and test 2's verdict on the visuals was positive. (DESIGN.md test 1 table, storyboard notes for draft 4.)

**One that did not hold for my models: "a fixed seed gives reproducible, controllable images."**
- FLUX.2 klein on Cloudflare ignored the seed: the same prompt and seed gave different images (EXP-07).
- I treated the seed as a *take number* instead, and made the input-hash cache the source of determinism. An unchanged shot is never regenerated, so it can't drift.
- Reference sheets also behaved differently from what I expected. They locked identity, but they also locked clothes, so shots needing different clothes had to drop them (F-21).

## 5. Curiosity beyond the floor
- **A memory benchmark of Wan 2.2 TI2V-5B on a free Kaggle T4** (EXP-12): where it fails (RAM, then the GPU at step 0), why (fp32 loading; attention at about 27k tokens without flash-attn), and the patches that move the limit. This is useful to anyone else on the free tier.
- **Tools others can use:**
  - `py -m pipeline framing` draws head-safe boxes and both crops on every keyframe before rendering (EXP-10).
  - `scripts/score_previews.py` renders each score candidate under the real narration (EXP-13).
  - `asr-check` uses a speech recogniser to check an Amharic split (EXP-05).
- **Word-timed visual beats:** pictures land 0.15 s before the word they show, timed from the cached narration with no extra model call (EXP-09).
- **Cultural accuracy as an experiment:** describing a jebena's *shape* rather than naming it was what made the model draw a real one (EXP-11).

## 6. What I would build next
- The pronunciation pass, as a pipeline feature: a per-word pronunciation map in the storyboard, applied before TTS and checked by `asr-check`.
- Wan 2.2 on a ≥ 24 GB GPU for the 4–6 shots where motion matters most (s01 mist, s05 football, s06 river). Each clip would be reviewed against the consent terms, because video models can turn heads toward the camera.
- A third user test with viewers who haven't heard earlier cuts.

## Numbers (COSTS.md, runs.jsonl)
- **TTS:** 2 of 10 daily requests for the two continuous reads that shaped the film.
- **Images:** 43+ FLUX.2 klein images, 0 errors, about 17 s median.
- **Music:** ACE-Step, 3 × 75 s candidates, about 60 s each on a T4 (about 4.5 GPU-minutes).
- **Wan:** 0 clips, about 33 GPU-minutes spent.
- **Final re-render after choosing the score:** 139 s, 0 model calls.
