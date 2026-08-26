CONFIG = {
    "product": "Retention Engineering",
    "eyebrow": "SHORT-FORM VIDEO SYSTEM",
    "subtitle": "The Prompt Pack — offline copy of all six modules.",
    "accent": "#B84A5A",
    "output": "retention-prompt-pack.pdf",
    "intro": [
        "This is a production system for narrative short-form video — the format where "
        "someone stays for two minutes because they need to know how the story ends.",
        "Every prompt works on the free tier of any current AI assistant. Work the modules "
        "in order; each takes the previous one's output as input. Replace anything in "
        "[square brackets] before sending.",
    ],
    "intro_note": "One thing to be clear about up front: this system targets 105 to 125 "
                  "seconds, well above TikTok's 42.7-second average. That is a deliberate "
                  "trade. You give up the easy completion rate a 15-second clip gets, and "
                  "buy total watch time and series retention instead. It only pays off if "
                  "the retention architecture in Modules 3 and 6 actually holds.",
    "modules": [
        {
            "title": "Source Mining",
            "intro": "Most short-form content fails before a word is written, because the "
                     "underlying story was never worth telling. This module filters for "
                     "stories that carry their own momentum.",
            "prompt": """I make narrative short-form video in this niche: [describe it].

Find 10 story premises from public sources (forums, news archives,
community posts, historical records) that fit ALL of these:
- A clear inciting incident within the first few sentences
- At least two reversals or revelations before the ending
- An outcome that isn't obvious from the setup
- No named private individuals

For each, give me: the premise in one sentence, where the first
reversal lands, and what the reader doesn't see coming.

Rank them by how hard it would be to stop reading halfway.""",
            "tip": "The ranking criterion is the whole point. A story you'd abandon halfway "
                   "in text form will lose viewers halfway in video form — no amount of "
                   "editing rescues a premise with no pull.",
        },
        {
            "title": "Hook Engineering",
            "intro": "The first three seconds decide whether the other 120 exist. This "
                     "module builds the opening against a fixed hierarchy rather than by "
                     "instinct.",
            "prompt": """Story premise: [paste your chosen premise from Module 1].

Write 8 opening lines, each under 12 words, spoken aloud as the
first thing the viewer hears.

Use this hierarchy, strongest first:
1. Immediate danger
2. Impossible situation
3. Disturbing mystery
4. High stakes
5. Betrayal
6. Curiosity gap
7. Emotional conflict

Label which tier each line uses. At least three must come from
tiers 1-3.

Reject anything that: asks a rhetorical question, starts with
"So", "Imagine", or "This is the story of", or explains context
before the hook lands.""",
            "tip": "The rejection list exists because those four patterns are what a language "
                   "model reaches for by default, and they are the exact patterns that lose "
                   "viewers. Enforce it strictly — regenerate rather than accept.",
        },
        {
            "title": "Retention Architecture",
            "intro": "Between the hook and the ending is where most videos quietly die. The "
                     "fix is structural: a new piece of information at a fixed cadence, "
                     "planned before the script is written.",
            "prompt": """Story: [paste premise]. Hook: [paste chosen hook].

Build a retention map for a 110-second video. Mark:
- Second 0-3: the hook
- Second 15-20: first reveal (something the viewer didn't know
  when the video started)
- Then a new reveal, twist, or escalation every 10-15 seconds
- The final 5 seconds: either resolution or cliffhanger

For each beat, write one line describing what NEW information the
viewer receives. If a beat contains no new information, cut it and
redistribute the time.

Flag any stretch longer than 15 seconds without a beat.""",
            "tip": "The final instruction is the useful one. Run it, then look only at the "
                   "flagged stretches — those are the exact timestamps where your retention "
                   "graph will show a cliff.",
        },
        {
            "title": "TTS-Native Scripting",
            "intro": "Text-to-speech reads differently than a person does. Writing for the "
                     "page and hoping the voice engine copes is the most common production "
                     "mistake in this format.",
            "prompt": """Retention map: [paste Module 3 output].

Write the full spoken script, 240-290 words, following these rules
exactly:

- Spell out all numbers as words (twenty three, not 23)
- Short sentences. Break any sentence over 15 words into two.
- No emojis, no asterisks, no parentheses, no em dashes
- No abbreviations the voice engine would mispronounce
- Commas only where you want an audible pause
- Nothing that isn't spoken aloud -- no stage directions, no
  headers, no speaker labels

Output only the script text, nothing else.""",
            "tip": "Read the output aloud yourself before you generate audio. Anything that "
                   "makes you stumble will make the voice engine stumble, and re-rendering "
                   "costs more time than a proofread.",
        },
        {
            "title": "Visual and Audio Layer",
            "intro": "The visual track's job in this format is to occupy the eye without "
                     "competing for the ear. Get that balance wrong and retention drops even "
                     "when the story is strong.",
            "prompt": """Script: [paste Module 4 script].
Retention map: [paste Module 3 beats].

Produce:
1. Overlay text for each beat -- 3-6 words maximum, appearing at
   the moment the beat lands, never a transcript of the narration
2. Background footage direction: what kind of visual motion, and
   what to avoid so it doesn't pull attention from the audio
3. Sound effect cues tied to specific beats, with timestamps
4. The two or three moments where the visual should change
   sharply, to reset attention

Rule: overlay text must never duplicate what is being said at that
same moment. It either emphasises or adds.""",
            "tip": "The no-duplication rule is worth defending. On-screen text that repeats "
                   "the narration gives the viewer permission to mute — and a muted viewer "
                   "is one swipe from gone.",
        },
        {
            "title": "Multi-Part and Cliffhangers",
            "intro": "Splitting a story across parts multiplies total watch time, but only "
                     "if the break lands somewhere the viewer can't walk away from. A bad "
                     "split loses the whole audience at part two.",
            "prompt": """Full story: [paste premise and script].

If this story is strong enough to split across 2-3 parts:
1. Identify the split point -- the moment where stopping is
   genuinely uncomfortable
2. Write the closing 10 seconds of each non-final part, ending on
   the unresolved beat
3. Write the opening 10 seconds of each subsequent part, which
   must re-hook someone who did NOT see the previous part
4. Confirm each part still holds 240-290 words

If the story is not strong enough to split, say so and explain
which structural element is missing. Do not force a split.""",
            "tip": "Point 3 is where most series fail. Part two usually opens with a recap, "
                   "which is fatal — new viewers get no hook and returning viewers get "
                   "nothing new. Open on tension, backfill context inside the first reveal.",
        },
    ],
    "closing_eyebrow": "WHEN YOU'RE DONE",
    "closing_title": "Reading your retention graph",
    "closing": [
        "TikTok shows a second-by-second retention curve, which makes this system testable "
        "rather than theoretical. Compare the curve against your Module 3 beat map: a cliff "
        "should never appear where you placed a reveal, and if it does, that beat wasn't "
        "carrying new information.",
        "Benchmarks worth holding yourself to at this length: roughly 40 to 50 percent "
        "average retention is typical across TikTok, and strong narrative content in the "
        "1-2 minute range should beat that. Completion above 70 percent is where "
        "distribution changes character.",
        "If your curve drops hard in the first 5 seconds, the problem is Module 2, not your "
        "story. If it drops steadily through the middle, it's Module 3. Diagnose before "
        "rewriting.",
    ],
    "closing_note": "Every prompt here is a starting point, not scripture. When a beat "
                    "structure works unusually well for your niche, write it down and reuse "
                    "it — the system is meant to accumulate.",
}
