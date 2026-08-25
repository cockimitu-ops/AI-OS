# AI OS

## Status
Version: 0.1.0-alpha
Current Sprint: Sprint 001 — Repository Foundation
Last Updated: 2026-08-03

## Vision
AI OS is a system for organizing, operating, and scaling AI-assisted work — content production, research, automation, and analysis — as a single coherent repository rather than a collection of disconnected notes and tools. It is built to be read by both humans and machines: a person navigating in Obsidian and an AI agent or MCP server reading the same Markdown files should arrive at the same understanding.

## Mission
Provide a durable, version-controlled, machine-readable foundation for AI-native work:
- A single source of truth for how systems, capabilities, agents, and workflows are defined.
- A structure that scales from a handful of files to thousands without requiring a redesign.
- A repository that documents its own architecture and decisions as it grows.

## Architecture
Obsidian is the interface layer only — it renders and links the files but holds no state of its own.
Markdown is the source of truth — every concept, decision, and piece of context is a `.md` file with a defined location and purpose.
Git is the version history — every change to the repository is tracked, attributable, and reversible.
Future MCP servers and AI agents are consumers — they read this repository directly, so its structure and naming must be predictable and stable.

See [[Architecture]] for the full breakdown.

## Repository Philosophy
- Build systems, not pages.
- Build capabilities, not collections.
- Every concept exists exactly once.
- Prefer modularity and linking over duplication.
- Every folder has one clear responsibility.
- Documentation is part of the product, not an afterthought.

See [[Principles]] for the complete set of engineering principles.

## Folder Structure

```
AI-OS/
├── 00_System/          Entry points, dashboards, roadmap, changelog, glossary
├── 01_Architecture/    Vision, principles, architecture, conventions, ADRs
├── 02_Systems/         Operating systems: Content, Research, Analytics, Automation, AI, Architecture
├── 03_Capabilities/    Reusable, named capabilities the systems expose
├── 04_Agents/          AI agent definitions and configurations
├── 05_Workflows/       Multi-step processes that compose capabilities and agents
├── 06_Assets/          Shared non-Markdown assets referenced by the vault
├── 07_Context/         Standing context fed to agents and workflows
├── 08_Research/        Research notes and findings
├── 09_Analytics/       Metrics, reports, and performance tracking
├── 10_Projects/        Time-bound initiatives with a defined end state
└── 99_Archive/         Deprecated or superseded material, kept for history
```

Each folder contains its own `README.md` describing its responsibility in detail. See [[Repository_Structure]] for the authoritative version of this map.

## Development Workflow
Architecture is owned by the Chief Systems Architect. Implementation is owned by the Lead Repository Engineer. Changes to structure or conventions are proposed as suggestions, not applied unilaterally — see [[Development_Workflow]] and `Suggestions.md`. Formal architectural decisions are recorded as ADRs under `01_Architecture/ADR/`.

## Current Version
`0.1.0-alpha`

## Current Sprint
**Sprint 001 — Repository Foundation.** Establishes the folder structure, the core system documents, and the architecture documentation set. No capabilities, agents, or workflows are implemented yet.

## Related Documents
- [[Vision]]
- [[Principles]]
- [[Architecture]]
- [[Repository_Structure]]
- [[Development_Workflow]]
- [[Roadmap]]
