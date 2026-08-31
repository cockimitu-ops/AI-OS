# AI-OS Web Client

A thin HTTP layer over the existing TaskRunner: chat, three dashboards (money
board, DMARC leads, flip log), uploads, and downloads. `server.py` owns HTTP
mechanics, `api.py` owns handlers, `static/` is a vanilla-JS PWA with no build
step. Nothing here re-implements task queuing, agent routing or model logic —
it writes the same task files `dispatch_task.py` and `telegram_bridge.py` do.

Runs as `aios-webapp.service`, bound explicitly to the Tailscale IP
(`AIOS_WEB_BIND`, default `100.64.2.100:8787`) — never `0.0.0.0`. Tailscale is
the access boundary; the bearer token (`AIOS_WEB_TOKEN`) is defence in depth
on top of it, not instead of it.

## HTTPS, and why it is not cosmetic

The app is currently served over plain HTTP. Browsers only grant a **secure
context** over HTTPS (or localhost), and several things Felix wants are gated
on that, not on a padlock icon:

- **No service worker** → the app cannot be installed to the home screen at
  all. This is the whole reason "add to home screen" has never worked.
- **No `crypto.randomUUID`** → it is simply undefined. It ran inside
  `getThreadId()`, before any message can be sent, so on 2026-08-31 it took
  the entire chat down on Felix's phone with "crypto.randomUUID is not a
  function". `app.js` now falls back to `crypto.getRandomValues`, which does
  exist in an insecure context.
- **No web push**, if that is ever wanted. (Telegram already delivers
  notifications today and does it well — see the bridge.)

`tailscale cert` reports *"HTTPS cert support is not enabled/configured for
your tailnet"*. That is one switch in the Tailscale admin console
(https://login.tailscale.com/admin/dns → HTTPS Certificates → Enable) and
cannot be done from this machine.

Once it is on:

    scripts/enable_https.sh

That verifies the certificate, then puts `tailscale serve` in front of the
existing HTTP listener. The server never speaks TLS itself and does not need
to; `aios-webapp.service` is unchanged.

**HTTPS is a different origin.** `https://crypton.tail279eb7.ts.net` and
`http://100.64.2.100:8787` do not share localStorage, so the token and chat
thread on the old address do not carry over — open the `?token=…` link the
script prints rather than retyping a 43-character token on a phone.

## The install button

`static/index.html` has an "Installieren" button that stays hidden until the
browser fires `beforeinstallprompt`, which it only does when the app is
genuinely installable. Its absence is therefore a real diagnostic: no button
means not installable, and the reason is the certificate.

## Service worker caching

Network-first for the app shell, cache only as the offline fallback —
deliberately not the usual cache-first default. This app changes several
times a day, and a service worker serving last week's `app.js` is the classic
way a PWA gets stuck on a version its owner already fixed: invisible, because
the page loads perfectly, just wrong.

`/api/*` and `/downloads/*` are never cached. A stale dashboard would look
current without being current; a cached report holds real business names,
addresses and phone numbers that the server gates behind a token and a
browser cache does not.
