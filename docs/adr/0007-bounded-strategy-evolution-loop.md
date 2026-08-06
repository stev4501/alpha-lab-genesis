# ADR-0007: Bounded Strategy Evolution Loop

- Status: proposed architecture recorded by human direction; G-0004
  implementation is not approved
- Date: 2026-08-06
- Change: A-0007
- Generation: G-0003

## Context

Alpha Lab can wake on a schedule, validate its repository, register immutable
data, execute preregistered experiments, preserve evidence, and stop safely. It
does not yet have a bounded mechanism for routinely selecting distinct strategy
hypotheses or separating strategy evolution from forward paper observation.

A software-evolution rule such as "tests pass, therefore commit" is insufficient
for investment research. Repeatedly searching historical data until a positive
result appears creates selection bias and backtest overfitting even when every
software test passes.

## Decision

Alpha Lab will use two separate control loops.

### Weekly evolution loop

The existing weekly run is the only loop allowed to create or change candidate
strategies. Each awakening:

1. Recovers and validates repository state.
2. Registers or resolves an immutable point-in-time data snapshot.
3. Selects the highest-priority executable action from `STATE.json`.
4. Converts at most one queued idea into a falsifiable hypothesis after the
   approved enforcement boundary exists.
5. Preregisters before evaluation.
6. Evaluates at most one experiment net of nonzero costs and slippage.
7. Uses an independent adversarial reviewer before finalization.
8. Records one canonical outcome: `keep`, `discard`, `iterate`, `promote`,
   `demote`, or `block`.
9. Persists a complete, validated state transition and stops.

The run retains the 90-minute budget, ten-minute closing reserve, and
one-experiment maximum.

### Forward-evidence collector

A separate post-close collector may be activated only when all of these
conditions are satisfied:

1. a frozen strategy passes a preregistered `walk_forward` eligibility gate
   that does not itself require forward evidence;
2. strategy code, parameters, decision rules, cost model, and slippage model are
   frozen;
3. paper-account semantics and per-strategy lifecycle state are implemented;
4. append-only evidence isolation and lineage-taint enforcement are installed;
5. idempotent occurrence accounting and a fenced repository-writer lease are
   installed and tested; and
6. a human approves the separate recurring task.

The collector produces the forward evidence required for a later transition
into `paper`. It may:

- append a new immutable market observation;
- calculate the frozen strategy's next paper decision;
- reconcile simulated positions and cash;
- evaluate preregistered promotion, demotion, and kill criteria without changing
  evidence stage or strategy status; and
- report material findings.

It may not generate hypotheses, tune parameters, change strategy code, consume
confirmation data for discovery, or promote itself. Forward observations must
be stored in an append-only, checksummed evidence stream. Any later hypothesis
influenced by those observations is lineage-tainted and cannot claim untouched
confirmation status for the observed interval. Until every activation condition
is satisfied, this task remains unscheduled.

## Strategy search boundary

Before autonomous strategy generation begins, the approved G-0004
implementation must provide a machine-validated strategy grammar with these
dimensions:

- universe;
- signal family;
- formation window;
- rebalance rule;
- position sizing;
- risk constraints;
- execution assumptions; and
- exit rule.

One experiment may change only one conceptual dimension from its declared
parent. A parameter sweep consumes one trial per evaluated configuration.
Cosmetic parameter changes do not qualify as new hypotheses.

The grammar implementation must use a canonical machine-readable strategy
representation, permitted value domains, parent fingerprints, parameter
namespaces, and explicit dependency rules. Opaque code changes cannot establish
one-concept compliance through self-declaration; they require human approval or
remain exploratory and ineligible for promotion.

## Statistical governance

The implementation must:

- preserve discovery and confirmation separation;
- atomically reserve a unique trial-event ID before any evaluation;
- record candidates, parameter cells, seeds, retries, failures, and aborted
  evaluations in an append-only trial-event ledger;
- prohibit confirmation-data reuse for tuning;
- mediate and record every confirmation-data access against immutable dataset,
  interval, strategy, and code fingerprints;
- apply a preregistered multiple-testing adjustment or alpha-spending rule;
- evaluate rolling or walk-forward out-of-sample periods;
- stress costs, slippage, turnover, concentration, and relevant regimes; and
- require a plausible economic mechanism in addition to positive metrics.

The system may prove artifact integrity and historical evaluation claims. It
must not claim that future profitability is proven.

## Promotion ladder

Candidates advance only through:

`discovery -> out_of_sample -> walk_forward -> paper`

Each promotion requires a frozen strategy version and preregistered gate.
Failure at a later stage may demote or discard the strategy. A champion is always
named with its evidence stage.

The transition from `walk_forward` into forward observation is not itself a
promotion to `paper`. It authorizes evidence collection. A later, separately
preregistered decision may promote the frozen strategy to `paper` after the
minimum forward horizon and decision rules are satisfied.

## Approval boundary

Current G-0003 components seal the experiment schema, preregistration,
repository validation, evidence review, and finalization paths that would need
to enforce these controls. This A-0007 transition records the proposed
architecture only. A-0008 will prepare a narrow G-0004 change proposal after
A-0006 completes and must stop for human approval. Neither action implements or
claims enforcement under G-0003.

The proposal must identify:

- each protected or sealed file requiring change;
- the exact non-bypassable invariant added by that change;
- migration and cross-generation comparability consequences;
- tests that fail under the current bypasses; and
- rollback and historical-artifact preservation behavior.

No strategy may be generated, tuned, or promoted through the new autonomous
evolution path until the approved generation is installed and independently
reviewed.

## Required subsequent implementation artifacts

The approved generation implementation is complete only when the repository
contains:

1. a versioned strategy-grammar schema;
2. an append-only hypothesis queue with parent and novelty metadata;
3. automated duplicate and one-concept-change validation;
4. trial-budget and confirmation-touch accounting;
5. preregistered promotion and retirement criteria;
6. end-to-end tests proving invalid transitions are rejected; and
7. reviewer provenance stronger than a self-declared agent-ID inequality;
8. repository-scoped lease, occurrence IDs, idempotent retry behavior, and
   atomic failed-run checkpoints before any second scheduled writer exists; and
9. independent review evidence.

## Consequences

- Strategy evolution remains slower than unrestricted search.
- Positive results become harder to obtain but more interpretable.
- Evidence isolation and lineage tainting reduce contamination from forward
  results; implementation must prove these controls before observer activation.
- Activating a daily observer increases scheduled-task cost and requires
  separate human approval.
- A-0007 records architecture, not an operational autonomy expansion.
