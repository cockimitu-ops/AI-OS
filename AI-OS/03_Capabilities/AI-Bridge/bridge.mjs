// bridge.mjs — Kern der AI Bridge.
// Gemini laeuft ueber deinen API-Key, Claude ueber Claude Code (Pro-Abo, kein Key noetig).
//
// CLI:
//   node bridge.mjs models              -> zeigt alle Modelle, die dein Gemini-Key darf
//   node bridge.mjs gemini "frage"      -> fragt Gemini
//   node bridge.mjs claude "frage"      -> fragt Claude (verbraucht Pro-Kontingent!)
//   node bridge.mjs doctor              -> prueft Setup

import { readFileSync, existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

export const ROOT = dirname(fileURLToPath(import.meta.url));

/* ---------- .env laden (ohne Dependency) ---------- */
function loadEnv() {
  const p = join(ROOT, ".env");
  if (!existsSync(p)) return;
  for (const line of readFileSync(p, "utf8").split(/\r?\n/)) {
    const m = line.match(/^\s*([A-Za-z0-9_]+)\s*=\s*(.*?)\s*$/);
    if (m && !process.env[m[1]]) {
      process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
    }
  }
}
loadEnv();

const GEMINI_KEY = process.env.GEMINI_API_KEY;
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-flash-latest";
const CLAUDE_MODEL = process.env.CLAUDE_MODEL || "sonnet";
const CLAUDE_TIMEOUT = Number(process.env.CLAUDE_TIMEOUT_MS || 300000);

const GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta";

/* ---------- Gemini ---------- */

export async function listGeminiModels() {
  if (!GEMINI_KEY) throw new Error("GEMINI_API_KEY fehlt. Trag ihn in .env ein.");
  const res = await fetch(`${GEMINI_BASE}/models`, {
    headers: { "x-goog-api-key": GEMINI_KEY },
  });
  if (!res.ok) {
    throw new Error(`Gemini ListModels ${res.status}: ${(await res.text()).slice(0, 400)}`);
  }
  const data = await res.json();
  return (data.models || [])
    .filter((m) => (m.supportedGenerationMethods || []).includes("generateContent"))
    .map((m) => ({
      id: m.name.replace(/^models\//, ""),
      display: m.displayName,
      inputTokens: m.inputTokenLimit,
    }));
}

export async function askGemini(prompt, opts = {}) {
  if (!GEMINI_KEY) throw new Error("GEMINI_API_KEY fehlt. Trag ihn in .env ein.");
  const model = opts.model || GEMINI_MODEL;

  const body = {
    contents: [{ role: "user", parts: [{ text: prompt }] }],
    generationConfig: { temperature: opts.temperature ?? 0.7 },
  };
  if (opts.system) body.systemInstruction = { parts: [{ text: opts.system }] };

  const res = await fetch(`${GEMINI_BASE}/models/${model}:generateContent`, {
    method: "POST",
    headers: { "content-type": "application/json", "x-goog-api-key": GEMINI_KEY },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const txt = (await res.text()).slice(0, 400);
    if (res.status === 404) {
      throw new Error(
        `Modell "${model}" nicht gefunden.\n` +
          `Lauf "node bridge.mjs models" und trag eine gueltige ID als GEMINI_MODEL in .env ein.\n${txt}`
      );
    }
    if (res.status === 429) {
      throw new Error(`Gemini Rate-Limit erreicht (429). Warte kurz oder nimm ein Flash-Lite-Modell.\n${txt}`);
    }
    throw new Error(`Gemini ${res.status}: ${txt}`);
  }

  const data = await res.json();
  const parts = data.candidates?.[0]?.content?.parts ?? [];
  const text = parts.map((p) => p.text ?? "").join("").trim();
  if (!text) {
    const reason = data.candidates?.[0]?.finishReason || "unbekannt";
    throw new Error(`Gemini lieferte leere Antwort (finishReason: ${reason}).`);
  }
  return text;
}

/* ---------- Claude (Claude Code headless, kein API-Key) ---------- */

export function askClaude(prompt, opts = {}) {
  const model = opts.model ?? CLAUDE_MODEL;
  const args = ["-p"];
  if (model) args.push("--model", model);

  return new Promise((resolve, reject) => {
    const child = spawn("claude", args, {
      cwd: opts.cwd || ROOT,
      shell: process.platform === "win32", // claude ist auf Windows ein .cmd-Shim
    });

    let out = "";
    let err = "";
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`Claude-Timeout nach ${CLAUDE_TIMEOUT} ms.`));
    }, opts.timeoutMs || CLAUDE_TIMEOUT);

    child.stdout.on("data", (d) => (out += d));
    child.stderr.on("data", (d) => (err += d));

    child.on("error", (e) =>
      reject(
        new Error(
          `Claude Code CLI nicht gefunden (${e.message}).\n` +
            `Installieren: npm install -g @anthropic-ai/claude-code, dann "claude" starten und per Browser mit deinem Pro-Account einloggen.`
        )
      )
    );

    child.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) return resolve(out.trim());
      const hint = /limit|quota|usage/i.test(err)
        ? "\nHinweis: klingt nach erreichtem Pro-Limit. Pruef es mit /status in Claude Code."
        : "";
      reject(new Error(`Claude beendet mit Code ${code}: ${err.slice(0, 500)}${hint}`));
    });

    // Prompt ueber stdin statt argv -> keine Laengenbegrenzung der Kommandozeile
    child.stdin.write(prompt);
    child.stdin.end();
  });
}

/* ---------- Doctor ---------- */

async function doctor() {
  console.log("Node:", process.version);
  console.log("Plattform:", process.platform);

  if (!GEMINI_KEY) {
    console.log("GEMINI_API_KEY: FEHLT  -> .env anlegen");
  } else {
    console.log(`GEMINI_API_KEY: gesetzt (...${GEMINI_KEY.slice(-4)})`);
    try {
      const models = await listGeminiModels();
      const ok = models.some((m) => m.id === GEMINI_MODEL);
      console.log(`Gemini erreichbar: ja (${models.length} Modelle)`);
      console.log(`GEMINI_MODEL "${GEMINI_MODEL}": ${ok ? "gueltig" : "NICHT in der Liste -> node bridge.mjs models"}`);
    } catch (e) {
      console.log("Gemini erreichbar: nein ->", e.message);
    }
  }

  try {
    const r = await askClaude("Antworte exakt mit: OK");
    console.log("Claude Code:", r.slice(0, 40));
  } catch (e) {
    console.log("Claude Code: nein ->", e.message.split("\n")[0]);
  }
}

/* ---------- CLI ---------- */

const isMain = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;

if (isMain) {
  const [cmd, ...rest] = process.argv.slice(2);
  const prompt = rest.join(" ");

  try {
    if (cmd === "models") {
      const models = await listGeminiModels();
      for (const m of models) {
        console.log(`${m.id.padEnd(38)} ${String(m.inputTokens ?? "?").padStart(9)} tok  ${m.display ?? ""}`);
      }
      console.log(`\nAktuell in .env: GEMINI_MODEL=${GEMINI_MODEL}`);
    } else if (cmd === "gemini") {
      if (!prompt) throw new Error('Nutzung: node bridge.mjs gemini "deine frage"');
      console.log(await askGemini(prompt));
    } else if (cmd === "claude") {
      if (!prompt) throw new Error('Nutzung: node bridge.mjs claude "deine frage"');
      console.log(await askClaude(prompt));
    } else if (cmd === "doctor") {
      await doctor();
    } else {
      console.log(
        [
          "AI Bridge",
          "",
          "  node bridge.mjs doctor",
          "  node bridge.mjs models",
          '  node bridge.mjs gemini "frage"',
          '  node bridge.mjs claude "frage"',
          "",
          'Gemeinsamer Space:  node roundtable.mjs "aufgabe" --rounds 3',
        ].join("\n")
      );
    }
  } catch (e) {
    console.error("Fehler:", e.message);
    process.exit(1);
  }
}
