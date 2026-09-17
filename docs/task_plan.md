# Gita Agent — Task Plan (v1)

| | |
|---|---|
| **Status** | Draft for review |
| **Owner** | Udaya Pillalamarri |
| **Answers to** | `docs/product_spec.md` §9 and §10 (gates), `docs/content_spec.md` §10.2 (pre-day-one checklist T1–T7), `docs/technical_spec.md` (all sections; Appendix B for what is deferred) |
| **Date** | 2026-09-16 |

---

## 1. How this plan works

- **Phases end in pull requests.** Every phase produces one or more PRs
  into `main`, each small enough to review in one sitting. Greptile reviews
  each PR under the rules in technical spec §15; `/pr-triage` under `/loop`
  polls for the review and hands the findings to Udaya for a decision.
  Nothing merges without a green CI run and a human click.
- **Tests first, per module.** Each implementation task lists the tests
  that are written before the code, taken from technical spec §12.2. A PR
  that adds behavior without tests is a review finding (§15 rule 2).
- **Phase 2 is the real run.** Before any module is built for keeps, every
  external service is exercised for real on the actual playlist. This is
  the lesson of v0's 167 green tests, and it is why the phase order below
  is not the module order.
- **Every task cites what it satisfies.** P0-n from the product spec, a
  section of the content or technical spec, or a T-n item from the
  operator checklist. A task with no citation is scope creep and does not
  belong here.
- **Estimates are in working sessions**, roughly two to four focused
  hours each, agent and owner together. They are honest guesses; the plan
  is revised in the same PR as the code when they turn out wrong (product
  spec §14).
- **The three loops**, once phase 1 lands: the *review loop* (Greptile on
  every PR, triaged by `/pr-triage`), the *build loop* (GitHub Actions on
  every PR: lint, types, unit tests, pack validation, doc ID check), and
  the *eval loop* (`gita eval` on demand and weekly on Cloud Build, gating
  every model or prompt change).

## 2. Phase map

| Phase | Name | Proves | Ends with |
|---|---|---|---|
| 0 | Clean slate | The specs and the review rules are on `main`; nothing else | The clean-slate PR merged, with the Greptile config in it |
| 1 | Skeleton and loops | The package, CI, and deploy scaffolding work, and the review loop reviews code under our rules | The skeleton PR merged after a Greptile review triaged end to end |
| 2 | Contract run | Every external service works as the spec says, on the real playlist | A contract-test PR and the "verified numbers" section filled in |
| 3 | Canon and packs | The canon loads byte-stable; pack artifacts exist and are reviewable | Canon loader, pack tooling, and the reviewed sequence for chapters 1–2 |
| 4 | The lesson | A faithful lesson can be composed from real segments and validated | Retrieval, paraphrase, composition, validation, rendering, `explain` |
| 5 | Delivery | Udaya receives lesson one in her inbox from the deployed system | Delivery job, links service, digest, deployment, first send |
| 6 | v1.0 operation | Thirty clean days; gate 1 | Gate 1 report |
| 7 | v1.1 | Reviewers, long form, story track, corrections, selected hardening; gate 2 | Gate 2 report; the v2 product spec begins |

## 3. Phase 0 — Clean slate

**Goal.** Put the four specs, the archived v0 docs, the removal of the v0
code, and the Greptile review rules on `main`, and nothing else. After
this phase every later PR is reviewed under our rules, because Greptile
reads its config from the PR's base branch.

| # | Task | Cites | Owner |
|---|---|---|---|
| 0.1 | Rewrite `.greptile/config.json`, `rules.md`, `files.json` from technical spec §15 on `chore/clean-slate`; `files.json` points the reviewer at the four specs; `ignorePatterns` no longer excludes `docs/*.md` (§15 rule 11); keep `/pr-triage` from `chore/greptile-code-review` | tech §15 | agent |
| 0.2 | Open the clean-slate PR from `chore/clean-slate` to `main`. It contains: the v0 code removal, `docs/archive/`, the four specs, the learnings log, the README, and the Greptile config. Greptile reviews it under its defaults (the config is not on `main` yet); `/pr-triage` under `/loop` collects the findings | tech §15 | agent opens, Udaya decides |
| 0.3 | Udaya reads the triage, decides on findings, merges. `main` now holds the specs and the rules; `v0-legacy` remains the tag for everything removed | product §14 | Udaya |

**Exit.** `main` is the clean slate with the review rules in place. No
code yet.
**Estimate.** 1 session.

## 4. Phase 1 — Skeleton and loops

**Goal.** The empty package, CI, and deploy scaffolding, landed through
the first PR that Greptile reviews under our own rules.

| # | Task | Cites | Tests first | Owner |
|---|---|---|---|---|
| 1.1 | Package skeleton: `gita/` with `__main__.py`, `cli.py`, `config.py`, `observability.py` copied from `v0-legacy` with its 23 tests; `pyproject.toml` with `ruff`, `mypy --strict`, `pytest`; `tests/unit`, `tests/fakes`, `tests/contract`, `tests/evals` | tech §5, D15 | `observability` (carried) | agent |
| 1.2 | GitHub Actions: lint, types, unit tests with coverage, `pack validate`, doc ID check (every `P0-`/`P1-`/`P2-` cited in the technical spec exists in the product spec) | tech §12.5 | the doc check is itself a test | agent |
| 1.3 | `deploy/` skeleton: two Dockerfiles, `cloudbuild.yaml` (build on tag; weekly contract-test and eval triggers), scheduler and IAM scripts as documented stubs | tech §13 | n/a | agent |
| 1.4 | Rewrite `docs/SETUP_GUIDE.md`: GCP prerequisite first, APIs, the Gmail OAuth flow and production-status requirement, Pinecone index, budget alert, Monitoring channels, the rights warning verbatim | P1-10, tech §13 | n/a | agent, Udaya reviews |
| 1.5 | Open the skeleton PR; `/pr-triage` under `/loop`; this is the first review under §15 rules, so its findings also test the rules: a rule that fires wrongly is fixed in the same PR | tech §15 | n/a | agent opens, Udaya decides |

**Exit.** `main` holds the skeleton, CI is green, and one Greptile review
under our rules has been triaged end to end.
**Estimate.** 2 sessions.

## 5. Phase 2 — Contract run

**Goal.** Exercise every edge in technical spec §4.1 against the real
service, on the real playlist, before building anything for keeps. Fill in
technical spec §7.5 with measured numbers. Fix the spec where reality
disagrees.

| # | Task | Cites | What is verified | Owner |
|---|---|---|---|---|
| 2.1 | Vertex transcription contract: window 0 and window 1 of the first Gita video; assert timestamp origin for clipped windows; record tokens and wall time | tech §7.2, §12.4 | Timestamp origin; per-window cost | agent |
| 2.2 | One full video end to end at 8 windows in flight; record wall time and any YouTube-hours limit behavior | tech §7.2, §7.5 | Concurrency; quota | agent |
| 2.3 | Embedding contract: `gemini-embedding-001` at 768 dims; batch size; endpoint location | tech §7.3, D6 | Batch size; location | agent |
| 2.4 | Pinecone contract: create `gita-segments`; upsert, query, fetch round-trip in a test namespace | tech §7.3, D5 | Index shape; metadata filters | agent |
| 2.5 | Firestore contract: `create()` conflict under two concurrent writers; a transaction that reads then writes; composite index creation from `deploy/firestore.indexes.json` | tech §8.2, §13 | Idempotency primitive | agent |
| 2.6 | GCS contract: two buckets; retention policy on raw; object create-if-absent as sentinel | tech §13, D4 | Sentinel; retention | agent |
| 2.7 | Gmail contract: one-time OAuth consent on Udaya's machine, consent screen in production status; send to Udaya's own address with a deterministic Message-ID; read it back with `gmail.metadata`; record whether Gmail preserved the Message-ID | tech §4.1, §8.4, E3 | Token flow; Message-ID behavior | Udaya (consent), agent |
| 2.8 | yt-dlp from a Cloud Run job: playlist listing; record whether the datacenter IP is challenged | tech §7.4, D18 | Discovery fallback need | agent |
| 2.9 | Cloud Scheduler to a Cloud Run Job with an OAuth token; one no-op job run end to end | tech §4.1, §13 | Trigger auth | agent |
| 2.10 | `links` cold start on the slim image with `--cpu-boost`, measured | tech §9, §7.5 | Cold start | agent |
| 2.11 | Write the results into technical spec §7.5; revise any section reality contradicts, in the same PR | product §14 | The spec is true | agent, Udaya reviews |

**Exit.** `tests/contract/` passes end to end with `GITA_LIVE_TESTS=1`,
§7.5 is filled in, and every "verified by contract test" phrase in the
technical spec has a number behind it.
**Estimate.** 3 sessions, one of them Udaya's for the OAuth consent and
account setup.

## 6. Phase 3 — Canon and packs

**Goal.** The canon store and the pack tooling, so that content work can
start and be reviewed while the lesson pipeline is built.

| # | Task | Cites | Tests first (tech §12.2) | Owner |
|---|---|---|---|---|
| 3.1 | `canon` module: load from the pinned commit, English originals only, prefix strip and trim, byte-stable reload, chapter-13 mapping, `canon_overrides.json`, `canon diff` | P0-19, content §2, tech §6.4 | `canon` row | agent |
| 3.2 | `packs` module: manifest schema with attestation refusal and the printed warning; artifact loaders; sequence validator (rules 1 and 2, count reported not failed, size-≥3 groups listed); per-chapter and per-video review status; `pack_digest`; `texts.yaml` completeness against `MessageType` | P0-20, P0-27, content §3, §4.1, §7 | `packs` row | agent |
| 3.3 | `pack discover`: yt-dlp listing written to the manifest `videos:` list for all four series | content §4.1, tech §7.4 | `ingest.discover` row | agent |
| 3.4 | `pack sequence draft` and `pack openings draft`: model-drafted proposals per chapter with the `group_v1` and `opening_v1` prompts | content §3.3, §3.4 | drafting is model-dependent; validated by 3.2's validator | agent |
| 3.5 | Udaya reviews the sequence and openings for chapters 1 and 2 and marks them reviewed (T2, T3); edits the primer and marks it reviewed (T1) | content §10.2 | n/a | Udaya |
| 3.6 | `pricing.py` with the versioned table and a cost test | P0-25 | `pricing` row | agent |
| 3.7 | PR: canon and packs | | | |

**Exit.** `gita canon load` produces a byte-stable snapshot; `gita pack
validate` passes on the default pack; chapters 1 and 2 are reviewed; the
primer is reviewed.
**Estimate.** 3 sessions, plus Udaya's review time for two chapters and
the primer.

## 7. Phase 4 — The lesson

**Goal.** Compose a faithful lesson from real segments and prove the
fidelity contract in tests before any email exists.

| # | Task | Cites | Tests first (tech §12.2) | Owner |
|---|---|---|---|---|
| 4.1 | `ingest` module for keeps: windows, transcribe, parse (timestamp normalization, `refs_alt`), grade (six signals, minimum rule, provisional vs final), embed, upsert, supersede, `--regrade`, sharding flags | P0-20, P0-21, P0-23, content §4.3–4.4, tech §7 | `ingest.windows`, `ingest.parse`, `ingest.grade`, `ingest.supersede` rows | agent |
| 4.2 | Ingest the three Gita series for real (17 videos); T4: hand-check twenty segments per grade on the first video and write confidence thresholds to the manifest; `--regrade` | product §10.1, content §10.2 T4 | contract | agent, Udaya (hand-check) |
| 4.3 | `retrieval` module: query build, search, direct refs, select, neighbors (positional, similarity floor via fetched vectors, low-grade stop), overrides, trace | P0-11, content §4.5, §4.6 | `retrieval` row including the **no-store test** | agent |
| 4.4 | T5: tune the relevance threshold and margin on twenty hand-checked verses; record in the manifest | content §10.2 T5 | eval `Retrieval quality` | agent, Udaya (hand-check) |
| 4.5 | `compose` module: paraphrase, compose with regeneration on hard hits, validate every content §5.4 row, render four editions with labels, marker, footer, canon-only line | P0-7 to P0-13, P0-15, content §5, §7.5, Appendix A | `compose.paraphrase`, `compose.compose`, `compose.validate`, `compose.render` rows | agent |
| 4.6 | `explain <lesson_id>` and `render <lesson_id> --edition` | P0-26, content §4.6 | covered by 4.3 and 4.5 fixtures | agent |
| 4.7 | `audit add` and `audit golden`; starter golden set of ten hand-built lessons | content §8, P2-2 | `audit` row | agent, Udaya (judgments) |
| 4.8 | `gita eval` v1: verse fidelity, attribution, retrieval quality, tone; judge-based evals with Gemini Pro | tech §12.3 | eval reports under `audit/evals/` | agent |
| 4.9 | Compose twenty lessons locally for chapters 1–2, render them, Udaya reads them | product §10.1 self audit | n/a | Udaya |
| 4.10 | PRs: ingest; retrieval; compose and evals (three PRs) | | | |

**Exit.** Twenty real lessons rendered locally that Udaya judges faithful
and readable; the no-store test proves canon-only fallback; the eval
report runs.
**Estimate.** 6 sessions. This is the heart of the project.

## 8. Phase 5 — Delivery

**Goal.** Udaya receives lesson one in her inbox from the deployed
system, and the operator surfaces around it work.

| # | Task | Cites | Tests first (tech §12.2) | Owner |
|---|---|---|---|---|
| 5.1 | `store` module for the operational records and erasure; `channel` protocol and `GmailChannel` with MIME, headers, deterministic Message-ID, `route_reply` stub | P0-14, P0-17, P2-3, P2-9, tech §6.3, §8.6 | `channel.gmail`, `store.erase` rows | agent |
| 5.2 | `deliver` job: due selection by window date, create-if-absent document, compose, learner re-read, send, sent+advance transaction, retry inside window, stale pending, missed window, notifications, metrics | P0-1 to P0-6, P0-16 to P0-18, tech §8 | `deliver.due`, `deliver.state`, `deliver.position`, `deliver.notify` rows | agent |
| 5.3 | `learner add/update/list/erase/set-position` with synchronous welcome | P0-5, P0-22, tech §8.5 | `learner.add` row | agent |
| 5.4 | `links` service: encrypted tokens with purpose and version checks, reactions with undo and note, unsubscribe GET confirm and POST one-click, scanner filtering, unsubscribe confirmation | P0-4, P0-16, P0-17, tech §9 | `links` row | agent |
| 5.5 | `digest` job: every P0-24 item; cost re-sum test; canon upstream check; model existence check | P0-24, P0-25 | `digest` row | agent |
| 5.6 | Deploy: images via Cloud Build, three jobs, the service, three schedules, three service accounts, secrets, indexes, Monitoring alerting policies | tech §11, §13 | contract tests re-run against the deployment | agent |
| 5.7 | T6, T7: operator config and Udaya's learner record; unsubscribe test; review-appendix render on a test lesson | content §10.2 | n/a | Udaya |
| 5.8 | First real send: `learner add` for Udaya, welcome arrives, lesson one arrives the next morning | P0-1, P0-5 | the thing itself | both |
| 5.9 | PRs: store and channel; deliver and learner; links; digest and deploy (four PRs) | | | |

**Exit.** Lesson one delivered by the scheduled job, visible in Firestore
as `sent`, with its trace, and `explain` prints it.
**Estimate.** 5 sessions.

## 9. Phase 6 — v1.0 operation and gate 1

**Goal.** Thirty consecutive clean days; the product spec §10.1 metrics
met.

| # | Task | Cites |
|---|---|---|
| 6.1 | Daily: Udaya reads the lesson and reacts; weekly: reads the digest | product §10.1 |
| 6.2 | Days 15 and 30: self fidelity audit of twenty lessons via `render --edition review`, logged with `audit add`; readability check | product §10.1, P0-26 |
| 6.3 | Ingest the Bhagavatam series within the first week (secondary lens live) | P0-21, product §10.1 |
| 6.4 | Review chapters ahead of position: a chapter every week or two | content §3.3 |
| 6.5 | Fixes found in operation, each as a PR with a test and, where the spec was wrong, a spec revision | product §14 |
| 6.6 | Gate 1 report: every §10.1 row with its measured value | product §10.1 |

**Exit.** Gate 1 passed and recorded.
**Estimate.** 30 calendar days; 3 to 4 sessions of work spread across
them.

## 10. Phase 7 — v1.1 and gate 2

**Goal.** Reviewers, the long form, the story track, corrections, and the
hardening that v1.0 evidence shows is needed.

| # | Task | Cites |
|---|---|---|
| 7.1 | Reviewer role: `reviewer add/remove/update`, reviewer welcome, review edition sent after the learner's send with its own delivery record, banner and questions; Udaya's father added first | P1-1, product §6.6, §8.5, content §7.3–7.4 |
| 7.2 | Long-form page: `render --edition longform` to GCS; `/l/<token>` in `links`; recipient-signed link in the footer; noindex | P1-2, product §6.5, content §6.3 |
| 7.3 | Story track: `pack episodes draft`, per-video review, `episodes.json`, the story lesson template, opt-in per learner, separate position | P1-3, content §6 |
| 7.4 | Corrections: `correction send` creating windowed documents | P1-5 |
| 7.5 | Hardening from Appendix B, chosen by v1.0 evidence: at minimum the `sending`/`uncertain` state once a second learner exists, and reviewer-document creation inside the sent transaction | tech Appendix B |
| 7.6 | Additional learners; multi-timezone; P1-7 pace options if wanted | P1-4, P1-7 |
| 7.7 | Golden set from reviewer feedback; `gita eval` running on the golden set in CI weekly; Claude as a second judge on a sample | P2-2, tech §12.3, E4 |
| 7.8 | Gate 2 report; product open question 6 resolved with a rights check; Google release policy confirmed; license branch pushed and merged | product §10.2 |

**Exit.** Gate 2 passed; the v2 product spec is started with v1.1
evidence in hand.
**Estimate.** 8 sessions across the 30-day v1.1 window.

## 11. What is copied from `v0-legacy`, and when

| Piece | Phase | Adapted how |
|---|---|---|
| `ingestion/observability.py` and `tests/test_observability.py` | 1.1 | Module path only |
| Sentinel pattern from `storage.py` | 4.1 | Becomes the raw-window object as sentinel |
| CLI shape from `orchestrator.py` | 1.1 | One `cli.py` with subcommands |
| `Dockerfile.ingestion` pattern | 1.3 | Two images, non-root, `yt-dlp` and `deno` |
| `tests/conftest.py` fixture conventions | 1.1 | Fakes in `tests/fakes/` |

Everything else in v0 is not carried.

## 12. Risks the plan is watching

| Risk | Where it surfaces | Mitigation |
|---|---|---|
| YouTube bot-challenges Cloud Run IPs | 2.8 | Manifest video list as fallback (D18); discovery from the operator's machine |
| Vertex YouTube-hours quota below what ingestion needs | 2.2 | Measure; shard across days if needed; audio-bytes path (P1-11) as fallback |
| Gmail rewrites the Message-ID | 2.7 | `sent_message_id` read back with `gmail.metadata`; subject-line fallback for v2 threading |
| `gemini-3-flash-preview` retired mid-project | monthly digest check | GA fallback named in D17; eval-gated migration (P0-13) |
| Transcription quality on poor-audio videos | 4.2 | Confidence grading; canon-only fallback; `--regrade` |
| Udaya's review time for sequence and openings | 3.5, 6.4 | Review ahead of position, a chapter at a time; only chapters 1–2 before day one |
| The plan's estimates are wrong | every phase | Revise the plan in the same PR; the learnings log records why |

## 13. Open questions

| # | Question | Who | Blocking? |
|---|---|---|---|
| K1 | Session cadence: how many sessions a week can Udaya give to review and hand-checks in phases 3 and 4? It sets the calendar for gate 1. | Udaya | No, but it sets expectations |
| K2 | Phase 4.9: should the twenty local lessons also be reviewed by Udaya's father before phase 4, as an early informal reviewer before phase 5, or wait for v1.1? | Udaya | No |
