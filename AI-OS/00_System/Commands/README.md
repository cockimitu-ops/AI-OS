# Commands

Purpose: The command layer — natural-language entry points that route to existing capabilities and workflows, without duplicating what they already document.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[00_System/README|00_System]], [[03_Capabilities/README|03_Capabilities]], [[05_Workflows/README|05_Workflows]]

---

## Responsibility
Answers "what do I say to get X done," nothing more. All actual logic — Purpose, Inputs, Outputs, Success Criteria — stays exactly once, in the capability or workflow being routed to.

## Contents
- [[00_System/Commands/Command_Index|Command Index]] — the routing table
- [[00_System/Commands/Quick_Start|Quick Start]] — a worked example of the full mechanism

## Why This Lives in 00_System/
Navigation and entry points are exactly what `00_System/` already does (`Home.md`, `Dashboard.md`). A command layer is another form of entry point, not new architecture — no ADR needed, same precedent as `Content/Knowledge/` and `Content/Templates/`.
