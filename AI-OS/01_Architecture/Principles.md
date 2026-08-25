# Principles

Purpose: The engineering principles every contribution to AI OS follows.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[Vision]], [[Architecture]], [[Naming_Convention]]

---

## Build systems, not pages
A file's existence should be justified by the role it plays in a system, capability, agent, or workflow — not because it seemed worth writing down at the time.

## Build capabilities, not collections
Group work by what it does, not by when it was created or what format it happens to be in. A folder of loosely related notes is a collection; a folder of things that compose into a capability is a system.

## Every concept exists exactly once
If the same idea is described in two places, one of them is wrong or redundant. Link to the canonical definition instead of restating it.

## Use atomic notes where appropriate
One idea per note when the idea is reusable or likely to be linked to independently. Not a rule to apply mechanically — a single document is still correct when its parts don't stand alone.

## Everything should be linkable
Prefer `[[wikilinks]]` over duplicating content. If something can't be usefully linked to, that's often a sign it's in the wrong place or too vague to be a real note yet.

## Every important decision should be documented
Structural or architectural decisions go through an ADR (`01_Architecture/ADR/`), not just an edit to the affected files. Implementation choices that don't change the architecture are recorded in the relevant document's own history via Git.

## Documentation is part of the product
A system, capability, or agent without a README or definition isn't done — it's unfinished, regardless of whether the underlying logic works.

## The vault should feel like software
Consistent structure, consistent naming, consistent headers. Optimize for someone (or something) that has never seen this vault before being able to navigate it correctly on the first try.
