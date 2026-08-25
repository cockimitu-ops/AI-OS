# Glossary

Purpose: Definitions of terms used consistently across AI OS.
Last Updated: 2026-08-03
Status: Active
Stability: Core
Related Documents: [[Principles]], [[Architecture]]

---

**AI OS**
This repository. An AI-native operating system that uses Obsidian as its interface, Markdown as its source of truth, and Git as its version history.

**System** (`02_Systems/`)
A broad operating domain (e.g., Content, Research, Analytics). Systems group related capabilities but don't do work themselves.

**Capability** (`03_Capabilities/`)
A single, named, reusable unit of work that a system exposes (e.g., "Hook Writing," "TTS Script Generation"). Capabilities are composed into workflows and used by agents.

**Agent** (`04_Agents/`)
A defined AI actor with a scope, a set of capabilities it can call, and constraints on what it's allowed to do.

**Workflow** (`05_Workflows/`)
A multi-step, repeatable process that composes capabilities (and sometimes agents) to produce a defined output.

**Context** (`07_Context/`)
Standing information fed into agents or workflows that isn't itself a capability — background, constraints, preferences.

**ADR (Architecture Decision Record)**
A short document recording a specific architectural decision: what was decided, why, and what alternatives were considered. See `01_Architecture/ADR/README.md`.

**MOC (Map of Content)**
A note whose job is to link to other notes rather than contain primary content. `Home.md` is the top-level MOC for this vault.

**Atomic note**
A note that contains exactly one idea, decision, or piece of content, so it can be linked to precisely instead of buried inside a larger document.

**Sprint**
A scoped unit of build work with a defined deliverable, tracked in `Roadmap.md` and recorded in `Changelog.md`.

**Source of truth**
The single authoritative location for a given piece of information. In AI OS, that's always a Markdown file — never a person's memory, a chat log, or a duplicate copy elsewhere in the vault.
