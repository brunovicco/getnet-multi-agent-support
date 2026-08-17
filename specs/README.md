# Spec-driven development

This repository was built spec-first: the specification and the design were written before the
implementation, and every change since is traceable to a requirement.

| Stage | Artifact | Purpose |
| --- | --- | --- |
| 1. Specify | [`001-multi-agent-support/spec.md`](001-multi-agent-support/spec.md) | WHAT the system must do, as testable acceptance criteria |
| 2. Design | [`001-multi-agent-support/design.md`](001-multi-agent-support/design.md) | HOW it is structured, with the seams that make it replaceable |
| 3. Decide | [`001-multi-agent-support/decisions.md`](001-multi-agent-support/decisions.md) | WHY each contested choice was made, and what was rejected |
| 4. Plan | [`001-multi-agent-support/tasks.md`](001-multi-agent-support/tasks.md) | Ordered tasks, each mapped to requirement IDs and tests |

Requirement identifiers (`REQ-*`) are the traceability key: they appear in the design, in the task
list, and in the test names or docstrings that verify them. A requirement with no test is treated
as unimplemented.

The loop is deliberate: a behaviour change starts in `spec.md`, moves through `design.md` when it
touches a boundary, and only then reaches code. Constants that encode product judgement (routing
confidence threshold, retrieval score gate) are named in the spec so they can be reviewed without
reading the implementation.
