# Naming Convention

Purpose: Naming rules for folders, files, and links across AI OS.
Last Updated: 2026-08-26
Status: Active
Stability: Core
Related Documents: [[Repository_Structure]], [[Development_Workflow]]

---

## Folders
- `Pascal_Case` (underscore-separated capitalized words).
- Top-level folders carry a two-digit numeric prefix for fixed ordering: `00_System`, `01_Architecture`, ... `99_Archive`.
- Subfolders below the top level do not carry numeric prefixes unless ordering matters within that folder specifically.
- Acronyms (e.g., `AI`) are kept as-is rather than forced into mixed case — see `02_Systems/AI/`. Ratified in [[ADR-0001_Naming_Disambiguation]].

### Two scoped exceptions — [[ADR-0006_Project_Folder_Naming]]
- **Project folders under `10_Projects/` use `PascalCase` without underscores** (`SocialMediaContent`, `QuickTurnaroundGigs`). A project name reads as one compound identifier, closer to a proper noun than a descriptive filename.
- **Product folders inside a project may use `kebab-case`** (`Micro-SaaS-Moat-Blueprint`), and a leading underscore marks tooling rather than product content (`_infra`). These names usually mirror a public artifact — a Gumroad slug, a URL, a file a buyer downloads — and rewriting them to match an internal rule breaks that correspondence for nothing.

Both are narrow by design: they cover `10_Projects/` and its contents, and are not a general licence to pick a style per folder.

## Files
- `Pascal_Case.md` — no spaces, no numeric prefixes unless the file is explicitly part of an ordered sequence (see ADR naming below).
- One file = one topic. If a file needs an "and" in its name, it's probably two files.

## Links
- Use Obsidian `[[wikilinks]]` for any reference to another file in the vault, not raw paths or Markdown link syntax, so the graph view and backlink search stay accurate.
- Link to the canonical file, not a duplicate. If you find yourself wanting to restate content instead of linking to it, that's a signal the content belongs in the linked file, not repeated here.
- Where a filename (like `README.md`) is not unique across the vault, link with a path from the vault root (e.g., `[[01_Architecture/README]]`) rather than a bare name.

## ADR Naming
`ADR-XXXX_Short_Title.md`, where `XXXX` is a zero-padded, sequential, never-reused four-digit ID (`ADR-0001`, `ADR-0002`, ...). See `ADR/README.md` for the full lifecycle. Confirmed in [[ADR-0001_Naming_Disambiguation]].

## Headers
Every major document opens with: Title, Purpose, Last Updated, Status, Related Documents. "Major" means anything in `00_System/`, `01_Architecture/`, or any definition file for a system, capability, agent, or workflow. A plain folder `README.md` uses a lighter version of the same header (Purpose, Last Updated, Status, Related Documents — title is implicit in the filename).

## Dates
`YYYY-MM-DD` everywhere. No relative dates ("last week") in committed documentation.
