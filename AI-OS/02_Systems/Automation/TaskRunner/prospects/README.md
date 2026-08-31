# Prospects

Purpose: Finds local businesses whose email domain can be spoofed, and ranks them by how good a lead they are. Feeds the DMARC remediation business — leg 2 of the [[Income_Portfolio]] sequence.
Last Updated: 2026-08-31
Status: Active — 3,873 domains discovered, nightly audit live 2026-08-31
Stability: Dynamic
Related Documents: [[02_Systems/Automation/TaskRunner/README|TaskRunner]], [[10_Projects/MoneyMaking/Income_Portfolio|Income Portfolio]]

---

## The premise, and what the data says about it
Most German SMBs publish no DMARC record, which means anyone can send email as them. It is a risk an owner grasps in one sentence, and roughly a 2h fix worth €150–300. The bottleneck was never the fix — it was knowing who to call.

Measured on the first 150 randomly-sampled local domains, 2026-08-31:

| Finding | Share |
|---|---|
| No DMARC record at all | **~39%** |
| DMARC `p=none` (monitors, enforces nothing) | ~24% |
| `quarantine` or `reject` (real protection) | ~17% |
| Qualified leads (score ≥ 6) | **71 of 150** |

Nearly half of local businesses are a qualified lead. That is the business case, measured rather than assumed.

## Strictly passive, and it must stay that way
Two data sources, both public and both built to be queried:

- **OpenStreetMap via Overpass API** — which local businesses have a website at all. Open data (ODbL), a public API, no scraping of anybody's site.
- **Public DNS (TXT, MX) via `dig`** — reading a domain's published records is not a scan, not a probe, and not access to anything of theirs. It is reading a phone book they published.

Nothing here connects to a prospect's server, tests a login, sends mail, or touches a port. **If a change would require any of that, it does not belong in this folder — it belongs behind a signed engagement.** That line is the difference between prospecting and an offence under §202a StGB, and it is not a fine one.

## How it runs
| When | Unit | What |
|---|---|---|
| Nightly 01:30 | `aios-prospector.timer` | DNS audit of up to 1,200 domains due for a check |
| Monthly, 1st 01:00 | `aios-prospector-discover.timer` | Refresh the domain list from OpenStreetMap |
| Daily 07:00 | `aios-morning.timer` | Top 3 *new* leads appear in the morning brief |

Each domain is re-audited every 7 days — a prospect who fixes their DMARC stops being a prospect. At ~3,900 domains that is ~560/night in steady state, comfortably inside the 1,200 budget.

## Scoring
Higher is a better lead. The weights encode the sales argument, not a security grade.

| Condition | Points |
|---|---|
| No DMARC record | +4 |
| DMARC `p=none` | +2 |
| DMARC `p=quarantine` | +1 |
| No SPF, or SPF `?all`/`+all` (authorises everyone) | +3 |
| SPF `~all` (softfail) | +1 |
| Has MX **and** already scores above zero | +2 |

Max 9. The MX bonus only applies to a domain that already has a weakness — mail flow amplifies risk, it isn't one by itself. A domain with `p=reject` and `-all` scores **0** and must never be called: they already did it, and pitching them wastes the only thing this list exists to save.

## Three findings from the first live run
Each of these would have produced a wrong phone call rather than an error:

- **DMARC inherits from the organizational domain (RFC 7489).** A subdomain with no record of its own is covered by its parent's policy. Checking only `_dmarc.<subdomain>` reported "no DMARC" for domains that were actually protected — a false positive that becomes a cold call telling someone about a problem they already fixed.
- **A subdomain's owner usually cannot publish DMARC for it.** `agentur.barmenia.de` is an insurance agent on the insurer's corporate domain; that zone is Barmenia's, not his. He is not a bad lead, he is the wrong person entirely. All subdomains are dropped — on a 4,000-name cold list, precision beats recall.
- **Auditing alphabetically shows A-names for a week.** The morning brief opened with *Adler-Apotheke, AED-Service, Ärztehaus…* because the audit walked the list in sorted order. The never-checked queue is shuffled (seeded per day, so a rerun is stable).

Also worth keeping: chains are dropped by location count, and shared-platform pages (`*.apotheken-website-vorschau.de`) by parent-domain reuse. Both have IT departments or a platform operator; neither is the customer.

## Using it
```bash
/usr/bin/python3 scripts/dmarc_prospector.py --report --limit 20   # current best leads
/usr/bin/python3 scripts/dmarc_prospector.py --audit --limit 50    # audit 50 now
/usr/bin/python3 scripts/dmarc_prospector.py --discover            # refresh from OSM
```

Areas are configured in `areas.md` — three directives per area, coordinates read off openstreetmap.org.

`domains.json`, `results.json`, and `reported.json` are runtime state and gitignored. `reported.json` is what stops the morning brief from showing the same five businesses every day; deleting it makes every lead new again.

## How you are allowed to contact them (read before the first call)
Building the list is legal. Cold outreach in Germany is the part with rules, and they are stricter than the US-centric advice most sales content assumes. **UWG §7** in short:

- **Cold email — effectively not allowed.** Unsolicited advertising email needs prior express consent (§7 Abs. 2 Nr. 2), and this applies to B2B too, not just consumers. It is the obvious move and the one that carries real Abmahnung risk.
- **Cold calling a business — needs "mutmaßliche Einwilligung"** (presumed consent, §7 Abs. 2 Nr. 1): a concrete reason to believe this specific business would want this specific call, from their line of work. Defensible for an IT-security fix to a company that plainly transacts by email; not a blanket permission.
- **Postal mail — allowed.** Old-fashioned, unrestricted, and against 660 local businesses genuinely competitive.
- **Walking in — allowed**, and the car makes it the natural fit with LocalArbitrage's radius.
- Their published contact form is an invitation to use it; that is a different thing from cold email.

None of this is legal advice and it is worth ten minutes with the actual text of §7 before the first campaign — but the practical read is that the *email* channel this list looks tailor-made for is the one channel to avoid, and letter or in-person is both legal and more differentiated anyway.

Second point, smaller: some entries carry a person's name (a sole trader's practice), which makes the list personal data under GDPR. Keep it on the server, do not publish it, and delete on request. That is why `domains.json`/`results.json` are gitignored rather than committed.

## What this does not do
It finds and ranks prospects. It does not contact anyone, write the outreach, or verify that a business will buy — and the conversion rate is unknown until the calls happen. A ranked list of 71 qualified leads is the input to a sales process, not a substitute for one.
