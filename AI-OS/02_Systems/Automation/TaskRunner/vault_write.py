#!/usr/bin/env python3
"""Structured write-back into the vault.

The gap this closes: 09_Analytics has held four database files with zero rows
since Sprint 012, and Promotion_Candidates has been empty just as long. The
Learning Loop in 02_Systems/Analytics/ is fully specified and nothing has ever
executed it, because the worker had no defined way to *produce* into the vault -
only to read it.

This does not grant a new capability. The worker runs with auto_run=True and a
shell; it could already write anywhere. What it lacked was a path that gets the
vault's own conventions right, and a boundary that keeps generated output away
from the files the vault depends on. Specifically:

- **Allowlist, not arbitrary paths.** A model improvising a destination lands
  notes in 00_System/ or overwrites Dashboard.md. Only the folders that exist to
  receive output are writable here.
- **Never overwrite.** Every write either creates a new file or appends a row.
  There is no code path in this module that replaces existing content.
- **Correct headers.** Naming_Convention.md requires Purpose/Last Updated/
  Status/Related Documents on every note, and a small model will not reliably
  produce that. It is generated here instead of prompted for.

CLI rather than an importable API, because the worker is a weak model driving a
shell - a subprocess call it can copy is far more reliable than an import it has
to get right:

    vault_write.py note --folder 08_Research --title "Groq Rate Limits" --body-file /tmp/b.md
    vault_write.py row  --file 09_Analytics/Hook_Database.md --cells "2026-08-27|Cold open|8.2s|Worked"
    vault_write.py destinations
"""
import argparse
import os
import re
import sys

VAULT = "/home/nost/AI-OS/AI-OS"

# Folders that exist to receive generated content. Everything else in the vault
# is either hand-maintained structure or append-only history.
NOTE_FOLDERS = {
    "08_Research": "Research notes and findings.",
    "09_Analytics": "Real metrics and reports about completed work.",
    "06_Assets": "Non-Markdown assets (rarely the right destination for a note).",
}
# Project folders are resolved dynamically - they change, and hardcoding them
# would rot the same way Repository_Structure.md did.
PROJECTS_ROOT = "10_Projects"

ROW_FILES = {
    "09_Analytics/Hook_Database.md",
    "09_Analytics/Ending_Database.md",
    "09_Analytics/Retention_Database.md",
    "09_Analytics/Promotion_Candidates.md",
}

TITLE_RE = re.compile(r"[^A-Za-z0-9]+")

# Open Interpreter instruments every shell command with progress markers -
# `echo "##active_line5##"` and `##end_of_execution##`. When the worker writes a
# body via a heredoc, those markers land *inside* the file. Caught by the first
# real end-to-end write, which produced a note whose Purpose: line was
# `echo "##active_line2##"`. Stripped here rather than prompted against, because
# this is the runtime's artifact and no amount of instruction reliably prevents
# it - the model never sees the injected lines.
NOISE_LINE_RE = re.compile(
    r"^\s*(?:echo\s+[\"\']?)?##(?:active_line\d*|end_of_execution)##[\"\']?\s*$")
NOISE_INLINE_RE = re.compile(r"##(?:active_line\d*|end_of_execution)##")


def _clean(text):
    """Remove Open Interpreter's execution markers from generated content."""
    if not text:
        return ""
    kept = [ln for ln in text.splitlines() if not NOISE_LINE_RE.match(ln)]
    cleaned = NOISE_INLINE_RE.sub("", "\n".join(kept))
    # Collapse the blank runs the removals leave behind.
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def _today():
    import time
    return time.strftime("%Y-%m-%d")


def _projects():
    root = os.path.join(VAULT, PROJECTS_ROOT)
    if not os.path.isdir(root):
        return []
    return sorted(
        f"{PROJECTS_ROOT}/{d}" for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and not d.startswith((".", "_"))
    )


def allowed_note_folders():
    return sorted(NOTE_FOLDERS) + _projects()


def _resolve(rel, allowed):
    """Resolve a vault-relative path, refusing anything outside the allowlist.

    realpath before the check, so `08_Research/../00_System` cannot slip
    through as a traversal."""
    rel = rel.strip().strip("/")
    full = os.path.realpath(os.path.join(VAULT, rel))
    if not full.startswith(os.path.realpath(VAULT) + os.sep):
        raise ValueError(f"refuses to write outside the vault: {rel}")
    if rel not in allowed:
        raise ValueError(
            f"'{rel}' is not a write destination.\nAllowed:\n  "
            + "\n  ".join(allowed))
    return full


def _filename(title):
    """Pascal_Case per Naming_Convention.md - a small model will not do this
    reliably, so it is derived rather than asked for."""
    parts = [p for p in TITLE_RE.split(title) if p]
    if not parts:
        raise ValueError("title produced no usable filename")
    return "_".join(p[:1].upper() + p[1:] for p in parts)[:80] + ".md"


def _first_sentence_for_purpose(body):
    """The Purpose: line needs one prose sentence, not the body's literal first
    line. Found live: a worker-written note started its body with "## Context",
    and that heading landed as Purpose: verbatim - a markdown header is not a
    sentence, and the worker has no reason to know Purpose: needs one.
    Skips heading lines, list markers, and blank lines to find the first real
    prose line instead."""
    for line in body.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.lstrip("#").strip() == "" or line.startswith("#"):
            continue  # a heading line, not prose
        if line.startswith(("-", "*", ">")):
            continue  # a list/quote marker line, not a standalone sentence
        return line[:160]
    return "Generated note."


def write_note(folder, title, body, status="Active", related=None, dry_run=False):
    body = _clean(body)
    if not body:
        raise ValueError("body is empty after stripping execution markers")
    target_dir = _resolve(folder, allowed_note_folders())
    name = _filename(title)
    path = os.path.join(target_dir, name)

    if os.path.exists(path):
        # Never overwrite. Suffix instead, so a repeated run is visibly a
        # second note rather than a silently destroyed first one.
        stem, ext = os.path.splitext(name)
        n = 2
        while os.path.exists(os.path.join(target_dir, f"{stem}_{n}{ext}")):
            n += 1
        name = f"{stem}_{n}{ext}"
        path = os.path.join(target_dir, name)

    rel_links = related or ["[[" + folder + "/README|" + folder + "]]"]
    purpose = _first_sentence_for_purpose(body)
    content = (
        f"# {title.strip()}\n\n"
        f"Purpose: {purpose}\n"
        f"Last Updated: {_today()}\n"
        f"Status: {status}\n"
        f"Related Documents: {', '.join(rel_links)}\n\n"
        f"---\n\n"
        f"{body.strip()}\n\n"
        f"---\n\n"
        f"*Written by TaskRunner on {_today()}. Generated content — review before "
        f"treating as established fact.*\n"
    )
    if dry_run:
        return path, content

    os.makedirs(target_dir, exist_ok=True)
    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)
    return path, content


def append_row(rel_file, cells, dry_run=False):
    """Append one row to an existing Markdown table.

    Appends to the end of the last table in the file rather than the end of the
    file, because these databases have prose sections after the table."""
    if rel_file.strip().strip("/") not in ROW_FILES:
        raise ValueError(
            f"'{rel_file}' is not a row destination.\nAllowed:\n  "
            + "\n  ".join(sorted(ROW_FILES)))
    path = _resolve(rel_file, ROW_FILES)
    if not os.path.exists(path):
        raise ValueError(f"{rel_file} does not exist")

    lines = open(path, encoding="utf-8").read().splitlines()
    last_row = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and line.strip().endswith("|"):
            last_row = i
    if last_row is None:
        raise ValueError(f"{rel_file} has no Markdown table to append to")

    cells = [_clean(c).replace("\n", " ") for c in cells]
    row = "| " + " | ".join(c.strip() for c in cells) + " |"
    expected = lines[last_row].count("|")
    if row.count("|") != expected:
        raise ValueError(
            f"row has {row.count('|') - 1} cells, table expects {expected - 1}\n"
            f"  table row: {lines[last_row]}\n  your row:  {row}")

    lines.insert(last_row + 1, row)
    if dry_run:
        return path, row

    tmp = path + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    os.replace(tmp, path)
    return path, row


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    n = sub.add_parser("note", help="create a new note in an allowlisted folder")
    n.add_argument("--folder", required=True)
    n.add_argument("--title", required=True)
    n.add_argument("--body")
    n.add_argument("--body-file")
    n.add_argument("--status", default="Active")
    n.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("row", help="append a row to an Analytics table")
    r.add_argument("--file", required=True)
    r.add_argument("--cells", required=True,
                   help="pipe-separated, e.g. \"2026-08-27|Cold open|8.2s\"")
    r.add_argument("--dry-run", action="store_true")

    sub.add_parser("destinations", help="list every legal write target")

    a = ap.parse_args()

    if a.cmd == "destinations" or not a.cmd:
        print("Notes (vault_write.py note --folder X):")
        for f in allowed_note_folders():
            print(f"  {f}")
        print("\nTable rows (vault_write.py row --file X):")
        for f in sorted(ROW_FILES):
            print(f"  {f}")
        return 0

    try:
        if a.cmd == "note":
            body = a.body
            if a.body_file:
                body = open(a.body_file, encoding="utf-8").read()
            if not body or not body.strip():
                print("Error: --body or --body-file required, and non-empty.",
                      file=sys.stderr)
                return 2
            path, _ = write_note(a.folder, a.title, body, a.status,
                                 dry_run=a.dry_run)
            rel = os.path.relpath(path, VAULT)
            print(f"{'[dry-run] would write' if a.dry_run else 'Wrote'}: {rel}")
        elif a.cmd == "row":
            path, row = append_row(a.file, a.cells.split("|"), dry_run=a.dry_run)
            rel = os.path.relpath(path, VAULT)
            print(f"{'[dry-run] would append to' if a.dry_run else 'Appended to'}: {rel}")
            print(f"  {row}")
    except (ValueError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
