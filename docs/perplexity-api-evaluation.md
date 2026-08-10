# Perplexity API evaluation for Alpha Lab Genesis

- Status: research note (no dataset status changes, no protected-surface changes)
- Date: 2026-08-10
- Scope: Sonar API + Perplexity Cookbook, mapped to the autonomous loop stages
  and the PIT discipline in `DATA_MANIFEST.json`, B-0003, and ADR-0007.

**Sourcing note.** docs.perplexity.ai blocked direct fetch from this
environment's egress policy, so every claim below was sourced from the official
docs' own machine-readable export (`https://docs.perplexity.ai/llms-full.txt`)
via an indexed mirror, plus search constrained to docs.perplexity.ai,
retrieved 2026-08-10. Each claim cites the canonical page URL recorded for it.
Items where the export was ambiguous are marked and repeated in §5 rather than
asserted.

## 1. API surface map

**Chat completions.** `POST https://api.perplexity.ai/chat/completions`, Bearer
auth, OpenAI-compatible request shape (`model`, `messages`, `temperature`,
`max_tokens`, `top_p`, `top_k`, `response_format`, `stream`)
([quickstart](https://docs.perplexity.ai/docs/getting-started/quickstart),
[sonar-post](https://docs.perplexity.ai/api-reference/sonar-post),
[openai-compatibility](https://docs.perplexity.ai/docs/sonar/openai-compatibility)).
Usage reporting includes `citation_tokens`, `num_search_queries`,
`reasoning_tokens`, and an itemized `cost` object on deep research
([sonar-deep-research](https://docs.perplexity.ai/docs/sonar/models/sonar-deep-research)).
No `seed` parameter is documented anywhere — determinism across runs is not a
supported contract (§5).

**Models.** Current enum: `sonar`, `sonar-pro`, `sonar-reasoning-pro`,
`sonar-deep-research`
([sonar-post](https://docs.perplexity.ai/api-reference/sonar-post),
[sec-guide](https://docs.perplexity.ai/guides/sec-guide)). `sonar-reasoning`
was deprecated and removed 2025-12-15 (replacement `sonar-reasoning-pro`);
`r1-1776` was removed 2025-08-01
([changelog](https://docs.perplexity.ai/docs/resources/changelog)). Anything in
our notes referencing `sonar-reasoning` or `llama-3-sonar-*` is stale.
`sonar-deep-research` takes `reasoning_effort: low|medium|high`
([llms-full.txt](https://docs.perplexity.ai/llms-full.txt)). **Bigger shift:**
the cookbook's canonical repo README now states the Agent API
(`POST /v1/responses`, multi-provider models plus `web_search` /
`finance_search` / `fetch_url` / `sandbox` tools) is the primary API and that
"The Sonar API (`/chat/completions`) is deprecated", pointing at
`docs.perplexity.ai/docs/agent-api/migrate-from-sonar`
([api-cookbook README](https://github.com/perplexityai/api-cookbook/blob/main/README.md)).
No shutdown date is given anywhere we could retrieve (§5) — but new
integrations should assume the Agent API is the long-term surface.

**Search grounding.** `search_mode`: `web` (default), `academic`, `sec` — `sec`
targets U.S. SEC filings
([academic-filter-guide](https://docs.perplexity.ai/guides/academic-filter-guide)).
`search_domain_filter`: up to 20 entries, allowlist or `-`-prefixed denylist
(cannot mix), URL-path granularity allowed
([domain-filter](https://docs.perplexity.ai/docs/search/filters/domain-filter)).
`search_recency_filter`: `hour|day|week|month|year`, mutually exclusive with
the date filters; `search_after_date_filter` / `search_before_date_filter`
take **MM/DD/YYYY** — day granularity only, filtering on *publication* date;
`last_updated_after_filter` / `last_updated_before_filter` filter on
page-update date
([date-range-filter-guide](https://docs.perplexity.ai/guides/date-range-filter-guide)).
Hard caveat: **all date/recency filters are silently ignored under
`search_mode="academic"`**
([academic-filter-guide](https://docs.perplexity.ai/guides/academic-filter-guide)).
`web_search_options.search_context_size: low|medium|high` controls retrieval
depth and the per-request search fee
([sec-guide](https://docs.perplexity.ai/guides/sec-guide),
[pricing](https://docs.perplexity.ai/docs/getting-started/pricing));
`disable_search` and `enable_search_classifier` exist
([llms-full.txt](https://docs.perplexity.ai/llms-full.txt)).

**Structured outputs.** `response_format: {"type":"json_schema", "json_schema":
{"name": ..., "schema": {...}}}`; `name` required, 1–64 alphanumeric chars;
schema adherence holds unless output hits `max_tokens`; the *first* request
with a new schema can take 10–30 s to prepare (then cached)
([output-control](https://docs.perplexity.ai/docs/agent-api/output-control),
[FAQ](https://docs.perplexity.ai/docs/resources/faq),
[agent-research-assistant cookbook](https://docs.perplexity.ai/docs/cookbook/examples/agent-research-assistant/README)).
Regex `response_format` no longer appears in current docs — treat as
unconfirmed/removed (§5).

**Citations payload.** The `citations` array is fully deprecated; the current
field is `search_results[]` with `title`, `url`, `date` (publish date), and
`last_updated`, both nullable
([changelog](https://docs.perplexity.ai/docs/resources/changelog),
[sonar-deep-research](https://docs.perplexity.ai/docs/sonar/models/sonar-deep-research)).
**No per-result retrieval timestamp is documented** — the only retrieval time
we can establish is our own wall clock at call time. That single fact drives
every PIT plan in §3.

**Async / batch.** An async API exists — created for `sonar-deep-research`
("research-intensive tasks that may require longer processing times"):
`POST /async/chat/completions`, `GET .../{request_id}`, results retained
**7 days**
([changelog](https://docs.perplexity.ai/docs/resources/changelog),
[llms-full.txt](https://docs.perplexity.ai/llms-full.txt)). Newer pages also
show a `/v1/async/sonar` path — the docs look mid-migration and the canonical
path is unverified (§5). No file-based batch API is documented.

**Standalone Search API.** `POST /search` returns raw ranked `results[]`
(`title`, `url`, `snippet`, `date`, `last_updated`) without LLM synthesis;
supports `max_results`, `max_tokens` per page, and the same date filters
([search-post](https://docs.perplexity.ai/api-reference/search-post),
[changelog](https://docs.perplexity.ai/docs/resources/changelog)). One guide
shows `/search/create` instead — canonical path unverified (§5).

**Rate limits & tiers.** Tiers advance automatically by cumulative spend and
never downgrade. Tier 0: 50 RPM for sonar/sonar-pro/sonar-reasoning-pro,
5 RPM for sonar-deep-research and async-create; Tier 1: 100/100/100/10 RPM
([rate-limits-usage-tiers](https://docs.perplexity.ai/docs/admin/rate-limits-usage-tiers)).
A prose passage on the same page claims 1,000–4,000 RPM for sonar-pro at
higher tiers, conflicting with the table — unresolved (§5). Any plausible tier
is far above our ~5–20 calls/week; rate limits are a non-issue for the loop.

**Pricing.** Token cost plus a per-request search fee scaled by
`search_context_size`: `sonar` $1/$1 per 1M in/out + $5–$12 per 1K requests;
`sonar-pro` $3/$15 + $6–$14 per 1K; `sonar-reasoning-pro` $2/$8 + $6–$14 per
1K ([pricing](https://docs.perplexity.ai/docs/getting-started/pricing),
[pricing page](https://docs.perplexity.ai/pricing)). `sonar-deep-research`:
$2/1M in, $8/1M out, $2/1M citation tokens, $5/1K search queries, $3/1M
reasoning tokens
([sonar-deep-research](https://docs.perplexity.ai/docs/sonar/models/sonar-deep-research)).
Order of magnitude: a `sonar` call ≈ $0.01; a deep-research job ≈ $0.5–$5
depending on effort. Latency is **not documented** for any model; the async
API's existence implies deep research runs minutes-scale. Measure in the
prototype before trusting any latency number.

**Data retention.** Sonar API has a documented Zero Data Retention policy; no
training on customer data
([privacy-security](https://docs.perplexity.ai/docs/resources/privacy-security)).
Async results being stored 7 days is the one documented exception.

## 2. Cookbook inventory

Inventory taken from the cookbook's canonical source repo
(`github.com/perplexityai/api-cookbook`, which states it syncs to
docs.perplexity.ai/cookbook on every commit; docs-site URLs follow
`https://docs.perplexity.ai/docs/cookbook/examples/<name>/README`). Relevance
scored 1–5 against Alpha Lab Genesis.

| Example / article | Purpose | API features used | Rel. | Why |
|---|---|---|---|---|
| [Financial News Tracker](https://docs.perplexity.ai/docs/cookbook/examples/financial-news-tracker/README) | Financial news monitoring + sentiment | `sonar-pro`, optional Pydantic `json_schema`, citations; **no recency filter** | **4** | Closest match to the post-close observer, but fails PIT rules as written (see §3.1). |
| [Fact Checker CLI](https://docs.perplexity.ai/docs/cookbook/examples/fact-checker-cli/README) | Rate claims TRUE/FALSE/MISLEADING with sources | `sonar-pro`, `json_schema`, citation-index remapping | 3 | Verdict-schema + citation-remap pattern is reusable for adversarial review tooling; not evidence-grade. |
| [Academic Research Finder](https://docs.perplexity.ai/docs/cookbook/examples/research-finder/README) | Find/summarize academic literature | `sonar-pro`, prompt-driven scholarly sourcing (doesn't even use `search_mode=academic`) | 3 | Skeleton for the hypothesis-generation literature scan (§3.2), though we'd rebuild the retrieval side. |
| [Equity Research Brief](https://docs.perplexity.ai/docs/cookbook/examples/equity-research-brief/README) | One-call research brief per ticker | **Agent API**: `finance_search`+`web_search`+`fetch_url`, `max_steps`, cost accounting | 3 | Demonstrates `finance_search` returning **as-of timestamps** and per-call cost — the current-generation pattern. |
| [Daily Knowledge Bot](https://docs.perplexity.ai/docs/cookbook/examples/daily-knowledge-bot/README) | Cron-scheduled daily fact fetch | `sonar`, external cron, date-stamped output files | 2 | Trivial content, but the only Sonar example that records retrieval dates; its cron shape matches the observer. |
| [Finance Chart Sandbox](https://docs.perplexity.ai/docs/cookbook/examples/finance-chart-sandbox/README) | Chart price history via sandboxed code exec | Agent API `sandbox` tool, `background:true` + polling, file artifacts | 2 | Background-job + artifact-download pattern is instructive; its data path (Yahoo scrape in sandbox) is not evidence-grade. |
| [SpaceX SPCX Briefing](https://docs.perplexity.ai/docs/cookbook/examples/spacex-spcx-briefing/README) | Quantitative brief on a new ticker | Agent API, `max_steps=8`, ticker-disambiguation prompting | 2 | Useful `finance_search` prompt engineering; no PIT relevance. |
| [OpenAI Agents Integration](https://docs.perplexity.ai/docs/cookbook/articles/openai-agents-integration/README) | Sonar inside OpenAI Agents SDK | `AsyncOpenAI` at `api.perplexity.ai`, function tools | 2 | Confirms OpenAI-compat surface for SDK choice; agent frameworks are out of scope for our loop. |
| [Disease Information App](https://docs.perplexity.ai/docs/cookbook/examples/disease-qa/README) | Browser medical Q&A | `sonar-pro`, JSON-by-prompt (no `response_format`) | 1 | Anti-pattern for us: schema enforcement by prompt only. |
| [Discord Bot](https://docs.perplexity.ai/docs/cookbook/examples/discord-py-bot/README) | Q&A Discord bot | OpenAI SDK, `sonar-pro` | 1 | Chat UX, irrelevant. |
| [Memory Management](https://docs.perplexity.ai/docs/cookbook/articles/memory-management/README) (+2 sub-guides) | Conversation memory via LlamaIndex / LanceDB | `sonar-pro` + summarization / vector store | 1 | Our loop is deliberately stateless one-shot; conversation memory is the opposite of preregistration. |

The cookbook also carries a **Community Showcase** of 26 third-party apps
(Briefo, CityPulse, 4Point Hoops, Ellipsis, BazaarAISaathi, CycleSyncAI, Daily
News Briefing, Executive Intelligence, Fact Dynamics, FirstPrinciples,
FlameGuardAI, Flow & Focus, Greenify, Monday, MVP LifeLine, PerplexiCart,
PerplexiGrid, Perplexity Client, Dart/Flutter SDKs, Perplexity Lens,
PosterLens, Sonar Chromium Browser, StarPlex, TruthTracer, UnCovered, Valetudo
AI — [showcase index](https://github.com/perplexityai/api-cookbook/tree/main/docs/showcase)).
All score **1**: marketing showcases, no implementation detail worth mining.

Two blunt observations: **no cookbook example records retrieval timestamps or
per-article publication dates** (except the Daily Knowledge Bot's filename
stamp and `finance_search`'s own as-of quote timestamps), and **none uses
`search_recency_filter`** — the "real-time" Financial News Tracker enforces
recency purely through prompt prose. The cookbook is a pattern library, not an
engineering reference; everything evidence-grade we must build ourselves.

## 3. Prioritized use cases for the autonomous loop

The one structural fact to hold onto: **Perplexity can never establish
historical availability** — `search_results[].date` is a provider-asserted
publish date over today's index, not an as-of index. So every integration
below is forward-only by construction: the response is snapshotted at call
time via `data_adapters/immutable_snapshots.py` (which already gates
`resolve_as_of` on `retrieved_at`), and nothing is ever backfilled. That is
exactly the D-0002 narrow-use policy generalized, and it means these
integrations *coexist with* B-0003 rather than being blocked by it.

### 3.1 Post-close news/event log for frozen strategies (Financial News Tracker, hardened)

- **Loop stage:** (c) post-close observation.
- **Problem solved:** ADR-0007's forward-evidence collector needs an
  append-only stream of market observations for frozen strategies. A dated,
  domain-filtered news digest per session close is the natural companion
  evidence to the paper-account reconciliation.
- **Honest assessment of the cookbook example:** as shipped it does **not**
  meet PIT rules. It sets no `search_recency_filter` (recency is prompt prose:
  "Time period: Last 24 hours"), its schema has no date field per news item,
  it records no retrieval timestamp, and it still references the removed
  `citations` field and `sonar-reasoning` model
  ([financial_news_tracker.py](https://github.com/perplexityai/api-cookbook/blob/main/docs/examples/financial-news-tracker/financial_news_tracker.py)).
  The salvageable part is the Pydantic→`response_format` pattern. Everything
  else we rebuild.
- **API shape:** `POST /chat/completions`, `model="sonar"`,
  `search_recency_filter="day"`, `search_domain_filter` allowlist (≤20, e.g.
  reuters.com, bloomberg.com, wsj.com, sec.gov), `web_search_options:
  {search_context_size:"medium"}`, `response_format` json_schema with per-item
  `published_date` echoed from sources. Read `search_results[]`
  (`url`,`date`,`last_updated`) — not model prose — as the dated record.
- **PIT provenance plan:** write the full raw response JSON to disk, register
  via `data_adapters/immutable_snapshots.py: register_snapshot()` with
  `retrieved_at = as_of = call wall-clock`; `search_results[].date` is
  provider-asserted publish metadata, **not sufficient** as an availability
  timestamp — the snapshot registry entry is the authority. Evidence is
  forward-only: usable for decisions at/after `retrieved_at`, never backfilled
  (same policy as D-0002).
- **Failure modes / fail-closed:** hallucinated items → only entries whose URL
  appears in `search_results` are admissible, others dropped and logged;
  citation drift (URL dies/edits) → the snapshot is the record, never
  re-fetch; empty/failed call → record a `no_observation` marker, never retry
  past budget; schema violation → discard run, keep raw snapshot.
- **Cost / latency:** ~1 call/day at ≈$0.006–0.01 (sonar medium context)
  — pennies/month. Latency undocumented; runs in the post-close task, not the
  90-minute session. Zero weekly-budget impact.
- **Gate:** ADR-0007 lists six activation conditions for the collector (frozen
  strategy past `walk_forward`, lineage-taint enforcement, writer lease,
  human approval…). None are met today, so this is a design-ahead prototype —
  build and dry-run it, schedule nothing.

```python
import json, time, requests, pathlib
from data_adapters.immutable_snapshots import register_snapshot

SCHEMA = {"type": "object", "additionalProperties": False,
  "required": ["items"], "properties": {"items": {"type": "array", "items": {
    "type": "object", "additionalProperties": False,
    "required": ["headline", "summary", "source_url", "published_date"],
    "properties": {"headline": {"type": "string"}, "summary": {"type": "string"},
                   "source_url": {"type": "string"}, "published_date": {"type": ["string", "null"]}}}}}}

body = {"model": "sonar",
        "messages": [{"role": "user", "content":
            "List today's material news events for SPY (S&P 500 ETF): macro data, Fed, index-level flows. Facts only, no advice."}],
        "search_recency_filter": "day",
        "search_domain_filter": ["reuters.com", "bloomberg.com", "wsj.com", "sec.gov", "federalreserve.gov"],
        "web_search_options": {"search_context_size": "medium"},
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "news_log", "schema": SCHEMA}}}
r = requests.post("https://api.perplexity.ai/chat/completions", timeout=120,
                  headers={"Authorization": f"Bearer {KEY}"}, json=body)
r.raise_for_status()
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
raw = pathlib.Path(f"data/raw/{DATASET_ID}/news_{now}.json")
raw.parent.mkdir(parents=True, exist_ok=True)
raw.write_text(json.dumps(r.json(), sort_keys=True, indent=1))
register_snapshot(pathlib.Path("."), raw, DATASET_ID, "SPY-newslog", as_of=now, retrieved_at=now)
```

- **Kill criteria:** >20% of returned items lack a corroborating
  `search_results` URL over a 20-run sample; or `search_results[].date` is
  null in the majority of results; or the observer's activation conditions
  stay unmet by the time G-0004 lands (park it).

### 3.2 Academic literature scan for hypothesis generation

- **Loop stage:** (a) hypothesis generation.
- **Problem solved:** the Parking Lot (`HYPOTHESES.md`) holds three stale
  ideas. A bounded, citation-grounded scan of the anomalies literature turns
  "idea from memory" into "idea with a named paper and falsifier candidate",
  feeding step 4 of the ADR-0007 run shape (one idea → falsifiable
  hypothesis).
- **API shape:** `POST /chat/completions`, `model="sonar-pro"` (better for
  multi-source synthesis), `search_mode="academic"`, structured output listing
  `{effect, canonical_paper, measurable_prediction, falsifier, data_needed}`.
  **Caveat:** date filters are silently ignored in academic mode
  ([academic-filter-guide](https://docs.perplexity.ai/guides/academic-filter-guide))
  — acceptable here because discovery has no PIT requirement.
- **PIT provenance plan:** none needed — output is discovery-stage input to
  human/agent judgment, never evidence. Snapshot the response into the run's
  `results/` artifact for reproducibility of the *decision trail* only.
- **Failure modes / fail-closed:** hallucinated papers → require DOI/URL in
  `search_results` and verify resolvability before a hypothesis cites it, else
  the candidate is dropped; non-determinism between runs → irrelevant for
  discovery, but record the exact request body in the artifact.
- **Cost / latency:** 1–2 calls per weekly session, ≈$0.02–0.05 each
  (sonar-pro $3/$15 per 1M + $6–14/1K requests). Latency undocumented —
  cap with a 120 s timeout inside the session's action budget.
- **Kill criteria:** two consecutive sessions where every returned candidate
  is either unverifiable or duplicates the Parking Lot.

```python
body = {"model": "sonar-pro", "search_mode": "academic",
        "messages": [{"role": "user", "content":
            "List 3 well-documented cross-sectional or time-series equity return anomalies "
            "with post-publication out-of-sample evidence. For each: the canonical paper, "
            "one measurable prediction testable on daily OHLCV of a single broad ETF, "
            "and what result would falsify it."}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "anomaly_scan",
            "schema": {"type": "object", "additionalProperties": False, "required": ["candidates"],
                "properties": {"candidates": {"type": "array", "items": {"type": "object",
                    "additionalProperties": False,
                    "required": ["effect", "canonical_paper", "prediction", "falsifier", "data_needed"],
                    "properties": {k: {"type": "string"} for k in
                        ["effect", "canonical_paper", "prediction", "falsifier", "data_needed"]}}}}}}}}
```

### 3.3 SEC-mode locator for distribution / corporate-action evidence

- **Loop stage:** (e) tooling/ops (data-integrity support for A-0009/B-0003).
- **Problem solved:** `DATA_MANIFEST.json` open issue: distributions are
  excluded, so D-0002 supports price-return evaluation only. To bound that
  error (or eventually build total-return evaluation), we need SPY
  distribution dates/amounts. Perplexity's role is **locator, not source**:
  `search_mode="sec"` finds the filings; the evidence itself is then fetched
  from EDGAR, which — unlike Perplexity — publishes authoritative acceptance
  timestamps, which is exactly the availability evidence BL-0003 enumerates.
- **API shape:** `POST /chat/completions`, `model="sonar"`,
  `search_mode="sec"`
  ([academic-filter-guide](https://docs.perplexity.ai/guides/academic-filter-guide)),
  structured output of `{filing_type, edgar_url, period}` per distribution
  event; then a *separate, non-Perplexity* fetch of each EDGAR URL, snapshot
  registered with EDGAR's own acceptance datetime recorded in provenance.
- **PIT provenance plan:** the Perplexity response is a pointer log only —
  never evidence. The EDGAR documents are the evidence and carry their own
  publication timestamps; register each as a content-addressed snapshot with
  `as_of` = EDGAR acceptance time, `retrieved_at` = fetch time. This is the
  first integration that could produce *genuinely PIT-verifiable* historical
  evidence, because the authority is EDGAR, not the search layer.
- **Failure modes / fail-closed:** wrong/missing filings → cross-check
  completeness against the known quarterly SPY distribution cadence; any
  event lacking a resolvable EDGAR URL is inadmissible; sec-mode coverage
  gaps are unknown (§5) → treat absence of results as "unknown", never as
  "no event".
- **Cost / latency:** a handful of sonar calls (≈$0.01 each) + EDGAR fetches;
  fits in one weekly action with room to spare.
- **Kill criteria:** sec-mode misses filings that a direct EDGAR full-text
  search finds, more than once — then drop Perplexity from the path and query
  EDGAR directly.

```python
body = {"model": "sonar", "search_mode": "sec",
        "messages": [{"role": "user", "content":
            "Find SEC filings and official trust documents listing SPDR S&P 500 ETF Trust (SPY) "
            "distribution declaration dates, ex-dates, and amounts for 2024-2026. "
            "Return EDGAR URLs only, no commentary."}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "spy_distributions",
            "schema": {"type": "object", "additionalProperties": False, "required": ["events"],
                "properties": {"events": {"type": "array", "items": {"type": "object",
                    "additionalProperties": False, "required": ["period", "edgar_url", "doc_type"],
                    "properties": {"period": {"type": "string"}, "edgar_url": {"type": "string"},
                                   "doc_type": {"type": "string"}}}}}}}}}
```

### 3.4 Async deep-research brief prepared *between* sessions

- **Loop stage:** (a)/(e) — pre-session input, prepared out-of-band.
- **Problem solved:** constraint 7. Deep research is minutes-scale (that's why
  the async API exists) and must not burn the 90-minute session. The async
  endpoint lets a cheap cron submit one `sonar-deep-research` job midweek;
  the weekly session's first minutes retrieve the finished result (7-day TTL
  covers any cadence,
  [changelog](https://docs.perplexity.ai/docs/resources/changelog)).
- **API shape:** `POST /async/chat/completions` (canonical path unverified,
  §5) with `{"request": {"model": "sonar-deep-research", "reasoning_effort":
  "low", "messages": [...]}}`; poll `GET /async/chat/completions/{id}`.
  Response includes `search_results` and the itemized `cost` object.
- **PIT provenance plan:** same as 3.1 — snapshot the retrieved result with
  our own retrieval wall-clock; discovery-tier input, forward-only if ever
  treated as evidence.
- **Failure modes / fail-closed:** job not finished by session start →
  session proceeds without it (the brief is advisory, never a prerequisite);
  cost blowout → `reasoning_effort:"low"` and a hard one-job-per-week cap;
  submission cron failure → nothing breaks, the session just has no brief.
- **Cost / latency:** one job/week; deep-research meters (in/out/citation/
  reasoning tokens + $5/1K queries) put realistic cost at ≈$0.5–2 at low
  effort. Retrieval inside the session is one GET — seconds.
- **Kill criteria:** two briefs in a row that change no session decision
  (measured by the journal), or per-job cost exceeding $5.

```python
job = requests.post("https://api.perplexity.ai/async/chat/completions",
    headers={"Authorization": f"Bearer {KEY}"},
    json={"request": {"model": "sonar-deep-research", "reasoning_effort": "low",
        "messages": [{"role": "user", "content":
            "Survey the past week's academic and practitioner publications on single-instrument "
            "daily-frequency equity strategies (trend, volatility scaling, seasonality). "
            "Summarize findings with sources; flag anything with a stated falsifiable prediction."}]}},
    timeout=60).json()
# later (weekly session opening):
result = requests.get(f"https://api.perplexity.ai/async/chat/completions/{job['id']}",
    headers={"Authorization": f"Bearer {KEY}"}, timeout=60).json()
if result.get("status") != "COMPLETED":
    result = None  # advisory input only; session proceeds without it
```

### 3.5 Time-capsule sidecar forecasts

- **Loop stage:** (d) time-capsule sidecar.
- **Problem solved:** the lab has no calibration record for search-grounded
  LLM forecasts. Recording sealed weekly forecasts *now* builds the dataset
  that would later justify (or kill) any grander use of Perplexity — cheaply
  and without touching any protected surface. Constraint 6 is structural:
  grades are informational forever.
- **API shape:** `POST /chat/completions`, `model="sonar"`, no filters,
  structured output `{statement, probability, horizon_utc,
  resolution_criterion}`; the resolution criterion must be mechanically
  checkable against an already-registered dataset (e.g. "D-000x close on
  horizon date > close on issue date").
- **PIT provenance plan:** the whole point is temporal sealing: snapshot +
  content-address the forecast at issue time via `register_snapshot`; the
  registry's `retrieved_at` gate proves the forecast predates its outcome.
  Grading later reads only registered price snapshots. Fully PIT-clean by
  construction.
- **Failure modes / fail-closed:** unresolvable criterion → forecast marked
  void, counted against the *integration*, not silently dropped;
  non-determinism → irrelevant, each forecast is a sealed one-shot; model
  refuses probability → void.
- **Cost / latency:** 1 call/week, ≈$0.01. Seconds. Negligible.
- **Kill criteria:** after 26 weeks, calibration no better than coin-flip
  (Brier ≥ 0.25 vs. a 0.5-constant baseline) → stop; the record itself is the
  experiment's value either way.

```python
body = {"model": "sonar",
        "messages": [{"role": "user", "content":
            "Forecast: will SPY's official closing price on the next Friday (UTC) be higher than "
            "its most recent official close? Give a probability in [0,1] and one sentence of reasoning."}],
        "response_format": {"type": "json_schema", "json_schema": {"name": "capsule",
            "schema": {"type": "object", "additionalProperties": False,
                "required": ["statement", "probability", "horizon_utc", "resolution_criterion"],
                "properties": {"statement": {"type": "string"},
                               "probability": {"type": "number", "minimum": 0, "maximum": 1},
                               "horizon_utc": {"type": "string"},
                               "resolution_criterion": {"type": "string"}}}}}}
# response snapshot -> register_snapshot(..., series_id="SPY-capsule", as_of=now, retrieved_at=now)
```

### 3.6 Standalone Search API as a dated-source discovery layer

- **Loop stage:** (c)/(e) — raw-result feeder for the observer and for
  data-integrity research.
- **Problem solved:** everything above except 3.3 filters evidence through an
  LLM synthesis, which adds hallucination surface. `POST /search` returns raw
  ranked results with `date` and `last_updated` and **no model prose**
  ([search-post](https://docs.perplexity.ai/api-reference/search-post)) — a
  cleaner substrate when what we want is "which documents exist about X",
  with the LLM step removed entirely.
- **API shape:** `POST /search` with `query`, `max_results`,
  `search_after_date_filter`; response `results[]`:
  `{title, url, snippet, date, last_updated}`.
- **PIT provenance plan:** `date`/`last_updated` are provider-asserted and
  nullable — **insufficient alone**. Admissible evidence requires fetching
  each candidate URL ourselves and registering the fetched bytes as a
  content-addressed snapshot with our `retrieved_at`; the Search API response
  itself is registered as a pointer log. Forward-only, same as 3.1.
- **Failure modes / fail-closed:** null dates → result usable for discovery,
  inadmissible as dated evidence; path ambiguity (`/search` vs
  `/search/create`, §5) → resolve in prototype before building on it; pricing
  undocumented (§5) → meter from day one, kill if opaque.
- **Cost / latency:** pricing not documented (§5); assume request-fee order
  of magnitude (~$5/1K) until measured. Single-digit seconds expected but
  unverified.
- **Kill criteria:** pricing or the endpoint path can't be pinned down with
  support, or >50% of finance-domain results return null `date`.

```python
r = requests.post("https://api.perplexity.ai/search",
    headers={"Authorization": f"Bearer {KEY}"},
    json={"query": "SPY S&P 500 ETF material news", "max_results": 10,
          "search_after_date_filter": "8/9/2026"}, timeout=60)
for res in r.json()["results"]:
    print(res["date"], res["last_updated"], res["url"])  # pointer log; fetch+snapshot separately
```

**Priority order:** 3.5 (cheapest, cleanest PIT story, start immediately) →
3.3 (directly serves A-0009's evidence needs) → 3.2 (feeds the next
hypothesis) → 3.1 (build now, schedule only after ADR-0007 gates) → 3.4 →
3.6 (blocked on §5 answers).

## 4. Explicit non-recommendations

1. **Backfilling Sonar answers as historical features.** Asking "what was
   known about X on 2025-03-01" with `search_before_date_filter="3/1/2025"`
   filters today's index by publish date; it does not reconstruct what was
   *retrievable* then (dead pages are gone, edited pages show current text,
   `last_updated` proves post-hoc mutation is normal). Using this as
   historical evidence is textbook look-ahead plus survivorship bias — the
   precise thing B-0003 exists to block. Fail-closed rule: any Perplexity
   evidence with `retrieved_at` after the simulated decision time is
   inadmissible, no exceptions, enforced by the existing `resolve_as_of` gate.
2. **Sonar-scored narratives steering promotion/demotion.** Letting the agent
   promote strategies because a sonar-pro summary "confirms the thesis"
   violates both preregistration and "calibration cannot buy authority." The
   model is non-deterministic (no seed parameter documented), the retrieval
   set shifts daily, and narrative plausibility is exactly the false-
   improvement channel H-0001 guards against. Scores may be *recorded*;
   promotion gates stay purely preregistered-metric-based.
3. **Synchronous `sonar-deep-research` inside the weekly 90 minutes.**
   Latency is undocumented and minutes-scale (that's why the async API
   exists), cost has three extra meters (citation, reasoning, per-query fees),
   and a hung call eats the closing reserve. If deep research is used at all,
   it goes through the async endpoint between sessions (use case 4), never
   inline.
4. **Replacing the OHLCV connector with Sonar-extracted prices.** Numbers
   transcribed by an LLM from web pages have hallucination and transcription
   risk on top of the *same* missing availability/revision metadata that
   already blocks D-0002 — strictly worse than the current provider on the
   only axis that matters (B-0003).

## 5. Open questions for the docs / Perplexity support

1. **Retrieval determinism:** Is there any way to pin the search index state
   (a seed, index snapshot ID, or replay token) so two identical requests see
   the same result set? Nothing is documented; without it, byte-identical
   snapshots are the only reproducibility we can offer.
2. **`search_results` date semantics:** Are `date` and `last_updated`
   crawler-observed or publisher-asserted? What fraction of results carry
   null dates? Is there any SLA on citation URL stability?
3. **Date filter granularity and timezone:** `search_after_date_filter` /
   `search_before_date_filter` accept MM/DD/YYYY only — what timezone anchors
   the day boundary, and is sub-day granularity available anywhere?
4. **Async canonical path and model coverage:** `/async/chat/completions` vs
   `/v1/async/sonar` — which is canonical? Is async accepted for models other
   than `sonar-deep-research` (the parameter list shows `sonar-pro` in an
   example)?
5. **Rate-limit matrix:** The tier table (Tier 1 = 100 RPM sonar-pro) and the
   prose on the same page (1,000–4,000 RPM) conflict; what are the real
   per-tier RPMs and the dollar thresholds per tier?
6. **Regex structured outputs:** Previously documented for sonar; absent from
   current structured-output docs. Removed or just undocumented?
7. **Structured-output limits:** Maximum schema size/nesting, unsupported
   JSON-Schema keywords, and whether the 10–30 s first-schema warm-up recurs
   per schema revision (it will, for us, every time we version a schema).
8. **Search API specifics:** `/search` vs `/search/create` canonical path,
   `max_results` ceiling, and standalone Search API pricing — none retrieved.
9. **Zero-data-retention vs async storage:** How does the 7-day async result
   TTL interact with the documented Sonar ZDR policy?
10. **`search_recency_filter` value set:** filter guide lists `hour`; the
    async parameter docs omit it — which is right?
11. **Sonar deprecation timeline:** the cookbook repo README declares
    `/chat/completions` deprecated in favor of the Agent API `/v1/responses`
    ([README](https://github.com/perplexityai/api-cookbook/blob/main/README.md)),
    but no sunset date is published. What is the support horizon, and do all
    Sonar search parameters (`search_mode`, date filters, domain filter) have
    Agent API equivalents?
12. **Structured-output tier gating:** cookbook examples say structured
    outputs need "Tier 3+"; the FAQ describes them as generally available for
    Sonar/Agent models. Which is current?

## Bottom line

Perplexity is usable by Alpha Lab Genesis **only as a forward-only,
snapshot-at-retrieval evidence source and a discovery-stage research tool** —
which happens to be exactly the shape our existing registry and the D-0002
narrow-use policy already enforce. It cannot help resolve B-0003 for market
data (no availability/revision metadata — the same hole the current connector
has), with one exception: as a *locator* for EDGAR documents (§3.3), whose
authoritative acceptance timestamps are the first realistic path to genuinely
PIT-verifiable event evidence in this repo. Start with the time-capsule
sidecar (§3.5) and the EDGAR locator (§3.3); build the observer news log
(§3.1) but leave it unscheduled behind ADR-0007's gates; file the §5
questions with Perplexity support before committing to the async or Search
API surfaces.
