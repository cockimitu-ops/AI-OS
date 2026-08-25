# 04_Agents

Purpose: Definitions of scoped AI roles — their allowed capabilities, required context, and where their authority ends.
Last Updated: 2026-08-11
Status: Active — 4 agents defined
Related Documents: [[Glossary]], [[03_Capabilities/README|03_Capabilities]], [[Future_Integration]]

---

## Responsibility
An agent definition states what a role is allowed to do: which capabilities/workflows it can call, what context it operates with by default, and where it must hand back to Felix rather than act alone. Agents are consumers of `03_Capabilities/`, not a place to redefine logic.

## Important: Execution Model Unchanged
This does not introduce automation. Every agent here is invoked manually, in chat — "as Research Analyst, do X" — per the standing decision in `Roadmap.md`. What changes is scope clarity, not who's running it: there is always exactly one executor.

## Contents
- [[Vault_Architect]] — maintains the AI OS itself
- [[Content_Producer]] — runs story production for SocialMediaContent
- [[Research_Analyst]] — runs QuickTurnaroundGigs fulfillment
- [[Business_Development]] — ContentAgency, TemplateSales, FundingApplications

## Status
4 agents defined, matching the 4 active work areas that actually need distinct scope. Not exhaustive — Personal, GetClean, and CyberSecurityLearning don't need a formal agent yet, since they're not workflow-driven the way the above are.
