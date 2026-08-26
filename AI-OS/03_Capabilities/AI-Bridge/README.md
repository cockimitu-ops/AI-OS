# AI Bridge — Claude × Gemini

> ⚠️ **PARKIERT seit 2026-08-26 — nicht produktiv nutzen.** Eine frühere Session
> (`~/HANDOFF-1.md`, 2026-08-24) hat genau das hier — Claude Code über
> Pro-Abo-Auth statt über einen echten API-Key laufen zu lassen, um Metered
> Billing zu umgehen — als "likely a real ToS problem" markiert und explizit
> geparkt, bis auf einen echten `ANTHROPIC_API_KEY` umgestellt wird. Nicht
> eindeutig geklärt: `-p`-Modus ist offiziell für Skripte/CI gedacht (siehe
> unten), aber ein Dauerbetrieb als unbeaufsichtigter Hintergrunddienst ist
> etwas anderes als eine CI-Pipeline. Technisch funktioniert `askClaude()`
> nachweislich (verifiziert 2026-08-26) — das ist nicht die offene Frage.
> Nicht wieder aktivieren, ohne dass Felix das bewusst entscheidet oder auf
> einen echten API-Key umgestellt wird.

Ein gemeinsamer Arbeitsraum, in dem sich beide Modelle gegenseitig aufrufen können.
**Ohne Anthropic-API-Key.**

## Warum das ohne Key geht

| Seite | Zugang | Kosten |
|---|---|---|
| Gemini | Dein API-Key aus AI Studio | Free Tier |
| Claude | Claude Code im Headless-Modus (`claude -p`) | Dein Pro-Abo |

Claude Code ist in Claude Pro enthalten und authentifiziert sich per Browser-Login,
nicht per API-Key. Der `-p`-Modus ist der offiziell dokumentierte nicht-interaktive
Modus für Skripte und CI — Prompt über stdin rein, Antwort über stdout raus.
Genau das nutzt `bridge.mjs`.

**Wichtig:** Wenn `ANTHROPIC_API_KEY` als Umgebungsvariable gesetzt ist, ignoriert
Claude Code dein Abo und rechnet über API-Tokens ab. Setz die Variable also nicht.

## Setup

**1. Claude Code installieren und einloggen**

```bash
npm install -g @anthropic-ai/claude-code
claude
```

Beim ersten Start öffnet sich der Browser. Mit deinem Pro-Account einloggen.
Was du eventuell einfügen musst, ist ein Login-Code, kein API-Key.
Prüfen mit `/status` in Claude Code.

**2. Gemini-Key eintragen**

```bash
copy .env.example .env
```

Key rein, dann die gültigen Modell-IDs abfragen:

```bash
node bridge.mjs models
```

Eine ID aus der Liste als `GEMINI_MODEL` in die `.env` schreiben. Die Modellnamen
ändern sich regelmäßig — deshalb abfragen statt raten.

**3. Setup prüfen**

```bash
node bridge.mjs doctor
```

Prüft beide Seiten einzeln und sagt dir, welche klemmt.

## Nutzung

Einzelaufrufe:

```bash
node bridge.mjs gemini "20 Hook-Varianten für ein ASMR-Short"
node bridge.mjs claude "Wo ist der Denkfehler in diesem Plan?"
```

Der gemeinsame Space — beide sehen dasselbe Transkript und schreiben abwechselnd:

```bash
node roundtable.mjs "Welche Fiverr-Nische zuerst, Konkurrenzanalyse oder Template-Verkauf?" --rounds 3
```

Optionen: `--rounds N` (Default 3), `--lead claude` (Default: Gemini eröffnet).

### Wie sie sich gegenseitig aufrufen

Beide Modelle kennen drei Steuerzeichen:

| Zeichen | Wirkung |
|---|---|
| `@claude: <frage>` | Gemini reicht gezielt an Claude weiter |
| `@gemini: <frage>` | Claude reicht gezielt an Gemini weiter |
| `[DONE]` | Aufgabe gelöst, Schleife bricht ab |

Zusätzlich läuft der echte Rückkanal über `CLAUDE.md`: Wenn du Claude Code direkt
in diesem Ordner startest, liest es die Datei und weiß, dass es
`node bridge.mjs gemini "..."` selbst ausführen darf. Damit delegiert Claude
breite Arbeit eigenständig an Gemini, ohne dass du dazwischenstehst.

Jede Session landet als Markdown mit Frontmatter in `space/` — direkt
Obsidian-kompatibel, passt in deinen Vault.

## Das Limit, das du einplanen musst

Claude-Code-Nutzung teilt sich die Kontingente mit claude.ai im Web und Desktop:
5-Stunden-Rolling-Window plus Wochenlimit. **Jeder Bridge-Call frisst dein Chat-Kontingent.**

Deshalb ist das System bewusst asymmetrisch gebaut:

- **Gemini = Arbeitspferd.** Breite, Varianten, Recherche, Iteration. Hohes Limit, darf viel.
- **Claude = Eskalation.** Prüfung, Urteil, Entscheidung. Selten, dafür wertvoll.

Ein `--rounds 3`-Durchlauf kostet dich etwa 3–4 Claude-Calls. Wenn du merkst,
dass dein Chat-Kontingent knapp wird: `/status` in Claude Code zeigt den Stand,
und `--lead gemini` mit weniger Runden drückt die Claude-Last.

Läufst du regelmäßig ins Limit, ist das der Punkt, an dem ein echter Anthropic-API-Key
mit Prepaid-Guthaben günstiger wird als Frust — aber nicht vorher.

## Was hier bewusst nicht drin ist

Kein Scripting der claude.ai-Weboberfläche. Das wäre eine Umgehung des Produkts
und würde dir im Zweifel den Account kosten. Der `-p`-Modus ist der vorgesehene
Weg und tut dasselbe, nur legitim.
