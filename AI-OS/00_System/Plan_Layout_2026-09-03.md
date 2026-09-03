# Layout-Auftrag für Codex — Stand 2026-09-03

Direkter Bauauftrag von Felix, keine Vorschlagsrunde. Fünf Punkte, unabhängig
voneinander baubar, in dieser Reihenfolge. Jeder Punkt hat: was gebaut wird,
warum, welche Dateien betroffen sind, und was schon existiert und
wiederverwendet werden muss statt neu erfunden zu werden.

Arbeitsverzeichnis: `AI-OS/02_Systems/Automation/TaskRunner/webapp/static/`
(alle Pfade unten sind relativ dazu, wenn nicht anders angegeben).

## Was schon steht (nicht neu bauen)

- **Material**: `.glass`/`.card`/`.hero` sind Gesso, kein Glas mehr — deckende
  Flächen (`--pane-solid` etc.), helle Oberkante + dunkle Unterkante
  (`--edge`, `--edge-dim`). Radius über `--r`/`--r-sm`. Vier Lichter
  (`dawn`/`day`/`dusk`/`night`) als CSS-Variablen in `style.css`, gestempelt
  über `body[data-light]` durch `fx.js`.
- **Malschicht**: `fx.js` malt eine Monet-artige Komposition (Horizont,
  Himmel/Wasser-Zonen, benannte Motive) auf drei Ebenen (`fx-canvas`,
  `fx-shadow`, `fx-ridge` — Schatten/Körper/Grat für Impasto-Relief), plus
  `paint-motifs.js` für zusätzliche Motive (Brücke, Heuschober, Pappeln,
  Segelboote, Mohnwiese, Kathedrale, Klippen). `window.fxSetLight(name)`,
  `window.fxLight()` sind die öffentliche Schnittstelle. Das Bild wird
  schrittweise gemalt (`stroke()` reiht ein, `drain()` arbeitet die Schlange
  über viele Frames ab, max. 10ms/Frame) — nie am Stück, nie blockierend.
- **Heute-Screen**: zeigt schon drei Handlungen (`#today-hero` + `#today-more`
  mit `.act`-Karten) statt einer Karte plus fünf Zahlenzeilen. `/api/today`
  liefert `next_actions` (Array, sortiert nach Euro).
- **Zentrale**: `#screen-command`, zeigt laufende Engine-Jobs, Warteschlange,
  Sicherheitsschalter, Dienste. `/api/workers` liefert die Daten.
- **Test-Referenz**: `test_taskrunner.py`, `test_safety_controls.py` — vor
  jeder Änderung laufen lassen (`python3 -m unittest test_taskrunner
  test_safety_controls` aus dem TaskRunner-Verzeichnis), danach wieder.
  Aktueller Stand: 627 Tests grün. Jede neue Test-Isolation, die den echten
  Schalter (`spend/safety_controls.json`) oder echte Engines anfasst, ist ein
  Bug — siehe die Kommentare bei `_isolate_safety_state`/`_stub_engines` in
  `test_taskrunner.py` für die Begründung.

## 1. Der Tag als Fläche statt als Liste

**Ziel**: Statt Karten übereinander (aktueller Zustand von `#screen-today`)
sitzen die drei Handlungen als gemalte Flächen im Bild selbst — das
Blockierende groß und nah, der Rest klein und weiter hinten. Monets
Heuhaufen ist ein Motiv im Feld, kein Listeneintrag.

**Konkret**:
- Kein neues Canvas. Die bestehenden drei Ebenen in `fx.js`
  (`shadowCanvas`/`bodyCanvas`/`ridgeCanvas`) bekommen ein zusätzliches,
  optionales Argument: eine Liste "Objekte im Feld" mit Position (0..1 in x/y,
  wobei y näher an `L.horizon` = weiter weg = kleiner) und Größe. Für jede
  Handlung wird — je nach `L.scene`-Motiv des aktuellen Lichts — ein
  passendes Motiv an einer aus Rang und Dringlichkeit abgeleiteten Position
  gemalt (Rang 1 = groß, vorne, nah am unteren Bildrand; Rang 3 = klein, nah
  am Horizont).
- Praktisch: `today-lab.html`
  (`AI-OS/02_Systems/Automation/TaskRunner/webapp/static/today-lab.html`,
  bereits vorhanden als Prototyp) zeigt die Gesso-Karten-Variante. Für diesen
  Punkt einen NEUEN Prototyp `today-field-lab.html` danebenlegen (nicht
  `today-lab.html` überschreiben), der:
  1. `/api/today` genauso lädt,
  2. die Karten NICHT als `.act`/`.hero`-Flächen zeichnet, sondern über
     `window.fxPlaceObject?.(rank, label)` (neue, zu bauende Funktion in
     `fx.js`) ein Motiv an eine Position im Feld setzt,
  3. Text (Titel, Betrag, Dauer) als dünne, halbtransparente Overlay-Zeile
     UNTER dem jeweiligen Motiv einblendet (kein Kasten, keine Fläche — nur
     Schrift mit Textschatten, damit sie auf jeder Malfarbe lesbar bleibt:
     `text-shadow: 0 1px 3px var(--edge-dim), 0 -1px 2px var(--edge)` als
     Ausgangspunkt, anpassen bis lesbar in allen vier Lichtern).
- Das Antippen eines Motivs klappt den vollen Text auf (gleiches
  Verhalten wie `.act.open` heute) — als Gesso-Zettel, der kurz erscheint,
  nicht als Dauerzustand.
- **Wichtig**: das Gate (`a.gates === true`) bekommt IMMER die größte, nächste
  Position, unabhängig vom Euro-Rang — siehe Begründung in `today-lab.html`s
  Kommentaren ("was blockiert, muss man lesen können").
- Screenshots aus allen vier Lichtern ziehen (`chromium-browser --headless
  --disable-gpu --no-sandbox --window-size=430,932 --screenshot=... --virtual-
  time-budget=9000 "http://<tailnet-ip>:8787/today-field-lab.html?token=...
  &light=dawn"` etc. — Token aus `AIOS_WEB_TOKEN`/laufendem
  `aios-webapp.service` holen, NICHT neu vergeben) und selbst prüfen, ob Text
  in JEDEM Licht lesbar bleibt, bevor das als fertig gilt.

## 2. Pinselstrich statt Balken

**Ziel**: Jeder Fortschrittsbalken (Monatslimit, Guthaben, Tageslimit) wird
aufgetragene Farbe mit gerissener Kante statt Rechteck.

**Konkret**:
- Fundstellen: `grep -n "class=\"meter\"\|<i style=\"width:" app.js style.css`
  — mindestens die Guthaben-Anzeige (OpenRouter) und `.meter`-Klasse in
  `style.css` betroffen.
- Neue Funktion in `fx.js` (oder ein neues kleines Modul `brush-meter.js`,
  analog zu `paint-motifs.js` als eigenständige Datei mit klarem Vertrag):
  `paintMeter(canvasEl, fraction, color)` — zeichnet mit derselben
  `stroke()`-Borsten-Technik einen waagerechten Balken, dessen RECHTE Kante
  ausgefranst ist (mehrere Striche mit zufällig leicht unterschiedlicher
  Länge am Ende, statt einer geraden Kante) proportional zu `fraction`.
  Läuft auf einem eigenen kleinen `<canvas>`-Element, das ein bestehendes
  `.meter`-Div ersetzt oder überlagert — Höhe ca. 6-10px, Breite = Elementbreite.
- Muss mit `ResizeObserver` oder beim Öffnen des jeweiligen Screens neu
  gezeichnet werden (Breite ändert sich mit Bildschirmgröße).
- Testen an: OpenRouter-Guthaben-Balken (`app.js`, Kosten-Screen),
  Tageslimit-Anzeige in der Zentrale (`#cmd-switches`).

## 3. Die Zeit sichtbar machen

**Ziel**: Ein dünner Streifen am oberen Rand zeigt, wo im Tag man ist und
wann das nächste Licht kommt — die Uhr als Teil des Bildes, nicht als Text.

**Konkret**:
- Neues Element `#fx-daystrip`, fixiert direkt unter der Kopfleiste (oberhalb
  des Inhalts, unterhalb von `header`/`.mark`), über die ganze Breite, ca.
  3-4px hoch.
- Vier Segmente (dawn/day/dusk/night), Breite proportional zur echten
  Stundenlänge jedes Lichts (`lightForHour()` in `fx.js` kennt die Grenzen:
  Nacht 22-6 Uhr = 8h, Morgen 6-9 = 3h, Mittag 9-17 = 8h, Abend 17-22 = 5h).
  Jedes Segment in der `--ground`-Farbe seines Lichts eingefärbt (aus den
  `LIGHTS[name].ground`-Werten in `fx.js`), nicht neu erfunden.
- Ein heller Punkt/Strich markiert die aktuelle Uhrzeit-Position im Streifen,
  aktualisiert sich mit `setInterval` (gleiche Kadenz wie `refreshLight()`,
  einmal pro Minute reicht).
- Antippen des Streifens öffnet das bestehende Licht-Wahl-Blatt
  (`openLightSheet()` in `app.js` existiert schon).
- CSS-only + ein `<script>`-Block, kein neues Canvas nötig (einfache
  `<div>`-Segmente mit `flex-basis` in Prozent reichen).

## 4. Textur, die etwas bedeutet

**Ziel**: Körnung/Leinenstruktur ist nicht nur Effekt — sie wird gröber, wo
etwas alt/überfällig ist, glatter bei frischen Daten.

**Konkret**:
- Betrifft die `#fx-grain`-Ebene (Leinenstruktur, in `fx.js` über
  `weaveInto()` erzeugt) UND einzelne Karten/Zeilen.
- Zwei Wege, beide klein anfangen und dann entscheiden welcher trägt:
  a) Global: der `#fx-grain`-Kontrast (`--grain-opacity` je Licht) leicht
     erhöhen, wenn eine "Alters"-Kennzahl über einem Schwellwert liegt (z.B.
     `d.sniper.last_run` älter als X Stunden, oder `rest_actions` hoch) —
     ein zusätzlicher CSS-Custom-Property `--grain-boost`, gesetzt von
     `app.js` beim Laden von `/api/today`.
  b) Lokal: einzelne `.act`/`.worker-row`-Karten bekommen ein feines
     `background-image` mit der Leinen-Textur (gleiche Kachel-Technik wie
     `weaveInto()` in `fx.js`, als wiederverwendbare Funktion exportieren:
     `window.fxWeaveTile(roughness)` -> Data-URL), deren Rauheit
     (Faden-Kontrast) mit dem Alter der jeweiligen Zeile skaliert — z.B.
     `letters_sent` seit X Tagen unverändert = rauere Kachel auf dieser Zeile.
- Anfangen mit (a), weil es eine Zeile Code ist und sofort sichtbar; (b) nur
  bauen, wenn (a) nach Ansicht zu unauffällig ist.

## 5. Ein Bild pro Tab statt einer Farbe

**Ziel**: Jeder Tab-Bereich (Heute, Chat, Geräte, Geld, und die neuen
Zentrale/Vorschläge/etc. unter "Mehr") bekommt ein eigenes Motiv im selben
Licht, sodass man am Bild erkennt wo man ist, bevor man die Schrift liest.

**Konkret**:
- `fx.js`s `LIGHTS[name].scene` ist aktuell EIN Array von Motiven fürs ganze
  Bild. Umbauen zu: `LIGHTS[name].scenes = { "screen-today": [...], "screen-
  money": [...], "screen-devices": [...], default: [...] }`. `paint()` liest
  `document.body.dataset.screen` (wird schon von `app.js`/`switchTo()`
  gesetzt, siehe `body[data-screen=...]`-Selektoren in `style.css`) und wählt
  die passende Szene.
- Motiv-Zuordnung, ein Vorschlag (Felix kann das noch ändern):
  - Heute: `sun`/`spires` (was das aktuelle Licht schon zeigt) — bleibt der
    "Leitstern" der App.
  - Geld: `bridge`/`haystacks` (Ernte-Motiv passt zu Einnahmen).
  - Geräte: `willow`/`sailboats` (ruhiger, technischer Bereich).
  - Chat: `pond`/`pond-dim` (Seerosen — Gespräch als Wasseroberfläche, an der
    sich Antworten spiegeln).
- **Wichtig**: `paint()` läuft schon bei jedem `resize()` und bei jedem
  Lichtwechsel. Zusätzlich muss `switchTo()` in `app.js` (wo
  `document.body.dataset.screen` gesetzt wird) `window.fxRepaint?.()`
  aufrufen, wenn sich die Szene für den neuen Screen von der vorigen
  unterscheidet — sonst bleibt das alte Motiv stehen. Einfachste Umsetzung:
  `fx.js` merkt sich das zuletzt gemalte `screen`, vergleicht bei einem
  `MutationObserver` auf `body[data-screen]` oder bei einem von `app.js`
  gerufenen Hook, und malt nur neu, wenn es sich unterscheidet (Kosten:
  komplettes Neumalen ist über die Schlangen-Technik schon billig genug,
  siehe Punkt "schrittweise" oben — kein Problem, das öfter zu tun).

## Reihenfolge und Test

1, 2, 3 sind unabhängig und können parallel/in beliebiger Reihenfolge
gebaut werden. 4 und 5 bauen auf `fx.js`s bestehender Struktur auf und sollten
NACH 1 kommen, weil 1 möglicherweise schon neue Positionierungs-Hooks in
`fx.js` einführt, die 5 mitbenutzen kann (eine Szene pro Tab UND eine
Objekt-Platzierung fürs Heute-Feld sind verwandte Mechanismen — nicht zwei
separate Systeme bauen, wenn eines beide trägt).

Nach jeder Änderung:
- `node --check <geänderte .js-Datei>`
- `python3 -m unittest test_taskrunner test_safety_controls` aus
  `AI-OS/02_Systems/Automation/TaskRunner/` — muss grün bleiben (aktuell 627).
- Mindestens einen Screenshot pro geändertem Screen, in mindestens zwei
  Lichtern (einem hellen, einem dunklen), tatsächlich ansehen, nicht nur
  rendern lassen — Lesbarkeit ist das wiederkehrende Problem bei diesem
  Umbau (siehe git-Historie: die schmalen Karten waren im dunklen Licht mit
  11% Deckkraft praktisch Glas, das wurde erst am Screenshot sichtbar, nicht
  im Code).

Nichts davon ersetzt `paint-lab.html`/`today-lab.html`/`command-lab.html` —
die bleiben als Vergleichs-Prototypen liegen, bis Felix die neuen Fassungen
freigibt. Änderungen an der echten App (`index.html`, `app.js`, `style.css`,
`fx.js`) sind trotzdem live und wirken sich sofort aus — bei Unsicherheit
lieber erst im `-lab.html`-Prototyp bauen und zeigen, dann in die echte App
übernehmen, genau wie bisher in dieser Session gehandhabt.

## Umsetzung und Abnahme — 2026-09-03

Alle fünf Punkte gebaut. Google AI Pro übernahm zwei Implementierungsrunden
in einer isolierten Kopie; Codex integrierte, prüfte und korrigierte die
Ergebnisse auf dem Server. Kein GLM für diese Umsetzung eingesetzt.

- `today-field-lab.html`: echter `/api/today`-Inhalt als gemalte Motive,
  Gate vor Euro-Rang, Fokus-/Tastaturbedienung und vollständiger Detaildialog.
  Weitere Aufgaben werden aus `rest_actions/rest_euros` korrekt angezeigt.
  Gemessene Titel-, Text- und Fußzeilenhöhen reservieren Platz; überprüft bei
  430×932 und 320×740. Alle vier Lichter visuell abgenommen. Die bisherigen
  drei Laborseiten und die produktive Heute-Ansicht bleiben erhalten.
- `brush-meter.js`: 8-Pixel-Pinselanzeigen für bestehende Verbrauchsbalken;
  zusätzlicher Tageslimit-Balken in der Zentrale. Null, ungültige Werte,
  Größenänderungen und zugängliche Prozentwerte sind geprüft.
- Tagesstreifen: reale vier Paletten, Zeitanteile 3/8/5/8 Stunden ab 06:00,
  aktuelle Zeitmarkierung, minutengenaue Aktualisierung; öffnet die vorhandene
  Lichtauswahl. Die Verbindung wurde im Browser angeklickt und geprüft.
- Körnung: gültiges `sniper.last_run` steuert den globalen Multiplikator
  zwischen 1 und 2,5; kein zusätzlicher Effekt bei fehlendem Datum, Zunahme
  erst nach 6 Stunden, Obergrenze nach 72 Stunden.
- Eigene Szenen pro Tab aus der vorhandenen Maltechnik. Neue Aufträge ersetzen
  auch während des Zeichnens die alte Warteschlange; keine zusätzliche
  Szenen-Leinwand. Der dekorative Hero-Reflex liegt hinter dem Text, und dunkle
  Tafeln sind wieder deckend genug für lesbare Schrift.

Abnahme: 668 Python-Tests grün, 9 Frontend-Chatprüfungen grün,
`test_layout.cjs` grün (Zeitgrenzen, Gate-Geometrie, alle Licht-/Handygrößen,
Neumalen, Leinwandzahl, Körnung, Pinselgrenzen/Resize, Restzähler und Dialog).
JavaScript-Syntax geprüft. Screenshots liegen auf dem Arbeitsrechner unter
`C:/Users/felix/aios-work-20260903/screenshots/`.

Produktive Dateien wurden nur nach Abgleich ihres Ausgangs-Hashes ersetzt.
Bestehende Änderungen anderer Arbeiten sind erhalten; die unmittelbaren
Vorgänger liegen als `.before-shared-layout-20260903` neben den geänderten
Dateien. Keine fremden Änderungen wurden pauschal committed oder zurückgesetzt.
