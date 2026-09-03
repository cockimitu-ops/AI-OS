extends RefCounted
## Vorlage. Echte Fassung als `AIOSSecret.gd` daneben legen - die ist per
## .gitignore ausgeschlossen und gehört nicht ins Repository.
##
## Das Repository ist öffentlich. Der Token gehört deshalb nicht in
## AIOSClient.gd, wo er vorher stand: Tailscale ist zwar die eigentliche
## Zugriffsgrenze, aber ein im Klartext veröffentlichter Bearer-Token wäre
## trotzdem verbrannt.

const TOKEN := "hier-den-echten-Token-eintragen"
