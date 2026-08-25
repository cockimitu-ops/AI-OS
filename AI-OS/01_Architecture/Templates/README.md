# Templates

Purpose: The Template Framework — reusable document structures that standardize information capture, independent of which AI model or capability fills them in.
Last Updated: 2026-08-03
Status: Active — Sprint 009
Related Documents: [[01_Architecture/README|01_Architecture]], [[03_Capabilities/README|03_Capabilities]], [[05_Workflows/README|05_Workflows]]

---

## Responsibility
Defines how a template is structured, versioned, validated, and reused — not any actual template. See [[Template_Philosophy]] for the full boundary against capabilities, knowledge, and workflows.

## Contents
- [[Template_Philosophy]] — why templates are their own layer
- [[Template_Structure]] — what a template definition contains
- [[Template_Metadata]] — the header a template itself carries
- [[Template_Variables]] — how placeholders get declared and filled
- [[Template_Validation]] — checking a filled instance against its template
- [[Template_Versioning]] — definitions change by new version, never by edit
- [[Template_Reuse]] — using the same template across multiple capabilities without drift
- [[Future_Integration]] — how Capabilities, Workflows, Agents, and Automation will use templates (consolidated across all frameworks)
- [[Template_Lifecycle]] — Proposed → Active → Deprecated → Retired
- [[Template_Quality_Standards]] — what makes a template definition well-formed (distinct from validating a filled instance)

## Why This Lives in 01_Architecture/
A cross-cutting, model-independent specification — like the Context Engine and Execution Engine, but governing document format/structure rather than runtime or retrieval. Formalized in [[ADR-0004_Template_Framework_Placement]], which generalizes [[ADR-0003_Execution_Engine_Placement]]'s reasoning to this third category rather than treating it as a one-off.

## Status
Sprint 009 complete. First production template — `10_Projects/SocialMediaContent/Templates/Publishing_Checklist.md` — built Sprint 011, moved here from `02_Systems/Content/` in Sprint 018's project/knowledge separation ([[ADR-0005_Project_Knowledge_Separation]]).
