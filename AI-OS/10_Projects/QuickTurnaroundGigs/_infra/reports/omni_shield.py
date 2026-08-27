CONFIG = {
    "title": "Competitor Analysis — Omni Shield",
    "eyebrow": "COMPETITIVE RESEARCH REPORT",
    "subtitle": "Standard Package — 5 Competitors, Comparison Matrix, SWOT, Recommendations",
    "accent": "#2F5D8A",
    "output": "omni-shield-competitor-analysis.pdf",
    "author": "Startup Competitor Analysis — Research & Briefing",
    "cover_note": [
        "Reference sample. Produced against a fictional brief (WiFi security for "
        "doctors' offices, homeowners, and small businesses) to validate the "
        "delivery process end-to-end. Every competitor, price, and complaint cited "
        "below is real and current as of the research date — nothing in this "
        "report is invented.",
    ],
    "sections": [
        {
            "eyebrow": "SECTION 1",
            "title": "Executive Summary",
            "content": [
                {"type": "p", "text":
                 "Omni Shield is entering a market split into two genuinely "
                 "different buyer types under one product idea: consumer/prosumer "
                 "home-security devices (Firewalla, Bitdefender BOX, Gryphon) and "
                 "compliance-driven small-business networking (IronWiFi, Cisco "
                 "Meraki Go). No competitor found here credibly serves all three "
                 "of Omni Shield's named segments — homeowners, SMBs, and doctors' "
                 "offices — at once. That gap is real, but it exists because the "
                 "segments have different buying triggers, not because nobody has "
                 "thought to combine them."},
                {"type": "label_p", "label": "Key finding:", "text":
                 "one plausible-looking competitor, CUJO AI, discontinued its "
                 "hardware entirely in 2021. It still surfaces in searches and "
                 "comparison articles as if current — exactly the kind of stale "
                 "data a competitor map built on one source would miss."},
                {"type": "h2", "text": "Top three recommendations"},
                {"type": "bullets", "items": [
                    "Don't build one undifferentiated product for three buyer "
                    "types — pick a lead segment.",
                    "The healthcare angle is the most defensible of the three: "
                    "compliance is a forcing function no consumer competitor "
                    "addresses at all.",
                    "Price against IronWiFi's compliance tier, not against "
                    "consumer hardware — a buyer who needs a signed BAA is not "
                    "price-comparing against a $99 router.",
                ]},
            ],
        },
        {
            "eyebrow": "SECTION 2",
            "title": "Market & Competitor Landscape",
            "content": [
                {"type": "label_p", "label": "Consumer / prosumer home security —",
                 "text": "hardware-plus-subscription or hardware-only devices "
                 "sold to individuals wanting an extra layer of home-network "
                 "protection. Firewalla, Bitdefender BOX, and Gryphon Guardian "
                 "compete here. Pricing runs $99–$599 upfront, subscriptions "
                 "(where they exist) $40–$150/year."},
                {"type": "label_p", "label": "SMB / compliance networking —",
                 "text": "cloud-managed WiFi sold to small organizations with a "
                 "specific access-control or audit requirement. Cisco Meraki Go "
                 "and IronWiFi compete here. Pricing is per-access-point or "
                 "per-user, recurring, and meaningfully higher over time than "
                 "consumer hardware."},
                {"type": "p", "text":
                 "Doctors' offices sit inside the second segment, not a third "
                 "one — a medical practice's actual requirement (WPA3-Enterprise, "
                 "three-zone segmentation, a signed BAA) is a compliance need, "
                 "served by vendors like IronWiFi, not a security-appliance need "
                 "served by consumer hardware."},
            ],
        },
        {
            "eyebrow": "SECTION 3",
            "title": "Competitor Profiles",
            "content": [
                {"type": "h2", "text": "Firewalla"},
                {"type": "label_p", "label": "Positioning:", "text":
                 "“Cyber Security Firewall” for home and prosumer/SMB "
                 "networks — plug-in appliance, local processing, no cloud "
                 "dependency for core function."},
                {"type": "label_p", "label": "Pricing:", "text":
                 "Hardware-only, no subscription required: Purple SE $249, "
                 "Purple $369, Gold SE $479, Gold Plus $599, Gold Pro $899. "
                 "Optional MSP portal: Family $40/yr, Business $300/yr."},
                {"type": "label_p", "label": "Target buyer:", "text":
                 "Technical homeowners and small IT-literate businesses "
                 "comfortable with a standalone appliance."},
                {"type": "label_p", "label": "Weaknesses / public signal:", "text":
                 "No public complaint pattern found at the appliance level — its "
                 "own positioning (local processing, no forced subscription) is "
                 "aimed directly at the complaint pattern found against "
                 "Bitdefender BOX below."},

                {"type": "h2", "text": "Bitdefender BOX"},
                {"type": "label_p", "label": "Positioning:", "text":
                 "Home network security appliance bundled with a Bitdefender "
                 "Total Security software subscription."},
                {"type": "label_p", "label": "Pricing:", "text":
                 "Renewal $130–150/year after year one (one source states "
                 "£89/year in the UK)."},
                {"type": "label_p", "label": "Target buyer:", "text":
                 "Non-technical homeowners wanting one bundled product rather "
                 "than separate hardware and software."},
                {"type": "label_p", "label": "Weaknesses / public signal — the "
                 "single most useful finding in this profile:", "text":
                 "multiple users report the subscription auto-renewing roughly "
                 "$30 above the publicly listed rate, with support reportedly "
                 "explaining that “automatic renewals are processed at the "
                 "highest list price.” Support response times were also "
                 "reported as slow (up to a week) and generic."},

                {"type": "h2", "text": "Gryphon Guardian"},
                {"type": "label_p", "label": "Positioning:", "text":
                 "Mesh WiFi router with parental controls and next-gen "
                 "firewall, marketed primarily at families."},
                {"type": "label_p", "label": "Pricing:", "text":
                 "$99/unit; optional $4.99/mo remote-access add-on (first 3 "
                 "months free)."},
                {"type": "label_p", "label": "Target buyer:", "text":
                 "Families with children, prioritizing parental control over "
                 "general network security depth."},
                {"type": "label_p", "label": "Weaknesses / public signal:", "text":
                 "Recurring complaints about dropped connections, and "
                 "incompatibility with some streaming services (Prime Video "
                 "specifically named) — a reliability complaint, not a pricing "
                 "one."},

                {"type": "h2", "text": "IronWiFi"},
                {"type": "label_p", "label": "Positioning:", "text":
                 "Cloud-native WiFi access and RADIUS management, explicitly "
                 "HIPAA-compliant, targeting healthcare, education, hospitality, "
                 "and coworking."},
                {"type": "label_p", "label": "Pricing:", "text":
                 "Plans from $65, scaled by users or access points; no hardware "
                 "or on-site staff required."},
                {"type": "label_p", "label": "Target buyer:", "text":
                 "Multi-site organizations with a real compliance requirement — "
                 "a healthcare network is the named example in their own "
                 "marketing."},
                {"type": "label_p", "label": "Weaknesses / public signal:", "text":
                 "None surfaced; one customer quote found is unambiguously "
                 "positive on exactly the compliance-logging value proposition. "
                 "The strongest-positioned competitor here for the doctors'-"
                 "office segment specifically."},

                {"type": "h2", "text": "Cisco Meraki Go / Meraki"},
                {"type": "label_p", "label": "Positioning:", "text":
                 "Cloud-managed small-business networking under the Cisco "
                 "brand — access points, switches, and a security gateway."},
                {"type": "label_p", "label": "Pricing:", "text":
                 "Meraki Go: no subscription on the base tier. Full Meraki: "
                 "MX67 ~$540, MX68 ~$780, licenses ~$205–345/yr."},
                {"type": "label_p", "label": "Target buyer:", "text":
                 "Small businesses wanting enterprise-brand reliability without "
                 "an in-house network admin."},
                {"type": "label_p", "label": "Weaknesses / public signal:", "text":
                 "No specific complaint pattern found; the two-tier structure "
                 "itself is a soft weakness — a growing business must migrate "
                 "off Go onto full Meraki, a real switching cost the marketing "
                 "doesn't foreground."},

                {"type": "note", "text":
                 "Discontinued, noted rather than profiled — CUJO AI: "
                 "repeatedly surfaces in searches and comparison articles as a "
                 "current option. It is not. CUJO AI announced discontinuation "
                 "of its Smart Internet Security Firewall device in 2021 and "
                 "has shipped no replacement hardware since."},
            ],
        },
        {
            "eyebrow": "SECTION 4",
            "title": "Feature & Pricing Comparison",
            "content": [
                {"type": "table", "col_widths": [26*3.2, 25*3.2, 25*3.2, 25*3.2, 25*3.2, 25*3.2],
                 "rows": [
                     ["", "Firewalla", "Bitdefender BOX", "Gryphon Guardian", "IronWiFi", "Meraki Go"],
                     ["Model", "Hardware, no forced sub", "Hardware + subscription", "Hardware, optional add-on", "Cloud, no hardware", "Hardware, tiered sub"],
                     ["Entry price", "$249", "~$100 + renewal", "$99", "$65+", "Hardware only (Go)"],
                     ["Recurring cost", "$0–300/yr (opt.)", "$130–150/yr", "$0–60/yr (opt.)", "From $65/mo", "$205–345/yr (full)"],
                     ["HIPAA-ready", "No", "No", "No", "Yes — core", "No"],
                     ["Audit logging", "Behavioral only", "No", "No", "Yes, per-event", "Basic monitoring"],
                     ["Parental controls", "Yes", "Basic", "Primary feature", "No", "No"],
                     ["Best-fit segment", "Technical home/SMB", "Non-technical home", "Family w/ children", "Doctors' office", "Growing small biz"],
                 ]},
            ],
        },
        {
            "eyebrow": "SECTION 5",
            "title": "SWOT — IronWiFi",
            "content": [
                {"type": "p", "text":
                 "Full SWOT for all five would repeat the same shape across "
                 "three products (Firewalla / Bitdefender / Gryphon all compete "
                 "on the same consumer axis). The one that matters most for "
                 "Omni Shield's three-segment ambition:"},
                {"type": "h2", "text": "Strengths"},
                {"type": "bullets", "items": [
                    "Only vendor here with real compliance credentials (BAA, "
                    "audit trails, VLAN segmentation) built in, not bolted on.",
                    "Cloud-native — no hardware to sell against.",
                ]},
                {"type": "h2", "text": "Weaknesses"},
                {"type": "bullets", "items": [
                    "Zero brand presence in the consumer/homeowner segment.",
                ]},
                {"type": "h2", "text": "Opportunities"},
                {"type": "bullets", "items": [
                    "Healthcare compliance requirements only get stricter, not "
                    "looser — a durable tailwind, not a trend.",
                ]},
                {"type": "h2", "text": "Threats"},
                {"type": "bullets", "items": [
                    "A larger compliance-focused vendor (Purple, seen in the "
                    "same research but not profiled here) could out-market on "
                    "the identical positioning with more capital.",
                ]},
            ],
        },
        {
            "eyebrow": "SECTION 6",
            "title": "Opportunities & Strategic Recommendations",
            "content": [
                {"type": "bullets", "items": [
                    "<b>Don't build one product for three segments.</b> No "
                    "competitor found here credibly serves homeowners, SMBs, "
                    "and medical practices with the same offering — the buying "
                    "triggers differ enough that one positioning statement "
                    "would be generic to all three and compelling to none.",
                    "<b>Lead with the doctors'-office segment specifically,</b> "
                    "not “SMB” broadly — it's the only one with a "
                    "forcing function (HIPAA) consumer competitors structurally "
                    "cannot address, and IronWiFi is the only real incumbent.",
                    "<b>Price against IronWiFi's model,</b> not consumer "
                    "hardware — a compliance buyer is not anchoring on a $99 "
                    "router.",
                    "<b>The specific wedge against IronWiFi:</b> it's cloud-"
                    "native with no hardware option. A physical-appliance "
                    "option for practices preferring on-prem processing is a "
                    "genuine differentiator against the strongest incumbent.",
                    "<b>Don't chase the consumer segment for growth.</b> It's "
                    "the most crowded of the three, and none of the public "
                    "complaints found (renewal pricing, dropped connections) "
                    "are gaps Omni Shield's stated three-segment positioning is "
                    "set up to exploit better than an incumbent that's iterated "
                    "on home routers specifically for years.",
                ]},
            ],
        },
        {
            "eyebrow": "APPENDIX",
            "title": "Sources & Methodology",
            "content": [
                {"type": "p", "text":
                 "Every competitor, price, and complaint above was sourced from "
                 "a live, current page at research time — vendor pricing pages, "
                 "G2/TrustRadius listings, and vendor-support forum threads for "
                 "complaint patterns. The CUJO AI discontinuation was confirmed "
                 "directly from the vendor's own announcement, not inferred "
                 "from its absence."},
                {"type": "note", "text":
                 "This report used direct web search rather than the "
                 "Perplexity round-trip a real order runs through — the "
                 "underlying research prompts are unchanged. Real per-order "
                 "turnaround time against a paid order is still unverified."},
            ],
        },
    ],
}
