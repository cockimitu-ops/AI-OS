# Automation

Purpose: Systems that run without a person actively driving each step. First real content as of Sprint 025 — an MCP server exposing the AI OS to any MCP-compatible AI client.
Last Updated: 2026-08-13
Status: Active — one real artifact, not run/verified yet
Related Documents: [[02_Systems/README|02_Systems]], [[Future_Integration]]

---

## AI OS MCP Server
Read-only MCP server, source in `ai-os-mcp/` (delivered as a separate zip, not part of this vault's own file tree). Exposes `search_vault`, `get_page`, `list_projects`, `get_project_status` — reads from Notion, not local files. Docker-packaged.

**Honestly unverified:** written without network access to actually compile/test it. Code follows the current MCP SDK and Notion client APIs as known, but hasn't been run. Whoever runs it first should check the build succeeds before trusting it.

## Gemini Access (added 2026-08-13)
Two different paths, depending on surface:
- **Regular Gemini chat (web/app):** no custom MCP support there. Same approach as Perplexity — share the specific public Notion link when needed. Higher token cost per query than MCP, but it's what that surface supports.
- **Antigravity** (Google's dev tool, replaced Gemini CLI June 2026): supports local stdio MCP servers, same format as Claude Desktop. The existing `ai-os-mcp` server works here with **zero new code** — add an entry to `~/.gemini/config/mcp_config.json` pointing at the same built server. Still unverified/uncompiled, same caveat as above.

## Relationship to the Standing Automation Decision
This is retrieval, not automation — nothing runs unless an MCP client actively calls a tool. The "manual, chat-triggered, no automation" decision (see `Roadmap.md`) is about *actions happening on their own*, which this doesn't do. Read-only by design specifically to stay inside that boundary.

## Status
One real artifact. n8n-based automation (for QuickTurnaroundGigs fulfillment, or TemplateSales's own product) discussed but not built — would need a real decision to actually reverse the no-automation stance first, not drift into it.
