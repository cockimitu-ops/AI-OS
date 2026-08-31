# Automation

Purpose: Systems that run without a person actively driving each step.
Last Updated: 2026-08-31
Status: Active — Task Runner is three live systemd services on the server; MCP Server builds clean, Notion side untested
Related Documents: [[02_Systems/README|02_Systems]], [[Future_Integration]]

---

## Task Runner (added 2026-08-26)
The actual live automation: a headless worker (Open Interpreter) that executes tasks dropped into a queue, reachable via CLI or Telegram, plus a daily cloud backup. Previously ran as loose scripts at the repo root, outside the vault; moved into [[02_Systems/Automation/TaskRunner/README|TaskRunner/]] so the vault reflects what's actually running on the server. Full detail — file roles, systemd wiring, why `backups/` excludes itself from its own backup — in that folder's README.

## AI OS MCP Server
Read-only MCP server. Source now lives in the repo at `AI-OSmcp/` (sibling to this vault, alongside `server-stack/`) — it is no longer a separate zip. Exposes `search_vault`, `get_page`, `list_projects`, `get_project_status` — reads from Notion, not local files. Docker-packaged.

**Build verified 2026-08-26:** `npm install` resolves cleanly and `npm run build` compiles with zero TypeScript errors on Node 22. The long-standing "written blind, never compiled" caveat is closed.

**Still untested:** everything downstream of the build. No call has ever been made against a real Notion integration token, so whether `search_vault` returns anything useful depends on the integration actually having been shared with the AI OS pages — which is a Notion-side setup step, not a code question.

## Gemini Access (added 2026-08-13)
Two different paths, depending on surface:
- **Regular Gemini chat (web/app):** no custom MCP support there. Same approach as Perplexity — share the specific public Notion link when needed. Higher token cost per query than MCP, but it's what that surface supports.
- **Antigravity** (Google's dev tool, replaced Gemini CLI June 2026): supports local stdio MCP servers, same format as Claude Desktop. The existing `ai-os-mcp` server works here with **zero new code** — add an entry to `~/.gemini/config/mcp_config.json` pointing at the same built server. Build now verified (see above); the Notion-side setup is still the untested part.

## Relationship to the Standing Automation Decision
This section used to say "this is retrieval, not automation" and claim the whole folder stayed inside the no-automation boundary. That was written when the MCP server was the only thing here, and stopped being true the moment TaskRunner moved in above it. Stated straight instead:

- **The MCP server is retrieval.** Nothing runs unless a client calls a tool. Inside the boundary.
- **TaskRunner is automation.** It executes shell commands unattended, on a Telegram message, with `auto_run=True`. That is exactly "actions happening on their own." It is outside the boundary, deliberately.

The old [[Roadmap]] line ("Agents: manual, chat-triggered — no separate infrastructure") described the four `04_Agents/` personas as of mid-August. **It no longer holds:** since 2026-08-30 those personas run scheduled and routed through TaskRunner behind a daily approval gate (see `TaskRunner/README.md`). The decision was superseded by building the infrastructure, deliberately — not contradicted by accident. `04_Agents/README.md` reflects the current state; treat any doc still calling the agents "manual only" as stale.

## Status
Two real artifacts (TaskRunner, MCP server) plus one parked capability ([[03_Capabilities/AI-Bridge/README|AI-Bridge]]). n8n-based automation (for QuickTurnaroundGigs fulfillment, or TemplateSales's own product) discussed but not built — `AI-Bridge`'s `docker-compose.yml` already ships an n8n service, unused while that capability is parked.
