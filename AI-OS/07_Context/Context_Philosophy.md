# Context Philosophy

Purpose: Why context and token efficiency matter, and the principles the Context Engine is built on.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[07_Context/README|07_Context]], [[Context_Resolution]], [[Principles]]

---

## Why Context Matters
An AI acting on this vault is only as good as what it reads before acting. Read too little and it acts on incomplete information. Read too much and cost, latency, and the chance of contradictory or irrelevant material all rise. The Context Engine exists to make "what to read" a fixed procedure, not a guess.

## Why Token Efficiency Matters
Every note read is tokens spent. At vault scale — the stated target is thousands of files — unconstrained reading doesn't degrade gracefully, it becomes the dominant cost of every task. Token efficiency isn't an optimization layered on top of correctness; past a certain scale it's a precondition for correctness, since a context window that's mostly irrelevant material crowds out the material that matters.

## Core Principles
These extend [[Principles]] rather than replace them:
- **Deterministic over exploratory.** An AI should know what to read, not search for it. See [[Context_Resolution]].
- **Declared, not inferred, dependencies.** A note states what it needs; nothing downstream has to guess. See [[Dependency_Rules]].
- **Smallest sufficient context.** Load what a task requires, not what's merely related. See [[Context_Budget]].
- **Knowledge earns permanence.** Nothing becomes standing context until it's been validated. See [[Knowledge_Promotion]].
