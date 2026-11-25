# Design

<!-- Drafted on 2026-11-25 by my coding agent from my own notes. I review it and rewrite it in my own words before submitting. -->

## Story
- **Whose story:** mine and my brother's. We grew up side by side in the *geter* (ገጠር), the green Ethiopian countryside. In the film he is simply "my brother" (ወንድሜ); his name is not used.
- **Logline:** Growing up side by side with my brother in the green Ethiopian countryside, in a home that always had coffee and was never empty.
- **Shape:** one day in the *geter* that grows into a whole childhood: morning, then the day's tasks and play, then the river, then a holiday, then evening coffee, then home.
  1. Waking into the *geter*: birdsong, the scent of flowers, forest bees, the village waking up.
  2. The village at work: cattle going out to pasture, mothers washing clothes upstream.
  3. My brother and I, side by side: fetching water from the spring, then football in the field while the cattle watch.
  4. The river: swimming downstream when the day grows hot.
  5. The holiday: gathering *qetema* (ቄጠማ) and tall grass with friends, the *qetema* spread through the house, the coffee brewing.
  6. The proverb: **ቡና የሌለው ቤት፣ ባዶ ነው** ("a house without coffee is empty").
  7. Belonging: our home was never empty. My brother's roots and mine are still there, in the *geter*.

## Audience and intent
- **Who watches:** my classmates and peers, and Ethiopians who grew up in rural places or long to feel rural life, especially people with that nostalgia.
- **Where they watch:** together in a classroom where everyone presents their own short video, on a shared screen (the 16:9 version), and later on their phones when I post it (the 9:16 version).
- **What they should feel at the end:** warmth, reflection and nostalgia. A viewer who grew up in the countryside should recognise their own childhood home in it.
- **How might we…** help a room of classmates, some of whom grew up in the countryside and some who did not, *feel* the warmth of a rural childhood home in under 90 seconds, through sounds, everyday tasks and one proverb everyone knows?

## Design decisions
- **Narration in Amharic, subtitles in English.** Amharic is the language of the memory and of the proverb. The English subtitles keep it open to everyone in the room.
- **A man's voice, one delivery throughout.** I am the narrator, so the voice is male. Every line uses the delivery I liked in the first draft's opening: "soft and slow, like waking up".
- **One flowing story, not a list.** Lines hand on to each other ("As the bees hummed… the village woke", "With the water home, we played…", "When a holiday drew near… and as the qetema was spread…"), and the whole narration is read in one continuous take (EXP-02).
- **The proverb gets its own shot (s09)**, introduced with "as they say" and given longer pauses, because it is the film's central idea.
- **The ending answers the proverb.** "A house without coffee is empty" is followed by "our home was never empty". The last word, ገጠር, is the word the film opens with.
- **Upstream / downstream as a motif.** Mothers wash clothes upstream (s03) and the boys swim downstream (s06): the same river, two kinds of life.
- **The opening valley returns at dusk (s10)**, so the film closes where it began.
- **Stylised, not portraits.** The boys are seen from behind or at a distance in a hand-painted style. This keeps the likeness respectful, reduces consistency problems and matches the consent given (see ETHICS.md).
- **Nothing that identifies the family or the place.** No names, no village name and no surnames in the narration, the storyboard or the prompts.

## Shot reasons
Each shot's reason is in `storyboard.json` → `shots[].reason`. In short:

| Shot | Size | Reason |
|---|---|---|
| s01 | extreme wide | Establish the place and its peace before any people appear |
| s02 | close-up | Bees on blossoms carry us from waking into the village waking |
| s03 | wide | Everyday village life: animals, work and the river |
| s04 | medium | Introduce my brother and the bond: a shared daily task |
| s05 | wide | Play and joy: a lighter beat after the chores |
| s06 | wide | Freedom of the river; downstream answers upstream |
| s07 | medium | Holiday tradition with friends; the qetema leads us home |
| s08 | insert | Warmth of home: qetema on the floor, the coffee ceremony |
| s09 | close-up | The family proverb, given room to land |
| s10 | extreme wide | Belonging: the opening valley at dusk |

## Prototype: the radio cut
- **What it is:** Amharic narration with English subtitles on a black screen, over a placeholder pad ducked under the voice. Built with `py -m pipeline narration`, then `retime`, then `assemble --mode radio`.
- **Draft 2** (`outputs/cuts/radio_4e62d2e01523.mp4`, 85 s, local only and **not for sharing**: drafts 1–2 speak my brother's name): the measured narration runs at 87 Amharic words per minute, so draft 1's shot lengths were too short for 8 of 10 lines. Draft 2 set each `duration_s` from the measured line (EXP-01).

### My own review of draft 2, and what changed (draft 3)
| What I noticed | Change in draft 3 |
|---|---|
| I'd rather not name my brother; "my brother and I" is enough | name removed from narration and subtitles (`brother_child`) |
| It felt like separate sentences; I want a flowing story | rewritten as one day; lines joined by connectives |
| The opening voice was great ("cool"); later lines changed | one style for every line (the opening's), one continuous read (EXP-02) |
| I am a man and want a man's voice | male voice audition (EXP-03); I chose **Iapetus** |

- **Draft 3 radio cut, the one to share with listeners:** `outputs/cuts/radio_e4cfcbb9f085.mp4`
  - 65.5 s; Iapetus, read in one continuous take
  - English subtitles on black; −14.0 LUFS
  - every line fits its shot (timing report `radio_e4cfcbb9f085.timing.md`)
  - the earlier draft 3 render `radio_633140d7a506.mp4` is the same audio but too quiet (−15.9 LUFS, F-11), so don't share it

### My review of draft 3, and what changed (draft 4)
After hearing my three listeners (user test 1 below), I agreed with all three notes. The pieces I liked about draft 3 (the single Iapetus voice, the day-in-the-life shape, the proverb) stay. What changed is the wording: more of the senses up front, less ነበር, and an ending that says *why* this childhood matters. TODO: anything else I noticed myself, in my own words.

- **Draft 4 radio cut, the one to share for the follow-up check:** `outputs/cuts/radio_71461dcbe940.mp4`
  - 71.0 s; one continuous Iapetus read
  - −14.0 LUFS (independent meter −13.9), true peak −1.2 dB
  - 15 subtitle cues, at most 2 lines of ≤ 43 characters
  - every line fits its shot
- **Do not share** `radio_6d34f88ae0ed.mp4` (its loudness pass fell back to dynamic, F-13) or `radio_9346ef6a1f30.mp4` (75-character subtitle lines, F-14).
- **Words to listen for** (the recogniser misheard these in the ASR check, EXP-05; that may be the recogniser, not the voice):
  - ጥጃዎች ሲዘሉ (s02)
  - the whole s04 line
  - ቀኑ ሲሞቅ … እንዋኝ (s06)
  - ቄጠማው ሲጎዘጎዝ፣ ቡናው ሲፈላ (s08)
  - the first syllable of እንደሚባለው (s09)

## User test 1: radio cut (at least 3 people from the audience)
**How:** play the radio cut once without introduction (in person, or on Slack or Telegram with headphones), then ask:
1. What did you picture? Which moment felt most like *your* home?
2. Where did your attention drift, and was any part too long?
3. Did any Amharic word sound wrong or unnatural? (Ask native speakers especially: ሲያንዣብቡ, ሲጎዘጎዝ, ቄጠማ, እንደሚባለው.)
4. Did the proverb land? What did the ending make you feel?
5. Was the voice right for this story? Did it feel like one person telling one story?

Tested on the draft 3 radio cut (`radio_e4cfcbb9f085.mp4`), 2026-11-25.

| Who (relation, not full name) | Grew up rural? | Date | What they said | Where they reacted |
|---|---|---|---|---|
| Best friend | TODO | 2026-11-25 | Liked the cut overall. Suggested a richer sensory opening than the bees "humming" (ሲያንጎራጉሩ): *ንቦች አበቦች ላይ ሲያንዣብቡ እና ወፎች ሲዘምሩ፣ ጥጃዎች ሲዘሉ፣ ዶሮዎች ሲሯሯጡ ማየት ለየት ያለ ስሜት አለው፤ አንዳንዴም ይናፍቀኛል።* | the opening (s01–s02) |
| My brother (co-subject of the story) | yes (we grew up together) | 2026-11-25 | It took him back to those times. There are more ነበር endings than needed. Add the feeling that growing up in the countryside is one of the things you love about life, and that people who grew up there know the feeling and never forget it. | the whole narration; the ending |
| Female friend | TODO | 2026-11-25 | Works well overall, but the flow breaks near the end. Suggested smoothing it with: *ቄጠማው ሲጎዘጎዝ፣ ቡናው ሲፈላ፣ እና ሰዉ ተውቦ ስናይ ደስ ይል ነበር። እነዚህ ነገሮች ልጅነቴን በገጠር ማሳለፌን እንድወደው አድርገውኛል እናም ሁሌም ከትውስታዬ ዉስጥ አይጠፉም።* | the end (s08–s10) |

- **Caveat:** my brother is in the story, so his reaction is not neutral. It is still valuable as a check that the memory rings true. TODO: fill in "Grew up rural?" for the two friends.

**Insights, and what changed in the storyboard (draft 4) because of them:**

| Insight | Who | Change in draft 4 |
|---|---|---|
| The opening can carry more of the senses of rural life | best friend | s02 is now the friend's line almost word for word: bees hovering, birds singing, calves leaping, chickens running, *"sometimes I miss it"*. s01 is shortened to make room. The s03 image prompt gains a leaping calf and running chickens. |
| Too many ነበር endings make it sound like a list | brother | ነበር cut from 8 to 4. Clauses now chain across shots (s03 → s04, s05 → s06), and ነበር is kept only where a beat closes. |
| Say that a rural childhood is loved and never forgotten | brother | s10: *"These things made me love growing up in the countryside; whoever grew up there knows this feeling and never forgets it."* |
| The flow breaks near the end | female friend | s08 is now her first line (qetema spread, coffee brewing, people dressed up: *"it was a joy"*). Her second line, merged with my brother's idea, closes s10. The s08 image prompt gains people in white holiday clothes. |

- Draft 4: 107 words, 4 ነበር (was 8), one continuous read, film **71 s** (was 65.5 s).

### My own listen to draft 4 (2026-11-25, `radio_71461dcbe940.mp4`)
- **Good:** the audio quality and mix are clean, and the subtitles are readable.
- **Not yet right:** the delivery feels **less natural than the earlier take** (draft 3, `radio_e4cfcbb9f085.mp4`, same Iapetus voice and style).

**Measured** (no model calls). Two pause detectors are used, so each number names its method:
- *my silencedetect*: FFmpeg `silencedetect=noise=-35dB:d=0.35` on the raw reads. I ran this; the agent reproduced the same numbers.
- *pipeline detector*: `common/silence.py`, below −40 dBFS for at least 0.25 s.

| | Draft 3 read `full_62660579a53d.wav` (felt natural) | Draft 4 read `full_64173211a953.wav` (felt stiffer) |
|---|---|---|
| Length / words | 64.68 s / 94 | 64.87 s / 107 |
| Pauses, my silencedetect | 24 pauses, 0.44–2.12 s, **22.4 s in total** | 21 pauses, 0.42–1.25 s, **17.4 s in total** |
| Longest pauses, my silencedetect | 40.07–42.19 (2.12), 22.17–23.81 (1.64) | 36.08–37.33 (1.25), 48.79–50.00 (1.21); 17.54–19.02 is one pause split in two by a blip (0.77 + 0.71) |
| Speaking rate, pipeline detector | 141 wpm | 141 wpm |
| Pauses *inside* lines, pipeline detector | 18, mean 0.63 s | 17, mean 0.65 s |
| Gaps *between* lines in the read | 1.0–2.2 s | 0.7–1.3 s |

- **Reading:** pause *counts* don't explain it. The voice speaks at the same rate with the same pauses inside lines. But the draft 4 read fits 13 more words into the same length, so it has **about 5 s less silence**, almost all of it *between* lines. It breathes less. The rest is most likely **intonation**, which pause measurements can't see:
  1. **Lines that end mid-sentence.** s03 and s05 end on "፣" and continue in the next line. The read is sent as one paragraph per shot, with an instruction to pause about two seconds between paragraphs, so the voice may close each of those half-sentences as if the thought were finished.
  2. **List-shaped lines.** s02 has four parallel ሲ- clauses and s08 has three, which invites a "list" melody.
  3. **Take-to-take variation.** Every TTS read is a new performance, even with identical settings.

**Where the cut changes the read's spacing** (`assemble` placed each line from the timeline; the read's own spacing is on the left):

| Shot | Raw read (s) | Cut (s) | Gap before: read → cut | Change |
|---|---|---|---|---|
| s01 | 0.00–5.48 | 1.00–6.48 | 0.00 → 1.00 | +1.00 (lead-in, `pause_before`) |
| s02 | 6.36–17.64 | 7.20–18.48 | 0.88 → 0.72 | −0.16 |
| s03 | 18.92–23.26 | 19.30–23.64 | 1.28 → 0.82 | **−0.46** (the breath after "አንዳንዴም ይናፍቀኛል" is shortened) |
| s04 | 23.98–27.54 | 24.20–27.76 | 0.72 → 0.56 | −0.16 |
| s05 | 28.40–32.10 | 28.70–32.40 | 0.86 → 0.94 | +0.08 |
| s06 | 32.84–36.18 | 33.20–36.54 | 0.74 → 0.80 | +0.06 |
| s07 | 37.22–42.50 | 37.80–43.08 | 1.04 → 1.26 | +0.22 |
| s08 | 43.36–48.90 | 43.70–49.24 | 0.86 → 0.62 | −0.24 |
| s09 (proverb) | 49.90–52.88 | 50.60–53.58 | 1.00 → 1.36 | **+0.36** |
| s10 | 53.70–64.64 | 55.40–66.34 | 0.82 → 1.82 | **+1.00** (after the proverb) |
| tail | 0.23 s after s10 | 1.66 s after s10, then 3 s end card | | +1.43 and +3.00 |

- **The read runs 64.87 s and the cut 71.00 s, +6.13 s.** That breaks down as:
  - 3.00 s end card
  - 1.00 s lead-in
  - 1.43 s tail
  - **0.70 s net between lines**: 1.72 s added (most of it around the proverb) and 1.02 s removed
- **Every gap includes rounding slack** (before Option A). `retime` rounded each shot up to the next 0.5 s, which added 0–0.5 s of arbitrary silence per line.
- **Decision:** I chose **Option A**: fix the spacing in the edit, with 0 TTS calls. It fixes everything measurable at no quota cost and leaves time for the picture and music stages before the deadline. Option B (one targeted re-read, grouping the half-sentences and lightening the lists) is kept in reserve in case the delivery still feels stiff.

### Option A: the cut follows the read's own spacing (draft 4b, `radio_4fa2a5146bca.mp4`)
- **What changed:**
  - `retime` rounds up to **0.1 s** instead of 0.5 s.
  - Each line's `pause_before` / `pause_after` is set so that `pause_after` of one line plus `pause_before` of the next ≈ the gap the voice actually left in the read.
  - Lead-in (1.0 s) and the closing beat before the end card (1.5 s) are kept as design choices.
  - Same read, same words, 0 model calls.
- **Result:** 70.3 s (was 71.0); −14.0 LUFS, true peak −1.27 dBTP (EBU R128 meter −13.9 / −1.3); 15 subtitle cues, rows ≤ 43 characters.

| Boundary | Read gap | Old cut (`radio_71461dcbe940`) | New cut (`radio_4fa2a5146bca`) |
|---|---|---|---|
| s01→s02 | 0.88 | 0.72 | 0.87 |
| s02→s03 (after ይናፍቀኛል) | 1.28 | 0.82 | **1.27** |
| s03→s04 | 0.72 | 0.56 | 0.71 |
| s04→s05 | 0.86 | 0.94 | 0.94 |
| s05→s06 | 0.74 | 0.80 | 0.70 |
| s06→s07 | 1.04 | 1.26 | 1.06 |
| s07→s08 | 0.86 | 0.62 | 0.92 |
| s08→s09 (before the proverb) | 1.00 | 1.36 | **1.01** |
| s09→s10 (after the proverb) | 0.82 | 1.82 | **0.82** |

- **Blind check:** `radio_71461dcbe940.mp4` vs `radio_4fa2a5146bca.mp4`, played in random order, without saying which is new. Which flows more naturally?

| Listener (relation) | Date | Preferred | Why, in their words |
|---|---|---|---|
| me | | | |
| | | | |

- TODO: my verdict. If the new cut still feels stiff, it is intonation inside the lines, and Option B is next (after 11:00 EAT, when `asr-check` can verify a new split).

### Follow-up check on draft 4 (same 5 questions, blind, headphones)
Play `outputs/cuts/radio_71461dcbe940.mp4` without introduction and record answers in each person's own words.

| Who (relation) | Grew up rural? | Date | What they said | Where they reacted |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

### Shipping decision for the narration (2026-11-25)
- **Ship draft 4b (Option A) as the narration** (`radio_4fa2a5146bca.mp4` audio). It's good, though I'd still like the reading to sound a little more natural. Option B (one targeted re-read: grouping the half-sentences in s03/s05, lightening the s02/s08 lists) stays documented as the next step if time allows.
- **Why not wait for Option B:**
  - It needs a TTS call *and* an `asr-check` to verify the new split, and both quotas reset only at 11:00 EAT on the deadline day.
  - The pictures, motion and music don't depend on the narration (ARCHITECTURE.md, "Why it is shaped this way"), so they can be built now.
  - A later re-read would only re-render the final cut.

## Pictures: decisions (2026-11-25)
- **Two boys, told apart by colour:** green shirt, khaki shorts, sandals; red shirt, blue shorts, barefoot. Both are stylised, seen from behind or at a distance. A reference sheet for each conditions every shot they appear in (EXP-07).
- **Cultural accuracy over first takes:**
  - s08 was redrawn: a jebena on a charcoal brazier, small sini cups, qetema on the floor, women in white netela seen from behind. The first take read as a cauldron ritual.
  - s09 became a push-in on that same jebena after three failed cup takes (F-16).
- **Movement:** every shot is a slow Ken Burns move that follows its motion prompt (push-in, pull-back, pan, near-still), so neighbouring shots move differently. Wan 2.2 clips replace them shot by shot when the Kaggle runs come back.
- **Baseline film, watchable now:**
  - `outputs/cuts/final-16x9_79e1e669fdc0.mp4` (class screen)
  - `outputs/cuts/final-9x16_73291dad58e1.mp4` (phones)

  Both are 70.3 s, Option A narration, placeholder pad until a score is chosen, end card centred.

## User test 2: near-final cut (at least 3 people)
| Who | Date | What they said | Where they reacted |
|---|---|---|---|
| | | | |

**What changed because of it:**
- TODO
