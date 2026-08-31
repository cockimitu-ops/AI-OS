# Kryptografie Grundlagen: Symmetrisch, Asymmetrisch, Hashing

Purpose: Diese Vorlesungsnotizen behandeln die Grundlagen der Kryptografie. Sie vergleichen symmetrische und asymmetrische Verschlüsselung, erklären AES-Blockchiffren un
Last Updated: 2026-08-31
Status: Active
Related Documents: [[10_Projects/CyberSecurityLearning/README|CyberSecurityLearning]], [[04_Agents/Study_Teacher|Study Teacher]]

---

## Summary
Diese Vorlesungsnotizen behandeln die Grundlagen der Kryptografie. Sie vergleichen symmetrische und asymmetrische Verschlüsselung, erklären AES-Blockchiffren und deren Betriebsmodi, gehen auf Eigenschaften von Hash-Funktionen und Passwörterschutz ein und erwähnen den Diffie-Hellman-Schlüsselaustausch sowie offene Fragen für die Klausurvorbereitung.

## Core Concepts
- Symmetrischer Schlüssel — gleicher Key zum ver- und entschlüsseln, schnell, Beispiel AES.
- Asymmetrischer Schlüssel — public/private keypair, langsam, Beispiele RSA / ECC.
- Hybride Verschlüsselung — Session Key wird symmetrisch verschlüsselt und über asymmetrische Verfahren ausgetauscht.
- AES — Block Cipher, verwendet 128-Bit-Blöcke und Keylängen von 128, 192 oder 256 Bit.
- ECB (Electronic Codebook) — ein AES-Modus, der niemals benutzt werden darf, da gleiche Blöcke zu gleichem Ciphertext führen (bekannt durch das Pinguin-Bild).
- CBC — ein AES-Modus, der einen IV (Initialization Vector) benötigt.
- CTR — ein AES-Modus, der aus einem Block Cipher einen Stream Cipher macht.
- Hashing — Einwegfunktion, nicht gleichbedeutend mit Verschlüsselung. Beispiele: SHA-256, SHA-3. MD5 und SHA1 gelten als kaputt (Kollisionen) und sollen nicht mehr verwendet werden.
- Salt — wird bei Passwörtern verwendet, um gegen Rainbow Tables zu schützen.
- bcrypt / argon2 — Passwort-Hashing-Verfahren, die by design langsam sind.
- Diffie-Hellman — Schlüsselaustausch über einen unsicheren Kanal (vom Professor mit Farben erklärt).
- Perfect Forward Secrecy — not defined in these notes.

## Action Items
- Perfect Forward Secrecy nochmal nachlesen.
- Folien 30-45 nacharbeiten.
- Übungsblatt 1 bis nächste Woche bearbeiten.

## Flashcards
Q: Was ist der Hauptunterschied zwischen symmetrischer und asymmetrischer Verschlüsselung laut den Notizen?
A: Symmetrische Verschlüsselung nutzt denselben Key zum Ver- und Entschlüsseln und ist schnell (z. B. AES). Asymmetrische Verschlüsselung nutzt ein Public/Private Keypair, ist langsamer und umfasst Verfahren wie RSA oder ECC.
Q: Warum darf der ECB-Modus bei AES niemals verwendet werden?
A: Weil gleiche Klartextblöcke zum gleichen Ciphertext führen (anschaulich bekannt durch das Pinguin-Bild).
Q: Welcher AES-Modus benötigt einen IV und welcher macht einen Stream Cipher daraus?
A: CBC benötigt einen IV, während CTR aus dem Block Cipher einen Stream Cipher macht.
Q: Warum sind MD5 und SHA1 nicht mehr zu verwenden?
A: Sie sind kaputt, da Kollisionen auftreten können.
Q: Wozu dient ein Salt bei Passwörtern?
A: Ein Salt schützt Passwörter vor Angriffen mit Rainbow Tables.
Q: Warum werden bcrypt oder argon2 für Passwörter eingesetzt?
A: Weil diese Hash-Verfahren by design langsam sind.

---

Source: `vl02_krypto_basics.md` (raw note, kept unchanged in the study inbox). Processed by Study Teacher — the source note remains the authority; anything below that contradicts it is this pass's error.

---

*Written by TaskRunner on 2026-08-31. Generated content — review before treating as established fact.*
