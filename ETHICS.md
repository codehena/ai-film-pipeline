# Ethics: consent, licences, labelling

> **Gate:** if a real person appears or is voiced without a consent record here, the film scores zero. Consent is recorded **before** generating anything of them.

## Consent record
One entry per real person shown, described or voiced. The `consent_ref` of each character in `storyboard.json` points here. Contact details (phone numbers, addresses) are deliberately **not** recorded in this repository.

### narrator
- **Who:** me, the author. I tell my own childhood story.
- **Shown as:** a stylised boy (`narrator_child`), hand-painted, seen from behind or at a distance, not a portrait.
- **Voiced by:** a prebuilt male Gemini TTS voice, **Iapetus**, which I chose by ear from an audition (EXPERIMENTS.md EXP-03). It is **not** a clone of my voice or anyone else's; no recording of a real person's voice was ever sent to a model.
- **Consent:** my own; I wrote the story and approve the narration lines.

### brother
- **Who:** my brother. He grew up with me and appears in shots s04–s07.
- **Privacy framing:** the film tells our story as "my brother and I" (እኔና ወንድሜ). He is never named in the narration, subtitles, prompts, storyboard, documents or commit history. That was my choice, to keep the film about a shared childhood rather than about identifying him.
- **Shown as:** a stylised boy (`brother_child`), hand-painted, not a portrait, never a realistic likeness.
- **Voiced:** no. He is mentioned in the narration (s04, s10) but does not speak.
- **What he agreed to:** to be part of this AI-made short film about our childhood in the *geter*. He said he is "very happy to be part of the video".
- **How consent was given:** verbally, in a phone call with me, on **2026-11-25**.
- **Written confirmation:** **received 2026-11-25**, before any image of him was generated. He confirmed in a written message that he agrees to the narration lines and to being shown as a stylised boy (hand-painted, from behind or at a distance, not a portrait) in a film posted publicly with an AI label. The message itself is kept privately and is **not** committed to this repository.
- **What was never used:** no photo of him (or of me), no recording of his voice, and no name. Keyframes are generated from text descriptions only (`characters[].description` in `storyboard.json`).
- **He can withdraw:** if he asks, his shots are regenerated without him or removed, and the post is taken down.

### Other people in the film
- Friends (s07), mothers washing clothes (s03) and children at the river (s06) are **generic, unnamed and not based on real individuals**. No consent record is needed; no real person's likeness is generated.

## Private data: what leaves my machine, and what is public
Several free endpoints may use inputs for training, so the rule is: send only what the film needs.

**Sent to external APIs (Gemini, Cloudflare; later Kaggle notebooks):**
- narration text, image prompts and music captions. From draft 3 on, these contain **no names** of real people.
- the **generated** narration audio (a synthetic Gemini voice, not a recording of anyone) is sent to a Gemini text model for transcription by `asr-check`, to check the split and the pronunciation. It contains the same words as the narration text and no names.
- **Never sent:** names, surnames, the name of the village, phone numbers, photos of real people, or any recorded voice.
- **One exception, recorded honestly:** in drafts 1–2 (2026-11-25), two narration lines (s04, s10) used my brother's first name. Those lines went to Gemini TTS in the 10 narration requests logged in `runs.jsonl` before I decided not to name him. A request that has already been sent cannot be recalled, so this is recorded here rather than hidden.

**Public (the GitHub repository):**
- **History rewritten before the first push** (2026-11-25): the 20 unpushed commits on `feat/phase2-radio-pipeline` were rewritten with `git filter-branch` to remove his name from every file and every commit message. Phrases were replaced with natural equivalents ("my brother", ወንድሜ, `brother_child`).
- **Verified after the rewrite:**
  - 0 occurrences in any commit's files, messages or diffs on the branch
  - the final files are byte-identical to before the rewrite
  - each rewritten commit differs only in `storyboard.json`, `DESIGN.md` and `ETHICS.md`, with authors and dates unchanged
  - every historical storyboard still validates
- `master` never contained the name.
- **Audit caveat:** `runs.jsonl` keeps the original input hashes for the drafts 1–2 lines of s04 and s10, which were computed from the text that was really sent. The rewritten history of those two lines hashes differently, so those two log entries cannot be reproduced from history. Every other logged call can.

**Local only (git-ignored, never published):**
- `outputs/` holds the drafts 1–2 narration audio and the radio cuts `radio_35007642475a.mp4` and `radio_4e62d2e01523.mp4`, which **speak his name**. They are not for sharing with test listeners; only draft 3 and later cuts are. I can delete them once draft 3 replaces them.

## Licences
Check each one yourself and record the date you checked.

| Component | Used for | Licence / terms | Checked |
|---|---|---|---|
| Gemini API, `gemini-3.8-flash-tts` | narration | Google Gemini API terms; free tier may use inputs to improve products | TODO |
| Gemini API, `gemini-3.5-flash-lite` | smoke test only | as above | TODO |
| FLUX.1 schnell (Cloudflare Workers AI) | keyframes | Apache 2.0 (verify on model card) + Cloudflare terms | TODO |
| FLUX.2 klein **4B** (Cloudflare Workers AI) | keyframes and reference sheets | Apache 2.0 per the brief (the 9B is non-commercial; not used). Cloudflare's model page links to BFL's terms; zero data retention | TODO: confirm on the model card |
| Wan 2.2 TI2V-5B | moving shots | Apache 2.0 (per brief) | TODO |
| ACE-Step 1.5 | score | MIT; outputs usable commercially (per brief) | TODO |
| FFmpeg 9.1 (gyan.dev full build) | assembly | GPL build (includes libx264) | TODO |

## Labelling plan
- **In the film:** the end card says "Made with AI tools. A true story, shared with my brother's consent." The schema refuses an end card that doesn't mention AI.
- **When posting:** switch on the platform's AI-content disclosure (platform: TODO).
- **Provenance:** keep watermarks and provenance metadata (SynthID, C2PA) intact, and don't strip metadata in the export.
- **Style:** the look is described by its qualities (gouache, hand-painted, golden light), never by naming a living artist.
- **In class:** say aloud when presenting that the pictures, voice and music were generated with AI.
