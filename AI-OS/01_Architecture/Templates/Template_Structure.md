# Template Structure

Purpose: What a template definition actually contains.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Template_Metadata]], [[Template_Variables]]
Required Notes: [[Template_Philosophy]]

---

## Core Principles
- A template is a named, ordered set of fields, each with a declared type (text, list, reference) and a stated purpose — not free-form prose with blanks.
- A field can reference another vault note (e.g., "Related Capability: [[...]]"), but the template doesn't dictate *which* note — that's filled in per use, per [[Template_Variables]].
- Structure and content are strictly separated: a template file never contains example content that could be mistaken for a real value — see [[Template_Quality_Standards]] for how this gets checked.

## Inputs
The recurring shape a document needs to take.

## Outputs
A structured template definition: field names, types, purposes.

## Dependencies
[[Template_Philosophy]].
