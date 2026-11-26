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
- **Who:** my brother. He grew up with me and appears in shots s04–s07 and s10 (always from behind or at a distance).
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
Each licence below was read at its official source on **2026-11-26** (link in the last column). Model-card claims about outputs are marked as such: they are not licence text.

| Component | Used for | Licence / terms, as stated at the source | Checked |
|---|---|---|---|
| Gemini API, `gemini-3.8-flash-tts` | narration | Gemini API Additional Terms (effective 2026-03-23). **Unpaid tier: Google may use submitted content to improve its products.** Paid tier: it doesn't. Google doesn't claim ownership of outputs; I remain responsible for their use. Hence private family details stay out of prompts, and my brother is never named. | 2026-11-26, [terms](https://ai.google.dev/gemini-api/terms) (redirects to aistudio.google.com/docs/terms) |
| Gemini API, `gemini-3.5-flash` / `flash-lite` | `asr-check` (speech recognition QA), smoke test | the same terms | 2026-11-26, same page |
| FLUX.1 schnell (Cloudflare Workers AI) | smoke test only (keyframes moved to FLUX.2 klein) | Apache 2.0; personal, scientific and commercial use | 2026-11-26, [model card](https://huggingface.co/black-forest-labs/FLUX.1-schnell) |
| FLUX.2 klein **4B** (Cloudflare Workers AI) | keyframes and reference sheets | **Apache 2.0**, open weights for commercial use (the 9B is non-commercial, not used). Acceptable-use rules apply. Cloudflare's page links to BFL's terms of service and lists zero data retention. | 2026-11-26, [model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B), [Cloudflare](https://developers.cloudflare.com/workers-ai/models/flux-2-klein-4b/) |
| Wan 2.2 TI2V-5B | moving shots: **tried, not in the film** (F-26) | Apache 2.0. The card claims no rights over generated content; the user is accountable for its use. | 2026-11-26, [model card](https://huggingface.co/Wan-AI/Wan2.2-TI2V-5B) |
| ACE-Step 1.5 | score (candidate c1) | **MIT** (code: [LICENSE](https://github.com/ACE-Step/ACE-Step-1.5/blob/main/LICENSE); weights: MIT on the card). The model card (not the licence) says generated music may be used commercially. | 2026-11-26, [model card](https://huggingface.co/ACE-Step/Ace-Step1.5) |
| FFmpeg (gyan.dev full build) | assembly | **GPLv3** (all gyan.dev builds are static, GPLv3). I only run it as a tool and don't redistribute it, so the GPL places no obligations on the film. | 2026-11-26, [builds page](https://www.gyan.dev/ffmpeg/builds/) |

## Labelling plan
- **In the film:** the end card says "Made with AI tools. A true story, shared with my brother's consent." The schema refuses an end card that doesn't mention AI.
- **Where it is shared:**
  - The two films (16:9 and 9:16) are on Google Drive, with links that open without a login, for the submission.
  - The public post is on **YouTube**. When uploading, in YouTube Studio → Details → "Altered content", answer **Yes**: the visuals, voice and music are AI-generated. YouTube then shows its AI/altered-content label on the video.
  - The description also says it plainly (the end card's wording, and that my brother consented).
- **Provenance:** keep watermarks and provenance metadata (SynthID, C2PA) intact, and don't strip metadata in the export.
- **Style:** the look is described by its qualities (gouache, hand-painted, golden light), never by naming a living artist.
- **In class:** say aloud when presenting that the pictures, voice and music were generated with AI.
