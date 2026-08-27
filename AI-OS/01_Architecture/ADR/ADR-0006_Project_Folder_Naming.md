# ADR-0006: Project Folder Naming

Status: Accepted
Date: 2026-08-26
Related Documents: [[Naming_Convention]], [[ADR-0001_Naming_Disambiguation]], [[ADR-0005_Project_Knowledge_Separation]], [[Repository_Structure]]

---

## Context
[[Naming_Convention]] states that folders use `Pascal_Case` — underscore-separated capitalized words. Every project folder created since [[ADR-0005_Project_Knowledge_Separation]] introduced `10_Projects/` violates it: `SocialMediaContent`, `QuickTurnaroundGigs`, `TemplateSales`, `ContentAgency`, `FundingApplications`, `CyberSecurityLearning`, `LocalArbitrage`, `MoneyMaking`, `GetClean`, `Personal`. All ten are PascalCase without underscores.

This has been an open backlog item in [[Roadmap]] since Sprint 018 — "either amend the rule or rename the folders" — carried unresolved through eleven sprints. The product folders added under `10_Projects/TemplateSales/` in Sprint 028 introduced a *third* style on top of both (`Micro-SaaS-Moat-Blueprint`, `Pricing-Teardown`, `_infra`), which is what made this worth settling rather than carrying further.

## Decision
**Amend the rule; do not rename the folders.**

`Naming_Convention.md` gains two documented exceptions to `Pascal_Case`:

1. **Project folders under `10_Projects/` use `PascalCase` without underscores.** A project name is a single compound identifier, closer to a proper noun than to a descriptive filename.
2. **Product/deliverable folders inside a project may use `kebab-case`,** and a leading underscore (`_infra`) marks a folder holding tooling rather than product content. These names are frequently the same string as a public artifact — a Gumroad slug, a URL, a filename a buyer downloads — and rewriting them to match an internal convention would break that correspondence for no gain.

## Alternatives Considered
- **Rename all ten project folders to `Social_Media_Content` etc.** Rejected. It touches every wikilink pointing into `10_Projects/` — the vault's link integrity is currently perfect (zero dead links across 218 files) and this would put all of it at risk to satisfy a rule no reader has been confused by. It would also rename `_infra`'s product folders away from the slugs they deliberately mirror.
- **Leave it undocumented.** Rejected — that is the status quo, and the status quo is an eleven-sprint-old backlog item plus a convention document that contradicts the actual tree. A rule the repository visibly does not follow teaches future readers that the conventions are decorative.
- **Stretch [[ADR-0001_Naming_Disambiguation]]'s acronym exception to cover this.** Rejected. That ADR is specifically about acronyms (`AI`); this is a different question, and quietly widening an old decision to cover a new case is exactly what ADR-0004 declined to do in the analogous situation.

## Consequences
- `Naming_Convention.md` now matches the tree. The Sprint 018 backlog item is closed.
- Three folder-naming styles coexist, each with a stated scope: `Pascal_Case` everywhere structural, `PascalCase` for projects, `kebab-case` for products inside a project.
- New projects follow the project style without needing to ask. New products follow their public slug.
- The precedent is narrow on purpose: it covers `10_Projects/` and what lives inside it. It is not a general licence to invent a naming style per folder.
