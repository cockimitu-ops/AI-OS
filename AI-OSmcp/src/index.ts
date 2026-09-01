#!/usr/bin/env node
/**
 * AI-OS MCP server — one endpoint every AI client on every device can reach.
 *
 * WHAT CHANGED AND WHY (rewritten 2026-09-01)
 *
 * The first version of this file spoke stdio and read Notion. Both were wrong
 * for what it is actually for.
 *
 *   stdio means one device. The transport requires the MCP client to launch
 *   this as a subprocess on the same machine, so "connect all my AIs on all
 *   my devices" would have meant installing Docker and this repo on every one
 *   of them, and would still never work from a phone. Streamable HTTP makes
 *   it a service: one URL, reachable from anything on the tailnet.
 *
 *   Notion is a copy. Everything that actually matters now - the money board,
 *   1016 mailable DMARC leads, the flip log, study notes, proposals, the spend
 *   ledger - lives in files on this server and was never synced to Notion at
 *   all. A server answering from Notion would confidently describe a system
 *   that no longer exists. It now reads the live system.
 *
 * It is a THIN FRONT DOOR, not a second brain. AI-OS already has three front
 * doors - dispatch_task.py (CLI), telegram_bridge.py (phone), webapp/ (browser)
 * - and all of them go through the same handlers in webapp/api.py. This is the
 * fourth, and it calls that same HTTP API on localhost rather than
 * reimplementing any of it. If a number looks wrong here, the bug is in api.py
 * and every front door has it.
 *
 * SECURITY
 *   - Binds to the Tailscale IP only, never 0.0.0.0. Same boundary as the web
 *     client: the tailnet is the real perimeter.
 *   - Requires the same bearer token the web client uses.
 *   - Read-only by default. dispatch_task is only registered when
 *     AIOS_MCP_ALLOW_DISPATCH=true - the same explicit-opt-in pattern
 *     OPENROUTER_PAID_ENABLED already uses for the paid model tier. An MCP
 *     client that can queue work on Felix's worker is a different risk from
 *     one that can read his notes, and that should be a decision, not a
 *     default.
 */
import { randomUUID } from "node:crypto";
import { createServer } from "node:http";
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// The Tailscale IP, not 127.0.0.1. server.py binds to AIOS_WEB_BIND
// (default 100.64.2.100) and deliberately never to 0.0.0.0 or loopback, so a
// localhost default here fails with a bare "fetch failed" - which is exactly
// what the first live call did. Mirrors the web server's own default so the
// two cannot drift apart silently.
const AIOS_API =
  process.env.AIOS_API_BASE ||
  `http://${process.env.AIOS_WEB_BIND || "100.64.2.100"}:${process.env.AIOS_WEB_PORT || 8787}`;
const TOKEN = process.env.AIOS_WEB_TOKEN;
const BIND = process.env.AIOS_MCP_BIND || "100.64.2.100";
const PORT = Number(process.env.AIOS_MCP_PORT || 8788);
const ALLOW_DISPATCH =
  (process.env.AIOS_MCP_ALLOW_DISPATCH || "").toLowerCase() === "true";

if (!TOKEN) {
  console.error(
    "AIOS_WEB_TOKEN is required - this server authenticates to the AI-OS API " +
      "with the same token the web client uses."
  );
  process.exit(1);
}

/** Call the AI-OS HTTP API. Never throws a raw fetch error at a model: an MCP
 *  client shows tool errors to the user as-is, so a stack trace is worse than
 *  a sentence saying what failed. */
async function callApi(
  path: string,
  method: "GET" | "POST" = "GET",
  body?: unknown
): Promise<any> {
  const res = await fetch(`${AIOS_API}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      "Content-Type": "application/json",
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const text = await res.text();
  let data: any;
  try {
    data = JSON.parse(text);
  } catch {
    throw new Error(
      `AI-OS API returned non-JSON from ${path} (HTTP ${res.status}): ${text.slice(0, 200)}`
    );
  }
  if (!res.ok) {
    throw new Error(data?.error || `AI-OS API error on ${path} (HTTP ${res.status})`);
  }
  return data;
}

function text(value: unknown) {
  return {
    content: [
      {
        type: "text" as const,
        text: typeof value === "string" ? value : JSON.stringify(value, null, 2),
      },
    ],
  };
}

const READ_TOOLS = [
  {
    name: "aios_today",
    description:
      "The single most useful call: what Felix should do next to earn money, " +
      "plus live counts (letters sent, mailable DMARC leads, proposals " +
      "waiting, unprocessed study notes, open flips). Start here when asked " +
      "anything about his current situation.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "aios_money_board",
    description:
      "The full ordered list of revenue actions and who must do each. " +
      "Gating steps (legally required first) sort above higher-earning ones.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "aios_search_vault",
    description:
      "Keyword search across the AI-OS vault's Markdown notes (the live files, " +
      "not a Notion copy). Returns ranked pages with snippets. Use this before " +
      "answering anything about how Felix's systems, projects or decisions work.",
    inputSchema: {
      type: "object",
      properties: {
        query: { type: "string", description: "Keyword or phrase" },
        limit: { type: "number", description: "Max hits (default 20)" },
      },
      required: ["query"],
      additionalProperties: false,
    },
  },
  {
    name: "aios_get_page",
    description:
      "Full Markdown of one vault page, by vault-relative path " +
      "('07_Context/Knowledge_Core.md') or bare name ('Knowledge_Core').",
    inputSchema: {
      type: "object",
      properties: { page: { type: "string" } },
      required: ["page"],
      additionalProperties: false,
    },
  },
  {
    name: "aios_dmarc_leads",
    description:
      "Qualified DMARC prospecting leads - business name, domain, what is " +
      "wrong with their email security, city and phone.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "aios_phone",
    description:
      "Live state of Felix's rooted phone: battery, whether the screen is on, " +
      "the foreground app, and the notifications actually worth seeing " +
      "(system plumbing and media controls are filtered out). Returns " +
      "reachable:false rather than failing when the phone is off or away - " +
      "that is a normal state for a phone, not an error.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
  {
    name: "aios_flip_log",
    description: "The LocalArbitrage flip log: what was bought, sold, and net per hour.",
    inputSchema: { type: "object", properties: {}, additionalProperties: false },
  },
];

const DISPATCH_TOOL = {
  name: "aios_dispatch_task",
  description:
    "Queue a task for Felix's AI-OS worker to execute on his server, and wait " +
    "for the result. This RUNS on his machine with shell access - use it for " +
    "work he asked for, never to explore. Optionally name an agent " +
    "(Vault_Architect, Research_Analyst, Business_Development, Content_Producer, " +
    "Tech_Scout, Study_Teacher).",
  inputSchema: {
    type: "object",
    properties: {
      instruction: { type: "string", description: "What the worker should do" },
      agent: { type: "string", description: "Optional agent name" },
    },
    required: ["instruction"],
    additionalProperties: false,
  },
};

function buildServer(): Server {
  const server = new Server(
    { name: "ai-os", version: "2.0.0" },
    { capabilities: { tools: {} } }
  );

  server.setRequestHandler(ListToolsRequestSchema, async () => ({
    tools: ALLOW_DISPATCH ? [...READ_TOOLS, DISPATCH_TOOL] : READ_TOOLS,
  }));

  server.setRequestHandler(CallToolRequestSchema, async (req) => {
    const args = (req.params.arguments || {}) as Record<string, any>;
    try {
      switch (req.params.name) {
        case "aios_today":
          return text(await callApi("/api/today"));
        case "aios_money_board":
          return text(await callApi("/api/money-board"));
        case "aios_search_vault":
          return text(
            await callApi("/api/vault-search", "POST", {
              query: args.query,
              limit: args.limit,
            })
          );
        case "aios_get_page":
          return text(await callApi("/api/vault-page", "POST", { page: args.page }));
        case "aios_dmarc_leads":
          return text(await callApi("/api/dmarc-leads"));
        case "aios_phone":
          return text(await callApi("/api/phone"));
        case "aios_flip_log":
          return text(await callApi("/api/flip-log"));
        case "aios_dispatch_task": {
          if (!ALLOW_DISPATCH) {
            throw new Error(
              "Dispatch is disabled. Set AIOS_MCP_ALLOW_DISPATCH=true to enable it."
            );
          }
          // Its own thread namespace, like tg_ and web_ - so a task queued by
          // an MCP client is distinguishable on disk from one Felix typed.
          const result = await callApi("/api/chat", "POST", {
            message: args.instruction,
            thread_id: `mcp_${randomUUID().slice(0, 8)}`,
          });
          return text(result.reply || "(worker returned nothing)");
        }
        default:
          throw new Error(`Unknown tool: ${req.params.name}`);
      }
    } catch (err: any) {
      return {
        isError: true,
        content: [{ type: "text" as const, text: `AI-OS: ${err?.message || String(err)}` }],
      };
    }
  });

  return server;
}

// Stateless: a fresh Server and transport per request. This costs a few
// objects and buys immunity to the whole class of bugs where one client's
// session state leaks into another's - and there is no streaming or
// server-initiated message here that would need a persistent session.
const httpServer = createServer(async (req, res) => {
  if (req.headers.authorization !== `Bearer ${TOKEN}`) {
    res.writeHead(401, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "unauthorized" }));
    return;
  }
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true, dispatch: ALLOW_DISPATCH }));
    return;
  }
  try {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
    });
    res.on("close", () => transport.close());
    await buildServer().connect(transport);
    await transport.handleRequest(req, res);
  } catch (err: any) {
    console.error("MCP request failed:", err?.message || err);
    if (!res.headersSent) {
      res.writeHead(500, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "internal error" }));
    }
  }
});

httpServer.listen(PORT, BIND, () => {
  console.log(
    `AI-OS MCP server on http://${BIND}:${PORT}/  ` +
      `(dispatch ${ALLOW_DISPATCH ? "ENABLED" : "read-only"})`
  );
});
