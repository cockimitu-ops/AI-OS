#!/usr/bin/env python3
"""Build a voice profile for Felix out of his own WhatsApp messages.

Why this exists: the worker's register is a generic assistant's. In the two
channels where only Felix is ever on the other end - the Telegram bridge
(`tg_*` threads) and the web client's chat (`web_*` threads) - he wants it to
talk like him. Everything else in the system stays professional: the DMARC
letters, Gumroad copy, Fiverr deliverables and every scheduled agent task are
deliberately outside this, and the gate in aios_runner enforces that by
thread id rather than by trusting a prompt to remember.

Fine-tuning is not the mechanism. The model chain is free OpenRouter models
plus budget-capped GLM-5.2 - none of them fine-tunable - and there is no GPU
here for a local LoRA. So voice is prompt-side: measured style rules plus
real examples, injected the same way Knowledge_Core.md already is.

Privacy, by construction: this reads a two-sided chat log and keeps only
Felix's own lines. The other participants' text is dropped at parse time and
never written to disk, never sent to a model. What survives from their side
is one boolean - whether Felix's message was answering someone or continuing
his own burst - because that rhythm is a real part of how he writes. Their
names are collected only to redact them out of the examples.

Output goes to voice/ (gitignored, alongside the raw import), NOT into
07_Context/ with Knowledge_Core: that folder is committed and Notion-synced,
and private chat logs have no business in either.

Stdlib only, same convention as money_board.py/dmarc_prospector.py.
"""
import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
VOICE_DIR = os.path.join(TASK_RUNNER_DIR, "voice")
MESSAGES_PATH = os.path.join(VOICE_DIR, "messages.jsonl")
PROFILE_PATH = os.path.join(VOICE_DIR, "Voice_Profile.md")

# WhatsApp exports come in two shapes and the difference is not cosmetic.
# Android: "31.08.26, 19:24 - Name: text"
# iOS:     "[31.08.26, 19:24:12] Name: text", peppered with U+200E LTR marks
# that make a naive `line.startswith("[")` fail on the very first line of the
# file. Both are matched here; the marks are stripped before anything else.
ANDROID_RE = re.compile(
    r"^(\d{1,2}[./]\d{1,2}[./]\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)"
    r"(?:\s*[APap]\.?[Mm]\.?)?\s+-\s+(.*)$")
IOS_RE = re.compile(
    r"^\[(\d{1,2}[./]\d{1,2}[./]\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)"
    r"(?:\s*[APap]\.?[Mm]\.?)?\]\s+(.*)$")
SENDER_RE = re.compile(r"^([^:]{1,60}?):\s(.*)$", re.DOTALL)

# Placeholder lines WhatsApp writes itself. These are not things Felix typed,
# and counting "<Medien ausgeschlossen>" as a 2-word message would drag the
# whole length distribution down.
NOISE = (
    "<medien ausgeschlossen>", "<media omitted>", "medien ausgeschlossen",
    "bild weggelassen", "image omitted", "video weggelassen", "video omitted",
    "audio weggelassen", "audio omitted", "sticker weggelassen",
    "sticker omitted", "gif weggelassen", "gif omitted",
    "dokument weggelassen", "document omitted",
    "diese nachricht wurde gelöscht.", "this message was deleted.",
    "du hast diese nachricht gelöscht.", "you deleted this message.",
    "nachricht gelöscht", "<anhang:", "<attached:",
    "nachrichten und anrufe sind ende-zu-ende-verschlüsselt",
    "messages and calls are end-to-end encrypted",
    "verpasster sprachanruf", "missed voice call",
    "verpasster videoanruf", "missed video call",
)

# The fixed NOISE list above turned out not to be enough on real exports:
# "<Video note omitted>" and "<View once voice message omitted>" both got
# through and were counted as things Felix wrote. WhatsApp names too many
# media types (in two languages, with per-type wording) to enumerate, so any
# message that is entirely one angle-bracketed "... omitted/weggelassen"
# placeholder is treated as WhatsApp's text rather than his.
PLACEHOLDER_RE = re.compile(
    r"^<[^>]{0,80}(omitted|weggelassen|ausgeschlossen|attached|anhang)[^>]{0,20}>$",
    re.IGNORECASE)

_MD_LIST_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+\S", re.M)
_MD_HEAD_RE = re.compile(r"^\s{0,3}#{1,4}\s+\S", re.M)

URL_RE = re.compile(r"https?://\S+|www\.\S+")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+\d[\d\s/()-]{6,}\d|\d{5,})(?!\w)")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")

GERMAN_MARKERS = {
    "und", "nicht", "ich", "das", "ist", "der", "die", "aber", "auch", "noch",
    "schon", "halt", "einfach", "mal", "war", "wird", "hab", "habe", "kann",
    "wenn", "weil", "dann", "was", "wie", "mit", "auf", "für", "nur", "ja",
    "nein", "ne", "doch", "immer", "wieder", "gut", "gerade", "grad",
}
ENGLISH_MARKERS = {
    "the", "and", "is", "are", "you", "your", "not", "but", "with", "this",
    "that", "just", "really", "actually", "gonna", "want", "need", "know",
    "think", "yeah", "yes", "no", "for", "have", "was", "were", "would",
}


def _strip_marks(line):
    return line.replace("‎", "").replace("‏", "").replace("‪", "") \
               .replace("‬", "").replace("﻿", "").rstrip("\n")


def _is_noise(text):
    low = text.strip().lower()
    if not low:
        return True
    if PLACEHOLDER_RE.match(text.strip()):
        return True
    return any(low.startswith(n) or low == n.rstrip(".") for n in NOISE)


def parse_export(text):
    """-> [{"sender": str, "text": str}] in file order.

    Multi-line messages matter: a line that does not start with a timestamp
    is a continuation of the previous message, not a new one. Treating each
    physical line as a message would inflate the message count and destroy
    the length distribution, which is the single most useful statistic here.
    """
    messages = []
    for raw_line in text.splitlines():
        line = _strip_marks(raw_line)
        m = IOS_RE.match(line) or ANDROID_RE.match(line)
        if not m:
            if messages and line.strip():
                messages[-1]["text"] += "\n" + line.strip()
            continue
        body = m.group(3)
        sm = SENDER_RE.match(body)
        if not sm:
            # A timestamped line with no "Name: " is a system notice
            # ("... sind Ende-zu-Ende-verschlüsselt"), not a message. Also
            # closes the previous message so the notice can't be glued on as
            # a continuation line.
            messages.append({"sender": None, "text": ""})
            continue
        messages.append({"sender": sm.group(1).strip(), "text": sm.group(2).strip()})
    return [m for m in messages if m["sender"]]


def detect_me(chats):
    """The one sender who appears in every export is Felix.

    Only works with 2+ chats, which is also the number needed for a profile
    worth having: register shifts a lot between a best friend, a parent and
    a group chat, and a profile built from one chat is a caricature of one
    relationship rather than a voice.
    """
    if len(chats) < 2:
        return None
    common = None
    for msgs in chats:
        senders = {m["sender"] for m in msgs}
        common = senders if common is None else (common & senders)
    return sorted(common)[0] if common and len(common) == 1 else None


def extract_mine(chats, me):
    """Felix's own messages only. Everyone else's text is dropped here and
    never leaves this function - the return value carries no one else's
    words. `answering` records whether the previous message was someone
    else's, which is what separates 'he replies in one line' from 'he sends
    four in a row', without keeping what was said to him."""
    mine, others = [], set()
    for chat_index, msgs in enumerate(chats):
        prev_was_other = True
        for m in msgs:
            if m["sender"] != me:
                others.add(m["sender"])
                prev_was_other = True
                continue
            if _is_noise(m["text"]):
                prev_was_other = False
                continue
            # Which chat a message came from, as an index and never a name:
            # it is needed to keep one relationship from supplying every
            # example, and the partner's name is not needed for that.
            mine.append({"text": m["text"], "answering": prev_was_other,
                         "chat": chat_index})
            prev_was_other = False
    return mine, others


def _words(text):
    return [w for w in re.split(r"\s+", text.strip()) if w]


# Unicode category "So" was the first cut and it was wrong on real data:
# Braille patterns (U+2800-28FF) and block-drawing characters are all "So",
# so the ASCII-art images people paste into WhatsApp put ⣿, ░, █ into the
# "emoji he reuses" list - four of the top ten - and the profile then told
# the model to use them. Allowlisted ranges instead of a category.
EMOJI_RANGES = (
    (0x1F300, 0x1FAFF),  # the emoji blocks proper
    (0x1F000, 0x1F0FF),  # mahjong / playing cards
    (0x2600, 0x27BF),    # misc symbols + dingbats: ☠ ♥ ❤ ✂ ✅
    (0x2B00, 0x2BFF),    # ⬆ ⭐
)
# Skin-tone modifiers and the variation selector are parts of an emoji, not
# emoji - counting them separately would rank "🏽" as its own favourite.
EMOJI_PARTS = set(range(0x1F3FB, 0x1F400)) | {0xFE0F, 0x200D}


def _emoji(text):
    out = []
    for ch in text:
        o = ord(ch)
        if o in EMOJI_PARTS:
            continue
        if any(lo <= o <= hi for lo, hi in EMOJI_RANGES):
            out.append(ch)
    return out


def _language(text):
    words = {w.strip(".,!?:;\"'()").lower() for w in _words(text)}
    de, en = len(words & GERMAN_MARKERS), len(words & ENGLISH_MARKERS)
    if de and en:
        return "mixed"
    if de:
        return "de"
    if en:
        return "en"
    return "unknown"


def _pct(n, total):
    return round(100.0 * n / total, 1) if total else 0.0


def compute_stats(mine):
    """Deterministic, zero-token. Everything here is a countable fact about
    how he writes - the parts a model can actually be instructed to imitate.
    """
    total = len(mine)
    if not total:
        return {"messages": 0}
    lengths = sorted(len(_words(m["text"])) for m in mine)
    langs = Counter(_language(m["text"]) for m in mine)
    emojis = Counter()
    for m in mine:
        emojis.update(_emoji(m["text"]))
    first_words = Counter()
    for m in mine:
        w = _words(m["text"])
        if w:
            first_words[w[0].strip(".,!?").lower()] += 1
    all_words = Counter()
    for m in mine:
        all_words.update(w.strip(".,!?:;\"'()").lower() for w in _words(m["text"]))

    def has(pred):
        return sum(1 for m in mine if pred(m["text"]))

    answering = [m for m in mine if m["answering"]]
    bursts = [m for m in mine if not m["answering"]]
    return {
        "messages": total,
        "words_median": lengths[len(lengths) // 2],
        "words_p90": lengths[int(len(lengths) * 0.9)],
        "words_mean": round(sum(lengths) / total, 1),
        "one_word_pct": _pct(sum(1 for n in lengths if n <= 1), total),
        "over_25_words_pct": _pct(sum(1 for n in lengths if n > 25), total),
        # In German every noun is capitalised, so a lowercase first letter is
        # a much stronger style signal here than it would be in English.
        "lowercase_start_pct": _pct(has(lambda t: t[:1].islower()), total),
        "capital_start_pct": _pct(has(lambda t: t[:1].isupper()), total),
        # The formatting facts. These turned out to matter more than any
        # word choice: reviewing real replies, the register held on short
        # lines and collapsed into bold headers and numbered lists the moment
        # the answer had substance. Stating the rate makes the rule a fact
        # about him rather than a style preference.
        "markdown_pct": _pct(has(lambda t: "**" in t or _MD_LIST_RE.search(t)
                                 or _MD_HEAD_RE.search(t)), total),
        "multiline_pct": _pct(has(lambda t: "\n" in t.strip()), total),
        "words_p95": lengths[int(len(lengths) * 0.95)],
        "words_p99": lengths[int(len(lengths) * 0.99)],
        "no_end_punct_pct": _pct(has(lambda t: t and t[-1] not in ".!?"), total),
        "ellipsis_pct": _pct(has(lambda t: "..." in t), total),
        "exclaim_pct": _pct(has(lambda t: "!" in t), total),
        "question_pct": _pct(has(lambda t: "?" in t), total),
        "emoji_pct": _pct(has(lambda t: bool(_emoji(t))), total),
        "top_emoji": [e for e, _ in emojis.most_common(10)],
        # Reported over the messages that could actually be classified, not
        # over all of them: a large share of his messages ("jo", "kk", "brb")
        # carry no marker word in either language, and counting those in the
        # denominator made the shares look like they had silently lost 40%.
        "lang": {k: _pct(v, total - langs.get("unknown", 0))
                 for k, v in langs.items() if k != "unknown"},
        "lang_classified_pct": _pct(total - langs.get("unknown", 0), total),
        # The rate that makes chat feel like chat: consecutive messages from
        # him with nobody answering in between. A model that always replies
        # in exactly one block never sounds like this no matter how good the
        # word choice is.
        "burst_pct": _pct(len(bursts), total),
        "reply_words_median": (
            sorted(len(_words(m["text"])) for m in answering)[len(answering) // 2]
            if answering else 0),
        # The share each chat contributed. On the first real import one chat
        # was 92% of 55,820 messages, which makes a "how Felix writes"
        # profile really a "how Felix writes to one person" profile - the
        # >=2-chats rule does not catch that, so the number is stated
        # outright rather than left for someone to notice.
        "chat_shares": sorted(
            (_pct(c, total)
             for c in Counter(m.get("chat", 0) for m in mine).values()),
            reverse=True),
        "top_openers": [w for w, _ in first_words.most_common(12)],
        "top_words": [w for w, c in all_words.most_common(40) if len(w) > 2][:20],
    }


def redact(text, names):
    """Strip anything that could identify a third party out of an example.

    Felix's own messages still mention other people by name, quote phone
    numbers and paste links. The examples are the part that gets shipped
    into a prompt, so they get scrubbed even though the raw import stays
    local: the redaction bar is what leaves this machine, not what sits on
    it."""
    text = URL_RE.sub("[link]", text)
    text = EMAIL_RE.sub("[email]", text)
    text = IBAN_RE.sub("[iban]", text)
    text = PHONE_RE.sub("[nummer]", text)
    for name in sorted(names, key=len, reverse=True):
        for token in [name] + name.split():
            if len(token) < 3:
                continue
            text = re.sub(rf"\b{re.escape(token)}\b", "[name]", text,
                          flags=re.IGNORECASE)
    return text


# Buckets, not one target length. Scoring every candidate by distance from
# the median produced 50 examples that were all exactly 3 words long - a
# perfectly accurate picture of the median and a useless one of the writer,
# in a corpus where 27% of messages are a single word and 10% run past ten.
LENGTH_BUCKETS = ((1, 1), (2, 2), (3, 3), (4, 5), (6, 7),
                  (8, 10), (11, 15), (16, 25), (26, 60))


def select_exemplars(mine, stats, names, n=50):
    """Real messages beat any description of them - but they have to be
    representative, and 'representative' is a distribution, not an average.

    Examples are drawn per length bucket in proportion to how often he
    actually writes messages of that length, and round-robin across chats
    inside each bucket so one relationship cannot supply all of them."""
    buckets = {b: [] for b in LENGTH_BUCKETS}
    counts = {b: 0 for b in LENGTH_BUCKETS}
    for m in mine:
        wc = len(_words(m["text"]))
        for b in LENGTH_BUCKETS:
            if b[0] <= wc <= b[1]:
                counts[b] += 1
                clean = redact(m["text"], names).strip()
                if clean and clean.count("[") <= 2:
                    buckets[b].append(
                        {"text": clean, "answering": m["answering"],
                         "chat": m.get("chat", 0)})
                break
    total = sum(counts.values()) or 1
    out, seen = [], set()
    for b in LENGTH_BUCKETS:
        want = round(n * counts[b] / total)
        if counts[b] and not want:
            want = 1  # a length he really uses should not vanish to rounding
        pool = buckets[b]
        if not pool or not want:
            continue
        by_chat = {}
        for item in pool:
            by_chat.setdefault(item["chat"], []).append(item)
        order = sorted(by_chat)
        picked, i = 0, 0
        while picked < want and any(by_chat[c] for c in order):
            chat = order[i % len(order)]
            i += 1
            if not by_chat[chat]:
                continue
            item = by_chat[chat].pop(len(by_chat[chat]) // 2)  # mid, not the
            key = item["text"].lower()                          # first/newest
            if key in seen:
                continue
            seen.add(key)
            out.append({"text": item["text"], "answering": item["answering"]})
            picked += 1
    return out[:n]


def _balance_note(stats):
    """Says out loud when the corpus is really one relationship.

    On the first real import, one chat was 92% of 55,820 messages. Nothing
    about that is wrong as data - it is genuinely where most of his writing
    went - but a profile silently built from it would carry one relationship's
    register (its endearments, its running jokes) into every conversation as
    though it were how he talks generally."""
    shares = stats.get("chat_shares") or []
    if not shares or shares[0] < 60:
        return ""
    return (
        f"> Heads-up: {shares[0]}% of these messages come from a single chat, "
        "so this is closer to how he writes to one person than how he writes "
        "in general. The examples below are balanced across chats to soften "
        "that, but the measured numbers above are not. Importing more chats "
        "of comparable size is what actually fixes it.\n"
    )


def render_profile(stats, exemplars):
    if not stats.get("messages"):
        return "# Voice Profile\n\nNo messages imported yet.\n"
    lang = stats["lang"]
    lines = [
        "# Voice Profile — how Felix writes",
        "",
        f"Generated by `scripts/voice_import.py` from {stats['messages']} of "
        "Felix's own WhatsApp messages. Every number below is counted, not "
        "estimated.",
        "",
        "## What this governs, and what it does not",
        "This changes **how** you say things when you are talking to Felix "
        "directly, in his Telegram chat or the web client. It never changes "
        "**what** is true, and it never lowers the bar for admitting you do "
        "not know something or have not checked. If sounding casual would "
        "mean sounding certain about something you have not verified, drop "
        "the voice, not the honesty — he asked for this for entertainment, "
        "not to be agreed with more smoothly.",
        "",
        "It applies to conversation only. Business letters, client-facing "
        "documents, Gumroad and Fiverr copy, and every scheduled task stay "
        "fully professional — those never see this file.",
        "",
        "## Measured style",
"### Hard rules — these are not preferences, they are counted facts",
        "",
        f"1. **No markdown. Ever.** Bold, bullet lists, numbered lists and "
        f"headings appear in {stats.get('markdown_pct', 0)}% of his "
        f"{stats['messages']:,} messages. A bulleted, bolded answer is not "
        "'a bit formal for him' - it is a format he has effectively never "
        "used in his life. Code blocks are the one exception: when he asks "
        "for a script, give him the script.",
        f"2. **One line.** {100 - stats.get('multiline_pct', 0):.1f}% of his "
        "messages are a single line. If something genuinely needs more, it "
        "is two or three short lines, never a structured block.",
        f"3. **Short.** Median {stats['words_median']} words, 90th percentile "
        f"{stats['words_p90']}, 99th percentile {stats.get('words_p99', 28)}. "
        f"{stats['one_word_pct']}% are one single word. Answering a question "
        f"directly, the median is {stats['reply_words_median']}. If the honest "
        "answer needs more room, say the short version first and let him ask.",
        f"4. **Write normally, capitalised.** "
        f"{stats.get('capital_start_pct', 0)}% of his messages start with a "
        f"capital letter; only {stats['lowercase_start_pct']}% start "
        "lowercase. Do not write everything in lowercase - that is an "
        "imitation of a style that is not actually his.",
        "",
        "### The rest of the measurements",
        f"- **Bursts**: {stats['burst_pct']}% of his messages continue his own "
        "previous one instead of answering someone. He thinks out loud across "
        "two or three short messages rather than composing one tidy block. "
        "Short consecutive lines are more like him than one balanced paragraph.",
        f"- **Capitalisation**: {stats['lowercase_start_pct']}% start "
        "lowercase — in German, where every noun is capitalised, that is a "
        "deliberate register, not sloppiness.",
        f"- **Punctuation**: {stats['no_end_punct_pct']}% end with no final "
        f"punctuation at all, {stats['ellipsis_pct']}% use \"...\", "
        f"{stats['exclaim_pct']}% use \"!\", {stats['question_pct']}% ask "
        "something.",
        f"- **Language**: of the "
        f"{stats['lang_classified_pct']}% of messages long enough to tell, "
        f"{lang.get('de', 0)}% German, {lang.get('en', 0)}% English, "
        f"{lang.get('mixed', 0)}% mixed inside one message. The rest are too "
        "short to classify, which is itself the point: a lot of what he sends "
        "is \"jo\", \"kk\", \"passt\". Code-switching mid-sentence is normal "
        "for him; do not tidy it into one language.",
        f"- **Emoji**: in {stats['emoji_pct']}% of messages, and he reuses a "
        "small fixed set: " + (" ".join(stats["top_emoji"]) or "(none)") +
        ". Use only these, at this rate. A model reaching for a wider emoji "
        "palette is the most obvious tell there is.",
        f"- **Opens with**: {', '.join(stats['top_openers'][:10])}",
        f"- **Reaches for**: {', '.join(stats['top_words'][:15])}",
        "",
        _balance_note(stats),
        "## Real messages of his",
        "Imitate the register, never the content — these are old messages, "
        "not facts about now. `[name]`, `[nummer]`, `[link]` are redactions.",
        "",
    ]
    for ex in exemplars:
        marker = "↩" if ex["answering"] else "→"
        lines.append(f"- {marker} {ex['text']}")
    return "\n".join(lines) + "\n"


def load_chats(paths):
    chats = []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            msgs = parse_export(f.read())
        if msgs:
            chats.append(msgs)
        else:
            print(f"[!] No messages parsed from {p} - unexpected format?",
                  file=sys.stderr)
    return chats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("exports", nargs="+", help="WhatsApp _chat.txt export files")
    ap.add_argument("--me", help="Your own name exactly as it appears in the "
                                 "export (default: the sender common to all)")
    ap.add_argument("--examples", type=int, default=50)
    ap.add_argument("--out", default=VOICE_DIR)
    args = ap.parse_args(argv)

    chats = load_chats(args.exports)
    if not chats:
        print("Nothing to import.", file=sys.stderr)
        return 1
    me = args.me or detect_me(chats)
    if not me:
        senders = sorted({m["sender"] for c in chats for m in c})
        print("Could not tell which sender is you. Pass --me NAME. Seen: "
              + ", ".join(senders), file=sys.stderr)
        return 1

    mine, others = extract_mine(chats, me)
    if not mine:
        print(f"No messages from '{me}' found.", file=sys.stderr)
        return 1
    stats = compute_stats(mine)
    exemplars = select_exemplars(mine, stats, others, n=args.examples)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "messages.jsonl"), "w", encoding="utf-8") as f:
        for m in mine:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")
    with open(os.path.join(args.out, "stats.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    profile_path = os.path.join(args.out, "Voice_Profile.md")
    with open(profile_path, "w", encoding="utf-8") as f:
        f.write(render_profile(stats, exemplars))

    print(f"[✓] {len(mine)} eigene Nachrichten aus {len(chats)} Chat(s) "
          f"({me}), {len(exemplars)} Beispiele")
    print(f"    Median {stats['words_median']} Wörter, "
          f"{stats['lowercase_start_pct']}% klein angefangen, "
          f"{stats['burst_pct']}% Bursts, {stats['emoji_pct']}% mit Emoji")
    print(f"    -> {profile_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
