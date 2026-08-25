# Template Philosophy

Purpose: Why templates exist as their own layer, distinct from capabilities, knowledge, and workflows.
Last Updated: 2026-08-03
Status: Active
Related Documents: [[01_Architecture/Templates/README|01_Architecture/Templates]], [[Execution_Philosophy]], [[Workflow_Philosophy]], [[Analytics_Philosophy]]

---

## Core Principles
- A template standardizes structure, not content. It defines the shape information should take, not what the information says. Knowledge notes define what's true; a template defines how a finding gets written down.
- A template contains no permanent knowledge and no execution logic of its own — it's a shape, not a fact and not a process.
- The same template used by different capabilities produces structurally consistent output regardless of which AI model fills it in — model-independence achieved by keeping structure separate from the content-generation logic, which stays in capabilities.
- A template is reusable across capabilities. A capability that needs a specific structure references a template rather than defining its own structure inline — avoiding duplication when two capabilities need the same shape.

## Inputs
A recurring need to capture or present information in a consistent shape.

## Outputs
A reusable structural definition, ready to be filled by any capability or workflow.

## Dependencies
None — this is the root note for the Template Framework, the same role [[Execution_Philosophy]], [[Workflow_Philosophy]], and [[Analytics_Philosophy]] play for their systems.
