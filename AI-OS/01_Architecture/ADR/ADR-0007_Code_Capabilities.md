# ADR-0007: Code Capabilities in 03_Capabilities

Status: Accepted
Date: 2026-08-27
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[ADR-0001_Naming_Disambiguation]], [[ADR-0006_Project_Folder_Naming]], [[02_Systems/Automation/README|Automation]]

---

## Context
`03_Capabilities/` holds seventeen Markdown specifications — `Hook_Writing.md`, `TTS_Optimization.md`, and so on. Each describes a unit of work in prose; none of them execute.

`03_Capabilities/AI-Bridge/` is different in kind. It is a running Node service: `bridge.mjs`, `server.mjs`, a Dockerfile, a compose file shipping an n8n container. It has a deploy story, a security posture, and an unresolved ToS question. It is currently parked.

Nothing in the folder distinguished the two. `03_Capabilities/README.md` did not mention AI-Bridge at all until Sprint 029 — an omission that survived because a reader scanning the folder has no way to tell that one entry is a service and sixteen are documents. The question this raises fairly is whether AI-Bridge is simply in the wrong folder.

## Decision
**AI-Bridge stays in `03_Capabilities/`. Add a `Kind:` header to distinguish the two sorts of capability.**

- `Kind: Spec` — a Markdown description of a unit of work. The default; the seventeen existing capabilities are all this, and are not retrofitted (see Consequences).
- `Kind: Service` — runnable code with a deploy story. Declared explicitly, because this is the case that surprises a reader.

A capability is "something the vault can do." Whether that thing is realised as a prompt-shaped document or as a container is an implementation detail of the capability, not a different category of thing. The folder is correctly named for both.

## Alternatives Considered
- **Move it to `02_Systems/Automation/`, beside TaskRunner.** The most tempting option, and rejected on the same evidence [[ADR-0006_Project_Folder_Naming]] used. Four path-based wikilinks (`[[03_Capabilities/AI-Bridge/README|AI-Bridge]]`) would break, and `Changelog.md` references the path in five places — a file this vault treats as append-only and never rewrites, so those references would become permanently wrong rather than merely stale. Against that: AI-Bridge is parked, so the move buys no operational benefit at all. Churn with a real cost and no upside.
- **Move it out of the vault entirely,** beside `AI-OSmcp/` and `server-stack/`. Coherent — that is where the other deployable code lives — but it is a bigger structural claim than the problem justifies, and it would strand the capability's documentation away from every other capability.
- **Leave it undocumented.** This is what produced the Sprint 029 omission. Rejected for the same reason ADR-0006 rejected it: a structure whose own index cannot describe it teaches readers the index is unreliable.

## Consequences
- A reader scanning `03_Capabilities/` can tell at a glance which entry will start a container.
- **The seventeen Spec capabilities are deliberately not retrofitted.** `Kind: Spec` is the default and adding it to seventeen files that are already unambiguous is churn of exactly the sort ADR-0006 declined. Add the header when a file is touched for another reason, or when a second Service capability makes the distinction load-bearing.
- If a second Service capability appears, this rule already covers it — no new ADR needed.
- The placement question is settled, so a future session finds an answer here instead of relitigating it. That is the actual deliverable: AI-Bridge's location has now been questioned twice.
