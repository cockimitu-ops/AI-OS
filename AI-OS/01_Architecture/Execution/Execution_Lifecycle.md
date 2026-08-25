# Execution Lifecycle

Purpose: The canonical, model-independent pipeline every task in AI OS follows.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Execution/README|01_Architecture/Execution]], [[Execution_Philosophy]], [[Task_Specification]]
Required Notes: [[Context_Resolution]], [[Knowledge_Promotion]]

---

## Pipeline

```
Task
 ↓
Intent Detection
 ↓
Capability Resolution
 ↓
Context Resolution
 ↓
Input Validation
 ↓
Execution
 ↓
Quality Assurance
 ↓
Output
 ↓
Learning Extraction
 ↓
Knowledge Promotion
 ↓
Finish
```

## Stages

| Stage | What Happens | Defined In |
|---|---|---|
| Task | A task is received — chat message, API call, or automation trigger | Whatever initiates it |
| Intent Detection | Determine what the task is actually asking for | This stage |
| Capability Resolution | Map the task to a specific entry in `03_Capabilities/` | This stage, indexed by `03_Capabilities/README.md` |
| Context Resolution | Load that capability's Required Notes | Delegates entirely to [[Context_Resolution]] — not redefined here |
| Input Validation | Confirm inputs match the capability's declared Inputs | [[Task_Specification]] |
| Execution | The capability actually runs | The model or agent handling the task |
| Quality Assurance | Check output against execution-level QA | [[Quality_Assurance]] |
| Output | Deliver the result | Whatever initiated the task |
| Learning Extraction | Decide if anything from this run is worth capturing | [[Learning_Loop]] |
| Knowledge Promotion | Route qualifying learnings into the promotion pipeline | Delegates entirely to [[Knowledge_Promotion]] — not redefined here |
| Finish | Task closes; runtime state is discarded unless explicitly promoted | [[Runtime_State]] |

## Rule
No stage is skipped and no stage is reordered — a task that looks simple enough to shortcut still passes through Intent Detection and Capability Resolution; skipping them is how a task ends up executed against the wrong capability.
