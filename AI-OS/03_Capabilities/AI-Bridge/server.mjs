// server.mjs — macht die Bridge über HTTP erreichbar, damit n8n sie ansprechen kann.
//
// Endpunkte:
//   GET  /health                 -> Statuscheck
//   POST /ask                    -> { model: "claude"|"gemini", prompt, system? }
//   POST /v1/chat/completions    -> OpenAI-kompatibel (für n8n AI-Nodes)
//
// SICHERHEIT: Dieser Server gibt Zugriff auf dein Claude-Pro-Abo.
// Niemals öffentlich exposen. Nur 127.0.0.1 oder internes Docker-Netz.
// Anderen Leuten Zugang geben wäre Account-Sharing und verstößt gegen die Nutzungsbedingungen.

import { createServer } from "node:http";
import { askGemini, askClaude } from "./bridge.mjs";

const PORT = Number(process.env.PORT || 8080);
// Default auf Loopback, nicht 0.0.0.0. Dieser Server gibt unauthentifizierten
// Zugriff auf Claude weiter, sobald BRIDGE_TOKEN leer ist (siehe authorized()) -
// mit 0.0.0.0 als Default haette ein Start ausserhalb von Docker die Bridge
// sofort im ganzen WLAN offen gehabt. Im Container ist HOST=0.0.0.0 richtig und
// ungefaehrlich, weil docker-compose den Port auf 127.0.0.1 bindet; dort wird
// die Variable explizit gesetzt.
const HOST = process.env.HOST || "127.0.0.1";
const BRIDGE_TOKEN = process.env.BRIDGE_TOKEN || "";
const MAX_CLAUDE = Number(process.env.MAX_CONCURRENT_CLAUDE || 1);

/* ---------- Warnung bei Fehlkonfiguration ---------- */
if (process.env.ANTHROPIC_API_KEY) {
  console.warn(
    "WARNUNG: ANTHROPIC_API_KEY ist gesetzt. Claude Code rechnet dann über API-Tokens ab\n" +
      "         statt über dein Pro-Abo. Variable entfernen, wenn das nicht gewollt ist."
  );
}
if (!process.env.CLAUDE_CODE_OAUTH_TOKEN) {
  console.warn(
    "HINWEIS: CLAUDE_CODE_OAUTH_TOKEN fehlt. Im Container schlagen Claude-Aufrufe fehl.\n" +
      "         Auf dem Host 'claude setup-token' laufen lassen und den Token durchreichen."
  );
}

/* ---------- Semaphore: Claude-Aufrufe drosseln ---------- */
// Ohne Limit feuert n8n bei parallelen Workflows dutzende Claude-Prozesse
// gleichzeitig los und verbrennt dein 5-Stunden-Fenster in Minuten.
let running = 0;
const queue = [];

function withLimit(fn) {
  return new Promise((resolve, reject) => {
    const run = async () => {
      running++;
      try {
        resolve(await fn());
      } catch (e) {
        reject(e);
      } finally {
        running--;
        const next = queue.shift();
        if (next) next();
      }
    };
    running < MAX_CLAUDE ? run() : queue.push(run);
  });
}

/* ---------- Helfer ---------- */
const json = (res, code, obj) => {
  const body = JSON.stringify(obj);
  res.writeHead(code, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(body),
  });
  res.end(body);
};

function readBody(req, limitBytes = 5_000_000) {
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (c) => {
      raw += c;
      if (raw.length > limitBytes) {
        reject(new Error("Body zu groß"));
        req.destroy();
      }
    });
    req.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        reject(new Error("Ungültiges JSON"));
      }
    });
    req.on("error", reject);
  });
}

function authorized(req) {
  if (!BRIDGE_TOKEN) return true; // kein Token gesetzt = offen (nur für localhost ok)
  const h = req.headers.authorization || "";
  return h === `Bearer ${BRIDGE_TOKEN}` || req.headers["x-bridge-token"] === BRIDGE_TOKEN;
}

/** OpenAI-Messages zu einem einzelnen Prompt zusammenfalten. */
function flatten(messages = []) {
  const system = messages
    .filter((m) => m.role === "system")
    .map((m) => m.content)
    .join("\n\n");

  const rest = messages
    .filter((m) => m.role !== "system")
    .map((m) => {
      const text = Array.isArray(m.content)
        ? m.content.map((p) => p.text ?? "").join("")
        : String(m.content ?? "");
      return m.role === "assistant" ? `Assistant: ${text}` : `User: ${text}`;
    })
    .join("\n\n");

  return { system, prompt: rest };
}

/** Routet anhand des Modellnamens auf die richtige Seite. */
async function dispatch(model, prompt, system) {
  const m = String(model || "claude").toLowerCase();
  if (m.includes("gemini")) {
    const full = system ? `${system}\n\n${prompt}` : prompt;
    return askGemini(full, { model: m === "gemini" ? undefined : model });
  }
  const full = system ? `${system}\n\n${prompt}` : prompt;
  const claudeModel = /opus|haiku|sonnet/.test(m) ? m.match(/opus|haiku|sonnet/)[0] : undefined;
  return withLimit(() => askClaude(full, claudeModel ? { model: claudeModel } : {}));
}

/* ---------- Server ---------- */
const server = createServer(async (req, res) => {
  const url = new URL(req.url, "http://localhost");

  if (url.pathname === "/health") {
    return json(res, 200, {
      status: "ok",
      claudeRunning: running,
      claudeQueued: queue.length,
      maxConcurrent: MAX_CLAUDE,
      geminiKey: Boolean(process.env.GEMINI_API_KEY),
      claudeToken: Boolean(process.env.CLAUDE_CODE_OAUTH_TOKEN),
    });
  }

  if (!authorized(req)) return json(res, 401, { error: "Unauthorized" });
  if (req.method !== "POST") return json(res, 405, { error: "Nur POST" });

  let body;
  try {
    body = await readBody(req);
  } catch (e) {
    return json(res, 400, { error: e.message });
  }

  try {
    /* --- einfacher Endpunkt --- */
    if (url.pathname === "/ask") {
      const { model = "claude", prompt, system } = body;
      if (!prompt) return json(res, 400, { error: "Feld 'prompt' fehlt" });
      const t0 = Date.now();
      const text = await dispatch(model, prompt, system);
      return json(res, 200, { model, text, ms: Date.now() - t0 });
    }

    /* --- OpenAI-kompatibel, damit n8n AI-Nodes direkt draufzeigen können --- */
    if (url.pathname === "/v1/chat/completions") {
      const { model = "claude-sonnet", messages = [] } = body;
      if (!messages.length) return json(res, 400, { error: "Feld 'messages' fehlt" });

      const { system, prompt } = flatten(messages);
      const text = await dispatch(model, prompt, system);

      return json(res, 200, {
        id: `chatcmpl-${Date.now().toString(36)}`,
        object: "chat.completion",
        created: Math.floor(Date.now() / 1000),
        model,
        choices: [
          { index: 0, message: { role: "assistant", content: text }, finish_reason: "stop" },
        ],
        // Echte Token-Zahlen gibt es hier nicht - Claude läuft über das Abo, nicht per Token.
        usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 },
      });
    }

    return json(res, 404, { error: "Unbekannter Endpunkt" });
  } catch (e) {
    const limitHit = /limit|quota|429/i.test(e.message);
    return json(res, limitHit ? 429 : 500, { error: e.message });
  }
});

server.listen(PORT, HOST, () => {
  console.log(`AI Bridge läuft auf ${HOST}:${PORT}`);
  console.log(`Claude-Parallelität: max ${MAX_CLAUDE}`);
  console.log(BRIDGE_TOKEN ? "Auth: Token aktiv" : "Auth: offen (nur für localhost geeignet!)");
});
