VL2 Krypto 14.10

symmetrisch vs asymmetrisch
- symm: gleicher key zum ver+entschlüsseln, schnell, AES
- asym: public/private keypair, langsam, RSA / ECC
  -> in der praxis hybrid! session key symm, austausch über asym

AES block cipher 128 bit blöcke, keylen 128/192/256
modes: ECB (NIEMALS benutzen, gleiche blöcke -> gleiches ciphertext, pinguin bild),
CBC braucht IV, CTR macht stream draus

hashing != verschlüsselung. einweg. SHA-256, SHA-3
MD5 und SHA1 kaputt (collisions) nicht mehr benutzen

salt bei passwörtern - gegen rainbow tables
bcrypt/argon2 weil langsam by design

Diffie Hellman - key exchange über unsicheren kanal, prof hat das mit farben erklärt
MITM problem wenn nicht authentifiziert -> deswegen zertifikate

perfect forward secrecy?? nochmal nachlesen
klausurrelevant laut prof: modes of operation + warum ECB schlecht

TODO folien 30-45 nacharbeiten, übungsblatt 1 bis nächste woche
