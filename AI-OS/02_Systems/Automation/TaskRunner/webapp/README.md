# AI-OS Web Client

A thin HTTP layer over the existing TaskRunner: chat, the dashboards (money
board, DMARC leads, snipes, flip log, costs), live phone control, uploads, and
downloads. `server.py` owns HTTP mechanics, `api.py` owns handlers, `static/`
is a vanilla-JS PWA with no build step. Nothing here re-implements task
queuing, agent routing or model logic — it writes the same task files
`dispatch_task.py` and `telegram_bridge.py` do.

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


## The live phone picture

`/device-stream?device=<id>&token=<t>` holds one response open and pushes JPEG
frames into it as `multipart/x-mixed-replace`; the browser shows that in a
plain `<img>`. The frames come from `scripts/phone_stream.py`: the phone's own
`screenrecord --output-format=h264` piped over adb into ffmpeg.

Why it exists, measured on the real phones on 2026-09-01:

    adb shell "input tap x y"      0.16 s
    screencap -p + adb pull        1.10 - 1.40 s
    live stream, input -> visible  0.47 s median (0.11 s best)

The tap was never the slow part; the picture was. The panel used to take one
still per interaction, so every button press cost more than a second of
staring at a dimmed old frame — which is what "die direkte fernsteuerung ist
mir zu langsam" meant.

Two things about this endpoint are unlike everything else here:

- **The token is in the URL.** An `<img>` request carries no `Authorization`
  header and there is no way to give it one. Same-origin, over the tailnet,
  and the token still has to be right — but it is the one place it travels
  this way.
- **ffmpeg is a hard dependency** (`apt install ffmpeg`). Without it the
  stream refuses to start and the panel falls back to single screenshots.

A stream with no viewers shuts itself down after 20 seconds. Leaving the
Geräte tab, backgrounding the app, or closing the page all end it — a phone
screen should not keep being recorded into a buffer nobody is reading.

**A dark display composites no frames at all**, so screenrecord has nothing to
encode and the picture legitimately never arrives. The stage says "Bildschirm
aus" and offers a wake button rather than showing a green LIVE badge over a
black rectangle.

## Chat: a real Claude Code session

The Chat tab does **not** talk to the local worker. It continues the actual
Claude Code session Felix has at his desk — `claude -p --resume <id>` — so the
conversation is one conversation whether he is at the machine or on his phone.
`/api/claude-sessions` lists them (newest first, with an estimated cost),
`/api/claude-transcript` reads one off disk, `/api/claude-send` starts a turn
and `/api/claude-result` collects it. See `scripts/claude_chat.py`.

**Sends run with `--dangerously-skip-permissions`.** That is Felix's explicit
decision, taken with the alternative in front of him: a headless run cannot
ask, so anything less either fails on the first real task or silently does
half of it. What it means in practice: a message typed on a phone can change
anything on this machine, with nobody watching. The boundary is the tailnet
plus the bearer token, and nothing else.

Sends are detached and write their result to a file under `claude_jobs/`, so
an answer survives the app being closed, the service restarting, or the phone
changing network — the same lesson `/api/chat` learned when a 93-second reply
arrived as "failed to fetch".

The local worker chat is still there behind `/api/chat` and is what the
Telegram bridge uses.

## Costs

`/api/costs` (`scripts/cost_board.py`) answers "was kostet der Spass" with two
deliberately separate halves:

- **OpenRouter** — real prepaid money. Balance and usage come live from
  OpenRouter's own API; `spend_guard.py` holds the monthly cap and, since
  2026-09-01, a per-call log so the screen can say *what* the money went on.
  This is the half with the top-up link, because it is the half that runs out.
- **Claude** — a list-price estimate computed from the transcripts' own token
  counts, priced with the real cache-write and cache-read rates rather than
  the input rate. Nothing is billed per turn; it runs on Felix's subscription.
  Everything that returns it says so, because presenting an estimate beside a
  real balance without saying which is which would be the most misleading
  thing this screen could do.

Per-transcript results are cached on `(mtime, size)` — the session archive is
~45 MB and one session alone is 23 of them.