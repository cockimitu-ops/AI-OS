#!/usr/bin/env python3
"""Ingests Felix's raw study notes into the vault as structured, revisable notes.

The gap: notes written during a lecture are fragments - shorthand, half
sentences, a term with no definition next to it. They are worth keeping and
almost never worth re-reading in that state, so they rot in an inbox folder.
This turns each one into a note with a summary, a concept list, action items
and flashcards, filed in the vault with the header convention the rest of it
uses, and logged so a second run never silently redoes the same work.

Where the model sits, and where it does not
-------------------------------------------
The model does exactly one thing: turn one note's raw text into structured
text. It does not choose destinations, generate headers, name files, decide
what has already been processed, or touch the filesystem at all. Every one of
those is deterministic and lives here, because a free-tier model getting a
path wrong is a documented event in this project (see System_Prompt.md's note
on the canonical scripts/ location, added after exactly that), and because a
misfiled study note is discovered months later when it is needed.

That split is the same one dmarc_prospector.py and tech_scout.py use: a
tested script does the mechanical work against real data, the model only
reasons over what it was handed.

Why it goes through the task queue instead of calling litellm
-------------------------------------------------------------
There is exactly one model-calling path in this system - aios_runner.py's
MODEL_CHAIN, with its retry-the-next-provider fallback, its timeout guard and
its paid-spend accounting via spend_guard.py. A second path here would
duplicate all of that and quietly bypass the spend ledger the moment the paid
tier was in play. So this enqueues a task file exactly the way
dispatch_task.py, telegram_bridge.py and the web client already do, and waits
for the worker's log. No new agent-routing or model logic.

Tasks are enqueued with no thread id, which also means the voice profile
never applies here - study notes are not the place for Felix's WhatsApp
register.

Non-destructive: the source notes are never moved, rewritten or deleted.
Felix wrote them; a dedupe state file tracks what has been processed instead.

Stdlib only, same convention as every other script in this folder.

    study_agent.py                         # process new notes, default inbox
    study_agent.py --limit 1 --verbose     # one note, chatty
    study_agent.py --dry-run               # show what would be processed
    study_agent.py --force some_note.md    # reprocess even if unchanged
    study_agent.py --status                # what has been ingested so far
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, TASK_RUNNER_DIR)

import agents        # noqa: E402  (needs sys.path set first)
import vault_write   # noqa: E402

VAULT = vault_write.VAULT
INBOX = os.path.join(TASK_RUNNER_DIR, "tasks", "inbox")
LOGS = os.path.join(TASK_RUNNER_DIR, "tasks", "logs")
STATE_DIR = os.path.join(TASK_RUNNER_DIR, "study")
STATE_PATH = os.path.join(STATE_DIR, "state.json")

# Where Felix drops raw notes. Overridable so an Obsidian vault synced by git
# elsewhere on disk can be the source instead - see --inbox / --git-pull.
DEFAULT_SOURCE = os.path.join(
    VAULT, "10_Projects", "CyberSecurityLearning", "Inbox")
# Processed notes land in the project they belong to, not a generic research
# folder: vault_write.py's allowlist accepts any 10_Projects/* directory.
DEFAULT_DEST = "10_Projects/CyberSecurityLearning"
STUDY_LOG = os.path.join(VAULT, "10_Projects", "CyberSecurityLearning",
                         "Study_Log.md")

AGENT = "Study_Teacher"
# The worker's own per-task ceiling is 180s per model attempt and MODEL_CHAIN
# retries across providers, so a single note can legitimately take minutes on
# a bad night. Generous, and still bounded.
DEFAULT_TIMEOUT_S = 420
# A whole lecture transcript would blow a free model's context and get the
# task truncated somewhere unpredictable. Long notes are split by the caller
# (or trimmed here with an explicit marker) rather than silently cut.
MAX_NOTE_CHARS = 12_000
# A nightly run should not fire twenty model calls at a rate-limited free
# tier because Felix emptied a semester into the folder at once.
DEFAULT_LIMIT = 5

MARKERS = ("TITLE:", "SUMMARY:", "CONCEPTS:", "ACTIONS:", "FLASHCARDS:")

# German markers are accepted as equals, not as a nicety. Caught live on the
# first paid-tier run: handed German lecture notes, GLM-5.2 sensibly answered
# in German and labelled the sections TITEL/ZUSAMMENFASSUNG/KONZEPTE/
# AKTIONEN/LERNKARTEN. The content was excellent and the whole answer was
# discarded over the label language. A stronger model reasoning "the source
# is German, so the answer should be" is exactly the behaviour worth having,
# so the parser bends instead of the model.
MARKER_ALIASES = {
    "TITEL:": "TITLE:", "ÜBERSCHRIFT:": "TITLE:",
    "ZUSAMMENFASSUNG:": "SUMMARY:", "KURZFASSUNG:": "SUMMARY:",
    "KONZEPTE:": "CONCEPTS:", "BEGRIFFE:": "CONCEPTS:",
    "KERNKONZEPTE:": "CONCEPTS:",
    "AKTIONEN:": "ACTIONS:", "AUFGABEN:": "ACTIONS:", "TODO:": "ACTIONS:",
    "TO-DOS:": "ACTIONS:", "OFFENE PUNKTE:": "ACTIONS:",
    "LERNKARTEN:": "FLASHCARDS:", "KARTEIKARTEN:": "FLASHCARDS:",
}
# Frage/Antwort as well as Q/A, for the same reason.
CARD_PREFIXES = ("Q:", "F:")

# Folder furniture, not study notes. Every vault directory carries a README by
# convention, so without this the very first run of every new inbox spends a
# model call turning the instructions into flashcards - caught on the first
# dry run here, doing exactly that.
SKIP_NAMES = {"readme.md", "index.md", "study_log.md"}


# --- state ---------------------------------------------------------------

def load_state():
    """Never raises: a corrupt or missing state file means "nothing processed
    yet", which is recoverable, rather than a crash that blocks every future
    run until someone notices."""
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE_PATH + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
    os.replace(tmp, STATE_PATH)  # atomic, same reason dispatch_task.py does it


def _digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --- source --------------------------------------------------------------

def git_pull(directory, verbose=False):
    """Best-effort sync for a source folder that is its own git repo (an
    Obsidian vault synced from the phone, typically).

    Deliberately non-fatal and --ff-only: a failed pull must leave the run
    working on whatever is already on disk rather than aborting the whole
    ingest, and this script has no business resolving a merge conflict in
    Felix's notes."""
    if not os.path.isdir(os.path.join(directory, ".git")):
        if verbose:
            print(f"[i] {directory} is not a git repo - skipping pull")
        return False
    try:
        proc = subprocess.run(
            ["git", "-C", directory, "pull", "--ff-only"],
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        print(f"[!] git pull failed ({e}) - continuing with local files",
              file=sys.stderr)
        return False
    if proc.returncode != 0:
        print(f"[!] git pull failed: {proc.stderr.strip()[:200]} - "
              "continuing with local files", file=sys.stderr)
        return False
    if verbose:
        print(f"[i] git pull: {proc.stdout.strip()[:200]}")
    return True


def discover(source, state, force=None, verbose=False):
    """-> [(path, text, digest)] for notes that are new or changed.

    Hash-based rather than mtime-based: a git sync, a file copy or an editor
    that rewrites on save all bump mtime without changing a word, and each of
    those would otherwise re-run a model call and create a duplicate note."""
    if not os.path.isdir(source):
        return []
    out = []
    for name in sorted(os.listdir(source)):
        if name.startswith((".", "_")) or name.lower() in SKIP_NAMES:
            continue
        if not name.lower().endswith((".md", ".txt")):
            continue
        path = os.path.join(source, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            print(f"[!] cannot read {name}: {e}", file=sys.stderr)
            continue
        if not text.strip():
            if verbose:
                print(f"[i] {name} is empty - skipped")
            continue
        digest = _digest(text)
        known = state.get(name)
        if known and known.get("digest") == digest and name not in (force or ()):
            if verbose:
                print(f"[i] {name} unchanged since {known.get('processed')}")
            continue
        out.append((path, text, digest))
    return out


# --- capture -------------------------------------------------------------

_SLUG_RE = None  # set below; re is imported lazily to keep the import list flat


def capture_note(text, source=DEFAULT_SOURCE, prefix="notiz", when=None):
    """Write raw text straight into the study inbox. -> path.

    Capture and processing are deliberately separate. In a lecture the only
    thing that matters is that the text lands somewhere safe in under a
    second - waiting on a model round trip, or failing because the free tier
    is rate limited right then, would mean the note is simply lost. The
    nightly run (or an on-demand run) does the thinking later.

    Never overwrites: two notes captured in the same minute get distinct
    files, because the second one being silently swallowed is indistinguishable
    from it having been saved."""
    import re
    text = (text or "").strip()
    if not text:
        raise ValueError("empty note")
    when = when or datetime.now()
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", first)[:40].strip("_").lower() or prefix
    base = f"{when.strftime('%Y%m%d_%H%M')}_{slug}"
    os.makedirs(source, exist_ok=True)
    name, n = f"{base}.md", 2
    while os.path.exists(os.path.join(source, name)):
        name = f"{base}_{n}.md"
        n += 1
    path = os.path.join(source, name)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")
    os.replace(tmp, path)
    return path


def pending_count(source=DEFAULT_SOURCE):
    """How many captured notes are waiting to be processed."""
    try:
        return len(discover(source, load_state()))
    except OSError:
        return 0


# --- the model call ------------------------------------------------------

def build_task(name, text):
    """The task body handed to the worker. The agent directive selects
    Study_Teacher; no thread directive, so this carries no conversation
    memory and no voice profile - neither belongs in coursework."""
    body = text.strip()
    if len(body) > MAX_NOTE_CHARS:
        # Explicitly marked rather than silently cut, so a truncated note is
        # visible in the output instead of looking like the lecture simply
        # ended mid-sentence.
        body = (body[:MAX_NOTE_CHARS]
                + "\n\n[... note truncated at "
                + f"{MAX_NOTE_CHARS} characters by study_agent.py ...]")
    return (
        agents.directive(AGENT)
        # Quality decides the outcome here: a definition that is subtly wrong
        # goes onto a flashcard and gets memorised. Asked for explicitly as
        # well as set in the agent's own header, so a direct CLI run does not
        # silently drop to the free chain if that header is ever edited.
        + agents.model_directive("paid")
        + f"Process this study note. Its filename is: {name}\n\n"
        "Return only the TITLE/SUMMARY/CONCEPTS/ACTIONS/FLASHCARDS block "
        "your role defines. Add nothing that is not in the note below.\n\n"
        "--- BEGIN NOTE ---\n"
        + body
        + "\n--- END NOTE ---\n"
    )


def run_through_worker(task_body, timeout_s=DEFAULT_TIMEOUT_S, poll=2):
    """Enqueue one task and wait for the worker's log. -> output text.

    Same mechanism as dispatch_task.py and the web client, including the
    atomic .part rename: the worker polls this directory, and a half-written
    task file appearing as a whole one is a real failure mode.

    Raises RuntimeError on timeout rather than returning something empty -
    the caller must be able to tell "the model said nothing" apart from "the
    worker never answered", because only one of those should count as the
    note having been processed."""
    for d in (INBOX, LOGS):
        os.makedirs(d, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"task_study_{stamp}.md"
    task_path = os.path.join(INBOX, filename)
    log_path = os.path.join(LOGS, f"{filename}.log")

    tmp = task_path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(task_body)
    os.replace(tmp, task_path)

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if os.path.exists(log_path):
            with open(log_path, encoding="utf-8") as f:
                return f.read().strip()
        time.sleep(poll)
    raise RuntimeError(f"worker did not answer within {timeout_s}s")


# --- parsing the model's answer ------------------------------------------

def parse_sections(output):
    """-> dict of section -> text, or None if the answer is not usable.

    Tolerant about surrounding noise (a stray preamble, a code fence) and
    strict about the one thing that matters: a note is only written if the
    model actually produced a summary. Free models in this chain have a
    documented habit of returning a tool transcript instead of prose (see
    aios_runner.py's synthesis fix), and that must not become a study note."""
    if not output:
        return None
    text = output.strip()
    if text.upper().startswith("UNUSABLE:") or text.startswith("ERROR"):
        return None
    # Strip a wrapping code fence if the model added one anyway.
    if text.startswith("```"):
        lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
        text = "\n".join(lines).strip()

    found, current = {}, None
    for line in text.splitlines():
        stripped = line.strip()
        upper = stripped.upper()
        marker = next((m for m in MARKERS if upper.startswith(m)), None)
        alias = None if marker else next(
            (a for a in MARKER_ALIASES if upper.startswith(a)), None)
        if marker or alias:
            hit = marker or alias
            current = (marker or MARKER_ALIASES[alias]).rstrip(":")
            found[current] = stripped[len(hit):].strip()
            continue
        if current:
            found[current] = (found[current] + "\n" + line).strip() \
                if found[current] else line.strip()
    summary = (found.get("SUMMARY") or "").strip()
    if len(summary) < 20:
        return None  # no real summary -> not a processed note
    return found


def build_body(sections, source_name):
    """Assemble the note body. vault_write.write_note adds the header block,
    so nothing here duplicates it."""
    parts = [
        "## Summary", sections.get("SUMMARY", "").strip(), "",
        "## Core Concepts", sections.get("CONCEPTS", "").strip() or "- none in these notes", "",
        "## Action Items", sections.get("ACTIONS", "").strip() or "- none", "",
        "## Flashcards", sections.get("FLASHCARDS", "").strip() or "none", "",
        "---", "",
        f"Source: `{source_name}` (raw note, kept unchanged in the study inbox). "
        "Processed by Study Teacher — the source note remains the authority; "
        "anything below that contradicts it is this pass's error.",
    ]
    return "\n".join(parts).strip()


# --- study log -----------------------------------------------------------

LOG_HEADING = "## Ingested Notes"


def append_study_log(source_name, note_path, concepts, cards, when=None,
                     path=None):
    """Append one line per ingested note. Append-only and never rewrites an
    existing line - the same rule vault_write.py holds itself to.

    Creates the file with a proper vault header if it does not exist yet, so
    the first ever run does not produce a headerless file that the naming
    convention would reject."""
    path = path or STUDY_LOG
    when = when or datetime.now().strftime("%Y-%m-%d %H:%M")
    rel = os.path.relpath(note_path, VAULT)
    line = (f"- {when} — `{source_name}` → [[{rel[:-3]}|{os.path.basename(note_path)[:-3]}]] "
            f"({concepts} Konzepte, {cards} Karten)")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        header = (
            "# Study Log\n\n"
            "Purpose: Append-only record of which raw study notes have been "
            "ingested into the vault, when, and what came out.\n"
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d')}\n"
            "Status: Active\n"
            "Related Documents: [[10_Projects/CyberSecurityLearning/README|"
            "CyberSecurityLearning]], [[04_Agents/Study_Teacher|Study Teacher]]\n\n"
            "---\n\n"
            f"{LOG_HEADING}\n\n"
        )
        with open(path, "w", encoding="utf-8") as f:
            f.write(header)
    with open(path, "r", encoding="utf-8") as f:
        existing = f.read()
    # A missing heading (someone edited the file) must not send the entry to
    # the end of an unrelated section - it is recreated instead.
    if LOG_HEADING not in existing:
        existing = existing.rstrip() + f"\n\n{LOG_HEADING}\n\n"
    # Exactly one newline between rows, and never glued onto the previous
    # paragraph - the precise bug flip_log.py hit writing into its own table.
    body = existing.rstrip("\n") + "\n" + line + "\n"
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, path)
    return line


# --- the pipeline --------------------------------------------------------

def process_note(path, text, digest, dest, timeout_s=DEFAULT_TIMEOUT_S,
                 dry_run=False, verbose=False):
    """One note, end to end. -> (status, detail).

    Never raises for a per-note failure: one unusable note in a batch of ten
    must not stop the other nine, and a nightly unattended run has nobody to
    retry it by hand."""
    name = os.path.basename(path)
    if dry_run:
        return "dry-run", f"would process {name} ({len(text)} chars)"
    try:
        output = run_through_worker(build_task(name, text), timeout_s=timeout_s)
    except RuntimeError as e:
        return "timeout", str(e)
    except OSError as e:
        return "error", f"could not enqueue: {e}"

    sections = parse_sections(output)
    if not sections:
        # Deliberately NOT recorded as processed: an unusable answer means
        # this note should be retried on the next run, not skipped forever
        # because a free model was having a bad night.
        return "unusable", (output or "empty answer").strip()[:200]

    title = (sections.get("TITLE") or "").strip().strip('"') \
        or os.path.splitext(name)[0].replace("_", " ")
    body = build_body(sections, name)
    # First sentence of the model's own summary, not the whole paragraph:
    # the header wants one line saying what the note is.
    purpose = (sections.get("SUMMARY", "").strip().split(". ")[0].strip()
               or f"Processed study note from {name}.")
    if not purpose.endswith("."):
        purpose += "."
    try:
        note_path, _ = vault_write.write_note(
            dest, title[:70], body, purpose=purpose,
            related=[f"[[{dest}/README|{dest.split('/')[-1]}]]",
                     "[[04_Agents/Study_Teacher|Study Teacher]]"])
    except (ValueError, OSError) as e:
        return "write-failed", str(e)

    concepts = sum(1 for ln in sections.get("CONCEPTS", "").splitlines()
                   if ln.strip().startswith("-")
                   and "none in these notes" not in ln)
    cards = sum(sections.get("FLASHCARDS", "").upper().count(p)
                for p in CARD_PREFIXES)
    try:
        append_study_log(name, note_path, concepts, cards)
    except OSError as e:
        # The note itself is written and is the thing that matters; a failed
        # log line is worth reporting, not worth discarding the note over.
        print(f"[!] study log not updated for {name}: {e}", file=sys.stderr)
    return "ok", os.path.relpath(note_path, VAULT)


def run(source=DEFAULT_SOURCE, dest=DEFAULT_DEST, limit=DEFAULT_LIMIT,
        timeout_s=DEFAULT_TIMEOUT_S, dry_run=False, do_pull=False,
        force=None, verbose=False):
    # Validated before any model call: a bad destination should cost nothing,
    # not surface after the worker has already spent a minute on the note.
    if dest not in vault_write.allowed_note_folders():
        print(f"[!] '{dest}' is not a vault write destination.\nAllowed:\n  "
              + "\n  ".join(vault_write.allowed_note_folders()), file=sys.stderr)
        return 1
    if not os.path.isdir(source):
        print(f"[!] study inbox does not exist: {source}", file=sys.stderr)
        return 1
    if do_pull:
        git_pull(source, verbose=verbose)

    state = load_state()
    pending = discover(source, state, force=force, verbose=verbose)
    if not pending:
        print("Keine neuen Study-Notizen.")
        return 0
    if limit and len(pending) > limit:
        print(f"[i] {len(pending)} neue Notizen, verarbeite {limit} "
              "(Rest beim naechsten Lauf)")
        pending = pending[:limit]

    counts = {}
    for path, text, digest in pending:
        name = os.path.basename(path)
        print(f"[*] {name}")
        status, detail = process_note(path, text, digest, dest,
                                      timeout_s=timeout_s, dry_run=dry_run,
                                      verbose=verbose)
        counts[status] = counts.get(status, 0) + 1
        if status == "ok":
            print(f"    ✓ {detail}")
            state[name] = {"digest": digest,
                           "processed": datetime.now().isoformat(timespec="seconds"),
                           "note": detail}
        elif status == "dry-run":
            print(f"    · {detail}")
        else:
            print(f"    ! {status}: {detail}", file=sys.stderr)
    if not dry_run:
        save_state(state)
    print("Fertig: " + ", ".join(f"{v}x {k}" for k, v in sorted(counts.items())))
    # Non-zero only if nothing at all succeeded and something was attempted -
    # a partial batch is a normal outcome worth reporting, not a unit failure
    # that systemd should flag red every time one note is thin.
    return 0 if (dry_run or counts.get("ok")) else 1


def show_status():
    state = load_state()
    if not state:
        print("Noch nichts ingestiert.")
        return 0
    print(f"{len(state)} Notiz(en) verarbeitet:")
    for name, meta in sorted(state.items(),
                             key=lambda kv: kv[1].get("processed", ""),
                             reverse=True)[:20]:
        print(f"  {meta.get('processed', '?')[:16]}  {name} -> {meta.get('note', '?')}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--inbox", default=DEFAULT_SOURCE,
                    help="folder holding raw notes (default: the "
                         "CyberSecurityLearning inbox)")
    ap.add_argument("--folder", default=DEFAULT_DEST,
                    help="vault destination for processed notes")
    ap.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                    help="max notes per run (0 = no limit)")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S,
                    help="seconds to wait for the worker per note")
    ap.add_argument("--git-pull", action="store_true",
                    help="git pull the inbox first, if it is its own repo")
    ap.add_argument("--force", nargs="*", metavar="NAME",
                    help="reprocess these filenames even if unchanged")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--status", action="store_true",
                    help="show what has been ingested and exit")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)

    if args.status:
        return show_status()
    return run(source=args.inbox, dest=args.folder, limit=args.limit,
               timeout_s=args.timeout, dry_run=args.dry_run,
               do_pull=args.git_pull, force=set(args.force or ()),
               verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
