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
- **What was measured** (no new model calls; numbers from the two continuous reads and the two cuts):

| | Draft 3 (felt natural) | Draft 4 (felt stiffer) |
|---|---|---|
| Speaking rate | 141 wpm | 141 wpm |
| Pauses inside lines | 18, mean 0.63 s, longest 1.22 s | 17, mean 0.65 s, longest 1.20 s |
| Gaps between lines in the read | 1.0–2.2 s | 0.7–1.3 s |
| Gaps between lines in the cut | 0.5–1.6 s | 0.6–1.8 s |
| Biggest change the edit makes to a gap | −1.54 s (s01→s02) | **+1.00 s after the proverb** (s09→s10: 0.82 → 1.82 s) |

- **Reading:** pace and pausing are the same, so the difference is most likely **intonation** (the melody of the voice), which these numbers can't see. Three suspects, all from draft 4's changes:
  1. **Lines that end mid-sentence.** s03 and s05 end on "፣" and continue in the next line. The read is sent as one paragraph per shot, with an instruction to pause about two seconds between paragraphs, so the voice may close each of those half-sentences as if the thought were finished.
  2. **List-shaped lines.** s02 has four parallel ሲ- clauses and s08 has three, which invites a "list" melody.
  3. **Take-to-take variation.** Every TTS read is a new performance, even with identical settings.
- The cut also adds a full second of silence after the proverb, which may make the ending feel stretched.
- **Next, before spending any TTS quota:** listen to the raw continuous reads (`outputs/narration/full_64173211a953.wav` for draft 4, `full_62660579a53d.wav` for draft 3).
  - If the raw draft 4 read sounds natural, the stiffness comes from the edit (re-spacing), which is free to fix.
  - If it already sounds stiff, the cause is the text or the take, and a targeted re-read is the fix.
- TODO: my verdict after that listen.

### Follow-up check on draft 4 (same 5 questions, blind, headphones)
Play `outputs/cuts/radio_71461dcbe940.mp4` without introduction and record answers in each person's own words.

| Who (relation) | Grew up rural? | Date | What they said | Where they reacted |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## User test 2: near-final cut (at least 3 people)
| Who | Date | What they said | Where they reacted |
|---|---|---|---|
| | | | |

**What changed because of it:**
- TODO
