# CCR-0001 (G-0004): validity stamps must be earned, not written

- Origin: `backlog/BL-0002-g0004-change-request.md`, drafted by autonomous
  session `2026-08-09-0851` (research mode)
- Status: **proposed** — nothing applied, nothing sealed touched. No patch is
  attached; see §9 for why.
- Requires sealed changes: **YES** (`evaluator/daily_bar.py`,
  `scripts/validate_repository.py`, `scripts/finalize_experiment.py`,
  `CORE_MANIFEST.json` hash entries)
- Requires protected-path changes: yes (`CORE_MANIFEST.json`,
  `loop/validate_session.sh`, possibly `schemas/data-manifest.schema.json`)
- Requires a new immutable freeze tag: yes — see §6a, including a naming trap
- Related: `docs/adr/0007-bounded-strategy-evolution-loop.md` (approval
  boundary), `docs/adr/0008-mvp-reduction.md` (exit criterion 5; the
  `CORE_SKILLS` un-hardcoding directive), `docs/adr/0009-agent-owned-operations.md`
  (the human owns the core), `FAILURES.md` B-0001/B-0003,
  `backlog/BL-0001-golden-replay-e0002.md` (§8 input),
  `backlog/BL-0003-b0003-provider-evidence.md` (§3.4 depends on it)

## Why this exists

`evaluator/daily_bar.py` lines 429–437 finalize every experiment with:

```python
validity = {
    **prereg["validity"],
    "lookahead_check": "passed",
    "survivorship_check": "passed",
    "leakage_check": "passed",
    "corporate_action_check": "passed",
    "missing_data_check": "passed",
    "independent_review": "not_run",
}
```

No check runs. Five string literals assert five properties of the evaluation
that nothing in the repository has established. Both completed experiments
carry the unearned stamps in `results/E-0001/validity.json`,
`results/E-0002/validity.json`, and their `EXPERIMENTS.jsonl` records.

This is worse than an absent check, because `scripts/finalize_experiment.py`
line 117 *consumes* these stamps: promotion is blocked unless all five read
`"passed"`. The gate exists, is wired up, and is fed a constant. It would
pass a strategy with catastrophic lookahead as readily as a sound one.

The defect has been known and deliberately unfixed since 2026-08-08. It is
reserved as the first exercise of the human-approval gate (ADR-0008 exit
criterion 5), which is what this document is.

## §1 Files requiring change

| File | Sealed? | Change | Necessity |
| --- | --- | --- | --- |
| `evaluator/daily_bar.py` | sealed (EV-0002) | Run the checks; derive `validity` from a check ledger; write `results/<E>/checks.json`; add it to `outputs` and the artifact manifest | Required — this is the defect |
| `scripts/validate_repository.py` | sealed (EV-0002) | For records at generation ≥ G-0004, refuse any validity value of `"passed"` that lacks a matching ledger entry; un-hardcode `CORE_SKILLS` (§1a) | Required — otherwise a hand-edited `validity.json` reproduces the defect one layer up |
| `scripts/finalize_experiment.py` | sealed (EV-0002) | Decide the fate of `PROMOTION_CHECKS` under honest stamps (§3.6) | Required to *decide*; possibly zero code change |
| `CORE_MANIFEST.json` | protected | New sha256 for each changed sealed path; `system_generation` → `G-0004`; `core_skills` becomes the authoritative skill set (§1a) | Required |
| `loop/validate_session.sh` | protected (not sealed) | `REFERENCE_TAG` → the successor tag, one line | Required, and time-critical — §6a |
| `schemas/experiment.schema.json` | sealed (EV-0002) | **No change needed.** `$defs.check` already permits `not_run`, `passed`, `failed`, `warning`, `not_applicable`, and all five fields are already required | — |
| `schemas/data-manifest.schema.json` | protected | Only if missing-data option (c) is chosen (§3.5): add an optional declared session count per dataset | Conditional |

New unsealed files (agent-writable, no approval needed once G-0004 lands):
`tests/test_validity_checks.py` (§5).

### §1a The `CORE_SKILLS` un-hardcoding — in scope

ADR-0008 records the human's directive that the six dormant skills stay in
place "until a G-0004 change proposal — which must also cover un-hardcoding
the skill set — is approved". This request therefore includes it rather than
deferring it. The two changes are unrelated in subject matter but identical
in mechanism (both are sealed-validator edits requiring one generation bump,
one reseal, and one freeze tag), and splitting them would mean two approval
round trips and two freeze tags for one reseal. That cost is real; the
coupling risk is not, because neither change can silently affect the other.

Proposed shape, which is *not* simply deleting the constraint:

- `scripts/validate_repository.py` derives the expected skill set from
  `CORE_MANIFEST.json`'s `core_skills` instead of the module-level
  `CORE_SKILLS` literal (lines 26–36, consumed at lines 367 and 373).
- The existing per-skill checks stay: every declared skill must have a
  `skills/<name>/SKILL.md`, frontmatter `name` must equal the directory, and
  the declared version must match the frontmatter.
- A floor invariant replaces the hardcoded set: `core_skills` must be
  non-empty and must contain at least the operative three
  (`genesis-orchestrator`, `experiment-loop`, `memory-handoff`). Without this
  floor, un-hardcoding converts a real constraint into no constraint at all,
  and a future manifest declaring zero skills would validate.
- The anchor of trust moves from validator source to `CORE_MANIFEST.json`,
  which is a protected file requiring human approval to change. That is the
  intended trust boundary; it is not a weakening.

Removing the six dormant skill directories is **not** part of this request. It
becomes *possible* once this lands; whether to do it is a separate decision.

## §2 The non-bypassable invariant

**A validity stamp may read `"passed"` only if a named check ran during the
evaluation and recorded evidence. Anything else is `"not_run"`.**

Mechanically, in the evaluator:

1. Introduce a check ledger — an append-only list built during `evaluate()`.
   Each entry is `{check_id, status, evidence, observations}` where `evidence`
   is a non-empty structured record of what was actually inspected (counts,
   dates, resolved identifiers), not prose.
2. `validity[<name>]` is **derived** from the ledger, never written as a
   literal. The derivation is total: a check with no ledger entry yields
   `"not_run"`. The five literals at lines 431–435 disappear; there is no code
   path that can produce `"passed"` without a ledger entry.
3. The ledger is persisted as `results/<E>/checks.json`, added to `outputs`
   (so the existing `FileExistsError` immutability guard at line 448 covers
   it) and to the artifact manifest, so it is hashed and verified by
   `scripts/finalize_experiment.py`'s `verify_artifacts`.
4. The default is failure-shaped. If a check raises, its status is `"failed"`
   with the exception recorded — never absent, never silently `"passed"`.

And in the validator, for records at generation ≥ G-0004:

5. Any of the five validity fields reading `"passed"` in an `EXPERIMENTS.jsonl`
   record must have a `checks.json` entry with the same `check_id`, status
   `"passed"`, and non-empty evidence. Otherwise the repository contract is
   invalid.

Rule 5 is what makes the invariant non-bypassable rather than merely correct.
Rule 1–4 fix the evaluator; rule 5 means that hand-editing a `validity.json`,
or writing a record by any route other than the sealed evaluator, is caught by
`scripts/validate_repository.py` — which `loop/validate_session.sh` check 6
runs on every session branch before anything reaches `main`.

Note the deliberate asymmetry: nothing forces a check to be *good*. The
invariant guarantees only that a `"passed"` corresponds to code that ran and
evidence that exists. That is the honest limit of what this change buys.

## §3 What each check would verify, on this data path

Scope of the evaluation being stamped: daily bars, one instrument, one
immutable snapshot CSV resolved through `DATA_MANIFEST.json`, a strategy
called at each session close whose weights execute at the next session's open.

### §3.1 `lookahead_check` — implementable now, recommend `"passed"`

What it verifies, precisely:

- At every strategy invocation, the history handed to `target_weights` contains
  no row dated after `as_of`, and contains exactly `index + 1` sessions per
  symbol (the session loop, lines 385–419; the strategy call is line 417).
- Weights returned at session *t* are applied no earlier than session *t+1*
  (`pending_weights` is consumed at the top of the next iteration, line 389),
  and fills use that session's **open** (line 154, line 171), never its close
  and never any later bar.
- The benchmark interval starts at `dates[warmup_sessions]`'s open — the same
  instant the strategy's first fill can occur (line 271–275). This is B-0002's
  fix; stamping it means asserting it every run rather than trusting EV-0002's
  provenance.

Evidence recorded: invocation count, the maximum `(max history date − as_of)`
observed in sessions (must be ≤ 0), the minimum application lag in sessions
(must be ≥ 1), and the evaluation start/end dates.

One defect found while drafting, which this check should close: line 417
passes `strategy(dict(history), date)`. `dict()` is
a shallow copy — the strategy receives the evaluator's own row lists and its
own mutable row dicts. It cannot see the future through them, but it can
*rewrite the past* mid-run, and the next session's equity would be computed
from mutated bars with nothing detecting it. Recommend the invariant include
handing the strategy a defensive deep copy, and the check record a hash of the
bar data before and after the strategy call. This is a small change with a
real failure mode and it belongs here, in the only generation bump on the
table.

### §3.2 `survivorship_check` — recommend `"not_applicable"`, never `"passed"`

A survivorship check answers: were instruments that later disappeared present
in the universe at the time decisions were made? On a universe declared
`"SPY only for the full registered interval"` with static effective dating
(`DATA_MANIFEST.json` U-0001), the question has no content. `load_bars` line
112–115 already enforces that the symbol set is identical on every session, so
there is no membership to survive.

Honest status is `"not_applicable"`, derived — not asserted — from resolved
facts: the universe's effective dating is static, the dataset's symbol set has
cardinality 1, and it is constant across all sessions. If any of those is
false the status is `"not_run"`, because a real check needs a point-in-time
membership record with delisting dates, and nothing in this repository has
one.

`"passed"` must not be reachable for this check in G-0004. A single-symbol
universe cannot demonstrate survivorship freedom; it can only be exempt from
the question. Note that `DATA_MANIFEST.json` currently claims
`"survivorship_free": true` for D-0001 and D-0002 — that flag is a provider-
level assertion about a one-symbol file and must not be read as evidence.

### §3.3 `leakage_check` — implementable now, with a stated limit

What it verifies: the strategy consumed nothing but what the evaluator handed
it. Two halves, both real:

- *Static*: `sha256(strategy_entrypoint)` equals `design.strategy_sha256`
  (already enforced at line 349 — the check records it rather than re-invents
  it), and exactly one dataset was resolved, matching
  `design.dataset_ids[0]`, with `sha256(DATA_MANIFEST.json)` equal to
  `design.data_manifest_sha256` (line 307).
- *Dynamic*: install a `sys.addaudithook` around `exec_module` (line 60) and
  around every strategy invocation, recording every `open`, `os.*`, `socket`,
  `subprocess`, and `urllib` event raised from strategy code. Any filesystem
  or network access during strategy execution is a leakage finding. A hit
  under `data/`, or under any future holdout path, is `"failed"`.

Stated limit, which must appear in the check's evidence and not only here: an
audit hook is instrumentation, not a sandbox. Code running in-process can
remove it. The stamp therefore means "no leakage was observed by the audit
hook", and the human approving this should approve that wording, because it is
what the stamp will be worth. Strategies are generated by this system rather
than adversarially supplied, which is why instrumentation is proportionate;
if that ever stops being true, this check needs a process boundary.

### §3.4 `corporate_action_check` — cannot be implemented; must be `"not_run"`

This is the stamp with the widest gap between what it claims today and what is
knowable here, and it is the reason this request cannot be read as
"implement five checks".

To verify that returns are unpolluted by splits, dividends, and re-adjustments
you need a corporate-action record with effective dates, plus the provider's
adjustment policy. `DATA_MANIFEST.json` says in its own words that neither
exists: `corporate_action_policy` for D-0002 states distributions are excluded
and that normalization changed only the header and the symbol column, and
`validation.open_issues` states "Provider adjustment semantics are not exposed
by the connector." That is B-0003 (`FAILURES.md`, open, high severity), the
blocker `backlog/BL-0003-b0003-provider-evidence.md` exists to characterize.

Therefore: status `"not_run"` under G-0004, unconditionally, until BL-0003
produces a provider that exposes adjustment semantics.

A partial detector is still worth running *as evidence*: flag every session
where `|open_t / close_{t-1} − 1|` exceeds a preregistered threshold (10% is a
reasonable default for a broad-market ETF) and record the dates. Without an
action feed those candidates cannot be classified, so they raise the status to
`"warning"` at most, never to `"passed"`. Recommendation: implement the
detector, record its output, and let it move the status from `"not_run"` to
`"warning"` when it fires. The alternative — omit the detector entirely — is
defensible and cheaper; it is the human's call.

### §3.5 `missing_data_check` — implementable only against a declared expectation

`load_bars` (lines 74–116) already validates a great deal *within* the file:
required columns exactly, parseable dates, positive prices, non-negative
volume, valid OHLC envelopes, no duplicate symbol-days, an identical symbol
set on every session, at least three sessions. None of that is recorded
anywhere, which is the first thing to fix — these are real checks whose
results are currently thrown away.

But the one thing a missing-data check must catch, this code cannot see: a
trading session absent from the file altogether. The file defines its own
calendar, so a gap is invisible. Three ways to fix that:

- (a) An exchange calendar. Correct, and out of scope — it is a new dataset
  with its own provenance problem, and the environment is stdlib-only.
- (b) A weekday-gap heuristic: flag consecutive sessions more than four
  calendar days apart. Cheap, catches gross truncation, and cannot
  distinguish a missing session from a holiday. Evidence, not a pass.
- (c) A declared expectation: add an optional `expected_sessions` (integer) to
  each dataset in `DATA_MANIFEST.json` (and to
  `schemas/data-manifest.schema.json`, protected). The check compares it to
  the observed session count and passes only on exact equality.

Recommendation: (c) as the pass condition, with (b) always run and recorded.
`"passed"` when a declared count matches exactly; `"warning"` when (b) fires
and no count is declared; `"not_run"` when neither applies. Option (c) moves
the trust to a human-registered number in a protected file, which is honest
about where the assurance comes from — the machine checks the file against the
declaration, and a human owns the declaration.

Note that the registration of D-0002 already counted its sessions ("650 unique
D-0002 rows in ascending session order", `validation.checks`). The number
exists; it is just not in a field anything reads.

### §3.6 The consequence nobody can route around: promotion becomes impossible

This is the most important paragraph in this request.

`scripts/finalize_experiment.py` lines 116–120 block promotion unless all five
checks read exactly `"passed"`. Under honest stamps the best achievable state
on today's data is:

| check | honest status under G-0004 |
| --- | --- |
| `lookahead_check` | `passed` |
| `survivorship_check` | `not_applicable` |
| `leakage_check` | `passed` |
| `corporate_action_check` | `not_run` (or `warning`) |
| `missing_data_check` | `passed`, if `expected_sessions` is declared |

So **no experiment can be promoted under G-0004 until B-0003 is resolved.**
Three ways to respond:

- (a) *Leave the gate strict.* Promotion stays impossible until the data
  provenance blockers close. Nothing is actually lost: B-0001 and B-0003 are
  open and already say historical strategy evaluation is not valid here, and
  `STATE.json` records `champion_strategy_id: null` — nothing has ever been
  promoted. This change would convert a narrative blocker into a machine-
  enforced one, which is the entire point of the exercise.
- (b) *Accept `"not_applicable"` as pass-equivalent, never `"not_run"`.*
  Necessary if a static-universe experiment should ever be promotable at all.
  Safe only because §3.2 derives `"not_applicable"` from resolved manifest
  facts rather than accepting an assertion.
- (c) *Per-experiment human waiver recorded in `review.json`.*

Recommendation: **(a) plus (b), and explicitly not (c).** A waiver is a bypass,
and this change exists to delete a bypass. If a human wants to promote despite
an unverifiable corporate-action status, the honest route is to resolve B-0003
or to change the promotion rule deliberately in a later generation — not to
stamp an exception onto an individual experiment where it will be read later
as evidence.

If the human prefers (c), it belongs in a separate request; adding it here
would let the first-ever approval round trip smuggle in a new bypass.

## §4 Migration and comparability

- **No recorded evidence is rewritten.** `results/E-0001/`, `results/E-0002/`,
  their `validity.json` files, and their `EXPERIMENTS.jsonl` lines keep the
  stamps they were recorded with. The unearned `"passed"` values stay exactly
  where they are. They are the historical record of what the system claimed,
  and the record of this defect. `EXPERIMENTS.jsonl` is append-only; results
  directories are immutable by rule and by the evaluator's own
  `FileExistsError` guard.
- **The validator's new rule is generation-gated.** Rule 5 of §2 applies only
  to records whose `design.system_generation` is ≥ G-0004. The validator
  already computes `generation_number()` and already compares record
  generations to the current one, so the gate uses existing machinery. Without
  this gate, landing G-0004 would instantly make the repository contract
  invalid on two historical records and wedge every session at
  `loop/validate_session.sh` check 6.
- **Cross-generation results are not directly comparable**, per
  `CORE_MANIFEST.json` `change_policy.cross_generation_results_directly_comparable:
  false`. E-0002's metrics remain the G-0002 baseline for G-0002; a G-0004
  experiment is not comparable to it by rule. Note that in this instance the
  *numbers* would in fact be unchanged — no metric computation is touched —
  which makes it tempting to treat them as comparable anyway. Resist that:
  the policy is about what the generation certifies, not about arithmetic.
- **`STATE.json`** `objective.system_generation` reads `G-0003` and would need
  to move to `G-0004`. It is unsealed and agent-writable. Open question 2 in
  `HANDOFF.md` (whether sessions maintain `STATE.json` at all during
  loop-proving) should be answered before, not during, this migration.

## §5 Tests that must fail under current behavior

Each of these must be red on today's `main` and green after G-0004. They live
in `tests/`, are not sealed, and an autonomous session can write them — but
only *after* the change lands, since a repository whose test suite fails puts
every subsequent session into maintenance mode via the runner's selfcheck.
Writing them now would wedge the loop; this is why they are specified here and
not committed.

1. **The core regression.** Evaluate an experiment in a scratch root with a
   strategy and dataset for which no check can pass, and assert
   `validity.json` contains no `"passed"` among the five. Today all five are
   `"passed"`; this fails.
2. **No ledger, no pass.** Assert every `"passed"` in `validity.json` has a
   `checks.json` entry with a matching `check_id` and non-empty evidence.
   Today `checks.json` does not exist; this fails.
3. **Validator catches a forged stamp.** Construct a scratch repository with a
   G-0004 record whose `validity.lookahead_check` is `"passed"` and whose
   `checks.json` lacks the entry; assert `validate_repository.py` exits
   non-zero. Today it exits zero.
4. **Historical records still validate.** Assert `validate_repository.py`
   exits zero on the real repository, with E-0001 and E-0002 untouched. Green
   today; must stay green. This is the migration test — without it, §4's
   generation gate is untested.
5. **Lookahead is actually detected.** Inject a strategy that reaches for a
   future bar (via the mutable-history hole in §3.1, or by returning weights
   the evaluator would apply to the current session) and assert the run fails
   or the stamp reads `"failed"`. Today it is stamped `"passed"`.
6. **Leakage is actually detected.** A strategy that opens a file under
   `data/` during `target_weights` yields `"failed"`. Today: `"passed"`.
7. **Positive control.** A clean strategy on clean data yields `"passed"` for
   `lookahead_check` and `leakage_check`. Without this, every test above could
   be satisfied by a check that fails everything.
8. **Skill-set derivation.** With `CORE_MANIFEST.json` declaring a skill whose
   directory is absent, the validator fails; with a manifest omitting an
   operative skill, the §1a floor fails. Green-field — no current behavior.

**`tests/test_golden_replay_e0002.py` will break, and it must be fixed in the
same change.** It loads the evaluator from the *working tree*
(`load_module(..., ROOT / "evaluator" / "daily_bar.py")`, line 133) and asserts
that file's sha256 equals the G-0002 sealed hash
(`test_evaluator_bytes_are_the_sealed_g0002_evaluator`, lines 188–201). After
G-0004 the assertion fails, and — worse if it were removed — the replay would
be running *new* evaluator code against E-0002's inputs, which proves nothing
about E-0002. The fix is to materialize the historical evaluator bytes from
`pre-mvp-freeze` (or `design.code_commit`) into the scratch root and load from
there, exactly as the test already does for `DATA_MANIFEST.json` and
`CORE_MANIFEST.json`. This coupling is easy to miss until the loop turns red;
a red test suite puts every subsequent session into maintenance mode.

## §6 Rollback and historical-artifact preservation

- **Rollback is a revert plus a tag pointer, both human acts.** Revert the
  sealed files and `CORE_MANIFEST.json` to their G-0003 contents and set
  `REFERENCE_TAG` back to `pre-mvp-freeze`. Both are protected paths; no
  session can perform or trigger a rollback.
- **Nothing needs undoing in evidence.** Because §4 rewrites no artifact, a
  rollback leaves G-0004 experiment records in place. They would then be
  records at a generation above the manifest's, which
  `validate_repository.py` explicitly rejects ("belongs to a future system
  generation"). So a rollback after any G-0004 experiment has been recorded is
  not clean — the repository would be invalid until those records' generation
  is reconciled, and `EXPERIMENTS.jsonl` is append-only, so they cannot be
  removed. **Roll back before running an experiment under G-0004, or not at
  all.** This should be stated in the ADR that accompanies the change.
- The successor freeze tag is not deleted on rollback. Tags are the historical
  record of what was sealed when; a rollback is a new event, not an erasure.
- `pre-mvp-freeze` continues to hold every G-0003 byte, so recovery of any
  pre-change file is a `git show` away.

## §6a The successor freeze tag, and a trap in the ruleset

`loop/validate_session.sh` verifies sealed hashes against `CORE_MANIFEST.json`
**as it exists at `REFERENCE_TAG`** (line 16, currently `pre-mvp-freeze`),
never against the session's tree — which is precisely why an agent that edits
a sealed file and its manifest entry together still fails. A G-0004 that
changes sealed hashes therefore requires:

1. A human-created tag on the commit carrying the new `CORE_MANIFEST.json`.
2. A one-line change to `REFERENCE_TAG` in `loop/validate_session.sh`.

**Naming trap — verify before relying on it.** The tag ruleset "freeze tag
immutability" matches `refs/tags/pre-*`. A successor named `g0004-freeze`
would be created successfully, protected by nothing, and produce no error at
any point — a freeze tag that is not frozen, failing silently in the one
direction that matters. Name it **`pre-g0004-freeze`**, or add a second
include pattern to the ruleset first. Either way, verify with a rejected
force-update before relying on it, the same way `pre-mvp-freeze` was verified.
Do **not** move `pre-mvp-freeze`: it is immutable by ruleset and is the
historical record of G-0003.

**Ordering hazard — this will wedge the loop if sequenced wrong.** Check 5
reads sealed paths from the *session branch*, which branches from `main`. The
moment the new evaluator is on `main` and `REFERENCE_TAG` still points at
`pre-mvp-freeze`, every session fails check 5 through no fault of its own, and
every session's work is quarantined to a `failed/` branch. The agent cannot
repair this: both `loop/` and `CORE_MANIFEST.json` are protected paths it is
denied. Required sequence, as one push or with no scheduled session between:

1. Land the sealed changes and the new `CORE_MANIFEST.json` on `main`.
2. Create `pre-g0004-freeze` on that commit; verify immutability.
3. Update `REFERENCE_TAG` in `loop/validate_session.sh` — same push, or before
   the next scheduled session fires.
4. Only then let a session run.

If a session does fire mid-transition, its failure is an artifact of the
migration and must not be counted against ADR-0008 exit criterion 1 — and it
is not the induced failure of criterion 2 either, since it demonstrates the
validator failing on a repository fault rather than on bad work.

## §7 The human approval point

The agent stops here. Everything above is a proposal; nothing in this request
has been applied, and no sealed or protected file was modified in producing it.

The human is asked to approve or reject, explicitly:

1. The §2 invariant, including its stated limit (a ledger entry proves a check
   ran, not that the check is good).
2. Per-check dispositions in §3, in particular that `survivorship_check` is
   `"not_applicable"` and `corporate_action_check` is `"not_run"` — that is,
   that G-0004 makes two of five stamps permanently non-passing on today's
   data, by design.
3. §3.6: that promotion becomes impossible until B-0003 resolves —
   recommendation (a)+(b), no waiver mechanism.
4. §1a: that `CORE_SKILLS` un-hardcoding rides in this generation, with the
   floor invariant.
5. §8: whether the interpreter version is recorded in G-0004 (recommended),
   enforced (recommended against, for now), or left alone.
6. §6a: the successor tag name, the ruleset pattern, and the migration
   sequence.
7. Who writes the sealed code (§9).

Once approved, the sealed change is a human act. The agent's role resumes
after G-0004 lands: writing the §5 tests, updating
`tests/test_golden_replay_e0002.py`, and running the first experiment under
honest stamps.

## §8 Should the interpreter version be in this scope?

Input from BL-0001, which HANDOFF.md requires this request to answer rather
than assume. Session 2026-08-09-0525's golden replay of E-0002 found
`equity.csv`, `trades.csv`, and `validity.json` reproduce byte-for-byte while
`metrics.json` differs in exactly one field: `turnover`, in its last two
digits. Cause proven, not guessed — `turnover` is the only metric summing a
long float list (501 equities, line 242), CPython 3.12 changed `sum()` over
floats to Neumaier compensated summation, E-0002 was recorded on ≥ 3.12, and
the loop runner pins 3.11. `design.environment_id` is the free-text string
`"python-stdlib-mvp"`; nothing anywhere records or enforces an interpreter
version.

**For inclusion.** The evaluator is already being opened and resealed, so
recording costs two lines in a file whose hash is changing anyway; a separate
change would need its own approval round trip and its own freeze tag for two
lines. Every G-0004 experiment recorded without it inherits the same ambiguity
E-0002 has — a future replay mismatch will again cost a session's work to
diagnose, and next time the cause may not be benign. And a check ledger whose
entries are "evidence that this run happened as described" is incomplete if it
cannot say what interpreter produced it.

**Against inclusion.** The finding is about metric reproducibility; this change
is about validity stamps. They share a file and nothing else. This is the
first-ever human approval round trip and its legibility is itself the thing
being tested (ADR-0008 exit criterion 5) — every unrelated item added is one
more thing the approver must evaluate, and one more reason a rejection is
ambiguous. Enforcement in particular is a contract change reaching
`scripts/preregister_experiment.py` and the meaning of `environment_id`, and
it earns its own request.

**Recommendation: record in G-0004, do not enforce.** Split the question,
because recording and enforcing have very different costs.

- *Record* (in scope): add `python_version={platform.python_version()}` and
  `python_implementation=` to `run.log`, and a `runtime` block to
  `artifact-manifest.json`. Zero new invariants, zero refusal paths, nothing
  can newly fail. It converts an unfalsifiable determinism claim into a
  checkable one. `run.log` already contains a wall-clock `finished_at`, so it
  was never reproducible and nothing regresses.
- *Enforce* (out of scope, defer to a follow-up): making
  `design.environment_id` structured and refusing to run when the live
  interpreter does not match it. This changes the preregistration contract,
  touches a second sealed script, and would make every experiment
  unreproducible on a future runner image — a real operational cost that
  deserves its own argument. File it as a backlog item when G-0004 lands.

Honest counter to my own recommendation: recording without enforcing means the
next replay mismatch is *diagnosable* but still *happens*. If the human's view
is that bit-exact reproducibility is a property the loop must have rather than
merely observe, then enforcement belongs here and the follow-up should not
exist — the evaluator is only opened once per generation, and this is that
once. Both readings are defensible; the recommendation above optimizes for a
small, legible first approval.

## §9 What this request deliberately does not do

- **No patch is attached**, unlike the earlier requests in this directory.
  Those proposed changes to `loop/` and `.github/` — protected but unsealed,
  where a verified diff is a convenience. This one proposes changes to the
  sealed evaluator and the sealed validator: the components the approval
  boundary exists to protect. An agent-authored diff of them would invite
  review-by-skim of exactly the code that must not be skimmed, and the sealed
  hashes it implies could not be verified without applying it. The request
  specifies behavior and invariants; the human writes the code, or asks the
  agent to write it under supervision as a separate, explicitly authorized
  act. That is a judgment call, not a rule, and it is reversible: say the word
  and a patch can be drafted.
- **It does not fix the defect.** The unconditional stamps remain exactly as
  they are on `main` until a human lands G-0004.
- **It does not touch recorded evidence.** No file under `results/`,
  `reviews/`, `data/`, and no line of `EXPERIMENTS.jsonl` changes, now or
  under the proposed change.
- **It does not remove the six dormant skills.** §1a makes that possible;
  doing it is a separate decision.
- **It does not resolve B-0001 or B-0003.** §3.4 makes their consequence
  visible in the machine record instead of only in `FAILURES.md`.

## Open questions for the human

1. §3.6 is the load-bearing one: is "no promotion until B-0003 resolves" the
   intended consequence, or does it need (b), or (c), or a different
   promotion rule?
2. §3.4 — implement the gap detector as `"warning"` evidence, or omit it?
3. §3.5 — is option (c) (`expected_sessions` in `DATA_MANIFEST.json`) worth a
   protected-schema change, or is (b)-only enough for now?
4. §8 — record, enforce, or neither?
5. §9 — who writes the sealed code?
6. Should G-0004 ship with an ADR? Every prior generation change has one, and
   §6's rollback constraint ("roll back before running an experiment under
   G-0004, or not at all") needs a durable home outside this request.
