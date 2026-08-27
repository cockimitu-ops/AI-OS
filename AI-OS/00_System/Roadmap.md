# Roadmap

Purpose: Sprint-level plan for building out AI OS.
Last Updated: 2026-08-26
Status: Active
Stability: Dynamic
Related Documents: [[Dashboard]], [[Changelog]], [[Development_Workflow]]

---

## Sprints 001–017 (complete)
Foundation through the MoneyMaking project and its research rounds. Full detail in `Changelog.md`.

## Sprint 018 — Project/Knowledge Separation (complete)
The biggest structural change since Sprint 001 — see [[ADR-0005_Project_Knowledge_Separation]]. Reusable knowledge/methodology stays in `02_Systems/`/`03_Capabilities/`; project-specific execution moved to `10_Projects/`. `Horror_Story_System`, `Reddit_Story_Workflow`, `AI_Video_Production`, `Story_Tracker`, produced stories, and both production workflow instances moved into new `10_Projects/SocialMediaContent/`. Three new active projects scaffolded from MoneyMaking's research: [[10_Projects/ContentAgency/README|ContentAgency]], [[10_Projects/TemplateSales/README|TemplateSales]], [[10_Projects/FundingApplications/README|FundingApplications]]. Full audit run before and after — caught and fixed two stale documents (Home.md, 00_System/README.md) along the way.

## Sprint 019 — Universe Support (dropped 2026-08-26, never started)
Was approved and queued for eleven sprints. Recurring monsters, locations, and organizations — Design Review Critical Item #3, confirmed relevant in Sprint 015.

**Dropped, not deferred again.** Its entire justification was written for a horror content brand, and that brand was archived in Sprint 027. Nothing in the vault currently needs recurring monsters or a shared mythology, and no story topic has been chosen that might. Kept on the Roadmap as an approved-but-unstarted sprint, it read as work being fallen behind on rather than work that stopped being relevant. See *Off the Table* below.

## Sprint 020 — QuickTurnaroundGigs (complete)
New project: fast, tactical client work (research/briefing gigs, real-time problem arbitrage) using the Perplexity-finds/Claude-executes pattern. [[10_Projects/TemplateSales/README|TemplateSales]] enriched with the overlapping digital-tools strategy rather than duplicated. Structure only, per explicit scope — see [[10_Projects/QuickTurnaroundGigs/README|QuickTurnaroundGigs]].

## Sprint 021 — Personal Project (complete)
First non-business project under `10_Projects/`: Reading List, Supplement Stack, Substance History. The last of these is explicitly the starting inventory for a future Get Clean project — discussed, not yet planned or scoped. Synced to Notion.

## Sprint 022 — Token Efficiency Pass (complete)
Trimmed boilerplate-heavy capability files, consolidated 4 near-duplicate integration docs into one, condensed Reddit_Story_Workflow to a stub, merged 3 review-cadence notes into [[Review_Cadences]]. 161 → 156 files, denser content.

## Sprint 023 — Fiverr Gig Build and Test (complete)
[[Research_And_Briefing_Gigs]] refocused on startup competitor analysis ($30/$80/$180). [[Fulfillment_Workflow]] rebuilt as a 6-step research process. Tested end-to-end against a mock company (Omni Shield) — validated the loop, surfaced the real finding that round-trip overhead, not thinking time, is the actual cost.

## Sprint 024 — Agents (complete)
`04_Agents/` populated for the first time since Sprint 001: [[Vault_Architect]], [[Content_Producer]], [[Research_Analyst]], [[Business_Development]], each with Scope/Allowed/Escalation. Execution model unchanged — manual, chat-triggered.

## Sprint 025 — MCP Server (complete, unverified)
Read-only MCP server exposing the vault via Notion (`search_vault`, `get_page`, `list_projects`, `get_project_status`), Docker-packaged. Delivered as a separate artifact, documented in `02_Systems/Automation/`. **Written without the ability to compile or run it — needs a real build check before being trusted.**

## Sprint 026 — Accuracy Pass (complete)
Fixed status drift: four files still described Agents and Automation as empty after both were built; this Roadmap itself was four sprints stale. Real lesson recorded below.

## Sprint 028 — Infrastructure and Products (complete, logged retroactively)
Two things happened between 2026-08-25 and 2026-08-26 that nothing in this file recorded until 2026-08-26.

**The vault got a runtime.** [[02_Systems/Automation/TaskRunner/README|TaskRunner]] — a headless Open Interpreter worker, a Telegram bridge, and a daily backup, as three systemd services. Tasks arrive from a shell command or a Telegram message and execute unattended with `auto_run=True`. See the note under *Decided* below for how this sits against the standing agents decision.

**[[10_Projects/TemplateSales/README|TemplateSales]] shipped three finished products** — Micro-SaaS Moat Blueprint ($29), Pricing Teardown ($29), Retention Engineering ($39), plus a $45 bundle. None are the "AI OS pattern" this Roadmap and that project both named as the first product; the strategy changed in execution and was never written down. Recorded, not silently accepted — see that project's README.

Also parked the same week: the Claude escalation tier and the whole [[03_Capabilities/AI-Bridge/README|AI-Bridge]] capability, both pending the same unresolved ToS question (below).

## Sprint 029 — Full Audit and Fix Pass (complete)
Read the whole repository — vault, TaskRunner, AI-Bridge, MCP server, server-stack, systemd units — and fixed what was actually broken. Eleven code/config defects (worker crash-loop, three write/read races, a backup-pruning path that could leave zero backups anywhere, a silent failure notifier that couldn't run, a TTY corrupting MCP stdio framing, an HTTP bridge binding to `0.0.0.0` with optional auth) and eleven status-drift defects. Full list in [[Changelog]] under 0.35.0-alpha. MCP server build verified for the first time since it was written in Sprint 025.

## Backlog — for review, not acted on
- Numeric threshold reconciliation (Reddit-specific numbers still in the shared capabilities' Success Criteria)
- A second story, so [[Series_Planning]] has a real pool
- Horror subgenre-specific knowledge (Rule Horror, Psychological Horror, etc.)
- Analytics Database scaling before volume makes it expensive
- "Generate Thumbnail Ideas" capability gap
- Define ContentAgency package tiers and pricing
- Decide what to package first in TemplateSales
- ~~Naming-convention inconsistency in `10_Projects/`~~ — **resolved 2026-08-26 via [[ADR-0006_Project_Folder_Naming]].** Rule amended, folders left alone: renaming ten project folders would put the vault's currently-perfect link integrity at risk to satisfy a rule nobody had been confused by.

## Decided
- **Agents:** manual, chat-triggered — confirmed. No separate infrastructure. Revisit only if usage limits or actual scale make it a real constraint.
  - **Scope clarified 2026-08-26.** This covers the four `04_Agents/` personas and still holds for them. It was never a vault-wide ban on infrastructure, and TaskRunner (Sprint 028) does not overturn it — TaskRunner is unattended execution infrastructure for a different purpose, not a persona given a runtime. Worth stating because `02_Systems/Automation/README.md` had been reading this line as vault-wide while hosting a live executor.

## Genuinely blocked — need a decision, not more building
- ~~**AI Video Production pillar status**~~ — **deferred by decision, 2026-08-26.** Not resolved, deliberately not resolved: the three TemplateSales products are built and ~20 minutes each from being live, and that is where the attention goes until they are. Same for choosing a new story topic. Both stay untouched rather than half-pursued; neither is blocking anything else.
- **Is the "AI OS pattern" still product #4?** TemplateSales built three other products instead. Either it comes back as the next product or it is dropped — right now it is neither.

*(The Claude-via-Pro ToS question moved to Off the Table on 2026-08-26 — decided, not still blocking.)*

## Off the Table
- **Funding** (InnoStartBonus, JUGEND GRÜNDET) — deliberately not pursued, by choice, not oversight (2026-08-13). Nothing here replaces its expected value; the tradeoff was made consciously.
- **Universe Support** (2026-08-26) — see Sprint 019 above. Scoped for a pillar that no longer exists. If a serialized-fiction topic is ever chosen, this comes back as a well-scoped sprint against that topic, not as a resumed backlog item.
- **Claude via the Pro subscription** (2026-08-26) — decided: both TaskRunner's escalation tier and [[03_Capabilities/AI-Bridge/README|AI-Bridge]] stay parked. The free Groq/Gemini chain is verified working and costs nothing; the ToS question is not worth resolving for capacity that isn't currently needed. Both are built and a flag away, so this reverses cheaply if the free tiers stop being enough. Reopening it means either accepting the risk explicitly or buying a metered `ANTHROPIC_API_KEY` — not rediscovering the question.

## Actual Next Steps (revised 2026-08-26)
See [[Income_Portfolio]] for the full reasoning. Step 2 below has changed materially since that file was written — the product exists now.
1. Fiverr gig live — thumbnail image is the only remaining step
2. **Publish Micro-SaaS Moat Blueprint** — Notion page + Gumroad listing + PNG cover export. ~20 minutes. It is built; nothing is blocking it but this. (Was "ship ONE template (the AI OS pattern)"; that product was never built, three others were.)
3. Make 3 short-form demos of it — still the step that decides whether it sells, and the capability already exists but has never been pointed at this
4. Then Pricing Teardown per `_infra/LAUNCH-ORDER.md`'s spacing, and a ContentAgency prospect list

## Sprint 027 — Horror Archived (complete)
Horror_Story_System, Horror_Story_Production, and Stories/ (The Doorbell Camera) moved to 99_Archive/HorrorProject/. Reasoning: research consistently found horror/entertainment doesn't monetize well as an audience; the production capability underneath it was never the problem. All 18 capabilities preserved unchanged - none were horror-specific in mechanism. Content_Producer agent rescoped to be genre-agnostic. Reddit_Story_Workflow is now the only defined story pillar; AI_Video_Production is the only pillar with real current activity. New story topic planned, not yet chosen.
