# AI-OS MCP Server

One endpoint that any MCP-capable AI client, on any of Felix's devices, can
point at to see and use the live AI-OS.

Runs as `aios-mcp.service` on `http://100.64.2.100:8788/` — the Tailscale IP,
never `0.0.0.0`. Same bearer token as the web client.

## Connecting a client

Anything on the tailnet needs only a URL and the token. For Claude Code:

```bash
claude mcp add --transport http ai-os http://100.64.2.100:8788/ \
  --header "Authorization: Bearer $AIOS_WEB_TOKEN"
```

For clients configured by JSON file, the shape is the same: an HTTP/streamable
transport, that URL, and an `Authorization: Bearer …` header. No Docker, no
repo checkout, no per-device install — that was the whole point of moving off
stdio.

## Tools

| Tool | What it answers |
|---|---|
| `aios_today` | What Felix should do next, plus live counts. Start here. |
| `aios_money_board` | Full ordered revenue list, gating steps first |
| `aios_search_vault` | Keyword search across the live vault Markdown |
| `aios_get_page` | One page's full content, by path or bare name |
| `aios_dmarc_leads` | Qualified leads with findings, city, phone |
| `aios_flip_log` | LocalArbitrage buys/sells and €/hour |
| `aios_dispatch_task` | Queue real work on the worker — **off by default** |

## Read-only by default

`aios_dispatch_task` is only registered when `AIOS_MCP_ALLOW_DISPATCH=true`.
An MCP client that can queue work on the worker — which runs with a shell —
is a different risk from one that can read notes, and that should be a
decision rather than a default. Same explicit-opt-in pattern
`OPENROUTER_PAID_ENABLED` uses for the paid model tier.

To enable: add `AIOS_MCP_ALLOW_DISPATCH=true` to `/home/nost/AI-OS/.env` and
`sudo systemctl restart aios-mcp`.

## Why it was rewritten (2026-09-01)

The first version spoke **stdio** and read **Notion**. Both were wrong for
what this is for.

- **stdio means one device.** The transport requires the client to launch the
  server as a subprocess on the same machine, so "connect all my AIs on all my
  devices" would have meant Docker plus this repo on every one of them, and
  would still never have worked from a phone. Streamable HTTP makes it a
  service: one URL, reachable from anything on the tailnet.
- **Notion is a copy.** Everything that matters now — the money board, the
  mailable DMARC leads, the flip log, study notes, proposals, the spend ledger
  — lives in files on this server and was never synced to Notion. A server
  answering from Notion would have confidently described a system that no
  longer exists.

## It is a front door, not a second brain

AI-OS already has three front doors — `dispatch_task.py` (CLI),
`telegram_bridge.py` (phone), `webapp/` (browser) — and all of them go through
the same handlers in `webapp/api.py`. This is the fourth, and it calls that
same HTTP API rather than reimplementing anything. If a number looks wrong
here, the bug is in `api.py` and every front door has it.

That also means this server needs `aios-webapp.service` running; systemd
enforces it with `Requires=`.

## Verified 2026-09-01

Live against the running service, not assumed: unauthenticated request
rejected with 401; MCP `initialize` handshake returns protocol 2025-06-18;
`tools/list` returns the six read tools; `aios_today` and `aios_search_vault`
return real current data; `aios_dispatch_task` refuses while read-only.

One bug the live test caught: the API base defaulted to `127.0.0.1`, but
`server.py` binds only to the Tailscale IP and deliberately never to loopback,
so every tool call failed with a bare `fetch failed`. The default now mirrors
the web server's own.
