# Task Specification

Purpose: The minimum information required before any task executes.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Execution/README|01_Architecture/Execution]], [[Execution_Lifecycle]]

---

## Required Fields

| Field | Answers |
|---|---|
| Objective | What outcome the task is for |
| Inputs | What's given to work with |
| Constraints | What must be respected (format, length, scope, standards) |
| Expected Outputs | What form the result should take |
| Success Criteria | How to tell the output actually satisfies the Objective |
| Related Capability | Which `03_Capabilities/` entry this maps to, if any |

## Format

```
Objective: <one line>
Inputs: <what's provided>
Constraints: <hard requirements>
Expected Outputs: <deliverable shape>
Success Criteria: <how it's judged>
Related Capability: [[Capability Name]] — or "none" if this task predates a defined capability
```

## Rule
A task without a Related Capability isn't blocked — it just skips straight to whatever Context Resolution its Objective implies, since there's no capability-declared Required Notes to inherit. This is expected for genuinely new work; once a pattern repeats, it should graduate into an actual capability (see `03_Capabilities/README.md`).
