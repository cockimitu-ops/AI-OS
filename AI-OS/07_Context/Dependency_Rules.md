# Dependency Rules

Purpose: How a note declares what it depends on, so context resolution never has to guess.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[07_Context/README|07_Context]], [[Context_Resolution]], [[03_Capabilities/README|03_Capabilities]]

---

## The Rule
Any note that something else needs to read before acting on it — capabilities, and eventually agents and workflows — declares its dependencies directly under the existing header (Title / Purpose / Last Updated / Status / Related Documents):

```
Required Notes: [[Note A]], [[Note B]]
Optional Notes: [[Note C]]
Related Notes: [[Note D]]
Used By: [[Note E]], [[Note F]]
```

Omit a line entirely if it's empty — don't write "Required Notes: none."

## Rules
- **Required Notes** are the minimum set that makes the note usable, not everything that's ever relevant.
- **Optional Notes** are named individually, never as "see the rest of the folder."
- **Related Notes** are for navigation, not execution — never auto-loaded (see [[Context_Resolution]]).
- Dependencies point to specific notes, never whole folders. A folder-level dependency can't be resolved without a search, which is exactly what this system exists to avoid.
- `Related Documents` (the existing header field) and `Related Notes` (this field) differ: `Related Documents` is general cross-referencing; `Related Notes` is specifically the low-priority, non-auto-loaded category from [[Context_Resolution]]. Existing files aren't required to retrofit this — it applies going forward, starting with capabilities.
- **Used By** is the reverse of Required/Optional: it lists what currently depends on this note. It's maintained by whoever adds the dependency elsewhere, not predicted in advance — an empty or absent `Used By` line means nothing has declared a dependency on this note yet, not that nothing should. Added Sprint 006; see `02_Systems/Content/Knowledge/` for its first real usage.
- **Knowledge Dependencies** is a labeled subset of Required Notes, used specifically on capability notes (`03_Capabilities/`) to call out which prerequisites come from `02_Systems/Content/Knowledge/` versus other kinds of required context (system docs, cross-cutting standards). It is not a second, independent dependency list — everything in it also appears in Required Notes, since [[Context_Resolution]]'s retrieval algorithm reads Required Notes and would miss anything filed only under Knowledge Dependencies. Added Sprint 010 during the capability retrofit; omit the field entirely (as several capabilities do) when no Knowledge Core note applies.

## Example
`03_Capabilities/Hook_Writing.md` would add:
```
Required Notes: [[Reddit_Story_Workflow]]
```
— Hook Writing can't be executed correctly without knowing the retention structure it serves.
