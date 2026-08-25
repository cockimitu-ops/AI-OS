# Template Metadata

Purpose: The header fields every template itself carries — the template-level counterpart to the vault's own document header.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Template_Structure]]
Required Notes: [[Naming_Convention]], [[Template_Versioning]]

---

## Core Principles
- A template's own metadata (Purpose, Version, Status, Used By) is separate from the fields a *filled-in instance* of that template would carry. This note governs the former; [[Template_Structure]] governs the latter.
- Reuses the vault's existing header standard (Title / Purpose / Last Updated / Status / Related Documents, from `Naming_Convention.md`) rather than inventing a parallel one. A template file is still just a vault note and follows the same rules every other note does.
- Adds exactly one template-specific field beyond the standard header: Template Version (see [[Template_Versioning]]) — nothing else is template-specific at the metadata level.

## Inputs
A new template being defined.

## Outputs
A metadata block: the existing standard header, plus one addition.

## Dependencies
`Naming_Convention.md` (existing standard, not duplicated), [[Template_Versioning]].
