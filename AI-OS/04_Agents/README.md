# 04_Agents

Purpose: Definitions of scoped AI roles — their allowed capabilities, required context, and where their authority ends.
Last Updated: 2026-08-30
Status: Active — 4 agents defined; routed, scheduled, and self-directing behind a daily approval gate as of 2026-08-30
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

## Handoffs (added 2026-08-30)

Every agent ran in isolation per task until now — Research_Analyst could finish a competitor report with real pricing implications, and the only place that went was a log Felix might or might not read. An agent can now end its own output with one line, `<!-- handoff: Agent: reason -->`, and TaskRunner enqueues that output as a new task for the named agent automatically — the same directive convention as the incoming `<!-- agent: X -->` header, just emitted instead of consumed. Not a general orchestration framework: there's still exactly one executor, no agent calls another mid-task, and a chain is capped at 3 hops so two agents that keep handing off to each other can't loop forever even if both ignore their own escalation rules (a real risk with free models under load — see `System_Prompt.md`).

Wired into the two flows that are actually real right now: Research_Analyst → Business_Development when a finding has pricing/market implications beyond the current order, and Content_Producer → Business_Development for exactly the "pricing/packaging is out of scope" line that already existed here as prose and did nothing on its own. Vault_Architect and Business_Development don't emit handoffs — nothing in either's real scope hands off to another agent today, and this wasn't wired speculatively for a flow that doesn't exist yet.

## Routing and schedules (added 2026-08-30)

Two things changed about *when* an agent runs, on top of the handoffs above:

**You no longer have to name one.** A task with no `--agent`/`@alias` is routed: TaskRunner asks one model which specialist fits, using each agent's own `Purpose:` line as the catalog, and runs it under that role. An explicitly named agent always wins — routing only fills a gap. If routing fails for any reason, the task runs on the base prompt exactly as it did before, so this can't turn a working task into a broken one.

**Agents run on a schedule.** A Markdown file in `TaskRunner/schedules/` with a `<!-- schedule: weekly mon 08:00 -->` directive queues that task automatically, and its result is pushed to Telegram rather than left in a log. The first live one checks which TemplateSales products are still unpublished — chosen because Business_Development's own prompt names distribution, not inventory, as the bottleneck.

Implementation detail and the traps found while building it are in [[02_Systems/Automation/TaskRunner/README|TaskRunner's README]]; this is the framing.

## Self-direction, gated (added 2026-08-30)

The agents now plan on their own every day — and change nothing on their own. Two daily planners (Business_Development at 18:30, Vault_Architect at 18:45) write **proposals**; at 20:00 Felix gets one Telegram message listing them and replies `approve 1 3`. Only then does anything become a real task.

Proposals come in two kinds. **AI work** is what the worker can finish alone — drafting, research, editing the vault — and approving it queues a real task. **Needs you** is anything requiring an account, a payment, a publish button, a conversation, or a judgement call; approving it adds to Felix's list and never queues a task, because handing a worker "publish the Gumroad listing" produces either flailing or a false report of success. The planner prompts deliberately tell agents to think *bigger* in the human category — it is where a move worth real money belongs, not a chore trimmed to fit an hour. Approved human items resurface in the morning brief until Felix marks them done.

That gate is structural rather than a rule in a prompt: a proposing run can write to the proposals store and has no code path into the task queue at all. It is the same reasoning [[02_Systems/Automation/TaskRunner/External_Access_Plan|External_Access_Plan.md]] applied to sending email — a confirmation outside the model's own judgement, because an instruction to "ask first" is exactly what a small model under load drops.

Both planners are pointed at revenue, deliberately: Business_Development at the fact that three finished TemplateSales products have earned nothing because none are published, and Vault_Architect at whether a system change helps Felix earn sooner rather than whether it makes the vault tidier.

**This is also how agents schedule themselves.** Vault_Architect may propose new or changed files in `TaskRunner/schedules/`, so the system can change its own cadence — through the 20:00 review like anything else. Self-scheduling and the approval gate are one mechanism, not two.

## Contents
- [[Vault_Architect]] — maintains the AI OS itself
- [[Content_Producer]] — runs story production for SocialMediaContent
- [[Research_Analyst]] — runs QuickTurnaroundGigs fulfillment
- [[Business_Development]] — ContentAgency, TemplateSales, FundingApplications

## Status
4 agents defined, matching the 4 active work areas that actually need distinct scope. Not exhaustive — Personal, GetClean, and CyberSecurityLearning don't need a formal agent yet, since they're not workflow-driven the way the above are.
