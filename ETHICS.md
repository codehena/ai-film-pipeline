# Ethics: consent, licences, labelling

> **Gate:** if a real person appears or is voiced without a consent record here, the film scores zero. Consent is recorded **before** generating anything of them.

## Consent record
One entry per real person shown, described or voiced. The `consent_ref` of each character in `storyboard.json` points here. Contact details (phone numbers, addresses) are deliberately **not** recorded in this repository.

### narrator
- **Who:** me, the author. I tell my own childhood story.
- **Shown as:** a stylised child (`narrator_child`), hand-painted, seen from behind or at a distance, not a portrait.
- **Voiced by:** a prebuilt Gemini TTS voice ("Kore"). It is **not** a clone of my voice or anyone else's.
- **Consent:** my own; I wrote the story and approve the narration lines.

### brother
- **Who:** my brother. He grew up with me and appears in shots s04–s07.
- **Shown as:** a stylised child (`brother_child`), hand-painted, not a portrait, never a realistic likeness.
- **Voiced:** no. He is named in the narration (s04, s10) but does not speak.
- **What he agreed to:** to be part of this AI-made short film about our childhood in the *geter*. He said he is "very happy to be part of the video".
- **How consent was given:** verbally, in a phone call with me.
- **Date of the call:** TODO (fill in)
- **To strengthen the record (recommended before keyframes):** send him the final narration lines with their English translation, and a description of how he will be shown (a stylised child, not a portrait, posted publicly with an AI label). Ask him to reply "I agree" in a text or voice message, and record the date and medium here. Keep the message itself privately; do not commit it.
- **He can withdraw:** if he asks, his shots are regenerated without him or removed, and the post is taken down.

### Other people in the film
- Friends (s07), women washing clothes (s03) and children at the river (s06) are **generic, unnamed and not based on real individuals**. No consent record is needed; no real person's likeness is generated.

## Private data kept out of free APIs
Several free endpoints may use inputs for training, so:
- **Sent:** narration text (which includes my brother's first name), image prompts and music captions.
- **Never sent:** surnames, the name of the village, phone numbers, photos of real people, or any recorded voice.

## Licences
Check each one yourself and record the date you checked.

| Component | Used for | Licence / terms | Checked |
|---|---|---|---|
| Gemini API, `gemini-3.8-flash-tts` | narration | Google Gemini API terms; free tier may use inputs to improve products | TODO |
| Gemini API, `gemini-3.5-flash-lite` | smoke test only | as above | TODO |
| FLUX.1 schnell (Cloudflare Workers AI) | keyframes | Apache 2.0 (verify on model card) + Cloudflare terms | TODO |
| FLUX.2 klein 4B / 9B | keyframes (candidate) | 4B Apache 2.0, 9B non-commercial (per brief) | TODO |
| Wan 2.2 TI2V-5B | moving shots | Apache 2.0 (per brief) | TODO |
| ACE-Step 1.5 | score | MIT; outputs usable commercially (per brief) | TODO |
| FFmpeg 9.1 (gyan.dev full build) | assembly | GPL build (includes libx264) | TODO |

## Labelling plan
- **In the film:** the end card says "Made with AI tools. A true story, shared with my brother's consent." The schema refuses an end card that doesn't mention AI.
- **When posting:** switch on the platform's AI-content disclosure (platform: TODO).
- **Provenance:** keep watermarks and provenance metadata (SynthID, C2PA) intact, and don't strip metadata in the export.
- **Style:** the look is described by its qualities (gouache, hand-painted, golden light), never by naming a living artist.
- **In class:** say aloud when presenting that the pictures, voice and music were generated with AI.
