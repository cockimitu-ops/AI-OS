# Learning Loop

Purpose: What happens to what's learned during execution, after it finishes.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Execution/README|01_Architecture/Execution]], [[Execution_Lifecycle]]
Required Notes: [[Knowledge_Promotion]]

---

## Decision

```
Did anything happen that wasn't already known?
 ├─ No  → Ignore. Nothing to capture.
 └─ Yes → Did it happen once, informally?
      ├─ Yes → Observation
      └─ No, recurring or high-stakes → Experiment
```

## Rule
This stage only decides *whether* something is worth feeding into the promotion pipeline — the pipeline itself (Observation → Experiment → Validated Learning → Permanent Knowledge) is fully defined in [[Knowledge_Promotion]] and is not redefined here.

## Hard Rule: No Direct Promotion
Nothing enters `02_Systems/`, `03_Capabilities/`, or `01_Architecture/` directly from a single execution, no matter how confident the result looks. Everything enters through [[Knowledge_Promotion]]'s pipeline. This is what keeps one unusual task from silently rewriting standing knowledge.
