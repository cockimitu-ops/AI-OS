#!/usr/bin/env python3
"""Periodic status update: 10:00, 14:00, 18:00, 22:00 Europe/Berlin.

Built because the first live day of the sniper was unreadable from the phone.
It ran 80 times, correctly found nothing worth driving to, and said nothing at
all - which looks exactly like a service that died at 07:00. Silence is only
informative if you already trust the thing that is silent.

So the rule here is the inverse of the morning brief's: this message is sent
even when there is nothing to report, and it reports the *numbers behind the
silence* ("120 Anzeigen geprüft, 3 neu, 0 passend") rather than omitting the
section. A quiet update is a heartbeat; a missing update is a problem.

Distinct from morning_brief.py, which greets the day and carries the approved
todo list, and from evening_review.py, which is the 20:00 approval gate. This
one is only "what happened in the last few hours".

Stdlib only: systemd runs it under /usr/bin/python3, outside the venv.
"""
import os
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.dirname(SCRIPT_DIR))
import dmarc_prospector  # noqa: E402
import health_check  # noqa: E402
import kleinanzeigen_sniper  # noqa: E402
import spend_guard  # noqa: E402

NOTIFIER = os.path.join(SCRIPT_DIR, "send_telegram_notification.py")

LEADS_PER_UPDATE = 2

# strftime("%A") under systemd's C locale returns "Monday" next to a German
# body. Mapped by index rather than by setting a locale, which would depend on
# de_DE being generated on the box.
WEEKDAYS = ("Montag", "Dienstag", "Mittwoch", "Donnerstag",
            "Freitag", "Samstag", "Sonntag")


def format_sniper_section(stats):
    """The heartbeat. Always rendered, including - especially - when the answer
    is nothing, because "0 passend" and no message at all mean very different
    things and only one of them is trustworthy."""
    if not stats or not stats.get("runs"):
        return "Sniper: keine Läufe im Zeitraum (Timer gestoppt?)"
    # Deliberately NOT the cumulative listing count. Each run re-reads the same
    # page 1, so "2000 Anzeigen geprüft" after 80 runs would mean 25 ads
    # counted 80 times - a number that looks like throughput and is really
    # just the clock. Runs and genuinely-new ads are both true.
    parts = [f"Sniper: {stats['runs']} Läufe",
             f"{stats['new_ads']} neue Anzeigen"]
    parts.append(f"{stats['alerts']} passend" if stats["alerts"]
                 else "nichts passendes")
    return " · ".join(parts)


def format_spend_section():
    """Absent, not silent-when-zero, unlike the sniper line: if the paid
    tier is off (the default) there is nothing meaningful to report, and a
    permanent "$0.00 of $6.00" line would just be noise four times a day for
    a feature most days never touches. Reusing OPENROUTER_MONTHLY_BUDGET_USD
    keeps this consistent with aios_runner.py's own default without
    duplicating it - importing aios_runner here would pull in Open
    Interpreter for one float, so the env var is read directly instead."""
    if os.environ.get("OPENROUTER_PAID_ENABLED", "").lower() != "true":
        return None
    budget = float(os.environ.get(
        "OPENROUTER_MONTHLY_BUDGET_USD", spend_guard.DEFAULT_MONTHLY_BUDGET_USD))
    return spend_guard.status_line(budget)


def format_health_section(checks):
    """Only speaks up when something is wrong. The morning brief already gives
    the all-clear once a day; repeating it four more times trains you to skim."""
    bad = [(k, d) for k, (ok, d) in checks.items() if not ok]
    if not bad:
        return None
    return "\n".join([f"Achtung ({len(bad)}):"] + [f"  - {k}: {d}" for k, d in bad])


def build_update(stats, leads, checks, now=None):
    now = now or time.localtime()
    parts = [f"Status {time.strftime('%H:%M', now)} - {WEEKDAYS[now.tm_wday]}",
             "", format_sniper_section(stats)]
    spend = format_spend_section()
    if spend:
        parts += ["", spend]
    if leads:
        parts += ["", leads]
    health = format_health_section(checks)
    if health:
        parts += ["", health]
    return "\n".join(parts)


def main():
    stats = kleinanzeigen_sniper.take_stats()
    leads, shown = dmarc_prospector.morning_section(limit=LEADS_PER_UPDATE)
    message = build_update(stats, leads, health_check.run_checks())
    print(message)
    result = subprocess.run([sys.executable, NOTIFIER, message], timeout=30, check=False)
    # Same ordering rule as the morning brief: only burn the leads once the
    # message is actually out, or a Telegram outage silently eats them.
    if shown and result.returncode == 0:
        dmarc_prospector.mark_reported(shown)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
