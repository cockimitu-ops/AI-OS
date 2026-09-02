#!/usr/bin/env bash
# One-time pairing for the Pico 4, run with the headset on USB.
#
# Everything here has to happen once, at the cable, and cannot be done from
# the server afterwards: the headset has to be told to trust this machine,
# and told to listen on the network. After that it is just another device in
# the panel.
#
# Before running: enable developer mode in the PICO app on the phone
# (Settings -> the headset -> Developer Mode), then plug the headset in and
# put it on - the authorisation prompt appears inside the headset and cannot
# be accepted from outside it.
set -euo pipefail

APK=""
if [ "${1:-}" = "--install-tailscale" ]; then
  APK="${2:-}"
  [ -f "$APK" ] || { echo "APK nicht gefunden: $APK" >&2; exit 1; }
fi

command -v adb >/dev/null || { echo "adb fehlt" >&2; exit 1; }

echo "== Angeschlossene Geräte =="
adb devices -l

SERIAL="$(adb devices | awk 'NR>1 && $2=="device" && $1 !~ /:/ {print $1; exit}')"
if [ -z "$SERIAL" ]; then
  echo
  echo "Kein per USB verbundenes Gerät im Zustand 'device'." >&2
  echo "Wenn dort 'unauthorized' steht: Headset aufsetzen und die Abfrage" >&2
  echo "bestätigen - sie erscheint IM Headset, nicht auf dem Bildschirm." >&2
  exit 1
fi
echo
echo "Verwende $SERIAL"

MODEL="$(adb -s "$SERIAL" shell getprop ro.product.model | tr -d '\r')"
echo "Modell: $MODEL"
case "$MODEL" in
  *[Pp][Ii][Cc][Oo]*|*A8*|*PA*) ;;
  *) echo "Warnung: sieht nicht nach einem Pico aus - trotzdem weiter." >&2 ;;
esac

if [ -n "$APK" ]; then
  echo
  echo "== Tailscale wird installiert =="
  # Ohne Tailscale ist das Headset nur im heimischen WLAN erreichbar. Mit
  # Tailscale gilt für den Pico dasselbe wie für die Handys: eine Adresse,
  # die überall funktioniert.
  adb -s "$SERIAL" install -r "$APK"
  echo "Installiert. Tailscale im Headset öffnen und anmelden, dann diesen"
  echo "Befehl erneut ausführen (ohne --install-tailscale)."
fi

echo
echo "== Netzwerk-Debugging einschalten =="
adb -s "$SERIAL" tcpip 5555
sleep 2

# Die Adresse, unter der der Server das Headset später findet. Tailscale
# zuerst: eine 100.x-Adresse funktioniert auch ausserhalb der Wohnung, eine
# 192.168.x nur zuhause.
IP="$(adb -s "$SERIAL" shell ip -4 addr show 2>/dev/null \
      | grep -oE 'inet 100\.[0-9.]+' | head -1 | awk '{print $2}')"
[ -n "$IP" ] || IP="$(adb -s "$SERIAL" shell ip -4 addr show wlan0 2>/dev/null \
      | grep -oE 'inet [0-9.]+' | head -1 | awk '{print $2}')"

if [ -z "$IP" ]; then
  echo "Konnte keine IP-Adresse auslesen - im Headset unter WLAN nachsehen." >&2
  exit 1
fi

echo "Adresse: $IP:5555"
adb connect "$IP:5555" || true
sleep 1
adb devices -l | grep "$IP" || echo "(noch nicht verbunden - Headset wach?)"

echo
echo "Fertig. Jetzt in /home/nost/AI-OS/.env eintragen:"
echo
echo "    AIOS_PICO_HOST=$IP:5555"
echo
echo "und dann:  sudo systemctl restart aios-webapp"
echo
echo "Das Headset taucht danach im Geräte-Tab auf. Kabel kann weg."
