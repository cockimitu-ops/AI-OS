# Future Integration

Purpose: How every framework (Context Engine, Execution Engine, Template Framework, Workflow Framework) will connect to Capabilities, Agents, MCP, and Automation — documented once, since all four frameworks said nearly the same thing separately. Consolidated from four near-duplicate notes (Sprint 022) to cut redundant boilerplate.
Last Updated: 2026-08-07
Status: Active — forward-looking, non-binding
Related Documents: [[01_Architecture/README|01_Architecture]], [[Execution_Philosophy]], [[Context_Philosophy]], [[Workflow_Philosophy]], [[Template_Philosophy]]

---

## Capabilities (exists — `03_Capabilities/`)
Already compatible with all four frameworks: a capability's declared Inputs/Outputs map onto Task Specification; its Output may reference a Template as structural shape; every Workflow step IS a capability call; Context Resolution reads a capability's own declared Required Notes.

## Agents (not yet built — `04_Agents/`)
Will need to state which capabilities it can call, inheriting those capabilities' Required Notes as its minimum context. The frameworks define what an agent reads and how it executes once scoped — not what it's allowed to do; that's a separate, still-open decision.

## MCP (not yet built)
An MCP server exposing this vault would implement the Execution Lifecycle as its own request boundary — the stages already map onto typical tool-call boundaries without new design work.

## Automation (not yet built — `02_Systems/Automation/`)
An unattended trigger enters at the same point a manual one would, across every framework — no shortened or "automated" variant anywhere in this vault's design.

## Workflows (framework built — `05_Workflows/`)
A workflow runs the full Execution Lifecycle, and Context Resolution, once per capability in its chain — not once for the whole workflow. This keeps context bounded per step instead of accumulating. Operationalized in [[Workflow_Composition]].
