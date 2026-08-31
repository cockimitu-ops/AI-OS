# Watches

Purpose: Saved Kleinanzeigen searches polled by `scripts/kleinanzeigen_sniper.py`. One Markdown file per search, same drop-a-file-in-a-folder convention `schedules/` uses — adding a search must never require sudo or a code change.
Last Updated: 2026-08-31
Status: Active — five watches live, timer enabled 2026-08-31
Stability: Dynamic
Related Documents: [[02_Systems/Automation/TaskRunner/README|TaskRunner]], [[10_Projects/LocalArbitrage/README|LocalArbitrage]]

---

## Why this exists
[[10_Projects/LocalArbitrage/README|LocalArbitrage]] states its own edge plainly: urgency sellers want *gone today*, and the buyer who messages first gets the item. That makes latency the whole game. A listing found 20 minutes late is usually a listing someone else already collected. This closes that gap without anyone refreshing a browser.

It serves two loops at once — the broken-phone flips and the general arbitrage categories — which is why the watch set deliberately contains contradictory filters (see `werkzeug.md` vs `handys_defekt.md` below).

## Directive grammar
Everything below the directives is prose for humans and is ignored by the parser.

| Directive | Required | Meaning |
|---|---|---|
| `search:` | yes¹ | Search keyword. Umlauts belong here — they change the results. |
| `url:` | yes¹ | Full URL instead, for searches the keyword form can't express. Wins over `search:`. |
| `location:` | no | Kleinanzeigen location id. Default `4178` (Crimmitschau). |
| `radius:` | no | km. Default `30`. Also drives the distance filter. |
| `price:` | no | `min-max`, `-max`, or `min-`. Ads with no stated price always pass. |
| `require:` | no | Comma list; **at least one** must appear in title or description. |
| `exclude:` | no | Comma list; **none** may appear in title or description. |

¹ one of `search:` or `url:`.

Look up another location id:
```bash
curl 'https://www.kleinanzeigen.de/s-ort-empfehlungen.json?query=Zwickau'
```
(Zwickau is `3800`, Crimmitschau `4178`.)

## Two rules that are load-bearing
**Unpriced ads always pass the price filter.** "VB" or no number at all is the seller-doesn't-know signal LocalArbitrage's README targets. Filtering those out would remove the best finds while looking like it worked.

**A watch's first run alerts on nothing.** It records what is already listed and stays silent. Without this, adding a search means an instant burst of 25 "new" ads that aren't new — which trains you to ignore the alerts, the one failure mode that makes the tool worthless. Re-seed a watch deliberately with `--reseed`.

## Current watches
| File | Loop | Notes |
|---|---|---|
| `handys_defekt.md` | Phone flips | Wider radius (40km) — a phone fits in a pocket. |
| `iphone_defekt.md` | Phone flips | Higher ceiling; lock phrases excluded (see below). |
| `monitore.md` | Arbitrage | Verified ~25 listings in radius on 2026-08-31. |
| `werkzeug.md` | Arbitrage | Brand allowlist via `require:`. |
| `aufloesung.md` | Arbitrage | Pure urgency signal, no price filter, expect noise. |

`defekt` is excluded in `werkzeug.md` and *searched for* in `handys_defekt.md`. That is not an inconsistency: a dead tool battery costs more than the tool, while a broken phone is usually a soft-brick — the entire premise of that flip.

## Two live findings worth not re-learning
Both were found by running this against the real site on 2026-08-31, not by reasoning about it:

- **A bare `icloud` exclude drops the good ads.** "iPhone 13 Bastler — iCloud **frei**" advertises exactly the case worth buying. Substring excludes on one ambiguous word cut both ways; the watch excludes phrases (`icloud sperre`, `aktivierungssperre`) instead.
- **Kleinanzeigen pads results past the requested radius.** A 35km search returned seven ads at 196–200km. The distance filter in `matches()` drops those, with 5km slack because the site rounds ("ca. 30 km"). On a car-based flip a 200km round trip eats the entire margin.

## Tuning
Start with `aufloesung.md` — it is the noisiest by design and the most likely to produce one large win. Add to `exclude:` as junk arrives rather than tightening `price:`, which is what removes the good finds.

```bash
# See what would fire, send nothing, write no state:
/usr/bin/python3 scripts/kleinanzeigen_sniper.py --dry-run --only aufloesung
```

## On the site itself
Automated access isn't something Kleinanzeigen's terms invite, so this stays deliberately unremarkable: one request per watch, 2–5s apart, waking hours only, a real browser User-Agent, and nothing republished anywhere. It is a personal saved-search notifier, not a scraper feeding a product. If the requests ever start failing or getting blocked, the answer is to stop, not to work around it — the flips are the business, this is only a convenience on top of them.
