# Future Integration

Purpose: How every framework (Context Engine, Execution Engine, Template Framework, Workflow Framework) will connect to Capabilities, Agents, MCP, and Automation — documented once, since all four frameworks said nearly the same thing separately. Consolidated from four near-duplicate notes (Sprint 022) to cut redundant boilerplate.
Last Updated: 2026-08-07
Status: Active — forward-looking, non-binding
Related Documents: [[01_Architecture/README|01_Architecture]], [[Execution_Philosophy]], [[Context_Philosophy]], [[Workflow_Philosophy]], [[Template_Philosophy]]

---

## Capabilities (exists — `03_Capabilities/`)
Already compatible with all four frameworks: a capability's declared Inputs/Outputs map onto Task Specification; its Output may reference a Template as structural shape; every Workflow step IS a capability call; Context Resolution reads a capability's own declared Required Notes.

## Agents (built — `04_Agents/`)
Each agent states which capabilities it can call, inheriting those capabilities' Required Notes as its minimum context. The frameworks define what an agent reads and how it executes. Since 2026-08-30 the 5 agents run scheduled/routed via TaskRunner behind a daily approval gate — see `02_Systems/Automation/TaskRunner/`.

## MCP (built, read-only — `AI-OSmcp/`)
A read-only Notion-backed MCP server exists; its build is verified but its Notion side has never been exercised in production. It implements the Execution Lifecycle as its own request boundary — the stages map onto tool-call boundaries without new design work.

## Automation (built — `02_Systems/Automation/`)
The TaskRunner runs unattended (~11 systemd units) since 2026-08-26. An unattended trigger enters at the same point a manual one would, across every framework — no shortened or "automated" variant anywhere in this vault's design.

## Workflows (framework built — `05_Workflows/`)
A workflow runs the full Execution Lifecycle, and Context Resolution, once per capability in its chain — not once for the whole workflow. This keeps context bounded per step instead of accumulating. Operationalized in [[Workflow_Composition]].
