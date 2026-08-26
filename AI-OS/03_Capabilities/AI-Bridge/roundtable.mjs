// roundtable.mjs — der gemeinsame Space.
//
// Beide Modelle sehen dasselbe Transkript und schreiben abwechselnd hinein.
// Gemini fuehrt (guenstig, hohes Limit), Claude eskaliert (teuer, Pro-Kontingent).
//
//   node roundtable.mjs "Aufgabe" [--rounds 3] [--lead gemini|claude]
//
// Steuerzeichen, die beide Modelle nutzen duerfen:
//   @claude: <frage>   -> Gemini reicht gezielt an Claude weiter
//   @gemini: <frage>   -> Claude reicht gezielt an Gemini weiter
//   [DONE]             -> Aufgabe geloest, Schleife bricht ab

import { writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { askGemini, askClaude, ROOT } from "./bridge.mjs";

/* ---------- Argumente ---------- */
const argv = process.argv.slice(2);
const opts = { rounds: "3", lead: "gemini" };
const words = [];

for (let i = 0; i < argv.length; i++) {
  if (argv[i].startsWith("--")) {
    opts[argv[i].slice(2)] = argv[i + 1];
    i++;
  } else {
    words.push(argv[i]);
  }
}

const task = words.join(" ").trim();
const ROUNDS = Number(opts.rounds) || 3;
const LEAD = opts.lead;

if (!task) {
  console.error('Nutzung: node roundtable.mjs "Deine Aufgabe" --rounds 3');
  process.exit(1);
}

/* ---------- Rollen ---------- */
const SHARED_RULES = `
Du arbeitest in einem gemeinsamen Arbeitsraum mit einem zweiten KI-Modell an einer Aufgabe fuer Felix.
Ihr seht beide dasselbe Transkript und schreibt abwechselnd hinein.

Regeln:
- Wiederhole nicht, was schon dasteht. Bau darauf auf oder widersprich begruendet.
- Widersprich ruhig. Zwei Modelle, die sich nur zustimmen, sind wertlos.
- Halte dich kurz. Maximal etwa 250 Woerter pro Beitrag.
- Willst du gezielt das andere Modell fragen, schreib eine Zeile die mit "@claude:" bzw. "@gemini:" beginnt.
- Ist die Aufgabe wirklich geloest, schreib [DONE] in die letzte Zeile. Nicht vorschnell.
- Keine Hoeflichkeitsfloskeln, kein "Gute Frage". Direkt zur Sache.
`.trim();

const ROLES = {
  gemini: `${SHARED_RULES}

Du bist GEMINI. Deine Rolle: Breite. Optionen generieren, Recherche, Varianten, schnelle Iteration.
Du bist das Arbeitspferd - du darfst viele Tokens verbrauchen.`,

  claude: `${SHARED_RULES}

Du bist CLAUDE. Deine Rolle: Tiefe und Qualitaetskontrolle. Du wirst selten aufgerufen, also zaehlt jeder Beitrag.
Prueff Geminis Vorschlaege auf Denkfehler, unrealistische Annahmen und fehlende Schritte. Entscheide und schaerfe.`,
};

/* ---------- Transkript ---------- */
const lines = [`# AUFGABE\n${task}\n`];
const render = () => lines.join("\n");

function buildPrompt(speaker) {
  return [
    ROLES[speaker],
    "",
    "=== GEMEINSAMER ARBEITSRAUM ===",
    render(),
    "=== ENDE ===",
    "",
    `Du bist jetzt dran (${speaker.toUpperCase()}). Schreib nur deinen Beitrag, ohne Namensprefix.`,
  ].join("\n");
}

async function speak(who) {
  const prompt = buildPrompt(who);
  const t0 = Date.now();
  process.stdout.write(`\n--- ${who.toUpperCase()} denkt ... `);
  const text = who === "gemini" ? await askGemini(prompt) : await askClaude(prompt);
  console.log(`${((Date.now() - t0) / 1000).toFixed(1)}s ---\n`);
  console.log(text);
  lines.push(`\n## ${who.toUpperCase()}\n${text}`);
  return text;
}

function directedQuestion(text, tag) {
  const m = text.match(new RegExp(`^@${tag}:\\s*(.+)$`, "im"));
  return m ? m[1].trim() : null;
}

/* ---------- Speichern (auch bei Abbruch) ---------- */
function save(claudeCalls, partial = false) {
  const dir = join(ROOT, "space");
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

  const stamp = new Date().toISOString().slice(0, 16).replace(/[-:T]/g, "");
  const slug = task
    .toLowerCase()
    .replace(/[^a-z0-9äöüß ]/gi, "")
    .trim()
    .split(/\s+/)
    .slice(0, 6)
    .join("-");
  const file = join(dir, `${stamp} ${slug || "session"}${partial ? " (abgebrochen)" : ""}.md`);

  const fm = [
    "---",
    "typ: roundtable",
    `datum: ${new Date().toISOString()}`,
    "modelle: [gemini, claude]",
    `claude-calls: ${claudeCalls}`,
    `status: ${partial ? "abgebrochen" : "fertig"}`,
    "---",
    "",
  ].join("\n");

  writeFileSync(file, fm + render() + "\n", "utf8");
  return file;
}

/* ---------- Hauptschleife ---------- */
let claudeCalls = 0;

async function main() {
  let done = false;
  const speaker = LEAD === "claude" ? "claude" : "gemini";

  for (let round = 1; round <= ROUNDS && !done; round++) {
    console.log(`\n================ RUNDE ${round}/${ROUNDS} ================`);

    const first = await speak(speaker);
    if (speaker === "claude") claudeCalls++;
    if (first.includes("[DONE]")) break;

    const other = speaker === "gemini" ? "claude" : "gemini";

    const q = directedQuestion(first, other);
    if (q) lines.push(`\n> Direkte Rueckfrage an ${other.toUpperCase()}: ${q}`);

    const second = await speak(other);
    if (other === "claude") claudeCalls++;
    if (second.includes("[DONE]")) done = true;
  }

  if (!done) {
    console.log("\n--- SYNTHESE (Claude) ---\n");
    const synth = await askClaude(
      `${ROLES.claude}\n\n=== ARBEITSRAUM ===\n${render()}\n=== ENDE ===\n\n` +
        "Die Runden sind aufgebraucht. Schreib jetzt das Ergebnis: die Entscheidung, die Begruendung in drei Saetzen, " +
        "und die konkreten naechsten Schritte als Liste. Keine Zusammenfassung des Gespraechs."
    );
    claudeCalls++;
    console.log(synth);
    lines.push(`\n## ERGEBNIS\n${synth}`);
  }

  const file = save(claudeCalls);
  console.log(`\n\nGespeichert: ${file}`);
  console.log(`Claude-Calls diese Session: ${claudeCalls} (zaehlen auf dein Pro-Limit)`);
}

try {
  await main();
} catch (e) {
  console.error(`\n\nAbgebrochen: ${e?.message ?? e}`);
  if (lines.length > 1) console.error(`Teilergebnis gesichert: ${save(claudeCalls, true)}`);
  process.exit(1);
}
