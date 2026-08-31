# Study Inbox

Purpose: Drop zone for raw, unprocessed study notes — lecture fragments, pasted excerpts, half-finished thoughts. `scripts/study_agent.py` reads from here.
Last Updated: 2026-08-31
Status: Active
Related Documents: [[10_Projects/CyberSecurityLearning/README|CyberSecurityLearning]], [[04_Agents/Study_Teacher|Study Teacher]], [[10_Projects/CyberSecurityLearning/Study_Log|Study Log]]

---

## How this works

Write anything here as `.md` or `.txt`. Messy is fine — fragments, shorthand and half sentences are what this is for. `study_agent.py` picks up new or changed files, hands each one to the Study Teacher agent, and files a processed note (summary, concepts, action items, flashcards) into `10_Projects/CyberSecurityLearning/`, logging it in [[Study_Log]].

**Your files are never touched.** Not moved, not rewritten, not deleted. The agent tracks what it has already seen by content hash in `TaskRunner/study/state.json`, so re-running is safe and editing a note makes it get processed again with the change.

This README is skipped (`README.md` is ignored by the scanner along with dotfiles).

## Running it

    cd /home/nost/AI-OS/AI-OS/02_Systems/Automation/TaskRunner
    python3 scripts/study_agent.py            # process what's new
    python3 scripts/study_agent.py --dry-run  # just show what it would do
    python3 scripts/study_agent.py --status   # what's been ingested so far

It also runs nightly on a systemd timer (`aios-study.timer`).

## The one rule the agent follows

It never adds a fact the notes do not contain. If a term is named but not defined, the processed note says so rather than filling in a definition from the model's own knowledge. For security coursework that matters: a subtly wrong definition on a flashcard gets memorised.
