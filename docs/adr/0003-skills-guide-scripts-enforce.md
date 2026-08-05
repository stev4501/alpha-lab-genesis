# ADR-0003: Skills Guide, Scripts Enforce

**Status:** Accepted
**Date:** 2026-08-05

## Context

Prompt instructions are useful for judgment but unreliable for mechanical
invariants such as schema validity, identifier uniqueness, and required files.

## Decision

Keep judgment and workflow in skills. Enforce deterministic repository
invariants with scripts and tests.

## Consequences

- Easier: detect malformed handoffs before a session ends.
- Easier: evolve judgment without weakening mechanical safety.
- Harder: schema and validator changes must remain synchronized.
- Impossible: treat a prose assertion as sufficient validation.
