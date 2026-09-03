# Geteiltes Gedächtnis zwischen den Engines — Entwurfs- und Bauauftrag

## Entscheidung + warum — umgesetzt am 2026-09-03

1. **Begrenzter Wortlaut statt generierter Zusammenfassung.** Ein gemeinsamer
   Chat speichert weiterhin höchstens 400 Nachrichten mit jeweils 8.000 Zeichen.
   Für einen Wechsel werden höchstens 24 jüngste Nachrichten mit zusammen
   maximal 6.000 Zeichen einschließlich Sprecherlabels und Kontextüberschrift
   übertragen. Kein zusätzlicher Modellaufruf für Zusammenfassungen; deren
   Fehler und laufende Kosten entfallen. Ältere Inhalte außerhalb des Fensters
   sind bewusst nicht garantiert, dauerhafte Entscheidungen gehören ins Vault.
2. **Der vorhandene conversation_store bleibt die einzige gemeinsame Ablage.**
   Pro Gespräch gibt es nun getrennte native Sitzungen für Claude, Codex und
   Google-Pro mit eigenem Lesestand. Ein neues Modell erhält den jüngsten
   Verlauf, ein zurückkehrendes nur die seit seiner letzten erfolgreichen
   Eingabe fehlenden Nachrichten. Eigene Antworten werden nur dann ausgelassen,
   wenn sie wirklich zur fortgesetzten nativen Sitzung gehören. Alte Dateien
   werden ohne Verlust ihrer Nachrichten gelesen; ihre einzelne Sitzungs-ID
   wird ausschließlich der ursprünglichen Engine zugeordnet. Die Weboberfläche
   behält beim Engine-Wechsel dieselbe Gesprächs-ID. Vorhandene lokale
   Claude-Sitzungen lassen sich einmalig in diesen gemeinsamen Verlauf aufnehmen.
3. **Kontextbudget wird ersetzt, nicht aufgestapelt.** Vorher gemessen: ca.
   7.507 Zeichen Briefing, davon 6.652 Zeichen Knowledge_Core und 522 Zeichen
   Aktivitätsjournal, ungefähr 1.900 Tokens bei der groben Zeichen/4-Schätzung
   (keine tokenizer-genaue Messung und keine Anbieter-Abrechnung). Maximal
   6.000 Verlaufzeichen wären nochmals grob 1.500 Tokens. Gemeinsame Chats senden
   das stabile Briefing nur beim Sitzungsstart oder nach einer Änderung erneut;
   das globale Journal wird nicht zusätzlich in denselben Chat gemischt. Die
   native CLI kann beim Fortsetzen trotzdem gespeicherten Kontext abrechnen —
   die Einsparung betrifft die vermeidbare zusätzliche Prompt-Kopie, nicht eine
   Garantie über die Anbieter-Abrechnung. AI-OS bleibt zustandslos pro Aufruf,
   bekommt seinen begrenzten Gesprächskontext und den ohnehin geladenen Core,
   aber keine zweite Worker-Historie. Chat-Stimme und Chat-Zeitlimit bleiben aktiv.

**Übergaben:** Die ursprüngliche Nachricht, Gesprächs-ID, Lesestand und bereits
besuchte Engines liegen beim Job auf dem Server. Ein Limit-Handoff funktioniert
dadurch auch nach Browser-Neuladen; wiederholtes Abfragen startet keinen zweiten
Job. Eingaben und erfolgreiche Antworten werden jeweils einmal gespeichert.
Fehlgeschlagene Antworten verschieben keinen Lesestand. Dateisperren schützen
konkurrierende Schreibzugriffe. Ein eingeschränkter Prüfauftrag bleibt auch
bei einer Übergabe eingeschränkt.

**Grenze:** Das verbindet AI-OS-Gespräche und deren lokale CLI-Sitzungen. Es ist
kein automatischer Zugriff auf sämtliche Chats der ChatGPT- oder Gemini-Website.
Bestehende Telegram-/CLI-Worker-Threads behalten ihre bisherige Speicherlogik.

Der ursprüngliche Bauauftrag bleibt im Folgenden als nachvollziehbare Grundlage
erhalten.

**Abnahme:** 668 Python-Tests grün, einschließlich simulierter Übergaben,
Wechsel/Rückwechsel, konkurrierender Antworten, Größenbegrenzung, Legacy-
Migration, Claude-Import und eingeschränkter Prüfaufträge. Dazu 9 grüne
Frontend-Verhaltenstests. Alle Provideraufrufe in diesen neuen Tests sind
ersetzt, keine Testprompts wurden an echte Konten gesendet. Im laufenden
Browser behielt Claude → Google → Claude denselben Titel und dieselben vier
Nachrichten. Die Webapp und der Worker wurden bei leerer Warteschlange neu
geladen und anschließend als aktiv geprüft. Nutzereigene alte Änderungen
und Chats wurden nicht gelöscht oder zurückgesetzt.

Direkter Auftrag von Felix, keine Vorschlagsrunde. Anders als sonst: das hier
ist NOCH NICHT ENTWORFEN. Drei offene Fragen unten sind zuerst zu
entscheiden (mit Begründung, die Felix nachvollziehen kann), dann zu bauen —
nicht raten und schweigend eine Wahl treffen.

Arbeitsverzeichnis: `AI-OS/02_Systems/Automation/TaskRunner/`. Alle Pfade
unten relativ dazu, wenn nicht anders angegeben.

## Das Problem

Felix chattet mit vier Engines (Claude, Codex, Google-Pro, der lokale
`aios`-Worker) über eine Weboberfläche (`webapp/`). Jede Engine bekommt heute
schon denselben *stehenden* Kurzkontext (`Knowledge_Core.md`, über
`scripts/shared_briefing.py:prepend()` — wer Felix ist, was die AI-OS ist,
welche Regeln gelten). Was fehlt, ist geteilte *Gesprächs*-Historie: wenn eine
Engine wegen eines Limits an eine andere übergibt (`engines.py:next_engine()`,
automatischer Handoff — siehe `engines.py:result()`), oder wenn Felix über den
manuellen "andere Engine fragen"-Knopf wechselt, sieht die neue Engine nur das
stehende Briefing plus den aktuellen Datei-/Repo-Zustand — nicht was in der
laufenden Unterhaltung tatsächlich gesagt wurde.

Felix will: ein Wechsel ist wirklich nahtlos, nicht nur "informiert, aber
ahnungslos vom bisherigen Gespräch".

## Was schon existiert (nicht neu erfinden)

- **`scripts/conversation_store.py`**: pro Konversation eine Datei
  (`create()`, `append(conversation_id, role, text, ...)`,
  `read()`, `history_context()`, `format_context()`). `engines.py:send()`
  nimmt einen `conversation_id`-Parameter und ruft
  `conversation_store.format_context(conversation_id)` auf, um bei
  Nicht-Claude-Engines den bisherigen Gesprächsverlauf VORNE an den Prompt zu
  hängen ("every other engine is a one-shot call, and this bounded block IS
  its memory of the conversation so far" — Kommentar in `engines.py`). Das
  ist bereits die Grundform von "geteiltem Gedächtnis" — Frage ist, ob sie
  reicht oder erweitert werden muss.
- **`memory.py`**: bounded Thread-Speicher (`MAX_TURNS=6`, `MAX_CHARS=6000`)
  für den `aios`-Worker, pro Telegram-Thread automatisch, per CLI nur mit
  `--thread` opt-in. Unklar, ob das in den Webapp-Chat verdrahtet ist —
  PRÜFEN, bevor irgendetwas Neues gebaut wird (siehe Roadmap-Backlog-Eintrag
  "Worker session memory", exakt dieser Punkt).
- **Native Sitzungen, gerade erst gebaut (2026-09-02/03)**: Codex bekam
  `codex_chat.py:ask(..., resume=<session_id>)` echt verdrahtet (ruft `codex
  exec resume <id>`), Google-Pro bekam `antigravity_chat.py:ask(...,
  conversation=<id>)` (ruft `agy --conversation <id> --continue`). Beide
  geben jetzt eine echte `session_id`/`conversation_id` in ihrer Antwort
  zurück. Das heißt: Codex und Google-Pro haben JETZT ZWEI Formen von
  Gedächtnis nebeneinander — ihre eigene native Konto-Historie (über
  `resume`/`--conversation`) UND den `conversation_store`-Kontextblock. Diese
  Doppelung ist wahrscheinlich der Kern der Entwurfsfrage unten, nicht
  Nebensache.
- **`engines.py:send()`**: `conversation_id`, wenn angegeben, muss laut Code
  bereits existieren (`conversation_store.exists()`). Der Handoff-Pfad
  (`fallback=True`, `next_engine()`) reicht bei einem Limit bereits an die
  nächste Engine weiter — PRÜFEN, ob dabei die `conversation_id`
  durchgereicht wird oder verloren geht (das wäre der Bug, den dieser Auftrag
  eigentlich beheben soll).
- **Claude** hat sein eigenes natives Session-Modell (`claude_chat.py`,
  `session_id`/`--resume`) und ist laut Kommentar in `engines.py` bereits die
  Ausnahme ("every OTHER engine is a one-shot call" — Claude nicht).

## Die drei offenen Fragen (aus `Plan_2026-09-02.md` §6, hierher übernommen)

Diese drei zuerst beantworten, mit einem kurzen Abschnitt "Entscheidung + warum"
am Anfang der Umsetzung, bevor Code entsteht:

1. **Was genau wird geteilt** — der volle Wortlaut jedes Turns, oder eine
   laufend aktualisierte Zusammenfassung (ähnlich `memory.py`s bounded
   Thread-Speicher, nur engine-übergreifend statt engine-eigen)? Voller
   Wortlaut ist einfacher und verlustfrei, kostet aber bei jedem Turn auf
   jeder der vier Engines erneut Tokens (siehe Punkt 3). Eine
   Zusammenfassung ist billiger, aber jemand muss sie schreiben und
   aktuell halten — mit welchem Modell, wie oft, und was passiert bei
   einem Zusammenfassungsfehler (siehe `memory.py:summary()` als
   möglicher Ausgangspunkt, falls es das schon in einer brauchbaren Form
   tut).
2. **Wo das landet** — ein gemeinsamer Speicher, den `shared_briefing.py`
   bei jedem Turn mitgibt (wie `Knowledge_Core.md`, nur pro Chat-Thread
   statt vault-weit), oder ein eigener Mechanismus (z.B. Erweiterung von
   `conversation_store.py` um ein "geteilt zwischen Engines"-Feld pro
   Konversation, statt einer separaten Datei)? Die Doppelung mit den
   nativen Sitzungen (siehe oben) gehört in diese Entscheidung: wenn Codex
   und Google-Pro schon ihre eigene Konto-Historie per `resume` haben,
   braucht der geteilte Speicher für DIESE beiden vielleicht nur noch die
   Übersetzung "was hat die jeweils andere Engine gesagt", nicht den
   ganzen eigenen Verlauf noch einmal.
3. **Kostenfrage** — jeder zusätzliche Kontext-Absatz kostet bei jeder der
   vier Engines erneut Tokens. Das ist explizit an die "Server-
   Vereinfachung" gekoppelt (`Roadmap.md`, Abschnitt "Planned — Server
   Simplification Patch", ebenfalls noch nicht begonnen: dort geht es
   unter anderem darum, warum Engine-Turns aktuell viel Zeit/Tokens
   kosten). Beide Baustellen sind absichtlich zusammen gedacht, nicht
   getrennt — wenn eine Lösung für geteiltes Gedächtnis den
   Kontext-Fußabdruck pro Turn weiter aufbläht, widerspricht sie dem
   zweiten Auftrag. Vor der Umsetzung: kurz messen, wie viele Tokens ein
   aktueller Turn mit `shared_briefing.prepend()` + ggf.
   `conversation_store.format_context()` schon kostet (die Kommentare in
   `codex_chat.py`/`safety_controls.py` nennen teils schon Zahlen für den
   reinen Briefing-Teil), damit die neue Lösung nicht dazu addiert, ohne
   dass irgendjemand die Summe kennt.

## Was ein guter Entwurf mindestens beantworten muss

- Was passiert beim automatischen Handoff (`engines.py:next_engine()` bei
  einem Limit) — bekommt die übernehmende Engine automatisch den geteilten
  Kontext, oder nur beim manuellen "andere Engine fragen"?
- Was passiert, wenn Felix mitten in einem Gespräch die Engine wechselt und
  danach wieder zur ersten zurückkehrt — sieht die erste Engine dann auch,
  was in der Zwischenzeit bei der zweiten passiert ist?
- Wie verhält sich das zu Claudes eigenem nativen Session-Modell — wird
  Claude in den geteilten Kontext eingebunden (liest ihn zusätzlich zu seiner
  eigenen Historie) oder bleibt Claude bewusst die Ausnahme, weil es schon
  die vollständigste eigene Erinnerung aller vier hat?
- Eine bewusste, benannte Grenze wie bei `memory.py` (`MAX_TURNS`,
  `MAX_CHARS`) — unbegrenzt wachsender geteilter Kontext ist kein Entwurf,
  sondern ein Leck.

## Test und Übergabe

- `python3 -m unittest test_taskrunner test_safety_controls` muss vor und
  nach jeder Änderung grün bleiben (Stand 2026-09-03: 627 Tests).
- Neue Tests für den neuen Mechanismus selbst schreiben — mindestens: geteilter
  Kontext überlebt einen simulierten Handoff; er bleibt innerhalb der
  gewählten Grenze (Zeichen/Turns); ein Test, der eine reale Engine anspricht,
  MUSS die Engine stubben (siehe `_stub_engines()` in `test_taskrunner.py` als
  Vorlage — ein Testlauf, der echte Google-Pro-/Codex-Aufrufe auslöst, ist in
  dieser Session zweimal real passiert und wurde beide Male als Fehler
  behoben, nicht als Feature).
- Am Ende einen kurzen Abschnitt "Entscheidung + warum" für die drei Fragen
  oben in diese Datei nachtragen (oder in eine neue
  `AI-OS/00_System/ADR`-artige Notiz, falls es das Muster im Vault schon für
  vergleichbare Entscheidungen gibt — `grep -rn ADR AI-OS/00_System/`
  prüfen), damit Felix nachlesen kann, was entschieden wurde und warum,
  ohne den Code selbst lesen zu müssen.
