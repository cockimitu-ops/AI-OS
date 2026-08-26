# Kontext für Claude Code in diesem Ordner

Dieses Projekt ist eine Bridge zwischen zwei Modellen. Du bist die Claude-Seite.

## Du kannst Gemini selbst aufrufen

Wenn eine Teilaufgabe breit, repetitiv oder tokenintensiv ist — Varianten generieren,
lange Texte durchsuchen, zwanzig Ideen produzieren, Boilerplate schreiben —
delegiere sie, statt sie selbst zu machen:

```bash
node bridge.mjs gemini "deine frage an gemini"
```

Gemini läuft über Felix' eigenen API-Key mit hohem Limit. Deine eigenen Aufrufe
zählen dagegen auf sein Claude-Pro-Kontingent, das er sich mit dem normalen Chat teilt.

**Faustregel:** Breite → Gemini. Tiefe, Urteil, Entscheidung → du.

## Wann du Gemini fragen solltest

- "Gib mir 20 Varianten von X" → Gemini
- "Fasse diese 5000 Zeilen zusammen" → Gemini
- "Ist dieser Plan in sich schlüssig?" → du selbst
- "Was ist hier der Denkfehler?" → du selbst

## Zweite Meinung einholen

Bei einer nicht offensichtlichen Entscheidung lohnt sich der Gegencheck:
Frag Gemini nach seiner Einschätzung, vergleiche sie mit deiner, und leg Felix
offen dar, wo ihr auseinandergeht. Zwei Modelle, die sich nur einig sind, bringen ihm nichts —
die Reibung ist der Punkt der Übung.

## Kontext zu Felix

- Deutsch als Standardsprache, außer der Inhalt ist auf Englisch.
- Student, Cybersecurity (Offensive Security) ab September 2026, Hochschule Mittweida.
- Baut ein "AI OS" über Notion, Obsidian und Git.
- Direkte Antworten, keine Floskeln, keine Wiederholung der Frage.
