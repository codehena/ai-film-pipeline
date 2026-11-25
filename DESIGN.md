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

## User test 1: radio cut (at least 3 people from the audience)
**How:** play the draft 3 radio cut once without introduction (in person, or on Slack or Telegram with headphones), then ask:
1. What did you picture? Which moment felt most like *your* home?
2. Where did your attention drift, and was any part too long?
3. Did any Amharic word sound wrong or unnatural? (Ask native speakers especially: ሲያንጎራጉሩ, ሲጎዘጎዝ, ቄጠማ, እንደሚባለው.)
4. Did the proverb land? What did the ending make you feel?
5. Was the voice right for this story? Did it feel like one person telling one story?

| Who (relation, not full name) | Grew up rural? | Date | What they said | Where they reacted |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

**Insights, and what I will change in the storyboard because of them:**
- TODO (link each change to the commit that made it)

## User test 2: near-final cut (at least 3 people)
| Who | Date | What they said | Where they reacted |
|---|---|---|---|
| | | | |

**What changed because of it:**
- TODO
