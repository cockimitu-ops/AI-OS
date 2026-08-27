# Retention Engineering — Notion Template Structure

Build as one Notion page with 6 sub-pages. Paste the content in; Notion
converts Markdown to blocks automatically.

---

## Cover Page

**Retention Engineering**
A production system for narrative short-form video.

> Duplicate this template. Work modules 1–6 in order. You'll finish with a
> retention-mapped script, overlay text, sound cues, and editor settings —
> ready to produce.

**What this is for:** story-driven short-form video, 105–125 seconds, where
someone stays because they need to know how it ends. Not talking-head, not
tutorials, not trend-chasing.

**The trade this system makes, stated up front:** TikTok's average video
runs 42.7 seconds. This system targets 105–125. You give up the easy
completion rate a 15-second clip gets, and buy total watch time and series
retention instead. It only works if the retention architecture holds — which
is what Modules 3 and 6 exist to enforce.

Progress: ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 ☐ 6

---

## Module 1 — Source Mining

**Purpose:** Most short-form fails before a word is written, because the
premise had no pull. Filter first.

| Premise (1 sentence) | First reversal lands at | What they don't see coming | Stop-reading difficulty |
|---|---|---|---|
| | | | |

**Prompt:**
```
I make narrative short-form video in this niche: [describe it].

Find 10 story premises from public sources (forums, news archives,
community posts, historical records) that fit ALL of these:
- A clear inciting incident within the first few sentences
- At least two reversals or revelations before the ending
- An outcome that isn't obvious from the setup
- No named private individuals

For each, give me: the premise in one sentence, where the first
reversal lands, and what the reader doesn't see coming.

Rank them by how hard it would be to stop reading halfway.
```

**The ranking criterion is the filter.** A story you'd abandon halfway in
text will lose viewers halfway in video. No editing rescues a dead premise.

**On sourcing:** stick to public posts and avoid identifying real private
individuals. Change identifying details. This is both an ethical line and a
practical one — platforms remove content that exposes people.

---

## Module 2 — Hook Engineering

**Purpose:** The first three seconds decide whether the other 120 exist.

**Hook hierarchy — strongest first:**
1. Immediate danger
2. Impossible situation
3. Disturbing mystery
4. High stakes
5. Betrayal
6. Curiosity gap
7. Emotional conflict

| Hook line (max 12 words) | Tier | Keep? |
|---|---|---|
| | | |

**Prompt:**
```
Story premise: [paste from Module 1].

Write 8 opening lines, each under 12 words, spoken aloud as the
first thing the viewer hears.

Use this hierarchy, strongest first:
1. Immediate danger  2. Impossible situation  3. Disturbing mystery
4. High stakes  5. Betrayal  6. Curiosity gap  7. Emotional conflict

Label which tier each line uses. At least three must come from
tiers 1-3.

Reject anything that: asks a rhetorical question, starts with
"So", "Imagine", or "This is the story of", or explains context
before the hook lands.
```

**Enforce the rejection list.** Those four patterns are exactly what a
language model defaults to, and exactly what loses viewers. Regenerate rather
than accept.

---

## Module 3 — Retention Architecture

**Purpose:** Plan where information lands *before* writing. This is the
module that makes the format work at 110 seconds.

**Beat map:**

| Timestamp | Beat | New information delivered |
|---|---|---|
| 0:00–0:03 | Hook | |
| 0:15–0:20 | First reveal | |
| ~0:30 | | |
| ~0:45 | | |
| ~1:00 | | |
| ~1:15 | | |
| ~1:30 | | |
| 1:45–1:50 | Resolution or cliffhanger | |

**Prompt:**
```
Story: [premise]. Hook: [chosen hook].

Build a retention map for a 110-second video. Mark:
- Second 0-3: the hook
- Second 15-20: first reveal (something the viewer didn't know
  when the video started)
- Then a new reveal, twist, or escalation every 10-15 seconds
- The final 5 seconds: either resolution or cliffhanger

For each beat, write one line describing what NEW information the
viewer receives. If a beat contains no new information, cut it and
redistribute the time.

Flag any stretch longer than 15 seconds without a beat.
```

**Use the flags.** Those timestamps are where your retention graph will show
a cliff. Fix them here, not after publishing.

---

## Module 4 — TTS-Native Scripting

**Purpose:** Text-to-speech reads differently than a person. Writing for the
page and hoping the engine copes is the most common production mistake.

**Rules:**
- Spell numbers as words (twenty three, not 23)
- Break any sentence over 15 words into two
- No emojis, asterisks, parentheses, em dashes
- No abbreviations the engine would mispronounce
- Commas only where you want an audible pause
- Spoken words only — no stage directions, no headers

**Target: 240–290 words = 105–125 seconds** at standard TTS pace.

**Prompt:**
```
Retention map: [paste Module 3 output].

Write the full spoken script, 240-290 words, following these rules
exactly:

- Spell out all numbers as words (twenty three, not 23)
- Short sentences. Break any sentence over 15 words into two.
- No emojis, no asterisks, no parentheses, no em dashes
- No abbreviations the voice engine would mispronounce
- Commas only where you want an audible pause
- Nothing that isn't spoken aloud -- no stage directions, no
  headers, no speaker labels

Output only the script text, nothing else.
```

**Read it aloud yourself before generating audio.** Anything that makes you
stumble makes the engine stumble, and re-rendering costs more than a
proofread.

---

## Module 5 — Visual and Audio Layer

**Purpose:** The visual track occupies the eye without competing for the ear.
Get the balance wrong and retention drops even with a strong story.

| Timestamp | Overlay text (3–6 words) | Visual | SFX |
|---|---|---|---|
| | | | |

**Prompt:**
```
Script: [paste Module 4 script].
Retention map: [paste Module 3 beats].

Produce:
1. Overlay text for each beat — 3-6 words maximum, appearing at
   the moment the beat lands, never a transcript of the narration
2. Background footage direction: what kind of visual motion, and
   what to avoid so it doesn't pull attention from the audio
3. Sound effect cues tied to specific beats, with timestamps
4. The two or three moments where the visual should change
   sharply, to reset attention

Rule: overlay text must never duplicate what is being said at that
same moment. It either emphasises or adds.
```

**Why the no-duplication rule matters:** on-screen text repeating the
narration gives the viewer permission to mute. A muted viewer is one swipe
from gone.

**Editor settings block:**
- Voice: ______
- TTS speed: ______
- Export speed: ______
- Background footage: ______

---

## Module 6 — Multi-Part and Cliffhangers

**Purpose:** Splitting multiplies total watch time — but only if the break
lands where walking away is uncomfortable. A bad split loses everyone at
part two.

**Prompt:**
```
Full story: [paste premise and script].

If this story is strong enough to split across 2-3 parts:
1. Identify the split point — the moment where stopping is
   genuinely uncomfortable
2. Write the closing 10 seconds of each non-final part, ending on
   the unresolved beat
3. Write the opening 10 seconds of each subsequent part, which
   must re-hook someone who did NOT see the previous part
4. Confirm each part still holds 240-290 words

If the story is not strong enough to split, say so and explain
which structural element is missing. Do not force a split.
```

**Point 3 is where series fail.** Part two usually opens with a recap —
fatal. New viewers get no hook, returning viewers get nothing new. Open on
tension, backfill context inside the first reveal.

**Maximum 3 parts.** Beyond that, drop-off between parts compounds faster
than the watch time gained.

---

## Reading your retention graph

TikTok shows a second-by-second curve. Compare it against your Module 3 beat
map:

| What you see | What it means | Which module to fix |
|---|---|---|
| Cliff in first 5 seconds | Hook failed | Module 2 |
| Steady decline through middle | Beat cadence too slow | Module 3 |
| Cliff where you placed a reveal | That beat carried no new information | Module 3 |
| Drop at part boundaries | Cliffhanger too weak, or part 2 opened on recap | Module 6 |
| Spike | Section replayed — either valuable or confusing | Investigate |

**Benchmarks at this length:** roughly 40–50% average retention is typical
across TikTok. Strong narrative content in the 1–2 minute range should beat
that. Completion above 70% is where distribution changes character — that's
the threshold worth chasing, not raw view count.

Diagnose before rewriting. A hook problem and a pacing problem look similar
in view counts and completely different in the curve.
