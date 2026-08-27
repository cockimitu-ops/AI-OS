# 04_Agents

Purpose: Definitions of scoped AI roles — their allowed capabilities, required context, and where their authority ends.
Last Updated: 2026-08-11
Status: Active — 4 agents defined
Related Documents: [[Glossary]], [[03_Capabilities/README|03_Capabilities]], [[Future_Integration]]

---

## Responsibility
An agent definition states what a role is allowed to do: which capabilities/workflows it can call, what context it operates with by default, and where it must hand back to Felix rather than act alone. Agents are consumers of `03_Capabilities/`, not a place to redefine logic.

## Execution Model (updated 2026-08-27)
These were chat-only definitions from Sprint 024 until 2026-08-27 — four scoped roles that nothing could actually invoke. They are now selectable by [[02_Systems/Automation/TaskRunner/README|TaskRunner]]:

```bash
python3 dispatch_task.py --agent research "profile Acme Corp"
```
On Telegram, lead with an alias: `@research profile Acme Corp`. Send `agents` for the roster.

Each file now carries an **Executable Prompt** block between `<!-- AGENT_PROMPT_START -->` / `<!-- AGENT_PROMPT_END -->` markers — the same convention [[02_Systems/Automation/TaskRunner/System_Prompt|System_Prompt.md]] uses. The worker **appends** that block to its base prompt rather than replacing it, so selecting an agent narrows focus without stripping the destructive-action guardrail.

The prose above each block stays the human-facing scope definition and must not be allowed to disagree with the machine-facing one below it.

**This does not reverse the standing decision.** That decision (`Roadmap.md`) is about `04_Agents/` personas not needing *their own separate infrastructure* — and they still don't. They ride on TaskRunner, which already existed, and there is still exactly one executor.

## Contents
- [[Vault_Architect]] — maintains the AI OS itself
- [[Content_Producer]] — runs story production for SocialMediaContent
- [[Research_Analyst]] — runs QuickTurnaroundGigs fulfillment
- [[Business_Development]] — ContentAgency, TemplateSales, FundingApplications

## Status
4 agents defined, matching the 4 active work areas that actually need distinct scope. Not exhaustive — Personal, GetClean, and CyberSecurityLearning don't need a formal agent yet, since they're not workflow-driven the way the above are.
