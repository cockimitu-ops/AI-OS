# Valuation Method

Purpose: How a listing gets priced before money moves. Deliberately structured to keep AI away from the one job it's worst at.
Last Updated: 2026-08-13
Status: Active — not yet tested against real purchases
Related Documents: [[10_Projects/LocalArbitrage/README|LocalArbitrage]], [[Transaction_Log]]

---

## The Core Rule
**AI does not estimate resale prices. Sold listings do.**

This is the single most important line in the project. An AI asked "what's this worth?" will produce a confident, plausible, specific number with no underlying data — and a hallucinated €140 estimate on a €60 item is how you lose real money, repeatedly, while feeling well-informed. Price comes from what comparable items *actually sold for*, not what a model guesses.

- eBay → search item → filter **Verkaufte Artikel** (sold, not active listings)
- Kleinanzeigen active listings show asking prices, which are aspirational — use as a ceiling signal only, never as the estimate
- No sold comps found = no purchase. An item you can't price is a gamble, not arbitrage.

## Where AI Is Genuinely Useful
Different jobs, none of them "guess the price":
- **Identify** — read a blurry photo or partial model number, tell you *what the thing actually is*. This is the highest-value AI task here, because misidentification is the most common source of underpricing (both the seller's and yours).
- **Interrogate** — given the listing text and photos, what's suspicious? What's likely broken? What's the seller not saying? What should I test in person?
- **Question list** — what to ask the seller before driving out there.
- **Listing copy** — title, description, keywords for the resale listing. Genuinely good at this.

## The Decision Card
Every candidate gets reduced to this before any drive happens:

```
Item:            Bosch GSR 18V drill
Asking:          €45
Sold comps:      €95 / €110 / €88  (median €95, n=3)
Max buy price:   €50
Est. net:        €40  (after fees + 22km fuel)
Time estimate:   3h end-to-end
€/hour:          ~€13
Risk:            Battery health unknown — test before paying
Verdict:         GO / NO
```

If €/hour comes out below what your time is otherwise worth, it's a NO regardless of the margin looking nice in percentage terms. A 100% markup on a €12 item is still €12.

## Multi-Model Roles (optional, not required)
Scout finds candidates → Analyst argues *against* buying → you decide. The Analyst role matters more than the Scout: the failure mode in flipping is talking yourself into marginal buys, and a model explicitly tasked with finding reasons to walk away is a real counterweight.

## Not Yet Validated
Zero purchases made. Every number above is a template, not evidence. The first 10 flips exist to test whether these estimates hold.
