# CCR-0001 (G-0004): make the five validity stamps earned

- Filed: 2026-08-09 by autonomous session `2026-08-09-0800` (research mode)
- Origin: `backlog/BL-0002-g0004-change-request.md`; defect first recorded in
  `docs/adr/0008-mvp-reduction.md`
- Requires sealed changes: **YES** — this is a generation change (G-0003 →
  G-0004) under `CORE_MANIFEST.json` `change_policy.human_approval_required`
- Status: **awaiting human approval.** Nothing in this request has been
  applied. No sealed, protected, or evidence file was modified to produce it.
- Related: `docs/adr/0007-bounded-strategy-evolution-loop.md` ("Approval
  boundary"), `backlog/BL-0001-golden-replay-e0002.md` (section 8 below),
  `backlog/BL-0003-b0003-provider-evidence.md` (section 3, corporate actions),
  `FAILURES.md` B-0003

---

## 0. The defect, stated precisely — and the half of it nobody wrote down

`evaluator/daily_bar.py` lines 429–437 build the validity record as:

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

No check runs. The five literals are unconditional. E-0001 and E-0002 both
carry them in `results/*/validity.json` and in `EXPERIMENTS.jsonl`.

That is the known half. The half this request exists to surface:

**The enforcement is already built and is being fed a manufactured input.**
`scripts/finalize_experiment.py` lines 13–19 define `PROMOTION_CHECKS` as
exactly those five fields, and lines 116–120 refuse `outcome == "promote"`
unless every one of them equals `"passed"`:

```python
failed = [check for check in PROMOTION_CHECKS if validity.get(check) != "passed"]
if failed:
    raise ValueError(f"Promotion blocked by validity checks: {failed}")
```

So the system does not lack a gate. It has a gate, and the evaluator hands it
five forged passes. This changes what G-0004 must buy in two ways:

1. Deleting the five override lines is, by itself, a *correct* fix — the
   preregistered values are all `"not_run"` (`scripts/preregister_experiment.py`
   lines 149–153), so `{**prereg["validity"]}` alone yields honest stamps. The
   minimum honest change is a **deletion**, not an addition.
2. That minimum change makes promotion permanently impossible, because
   `"not_run" != "passed"`. Any check that honestly cannot apply — survivorship
   on a one-symbol universe, certainly — would deadlock the ladder forever.

Therefore the evaluator and the promotion gate must change **together**, in one
generation, and the gate must learn the difference between *ran and passed*,
*cannot apply here*, and *not implemented*. A request that changed only the
evaluator would leave the system strictly less capable than the dishonest one.

---

## 1. Sealed and protected files requiring change

All six paths below are sealed under `CORE_MANIFEST.json` component `EV-0002`
(lines 12–43); each carries a `sha256` that must be recomputed and rewritten.

| # | Path | Sealed? | Change | In scope |
|---|------|---------|--------|----------|
| 1 | `evaluator/daily_bar.py` | yes | Replace the five literals with values returned by a check runner; write `checks.json` | **yes, required** |
| 2 | `scripts/finalize_experiment.py` | yes | Teach `PROMOTION_CHECKS` the accept-set `{passed, not_applicable}` | **yes, required** |
| 3 | `scripts/validate_repository.py` | yes | Add the cross-artifact invariant (§2.3); un-hardcode `CORE_SKILLS` (§1.2) | **yes, argued** |
| 4 | `CORE_MANIFEST.json` | protected | New `sha256` for every changed path; `system_generation` → `G-0004` | **yes, mechanical** |
| 5 | `schemas/experiment.schema.json` | yes + protected | none | **no, argued — §1.3** |
| 6 | `scripts/preregister_experiment.py` | yes | Compose the interpreter version into `design.environment_id` | **yes, argued — §8** |
| 7 | `scripts/record_evidence_review.py` | yes | none identified | no |

Unsealed but required in the same landing (agent may edit; listed so the change
is not mistaken for complete without them):

| Path | Change | Why it cannot be deferred |
|------|--------|---------------------------|
| `loop/validate_session.sh` line 16 | `REFERENCE_TAG` → the successor freeze tag | §6a — the session validator goes red until this moves |
| `tests/test_golden_replay_e0002.py` | Two assertions break by construction | §4.3 — this is the sharpest migration consequence in the request |
| `tests/` (new) | The failing tests of §5 | A change with no failing test proves nothing |

### 1.1 `scripts/finalize_experiment.py` — in scope, and BL-0002 did not list it

BL-0002's deliverable list names the evaluator, the manifest, and the
validator. It does not name `finalize_experiment.py`. That is the one addition
this request makes to its own brief, for the reason in §0: the promotion gate
consumes the exact five fields being fixed, and fixing the producer without the
consumer converts a fake pass into a deadlock. Both files are sealed under the
same component, so including it costs one hash entry and no extra approval.

### 1.2 `CORE_SKILLS` un-hardcoding — in scope, argued

`scripts/validate_repository.py` line 26 hardcodes all nine skill names and
lines 367–374 fail if any directory is missing or if `CORE_MANIFEST.json`
disagrees. ADR-0008 (lines 65–73) records that the six dormant skills therefore
cannot be removed without a sealed change, and asks that G-0004 cover it.

It is genuinely separable — nothing about skill-set validation touches validity
stamps. Include it anyway:

- **For:** both edits land in the *same sealed file*. Splitting them means two
  full human-approval round trips, two reseal cycles, and two freeze tags over
  one file, for no gain in reviewability — the diffs do not overlap and a
  reviewer can read them independently within one request.
- **Against, honestly:** it widens the blast radius of a change whose primary
  purpose is evidence integrity, and a reviewer who wants to reject the skill
  edit must now reject or amend a request they otherwise approve.

Recommendation: include, as a clearly separated part B, with the explicit note
that the human may approve part A alone and the agent will not treat partial
approval as rejection of part B.

### 1.3 `schemas/experiment.schema.json` — out of scope, argued, with a trigger

BL-0002 implies the schema may need changing. It does not:
`$defs.check` (lines 261–263) already admits
`["not_run", "passed", "failed", "warning", "not_applicable"]`, and the
`validity` object (lines 177–207) already requires all five keys. Honest stamps
are already schema-legal today. `VALIDITY_FIELDS` in the validator (line 104)
is a **presence** check on key names (lines 274–276), not a value check — so it
also needs no change for honest stamps.

The schema comes back into scope if, and only if, the human prefers the check
record to live *inside* `validity.json` rather than in a separate
`checks.json`. §2.2 recommends the separate artifact precisely to keep the
sealed schema out of this generation.

---

## 2. The exact non-bypassable invariants added

### 2.1 Evaluator: a stamp is a return value, never a literal

**Invariant I-1.** In `evaluator/daily_bar.py`, the string `"passed"` may not
appear as a literal assigned to any of the five fields. Each field takes the
`status` returned by a named check function, and the five check functions are
the only code permitted to produce `"passed"`.

Bypass analysis: an agent editing the evaluator to reintroduce a literal
changes a sealed file, which fails `validate_repository.py` line 392 (working
tree vs. manifest hash) and `loop/validate_session.sh` line 106 (working tree
vs. manifest at the freeze tag). That is the existing seal doing its job; I-1
adds no new enforcement mechanism, it removes the thing the seal was protecting
a lie inside of.

### 2.2 Evaluator: a passed stamp must leave a record

**Invariant I-2.** The evaluator writes `results/<id>/checks.json`, one entry
per check: `{name, status, scope, evidence}` — where `scope` states in prose
what the check does and does not cover, and `evidence` carries the counts or
values the verdict rests on (rows inspected, gaps found, decision/fill pairs
verified). A `"passed"` status with an empty `evidence` is itself invalid.

The plumbing already supports this and needs no design: a `checks.json` entry
added to the `outputs` list (lines 439–446) is covered by the `FileExistsError`
immutability guard (lines 447–448), is hashed into `artifact-manifest.json`
automatically by the loop at lines 475–476, and is re-verified at finalization
by `verify_artifacts` (`scripts/finalize_experiment.py` lines 55–67). One more
artifact costs one line in a list.

**One trap, worth naming because it fails silently.** That manifest loop
iterates `outputs[:-1]`, and the element it drops is the last one —
`artifact-manifest.json` itself, which cannot hash itself. So `checks.json` must
be **inserted before** `result_dir / "artifact-manifest.json"` (line 445), not
appended after it. Appending would leave `checks.json` written to disk,
unhashed, absent from the artifact manifest, and therefore absent from the
`EXPERIMENTS.jsonl` artifact list — which is precisely the evidence I-3 depends
on. Nothing would error; the record would just be quietly unverifiable. A test
asserting `checks.json` appears in `artifact-manifest.json` with a matching
sha256 belongs in §5 (it is folded into T-5).

### 2.3 Validator: a passed stamp with no record fails the repository

**Invariant I-3.** In `scripts/validate_repository.py`, for every
`EXPERIMENTS.jsonl` record whose `design.system_generation` is `G-0004` or
later: if any of the five fields equals `"passed"`, then
`results/<id>/checks.json` must exist, must contain an entry for that check with
status `"passed"`, and must appear in the record's `artifacts` list with a
matching `sha256` (the hash is already re-verified at line 299).

This is what makes the invariant non-bypassable rather than merely honest.
Hand-editing `validity.json` to say `"passed"` now requires also forging
`checks.json`, its entry in `artifact-manifest.json`, and its `sha256` in the
append-only `EXPERIMENTS.jsonl` record — and the ledger is append-only, so the
forgery must happen before the record is written, i.e. inside the sealed
evaluator, i.e. it must break a seal. The generation predicate is essential:
without it, this invariant would retroactively invalidate E-0001 and E-0002,
which §4 forbids.

### 2.4 Finalization: the gate accepts earned passes and honest exemptions

**Invariant I-4.** `PROMOTION_CHECKS` is evaluated against the accept-set
`{"passed", "not_applicable"}`. `"not_run"`, `"failed"`, and `"warning"` all
block promotion, and the error message names which check and which status.

The consequence must be stated plainly rather than engineered around: with
`leakage_check` and `corporate_action_check` honestly at `"not_run"` (§3),
**nothing can be promoted under G-0004 until those checks are implemented.**
That is not a defect of this request. It is the true statement about the
evidence, arriving where it belongs. It costs nothing today — research is
frozen, the evidence stage is `baseline`, and no promotion is pending. A waiver
mechanism (human-approved, recorded per experiment) is deliberately **not**
proposed here: the first thing a waiver would be used for is the very gap it
would be papering over.

---

## 3. What each check would actually verify, and which cannot be honest yet

Scope: daily bars, single instrument (SPY), fed from an immutable
content-addressed snapshot, no fitting, no universe construction.

### 3.1 `lookahead_check` — implementable now → `passed` / `failed`

What it verifies: that no decision consumed information dated at or after the
bar it acts on. The evaluator already has the structure that makes this
checkable rather than assertable — `history[symbol]` is appended after the
strategy call, weights computed on session *i* are held in `pending_weights`
and filled on session *i+1* (lines 416–419).

Concrete check: instrument the history handed to the strategy and assert
(a) every bar visible at decision time has `date <= decision_date`, and (b) for
every trade, the decision that produced it has a strictly earlier date. Record
counts of decisions and fills verified.

Caveat to record in `scope`: this verifies the *evaluator's* discipline, not the
strategy's. A strategy that closes over an out-of-band data file is not caught.
That limitation belongs in the `scope` string, not in a footnote nobody reads.

### 3.2 `missing_data_check` — implementable now, with a stated ceiling → `passed` / `failed`

What it verifies, from data already in hand: dates strictly increasing, no
duplicate dates, every evaluated date carries a bar for every required symbol,
OHLC coherence (`low <= open, close <= high`; strictly positive prices), no
null/NaN fields.

What it cannot verify: **a wholly absent session.** Detecting "2024-07-03 is
missing" requires a trading calendar, and the repository has none. Without one
this check cannot distinguish a market holiday from a dropped bar. The `scope`
string must say so in those words, because a stamp reading `passed` on a check
that silently cannot see whole-session gaps is a smaller version of exactly the
defect this request fixes.

### 3.3 `survivorship_check` — cannot apply → `not_applicable`

The universe is one symbol, static, with no constituent history and no
delisting. There is no survivorship bias to detect, and there is also no
mechanism that *could* detect one: universe membership with effective dates does
not exist in `DATA_MANIFEST.json`. `not_applicable` is the honest verdict, and
the check must justify it structurally — asserting the preregistered universe is
a single static symbol — rather than returning the constant.

The moment a multi-symbol or time-varying universe is preregistered, this must
return `not_run`, not `not_applicable`. That transition should be a test (§5).

### 3.4 `leakage_check` — not implementable → `not_run`

Distinct from lookahead: leakage is contamination between the evaluation window
and any holdout or fitting window — purge/embargo honored, holdout untouched,
parameters not fitted on evaluated data. Under the MVP there is no fitting step
and no holdout registry, so there is nothing to check *against*.
`purge_periods` and `embargo_periods` are preregistered fields
(`scripts/preregister_experiment.py` lines 147–148) but no code consumes them.

`not_run` is the honest verdict. Verifying "the evaluation window does not
intersect any registered holdout window" becomes possible when a holdout
registry exists; that is a later generation's work, not this one's.

### 3.5 `corporate_action_check` — not implementable, and blocked → `not_run`

What it would verify: that the price series' adjustment policy is declared
(raw / split-adjusted / total-return), that adjustments have effective dates,
and that no silent re-adjustment occurred between retrievals.

None of that metadata exists. `FAILURES.md` B-0003 records that the provider
exposes no publication timestamp, completed-bar flag, or revision identifier,
and `STATE.json` `handoff.unresolved_risks` records that distributions are
excluded from D-0001 and D-0002. This check is therefore blocked on external
evidence, not on implementation effort.

**This is the concrete consumer BL-0003 is looking for.** BL-0003 element 5
(adjustment semantics) and element 3 (revision identifiers) are precisely the
inputs that would let this check return anything other than `not_run`. The two
items should be read together.

### 3.6 Summary

| Check | G-0004 verdict | Blocks promotion under I-4? |
|-------|----------------|------------------------------|
| `lookahead_check` | `passed` (earned) | no |
| `missing_data_check` | `passed` (earned, ceiling stated) | no |
| `survivorship_check` | `not_applicable` | no |
| `leakage_check` | `not_run` | **yes** |
| `corporate_action_check` | `not_run` | **yes** (until B-0003) |

Two of five earned, one honestly exempt, two honestly blocked. Under G-0003 the
same table reads "five of five passed", and every entry in it is false.

---

## 4. Migration and cross-generation comparability

### 4.1 Recorded evidence is never rewritten

E-0001 and E-0002 keep their stamps exactly as recorded, in
`results/*/validity.json`, in their artifact manifests, and in
`EXPERIMENTS.jsonl` (append-only per ADR-0001). No backfill, no annotation
inside the artifacts. The stamps are false; the record of them is true, and the
record is what the ledger is for.

### 4.2 Comparability

`CORE_MANIFEST.json` `change_policy.cross_generation_results_directly_comparable`
is already `false` (line 59), so G-0002/G-0003 results are formally
non-comparable with G-0004 results and no new policy is needed. Substantively
the *metrics* are unaffected — this change touches no pricing, fill, or metric
code path — but the **validity claims** are not comparable in any sense: a
G-0004 `passed` means a check ran, a G-0002 `passed` means a literal was
written. Anyone comparing across the boundary must read them as different
fields that happen to share a name.

### 4.3 The golden replay breaks, by construction, in two places

This is the sharpest migration consequence and it is not hypothetical.
`tests/test_golden_replay_e0002.py` (added 2026-08-09 by BL-0001) will fail
under G-0004 at two specific assertions:

1. `test_evaluator_bytes_are_the_sealed_g0002_evaluator` (line 188) asserts the
   sha256 of `evaluator/daily_bar.py` **on disk** equals the sha256 recorded for
   it in the G-0002 `CORE_MANIFEST.json`. G-0004 changes the evaluator's bytes,
   so this assertion becomes false the moment the change lands.
2. `test_replayed_outputs_are_byte_identical` (line 221) compares
   `DETERMINISTIC_OUTPUTS = ("validity.json", "equity.csv", "trades.csv")`
   byte-for-byte. The G-0004 evaluator produces honest stamps, so the replayed
   `validity.json` no longer matches E-0002's recorded all-`passed` file.

Both failures are correct behavior — the test is doing its job — but they mean
**the G-0004 landing is incomplete until the replay test is rewritten**, and
whoever applies it must not discover this from a red suite. The rewrite is
straightforward and should be specified now, not improvised then: replay E-0002
against the *G-0002 evaluator bytes read from git* at `design.code_commit`
rather than against the on-disk file, which is what "golden replay" should have
meant all along and which makes the test immune to every future generation.
`tests/` is not sealed, so the agent can do this; it must be part of the same
commit, not a follow-up.

Note that this also removes the incidental value of the on-disk assertion —
"the evaluator has not drifted" — which should be re-added as a separate,
explicit test against the *current* generation's manifest.

---

## 5. Tests that must fail under current behavior

A change that no test currently rejects has not been demonstrated. Each of
these must be written to fail against G-0003 and pass under G-0004.

| # | Test | Fails today because |
|---|------|---------------------|
| T-1 | Evaluate a fixture whose bar series has a duplicated date → `missing_data_check == "failed"` | today it is `"passed"` |
| T-2 | Evaluate a fixture with a non-monotone / null-priced bar → `missing_data_check == "failed"` | today `"passed"` |
| T-3 | Single-symbol universe → `survivorship_check == "not_applicable"` | today `"passed"` |
| T-4 | Any G-0004 run → `corporate_action_check == "not_run"` and `leakage_check == "not_run"` | today both `"passed"` |
| T-5 | Clean run → `lookahead_check == "passed"`, `checks.json` carries a non-empty `evidence` for it, **and** `checks.json` appears in `artifact-manifest.json` with a matching sha256 | `checks.json` does not exist today; the manifest half also catches the `outputs[:-1]` ordering trap in §2.2 |
| T-6 | A `validity.json` hand-edited to `"passed"` with no matching `checks.json` entry → `validate_repository.py` errors | no such rule today (I-3) |
| T-7 | Promotion with `survivorship_check == "not_applicable"` and all else earned → **allowed** | blocked today: `"not_applicable" != "passed"` |
| T-8 | Promotion with any `"not_run"` → refused, error names the check | passes today only because nothing is ever `"not_run"` |
| T-9 | Pre-G-0004 records in `EXPERIMENTS.jsonl` still validate | guards §4.1 — must pass before *and* after |

T-9 is the regression that matters most: it is the one that catches an I-3
implementation that forgot the generation predicate and retroactively
invalidated the repository's entire evidence history.

---

## 6. Rollback and historical-artifact preservation

**Rollback** is a revert of the code commit plus restoration of the previous
`CORE_MANIFEST.json` (sealed hashes and `system_generation: G-0003`) plus
resetting `loop/validate_session.sh`'s `REFERENCE_TAG` to `pre-mvp-freeze`. No
data migration exists to undo, because nothing rewrites existing artifacts.

**What rollback does not undo:** any experiment finalized under G-0004 keeps its
`checks.json` and its honest stamps, and its `EXPERIMENTS.jsonl` record is
append-only and stays. A rolled-back repository therefore contains G-0004
records it can no longer produce. `validate_repository.py` must not choke on
them: the I-3 generation predicate makes it skip records at generations it does
not know, which is the same mechanism that protects E-0001/E-0002 forward. Both
directions come free from one correctly-written predicate — worth testing in
both directions (extend T-9).

**Historical artifacts** under `results/`, `reviews/`, `data/snapshots/`,
`data/raw/`, and `data/provenance/` are untouched in both directions. The
`pre-mvp-freeze` tag is not moved, ever (§6a).

### 6a. The successor freeze tag

`loop/validate_session.sh` line 16 sets `REFERENCE_TAG="pre-mvp-freeze"` and
lines 106–137 verify sealed hashes against `CORE_MANIFEST.json` **as it exists
at that tag**. G-0004 changes sealed hashes, so it needs a new tag and a
one-line change to that variable.

**Do not move `pre-mvp-freeze`.** It is immutable by ruleset and is the
historical record.

**Name the successor `pre-g0004-freeze`.** The tag ruleset `freeze tag
immutability` matches `refs/tags/pre-*`. A tag named outside that pattern —
`g0004-freeze`, the obvious choice — would be created successfully, protected by
nothing, and produce no error at any point. The failure mode is silence, which
is why the name is a requirement of this request and not a convention.

**Verify rather than assume.** After creating the tag, attempt a force-update
and confirm the server rejects it, exactly as `pre-mvp-freeze` was verified.
A protection nobody tested is a protection nobody has.

**Expect a red window.** `validate_repository.py` (line 392) checks the working
tree against the working-tree manifest and goes green as soon as the manifest is
updated. `loop/validate_session.sh` checks against the manifest *at the tag* and
stays red until the tag exists and `REFERENCE_TAG` points at it. Between those
two moments the session validator fails, correctly. **Do not resolve that
failure by editing hashes** — resolve it by creating the tag.

Ordering that closes the window: (1) land the code and manifest change,
(2) create and verify `pre-g0004-freeze` on that commit, (3) change
`REFERENCE_TAG` in the same or immediately following commit. Steps 2 and 3 are
human-applied — `loop/` is a human path (ADR-0009).

---

## 7. The human approval point

The agent stops here. What the human is being asked to approve:

1. **That the generation change happens at all** — G-0003 → G-0004, with the
   understanding from §2.4 that an honest system cannot promote anything until
   `leakage_check` and `corporate_action_check` become implementable, and that
   `corporate_action_check` depends on B-0003, which is not the agent's to
   resolve.
2. **The scope calls**, each of which the human may overturn without
   invalidating the rest: `finalize_experiment.py` **in** (§1.1),
   `CORE_SKILLS` un-hardcoding **in** as a separable part B (§1.2), the schema
   **out** (§1.3), interpreter version **recorded but not enforced** (§8).
3. **The five verdicts** in the §3.6 table — specifically that
   `survivorship_check` returns `not_applicable` rather than `not_run`, which is
   the one verdict in the table that is a judgment call rather than a fact.
4. **The tag plan** in §6a, including that a human creates and force-update-tests
   `pre-g0004-freeze` and edits `loop/validate_session.sh`.
5. **The golden-replay rewrite** in §4.3 as part of the same landing.

Who does what, per ADR-0009: the human owns sealed components, `loop/`,
generation changes, and this approval. The agent may write the new tests and the
replay rewrite under `tests/` once approved, and may not touch anything in §1's
first table under any circumstances.

Approving this document is not approving a diff. No implementation exists yet;
this request is the specification a diff would be reviewed against.

---

## 8. The interpreter version — decided: record, do not enforce, include in scope

BL-0001 established (see `backlog/BL-0001-golden-replay-e0002.md`, "Outcome
2026-08-09") that E-0002's `metrics.json` is not bit-reproducible across CPython
minor versions. `turnover` is the only metric summing a long float list (501
equities); CPython 3.12 switched `sum()` over floats to Neumaier compensated
summation. Recorded `0.8085773955620554`, replayed on 3.11
`0.8085773955620549` — 5e-16 relative, one metric, everything else exact.
`design.environment_id` is the free-text string `"python-stdlib-mvp"`; nothing
records or enforces an interpreter version anywhere.

BL-0002 requires this be argued either way rather than left unmentioned.

**Decision: record the interpreter version in `design.environment_id`; do not
enforce it; include the recording in G-0004's scope.**

*Why record.* Reproducibility claims that cannot name their interpreter are
claims about nothing. `environment_id` is already a required schema field
(`schemas/experiment.schema.json` line 99, `minLength: 1`), already free text,
and already composed at preregistration
(`scripts/preregister_experiment.py` line 116). Making it carry
`python-stdlib-mvp/cpython-3.11.9` is a change to what one sealed script
*composes*, not to the contract's shape — no schema change, no migration, no new
field. It is the cheapest possible place to put this information, and the cost
of omitting it compounds: every future experiment recorded without it is another
result whose divergence can never be explained after the fact.

*Why include it in G-0004 rather than filing it separately.*
`preregister_experiment.py` is sealed under the same EV-0002 component. A
separate change request for a one-line string composition would cost a second
full approval round trip, a second reseal, and a second freeze tag — more
process than the change. It rides along or it waits indefinitely, and waiting
indefinitely is how it gets forgotten.

*Why not enforce.* Refusing to evaluate under a non-matching interpreter is the
tempting version and it is wrong here:

- It would make E-0002's own golden replay unrunnable on 3.12+, breaking the
  one test that *proved* the divergence — punishing the work that found it.
- The divergence is 5e-16 on one metric. No decision in this repository turns on
  the sixteenth significant figure; the promotion rules operate on `total_return`
  and `sharpe_ratio`, both of which reproduced exactly.
- Enforcement without a pinned, reproducible environment (a lockfile, a
  container digest) is theatre: it would reject a mismatched interpreter while
  saying nothing about the rest of the environment.

*The argument against this decision, stated fairly.* If determinism is a
contract term, then "deterministic to 1e-15" is a weaker contract than the
repository's language implies, and recording without enforcing makes the
weakening explicit but does not fix it. Someone who believes bit-exactness is
the point should reject this section and require an enforced environment digest
instead — a larger change, correctly scoped to its own generation, and one this
request would support rather than resist. What is not defensible is the status
quo: a free-text string that names no interpreter, in a system that claims
replayability.

*Not proposed:* changing `turnover` to `math.fsum`. It would alter a sealed
metric computation, break byte-comparability with recorded results for no
decision-relevant gain, and mix a numerics change into an integrity change.

---

## 9. What this request does not do

- It does not fix the defect. Nothing was applied; `evaluator/daily_bar.py` is
  byte-identical to its sealed hash.
- It does not implement `leakage_check` or `corporate_action_check`, and does
  not propose a waiver that would let their absence be ignored.
- It does not resolve B-0001 or B-0003, and does not change any dataset's
  status.
- It does not touch `STATE.json`, whose `next_actions` (A-0008, A-0009) describe
  frozen research. A-0008's description — "prepare the narrow G-0004 change
  proposal" — is the ancestor of this document, but A-0008 is owned by the
  dormant `skill-lifecycle-governance` skill and its stated prerequisite
  ("A-0009 completed and B-0003 resolved") is unmet. This request is filed under
  BL-0002's authority, not A-0008's, and is deliberately narrower: validity
  stamps only, not the full ADR-0007 evolution-loop enforcement.
