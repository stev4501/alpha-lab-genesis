# BL-0003: Enumerate the provider evidence needed to close B-0003

- Status: open
- Priority: 3
- Requires sealed changes: no
- Origin: ADR-0008 proof backlog (2026-08-08)

## The blocker

`FAILURES.md` B-0003 (open, high severity): the finance connector behind
D-0001 and D-0002 exposes no publication timestamp, completed-bar flag, or
revision identifier, so neither dataset can be verified as point-in-time for
historical session-close decisions. This reopened B-0001 and blocks all
historical strategy evaluation beyond the retrieval-time-forward use narrow
policy noted in `DATA_MANIFEST.json` validation.open_issues. STATE.json
action A-0009 depends on resolving it.

## Deliverable

An analysis document (suggested: `docs/b0003-provider-evidence.md`, a new
file — do not edit FAILURES.md history, though appending an updated
"Resolution or next action" note to the B-0003 entry is permitted since
FAILURES.md is an append-friendly log) that enumerates, concretely, what a
data provider would have to expose for point-in-time status to be
VERIFIABLE rather than asserted. Cover at least:

1. Publication/availability evidence: a per-bar timestamp stating when the
   bar first became available to consumers, distinct from the bar's market
   date.
2. Completion evidence: a completed-bar / final-print flag distinguishing
   settled bars from intraday or preliminary values.
3. Revision evidence: a monotonically versioned revision identifier per bar
   (or per file), plus access to superseded values, so retrievals can be
   proven identical or diffed.
4. As-of query capability: the ability to ask "what did the series look like
   as of time T", which is what would make historical session-close
   backtests point-in-time defensible.
5. Corporate-action and adjustment semantics: explicit adjustment policy
   metadata (raw vs split-adjusted vs total-return) with effective dates,
   since silent re-adjustment is itself a revision channel.
6. Attestation/verifiability: which of the above can be independently
   checked by us (e.g. repeated retrieval diffing under checksums — already
   practiced in `data/snapshots/`) versus which require trusting provider
   claims, and what minimum subset makes B-0003 closable.

For each element, state: what D-0001/D-0002's current provider exposes today
(nothing, per the blocker), what the element would let us machine-enforce,
and which candidate check in the future G-0004 evaluator (see BL-0002) would
consume it.

## Definition of done

The document exists and is linked from the journal and HANDOFF.md, and
B-0003's "Resolution or next action" is updated to point at it. No dataset
status changes, no new data is retrieved, and STATE.json's blocker entries
are left for a session that actually resolves the blocker.
