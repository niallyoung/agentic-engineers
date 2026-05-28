---
name: queue-path-validator
description: Validates queue paths against canonical format
role: security-engineer
effort: low
---

# Queue Path Validator Skill

Validates that queue paths conform to the canonical format:
`~/.agentic-engineers/{session-id}/{harness}/queue/`

Rejects legacy paths and injection attempts.
