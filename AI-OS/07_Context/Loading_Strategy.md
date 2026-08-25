# Loading Strategy

Purpose: The fixed order an AI follows before, during, and after a task.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[07_Context/README|07_Context]], [[Context_Resolution]], [[Context_Budget]]

---

## Sequence

```
Task
 ↓
Determine capability (03_Capabilities/)
 ↓
Read Required Notes only
 ↓
Execute
 ↓
Read Optional Notes — only for a gap actually hit
 ↓
Produce output
 ↓
Identify learnings (see Knowledge_Promotion)
 ↓
Update knowledge, if the learning clears promotion
```

## Rules
- Required context is read once, up front — not incrementally re-checked mid-task.
- Optional context is read reactively, only when a specific gap appears — never pre-loaded "just in case."
- Escalation context (see [[Context_Resolution]]) is the only category read after a failure rather than before execution.
- Nothing is re-read within a single task unless the underlying note changed during that task.

## Interaction with Context Budget
This sequence assumes [[Context_Budget]] limits are already respected at each step — Loading Strategy defines *order*, Context Budget defines *how much*.
