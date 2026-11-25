# Design

<!-- Drafted on 2026-11-25 by my coding agent from my own notes. I review it and rewrite it in my own words before submitting. -->

## Story
- **Whose story:** mine and my brother's. We grew up side by side in the *geter* (ገጠር), the green Ethiopian countryside.
- **Logline:** Growing up beside my brother in the green Ethiopian countryside, in a home that always had coffee and was never empty.
- **Beats:**
  1. Waking into the *geter*: green fields, floral air, forest bees, birdsong, everyday rural life.
  2. Growing up side by side: fetching water from the spring together, then football in the open field with the cattle nearby.
  3. The river and the holidays: swimming downstream, and gathering *qetema* (ቄጠማ) and tall grass with friends before every holiday.
  4. Home: *qetema* on the floor, coffee on the fire, and the family proverb **ቡና የሌለው ቤት፣ ባዶ ነው** ("a house without coffee is empty").
  5. Belonging: our home was never empty. Our roots, my brother's and mine, are there.

## Audience and intent
- **Who watches:** my classmates and peers, and Ethiopians who grew up in rural places or long to feel rural life, especially people with that nostalgia.
- **Where they watch:** together in a classroom where everyone presents their own short video, on a shared screen (the 16:9 version), and later on their phones when I post it (the 9:16 version).
- **What they should feel at the end:** warmth, reflection and nostalgia. A viewer who grew up in the countryside should recognise their own childhood home in it.
- **How might we…** help a room of classmates, some of whom grew up in the countryside and some who did not, *feel* the warmth of a rural childhood home in under 90 seconds, through sounds, everyday tasks and one proverb everyone knows?

## Design decisions
- **Narration in Amharic, subtitles in English.** Amharic is the language of the memory and of the proverb. The English subtitles keep it open to everyone in the room.
- **Gender-neutral first person.** Amharic first-person verbs ("ያደግኩት", "እንሄድ ነበር") do not mark gender, so the narration works without naming the narrator.
- **The proverb gets its own shot (s09)**, with a slower `speech_metadata.style` and longer pauses, because it is the film's central idea.
- **The ending answers the proverb.** "A house without coffee is empty" is followed by "our home was never empty", which ties the coffee to warmth, belonging and each other.
- **Upstream / downstream as a motif.** Women wash clothes upstream (s03) and the children swim downstream (s06): the same river, two kinds of life.
- **The opening valley returns at dusk (s10)**, so the film closes where it began.
- **Stylised, not portraits.** The children are seen from behind or at a distance in a hand-painted style. This keeps the likeness respectful, reduces consistency problems and matches the consent given (see ETHICS.md).
- **Nothing that identifies the place.** No village name and no surnames, in the storyboard or in any API call.

## Shot reasons
Each shot's reason is in `storyboard.json` → `shots[].reason`. In short:

| Shot | Size | Reason |
|---|---|---|
| s01 | extreme wide | Establish the place and its peace before any people appear |
| s02 | close-up | Sensory detail (scent, bees) to pull the viewer into the memory |
| s03 | wide | Everyday village life: animals, work and the river |
| s04 | medium | Introduce my brother and the bond: a shared daily task |
| s05 | wide | Play and joy: a lighter beat after the chores |
| s06 | wide | Freedom of the river; downstream answers upstream |
| s07 | medium | Holiday tradition with friends; the qetema leads us home |
| s08 | insert | Warmth of home: qetema on the floor, the coffee ceremony |
| s09 | close-up | The family proverb, given room to land |
| s10 | extreme wide | Belonging: the opening valley at dusk |

## Prototype: the radio cut
- **What it is:** Amharic narration with English subtitles on a black screen, over a placeholder pad ducked under the voice. Built with `py -m pipeline narration`, then `py -m pipeline assemble --mode radio`.
- **File to share:** `outputs/cuts/radio_4e62d2e01523.mp4` (85 s, 1.9 MB, −14.8 LUFS).
- **Change made before testing (EXP-01):** the measured narration runs at 87 Amharic words per minute, so draft 1's shot lengths were too short for 8 of 10 lines. Draft 2 sets each `duration_s` from the measured line. The words did not change.

## User test 1: radio cut (at least 3 people from the audience)
**How:** play the radio cut once without introduction (in person, or on Slack or Telegram with headphones), then ask:
1. What did you picture? Which moment felt most like *your* home?
2. Where did your attention drift, and was any part too long? (Watch s03, a 13 s list of village sounds.)
3. Did any Amharic word sound wrong or unnatural? (Ask native speakers especially: ያንጎራጉሩ, ተጎዝጉዞ, ቄጠማ.)
4. Did the proverb land? What did the ending make you feel?
5. Was the voice right for this story? (Currently the prebuilt voice "Kore".)

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
