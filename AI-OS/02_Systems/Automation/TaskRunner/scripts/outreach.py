#!/usr/bin/env python3
"""Turns qualified DMARC leads into print-ready German business letters.

The bottleneck this removes: dmarc_prospector.py produces hundreds of
qualified leads, and every one of them then needs a human to research the
business, write a letter, and address an envelope. That is the "less human
time to make money" step - the leads were never the scarce part.

Postal mail specifically, and for a legal reason, not a stylistic one:
UWG 7 Abs. 2 Nr. 2 requires prior express consent for unsolicited
advertising email (B2B included), and cold calls need "mutmassliche
Einwilligung". An addressed letter is unrestricted. So the one channel this
data is shaped for is also the one that is clearly allowed.

NO PER-LETTER MODEL CALLS, deliberately. Everything that varies between
letters is a fact already in the ledger - business name, address, which
record is missing, which mail provider. A template renders that in
microseconds for zero tokens, and - the real reason - it cannot invent a
security claim about a real company's domain. An LLM writing 500 letters
about other people's DNS is a hallucination surface with legal consequences,
for no gain over string substitution.

Output is one self-contained HTML file, printed from a browser. No LaTeX, no
reportlab, no wkhtmltopdf - nothing to install on a Celeron, and the page
break behaviour is CSS the user can see and adjust.

Stdlib only, same constraint as the rest of scripts/.
"""
import argparse
import html
import json
import os
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TASK_RUNNER_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)
import dmarc_prospector as prospector  # noqa: E402

OUTREACH_DIR = os.path.join(TASK_RUNNER_DIR, "outreach")
CONTACTED_PATH = os.path.join(OUTREACH_DIR, "contacted.json")

# German letter post is ~EUR 0.95 apiece. A batch is a paid experiment, not a
# mailing list: 25 letters is ~EUR 24, enough to measure a response rate
# before committing real money to 500.
DEFAULT_BATCH = 25
POSTAGE_EUR = 0.95

# Filled from .env so no personal data is committed to the repo. Without
# these the letter has no sender, which is both useless and - for commercial
# post - legally wrong, so rendering refuses rather than emitting placeholders.
SENDER_FIELDS = ("OUTREACH_SENDER_NAME", "OUTREACH_SENDER_STREET",
                 "OUTREACH_SENDER_CITY", "OUTREACH_SENDER_EMAIL",
                 "OUTREACH_SENDER_PHONE")


def load_contacted():
    try:
        with open(CONTACTED_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def mark_contacted(domains, channel="post"):
    """Records who has been written to. A business that gets the same cold
    letter twice is a business that has learned to bin it."""
    contacted = load_contacted()
    stamp = datetime.now(timezone.utc).isoformat()
    for domain in domains:
        contacted[domain] = {"channel": channel, "at": stamp}
    os.makedirs(OUTREACH_DIR, exist_ok=True)
    tmp = CONTACTED_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(contacted, f, indent=1, sort_keys=True)
    os.replace(tmp, CONTACTED_PATH)
    return len(contacted)


def finding_sentence(result):
    """The one factual, verifiable claim the whole letter rests on.

    Deliberately describes only what the domain publishes - a DNS record that
    is absent or permissive. It never claims their systems were tested,
    scanned, or accessed, because they were not: this is a public DNS lookup.
    Keeping that distinction sharp in the copy is what separates this from
    the scare-mail every business owner already ignores."""
    dmarc, spf = result.get("dmarc"), result.get("spf")
    if dmarc is None:
        return ("Für Ihre Domain ist kein DMARC-Eintrag veröffentlicht. "
                "Das bedeutet: Es gibt keine hinterlegte Regel, die "
                "Empfänger-Server anweist, gefälschte Absender in Ihrem "
                "Namen abzulehnen.")
    if dmarc == "none":
        return ("Ihre Domain veröffentlicht zwar einen DMARC-Eintrag, aber "
                "mit der Richtlinie p=none. Diese Einstellung beobachtet nur "
                "und weist gefälschte Absender nicht ab - sie schützt also "
                "noch nicht.")
    return ("Ihre Domain veröffentlicht einen DMARC-Eintrag mit der "
            "Richtlinie p=quarantine. Das ist ein guter Zwischenschritt, "
            "aber noch nicht die volle Absicherung.")


def spf_sentence(result):
    spf = result.get("spf")
    if spf is None:
        return ("Zusätzlich ist kein SPF-Eintrag hinterlegt, der festlegt, "
                "welche Server überhaupt in Ihrem Namen versenden dürfen.")
    if spf in ("+all", "?all", "none"):
        return ("Zusätzlich ist Ihr SPF-Eintrag so gesetzt, dass er faktisch "
                "jeden Absender zulässt.")
    return ""


def render_letter(entry, result, sender, today):
    """One DIN-5008-ish business letter as an HTML block."""
    address = entry["address"]
    name = entry.get("name") or entry["domain"]
    provider = result.get("provider", "unknown")
    provider_line = ""
    if provider not in ("unknown", "no MX"):
        provider_line = (f"Ihre E-Mail läuft über {html.escape(provider)}; "
                         "dort ist die nötige Änderung in der Regel in etwa "
                         "einer Stunde erledigt.")

    e = html.escape
    parts = [f'<section class="letter">',
             f'<div class="sender-line">{e(sender["name"])} · '
             f'{e(sender["street"])} · {e(sender["city"])}</div>',
             f'<div class="recipient">{e(name)}<br>{e(address["street"])}<br>'
             f'{e(address["postcode"])} {e(address["city"])}</div>',
             f'<div class="date">{e(sender["city"].split(",")[0])}, {today}</div>',
             '<h1>Ihre Domain kann derzeit von Fremden als Absender '
             'benutzt werden</h1>',
             '<p>Sehr geehrte Damen und Herren,</p>',
             f'<p>ich habe einen öffentlich abrufbaren DNS-Eintrag Ihrer '
             f'Domain <strong>{e(entry["domain"])}</strong> geprüft - also '
             f'dieselbe Information, die jeder Mail-Server weltweit abfragen '
             f'kann. Dabei ist mir Folgendes aufgefallen:</p>',
             f'<p class="finding">{e(finding_sentence(result))} '
             f'{e(spf_sentence(result))}</p>',
             '<p>Praktisch heißt das: Jemand kann E-Mails verschicken, die '
             'für Ihre Kunden aussehen, als kämen sie von Ihnen - etwa eine '
             'Rechnung mit geänderter Bankverbindung. Der Schaden trifft '
             'zuerst Ihre Kunden und dann Ihren Ruf.</p>']
    if provider_line:
        parts.append(f'<p>{provider_line}</p>')
    parts += [
        '<p>Ich richte das als Festpreis ein: <strong>DMARC, SPF und DKIM '
        'korrekt konfiguriert, mit einer verständlichen Dokumentation '
        'dessen, was geändert wurde - 249 € netto.</strong> Dafür ändere ich '
        'ausschließlich DNS-Einträge; an Ihren Rechnern oder Postfächern '
        'wird nichts angefasst.</p>',
        '<p>Wenn Sie das lieber selbst oder mit Ihrer bisherigen IT-Betreuung '
        'umsetzen möchten: Der Befund oben ist frei prüfbar, und ich sende '
        'Ihnen die genauen Werte auf Anfrage gerne kostenlos zu. Mir ist '
        'wichtiger, dass es gemacht wird, als dass ich es mache.</p>',
        '<p>Bei Interesse erreichen Sie mich unter '
        f'{e(sender["phone"])} oder {e(sender["email"])}.</p>',
        '<p class="sig">Mit freundlichen Grüßen<br><br><br>'
        f'{e(sender["name"])}</p>',
        '<p class="footnote">Hinweis: Ich habe ausschließlich einen '
        'öffentlichen DNS-Eintrag abgefragt. Es fand kein Zugriff und kein '
        'Test an Ihren Systemen statt.</p>',
        '</section>']
    return "\n".join(parts)


CSS = """
@page { size: A4; margin: 25mm 20mm 20mm 25mm; }
body { font-family: Georgia, 'Times New Roman', serif; font-size: 11pt;
       line-height: 1.5; color: #111; background: #fff; margin: 0; }
.letter { page-break-after: always; max-width: 170mm; margin: 0 auto 20mm; }
.letter:last-child { page-break-after: auto; }
.sender-line { font-size: 7.5pt; color: #444; border-bottom: .4pt solid #999;
               padding-bottom: 2mm; margin-bottom: 8mm; }
.recipient { margin-bottom: 12mm; line-height: 1.4; }
.date { text-align: right; margin-bottom: 10mm; font-size: 10pt; }
h1 { font-size: 12.5pt; margin: 0 0 6mm; line-height: 1.35; }
p { margin: 0 0 4mm; }
.finding { border-left: 2.5pt solid #444; padding-left: 4mm; }
.sig { margin-top: 8mm; }
.footnote { margin-top: 10mm; font-size: 8pt; color: #555;
            border-top: .4pt solid #ccc; padding-top: 2mm; }
@media screen { body { background:#f4f4f4; padding: 20px; }
  .letter { background:#fff; padding: 25mm 20mm; margin-bottom: 20px;
            box-shadow: 0 1px 4px rgba(0,0,0,.2); } }
"""


def build_batch(domains, results, contacted, limit):
    """Best mailable leads, worst posture first, never repeating a contact."""
    candidates = []
    for domain, result in results.items():
        if domain in contacted:
            continue
        entry = domains.get(domain)
        if not entry or not entry.get("address"):
            continue
        if result.get("score", 0) < 6:
            continue
        candidates.append((result, entry))
    candidates.sort(key=lambda pair: (-pair[0]["score"], pair[1]["domain"]))
    return candidates[:limit]


def main():
    ap = argparse.ArgumentParser(description="Generate print-ready DMARC outreach letters.")
    ap.add_argument("--limit", type=int, default=DEFAULT_BATCH)
    ap.add_argument("--out", default=os.path.join(OUTREACH_DIR, "letters.html"))
    ap.add_argument("--commit", action="store_true",
                    help="mark this batch as contacted (do this only after actually posting)")
    args = ap.parse_args()

    missing = [f for f in SENDER_FIELDS if not os.environ.get(f)]
    if missing:
        print("Cannot render letters - these are unset in .env:", file=sys.stderr)
        for field in missing:
            print(f"  {field}", file=sys.stderr)
        print("\nA commercial letter needs a real sender; emitting placeholder "
              "letters would be worse than emitting none.", file=sys.stderr)
        return 2

    sender = {
        "name": os.environ["OUTREACH_SENDER_NAME"],
        "street": os.environ["OUTREACH_SENDER_STREET"],
        "city": os.environ["OUTREACH_SENDER_CITY"],
        "email": os.environ["OUTREACH_SENDER_EMAIL"],
        "phone": os.environ["OUTREACH_SENDER_PHONE"],
    }

    domains = prospector._load(prospector.DOMAINS_PATH, {})
    results = prospector._load(prospector.RESULTS_PATH, {})
    contacted = load_contacted()
    batch = build_batch(domains, results, contacted, args.limit)
    if not batch:
        print("No uncontacted mailable leads. Run --audit for more, or raise --limit.")
        return 0

    today = datetime.now().strftime("%d.%m.%Y")
    letters = [render_letter(entry, result, sender, today) for result, entry in batch]
    page = (f"<!doctype html><html lang=de><meta charset=utf-8>"
            f"<title>DMARC-Anschreiben ({len(letters)})</title>"
            f"<style>{CSS}</style>{''.join(letters)}</html>")

    os.makedirs(OUTREACH_DIR, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(page)

    print(f"{len(letters)} letters -> {args.out}")
    print(f"Postage at EUR {POSTAGE_EUR:.2f}: EUR {len(letters) * POSTAGE_EUR:.2f}")
    print(f"One sale at 249 EUR covers {int(249 / (len(letters) * POSTAGE_EUR))}x this batch.")
    for result, entry in batch[:5]:
        print(f"  [{result['score']}] {entry.get('name','?')[:38]:40} {entry['domain']}")
    if len(batch) > 5:
        print(f"  ... and {len(batch) - 5} more")

    if args.commit:
        total = mark_contacted([e["domain"] for _, e in batch])
        print(f"\nMarked {len(batch)} as contacted ({total} total).")
    else:
        print("\nNot marked as contacted. Re-run with --commit once actually posted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
