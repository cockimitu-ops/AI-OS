# Architecture

Purpose: How AI OS is structured, layer by layer.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[Vision]], [[Repository_Structure]], [[Development_Workflow]]

---

## Layers

**Interface — Obsidian**
Renders the vault, provides linking, search, and graph view. Holds no independent state — everything Obsidian shows is derived from the Markdown files on disk. The vault must remain fully meaningful without Obsidian open.

**Source of Truth — Markdown**
Every system, capability, agent, workflow, decision, and piece of context is a `.md` file with one defined location. No information is authoritative unless it exists here.

**Version History — Git**
Every change to the repository is a commit. History is how the vault answers "why does this exist" and "what did we try before," in addition to what `01_Architecture/ADR/` records explicitly for structural decisions.

**Consumption — MCP servers and AI agents**
Future automated readers of this repository. They read the same files a human reads in Obsidian, which is why structure and naming have to be predictable rather than convenient-for-now.

## Structural Layers (folder-level)

| Layer | Folder | Role |
|---|---|---|
| Meta | `00_System/` | Navigation, status, history, vocabulary |
| Governance | `01_Architecture/` | Vision, principles, structure, decisions |
| Runtime | `01_Architecture/Execution/` | Model-independent execution lifecycle (Sprint 005) |
| Standards | `01_Architecture/Templates/` | Model-independent document structure framework (Sprint 009) |
| Operation | `02_Systems/` | Reusable knowledge/methodology (Content, Research, Analytics, Automation, AI, Architecture) — no project execution as of [[ADR-0005_Project_Knowledge_Separation|ADR-0005]] |
| Execution | `10_Projects/` | Active initiatives — project-specific system docs, produced output, tracking |
| Reuse | `03_Capabilities/` | Named, composable units of work |
| Actors | `04_Agents/` | Defined AI agents and their scope |
| Composition | `05_Workflows/` | Multi-step processes built from capabilities and agents |
| Support | `06_Assets/` | Non-Markdown files referenced by the vault |
| Grounding / Retrieval | `07_Context/` | Standing context fed to agents and workflows, plus the Context Engine (Sprint 004) |
| Output | `08_Research/`, `09_Analytics/` | Content the systems produce |
| Time-bound | `10_Projects/` | Initiatives with a defined end |
| History | `99_Archive/` | Superseded material, kept not deleted |

## Design Constraints
- No folder duplicates another folder's responsibility. Where two folders look similar (see `Suggestions.md`), the distinction must be documented, not assumed.
- Every folder is self-describing via its own `README.md`.
- The structure must not need to change shape to accommodate scale — only to accumulate files within it.

## See Also
[[Repository_Structure]] for the literal folder tree and file inventory.
