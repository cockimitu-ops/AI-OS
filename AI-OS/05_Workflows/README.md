# 05_Workflows

Purpose: Multi-step, repeatable processes composed from capabilities — the framework, not yet any actual production workflow.
Last Updated: 2026-08-03
Status: Active — Sprint 008
Related Documents: [[03_Capabilities/README|03_Capabilities]], [[04_Agents/README|04_Agents]]

---

## Responsibility
A workflow sequences existing capabilities into a defined, repeatable process with a start, an end, and a known output. Workflows don't introduce new logic — they compose logic that already exists in `03_Capabilities/`. See [[Workflow_Philosophy]] for the full boundary.

## Contents
- [[Workflow_Philosophy]] — why workflows are their own layer, distinct from capabilities/knowledge/agents
- [[Workflow_Structure]] — what a workflow definition actually contains
- [[Workflow_Lifecycle]] — Defined → Triggered → Step Executing → Validated → Finished
- [[Workflow_Composition]] — how steps chain without duplicating Context or Execution mechanics
- [[Workflow_Inputs_And_Outputs]] — how workflow-level I/O relates to step-level I/O
- [[Workflow_Validation]] — checking output at each step and at Finish
- [[Workflow_Error_Handling]] — retry / skip / abort, and routing failures to Failure Analysis
- [[Workflow_Review]] — the workflow-level entry point into `Review_Process`
- [[Workflow_Versioning]] — definitions change by new version, never by edit
- [[Future_Integration]] — how Capabilities, Agents, MCP, and Automation will plug in later (consolidated across all frameworks)

## Status
Framework complete (Sprint 008). Production workflow *instances* — [[Reddit_Story_Production]] and [[Horror_Story_Production]] — were built here Sprints 011/015, then moved to [[10_Projects/SocialMediaContent/README|10_Projects/SocialMediaContent]] in Sprint 018's project/knowledge separation ([[ADR-0005_Project_Knowledge_Separation]]): an instance is execution belonging to a specific project, not part of the shared framework. `Used By` on the framework notes themselves stays blank — a production workflow *uses* the framework, it isn't referenced by it, regardless of which folder it lives in.
