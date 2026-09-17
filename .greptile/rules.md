# Review guidelines for gita-agent

Context for the reviewer. The structured rules in `config.json` are the
enforceable checks; this file explains the reasoning so borderline cases are
judged sensibly rather than mechanically. The rules are derived from
`docs/technical_spec.md` §15, which in turn derives from the product spec's
fidelity contract (§6.2) and requirements (§9).

## What this project is

A service that emails one short Bhagavad Gita lesson per day, in plain
English, to a private learner (in v1 the repository owner, later people she
adds). Each lesson has two layers: the **canon** (the verse in Sanskrit,
transliteration, and a named translation from the open `gita/gita` dataset,
pinned by commit and loaded from the original translator text) and the
**lens** (a passage from a teacher's recorded Telugu discourse, transcribed
and translated by Gemini on Vertex AI, retrieved by verse, and condensed by a
separate paraphrase step). The model writes exactly two things per lesson:
"What it means" and "A question to carry." Everything else is copied from a
store.

Three Cloud Run Jobs and one small Service in one Python package; Firestore,
Cloud Storage, Pinecone, Vertex AI, Gmail API. No agent framework in v1. A
single operator, one learner. Not a multi-tenant product, not yet public.
Calibrate accordingly: fidelity, idempotent delivery, secret hygiene, and
immutability matter; hypothetical scale does not.

## Review priorities, highest first

1. **Fidelity.** Model output must never reach the verse fields, and the
   teacher passage must come from a stored span with validated segment IDs.
   This is the product. A plausible passage the teacher never said is the
   worst failure the system can have.
2. **Secret leakage and auth.** No Google API keys at all; ADC everywhere;
   Pinecone's key only from Secret Manager; the Gmail OAuth token never in
   source or logs.
3. **Delivery correctness.** One document per learner per track per window
   date, created with create-if-absent inside a transaction, is the only
   guarantee against sending twice. Every delivery write is a transaction
   that reads first. A sent lesson is never modified.
4. **Cost and resource bounds.** Every external call has a timeout and a
   bounded retry; every Vertex call records tokens and priced cost; ingestion
   is idempotent per window by the raw object's existence.
5. **Missing tests.** Deterministic tests with fakes for every behavior;
   an untested error path is worse than an untested happy path.

## Conventions worth knowing before you flag something

- **Retrieval-only teacher content is deliberate.** If the store has nothing
  relevant, the lesson goes out canon-only and says so. Do not suggest
  filling the gap from the model's own knowledge of the Gita.
- **The delivery machine is deliberately minimal (technical spec §8).** An
  earlier draft had seven statuses, timeout sweeps, and an "uncertain" state;
  the owner cut it back for a single learner. Those mechanisms are listed in
  technical spec Appendix B with the point at which each becomes worth
  building. Do not suggest reintroducing them in v1.0.
- **A lost Gmail response is treated as sent in v1.0.** This is a recorded
  decision (D9), not an oversight.
- **Lesson count is an outcome, not a target.** The sequence validator
  reports counts and never fails on them. Do not suggest a cap.
- **Chapter 13 numbering follows the dataset (1–35), not printed editions
  (0–34);** `refs_alt` makes direct-reference lookup accept both. Do not
  suggest renumbering the store; byte-identity with the pinned source matters.
- **The welcome is sent synchronously by `learner add`,** not by the delivery
  job. That is intended.
- **Banned words have two tiers.** Hard words regenerate and block only after
  two retries; soft words are logged and never block. Do not suggest blocking
  on soft words.
- **Two buckets, one with a retention policy.** Retention is bucket-level in
  GCS; the store bucket has none so erasure can delete.
- **Gmail scopes are `gmail.send` and `gmail.metadata`.** The second exists to
  read back the Message-ID Gmail actually stamped. Do not suggest widening.
- **Python for everything in v1 (D21).** Go was considered; `links` is the
  candidate for a Go rewrite in v2 if measured cold start warrants it. Do not
  suggest a language change.
- **Bilingual by design.** Teacher recordings code-switch between Telugu and
  English mid-sentence. Code that assumes a single language per segment is
  wrong.
- **The owner is a woman;** use she/her in any generated summary, comment, or
  docstring that refers to her.

## Comment style

Be terse. One or two sentences per finding, with the concrete failure — the
input or state that triggers it and what goes wrong — not a general principle.
Cite the spec section or requirement ID the finding violates.

Do not raise: formatting, import order, naming preferences, docstring
presence, type-annotation completeness, or "consider extracting a helper" on
code that reads fine. If a change looks wrong but a spec section explains why
it is correct, say nothing.
