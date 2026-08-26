# Architecture Decision Records (ADR)

Purpose: Format and lifecycle for recording architectural decisions in AI OS.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[Development_Workflow]], [[Naming_Convention]]

---

## Purpose
An ADR records one architectural decision: what was decided, the context that led to it, the alternatives considered, and why the chosen option won. It exists so that a decision doesn't have to be re-litigated or re-explained every time someone (human or agent) encounters its consequences elsewhere in the vault.

## When to Write One
Any change to `01_Architecture/Repository_Structure.md` or `01_Architecture/Naming_Convention.md` — new top-level folders, renamed responsibilities, changed naming rules — gets an ADR. Content added within the existing structure does not.

## Format
Each ADR is a single file: `ADR-XXXX_Short_Title.md`

```
# ADR-XXXX: Title

Status: Proposed | Accepted | Superseded by ADR-YYYY
Date: YYYY-MM-DD
Related Documents: [[...]]

## Context
What situation or problem led to this decision.

## Decision
What was decided, stated plainly.

## Alternatives Considered
What else was on the table, and why it wasn't chosen.

## Consequences
What this decision makes easier, harder, or requires elsewhere in the vault.
```

## Lifecycle
1. **Proposed** — drafted, not yet acted on.
2. **Accepted** — approved; affected documents are updated to reflect it.
3. **Superseded** — a later ADR replaces this decision. The old ADR stays in place with its status updated and a link to the one that superseded it; ADRs are never deleted or rewritten.

## Naming
`ADR-XXXX_Short_Title.md` — a zero-padded, sequential, never-reused four-digit ID followed by a short Pascal_Case title. IDs are assigned in the order ADRs are proposed, not accepted, so a rejected ADR still permanently consumes its number.

## Current Records

| ID | Title | Status |
|---|---|---|
| [[ADR-0001_Naming_Disambiguation]] | Naming Disambiguation for 02_Systems Subfolders and Acronym Folder Names | Accepted |
| [[ADR-0002_Git_Workflow_Conventions]] | Git Workflow Conventions | Accepted |
| [[ADR-0003_Execution_Engine_Placement]] | Placement of Cross-Cutting Engine Subsystems | Accepted |
| [[ADR-0004_Template_Framework_Placement]] | Generalizing Cross-Cutting Subsystem Placement to Include Format/Documentation Standards | Accepted |
| [[ADR-0005_Project_Knowledge_Separation]] | Project/Knowledge Separation for Multi-Project, Token-Conscious Organization | Accepted |
| [[ADR-0006_Project_Folder_Naming]] | Project Folder Naming — two scoped exceptions to Pascal_Case | Accepted |
