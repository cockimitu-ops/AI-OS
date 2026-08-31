#!/usr/bin/env bash
# Puts the AI-OS web client behind HTTPS on the tailnet.
#
# Run this AFTER enabling HTTPS certificates in the Tailscale admin console:
#   https://login.tailscale.com/admin/dns  ->  "HTTPS Certificates" -> Enable
#
# Why it matters beyond the padlock: a browser only grants a "secure context"
# over HTTPS, and without one there is no service worker, so the app cannot
# be installed to the home screen at all. crypto.randomUUID() is missing too -
# that one took the whole chat down on Felix's phone on 2026-08-31 until it
# was given a fallback.
#
# The web server itself does not speak TLS and does not need to: `tailscale
# serve` terminates it and proxies to the existing HTTP listener, so nothing
# about aios-webapp.service changes.
set -euo pipefail

BIND="${AIOS_WEB_BIND:-100.64.2.100}"
PORT="${AIOS_WEB_PORT:-8787}"

name="$(tailscale status --json | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')"
echo "Tailnet name: $name"

if ! tailscale cert "$name" >/dev/null 2>&1; then
  echo
  echo "HTTPS certs are still not enabled for this tailnet."
  echo "Enable them here, then re-run this script:"
  echo "  https://login.tailscale.com/admin/dns  ->  HTTPS Certificates -> Enable"
  exit 1
fi

echo "Certificate OK. Putting the app behind https://$name ..."
tailscale serve --bg --https=443 "http://${BIND}:${PORT}"

echo
echo "Done. Open this on your phone (the token comes along, so no typing):"
echo "  https://${name}/?token=\$AIOS_WEB_TOKEN"
echo
echo "Note: HTTPS is a DIFFERENT ORIGIN than http://${BIND}:${PORT}, so the"
echo "browser starts with an empty localStorage there - the token and your"
echo "chat history on the old address do not carry over. That is why the"
echo "?token= link above matters."
echo
echo "Then: open it, tap 'Installieren' in the header (the button only appears"
echo "when the browser agrees the app is really installable), and it lands on"
echo "your home screen as a real app - own icon, no browser bars."
