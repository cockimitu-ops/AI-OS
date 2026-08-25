# 01_Architecture

Purpose: Governance layer — why the vault is shaped the way it is, and the record of decisions that shaped it.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[README|AI OS README]], [[00_System/README|00_System]]

---

## Responsibility
This folder holds the vault's own self-description: vision, principles, structure, naming, workflow, and the formal decision record (ADRs). It does not hold content produced by the systems the vault supports — that's `02_Systems/` onward.

## Contents
- `Vision.md` — why AI OS exists
- `Principles.md` — engineering principles that apply to every contribution
- `Architecture.md` — the layered structure of the vault
- `Repository_Structure.md` — the current, authoritative folder/file map
- `Naming_Convention.md` — naming rules for folders, files, and links
- `Development_Workflow.md` — roles, sprint cycle, and how change is proposed
- `ADR/` — Architecture Decision Records (four accepted: naming, git workflow, engine placement, template placement)
- `Execution/` — the Execution Engine: model-independent runtime lifecycle (Sprint 005)
- `Templates/` — the Template Framework: model-independent document structure (Sprint 009)

## Ownership
Everything in this folder is owned by the Chief Systems Architect. The Lead Repository Engineer implements what's documented here and proposes changes via `Suggestions.md`, not by editing these files directly.
