# Learnings: building Gita Agent with agentic development

A running log of what building this project with an AI coding agent
actually taught us, kept as raw material for a blog article on Udaya's
website. Entries are dated and terse. The article outline at the end grows
as themes recur. Nothing here is polished; that is the point.

Conventions: **Observation** is what happened. **Lesson** is what we would
tell someone else. **Evidence** points at the commit, doc, or moment.

---

## 2026-09-12 · Day one of the redesign

### Spec-driven development, in practice

- **Observation.** The product spec started as a 13-section draft written in
  one pass. Section-by-section review by the owner produced roughly forty
  commits of changes in one evening, including two new sections, a
  nineteen-rule fidelity contract, and a requirements table that doubled
  from 12 to 27 P0s once it was reconciled against the sections above it.
- **Lesson.** The first draft of a spec is a conversation starter, not a
  spec. The value came from the owner reading every section and asking
  "what about X?" and the agent immediately folding the answer back into
  the document with a commit. The document was never out of date for more
  than a few minutes.
- **Lesson.** Reconcile the requirements table *last*, against the finished
  narrative sections, and do it as a wholesale rewrite rather than patches.
  Half the P0s were implied by sections 6 through 8 and had no row.
- **Lesson.** Mark which sections are load-bearing (the fidelity contract,
  the non-goals, "v1 is private") and require an explicit decision to
  change them. Everything else evolves with evidence. Write that policy
  into the spec itself (§14).
- **Evidence.** `docs/product_spec.md` history on `chore/clean-slate`.

### Probe before you spec

- **Observation.** A thirty-minute feasibility probe on one real video,
  before any spec was written, removed most of the previous architecture.
  Gemini on Vertex transcribed and translated Telugu audio directly from a
  YouTube URL with start and end offsets, in one call, at roughly a tenth
  of the cost of the two-step Chirp-then-Gemini pipeline. No download, no
  ffmpeg, no audio bucket.
- **Lesson.** When a design hinges on whether a model can do a thing, spend
  the first hour finding out on real input. The answer changes the spec
  more than any amount of reasoning about it.
- **Evidence.** Memory notes for 2026-09-12; probe artifacts in the session
  scratchpad; product spec §7.2 "Source types".

### Mocked tests can be a perfect green lie

- **Observation.** The v0 codebase had 167 passing tests. The real Chirp 3
  endpoint rejected the code on the first real call: the model exists only
  in the `us` multi-region, and the module pointed at `global`. Every test
  mocked the client, so nothing could have caught it. The planned
  real-recording integration test (Phase 4.8) had never been run.
- **Lesson.** A test suite that never touches the real service proves the
  code is consistent with its own assumptions, nothing more. Put one real
  end-to-end run in phase 1, not phase 8, and treat "all tests pass" as
  necessary, not sufficient.
- **Evidence.** `git show v0-legacy:ingestion/transcription.py`, the
  `recognizers/_` path under `locations/global`.

### "Open data" needs provenance checking too

- **Observation.** The open Gita dataset's English translations had all
  been rewritten by GPT-3 in 2023 with a "fix grammar" prompt, with the
  translators' names still attached. The originals survived in an archive
  folder. This was found because the fidelity rules ("never attribute
  generated text to a named source") were written before any code, and
  checking the data against them was the obvious next step.
- **Lesson.** Write the fidelity rules first, then audit every input
  against them, including the inputs that come with a permissive license.
  A license on a compilation says nothing about what was done to its
  contents or who owns them.
- **Lesson.** Pin data sources by commit hash and treat upgrades as
  reviewed changes with a diff. The dataset had not changed in three years,
  and pinning still mattered, because the *choice of file within it* was
  the whole question.
- **Evidence.** Product spec §7.1; content spec §2.4 and §2.5.

### Evals must track the model, and humans become the evals

- **Observation.** The owner raised, unprompted, that evals written against
  one model's capability go stale as models improve. Separately, the
  reviewer role (her father, then others) was designed to retire at v2, with
  the reviewers' verified judgments becoming the golden set that runs as
  automated evals.
- **Lesson.** Separate deterministic unit tests (pipeline code) from
  model-dependent evals (fidelity, translation quality). Pin model ID and
  prompt version on every eval run and every produced artifact. Re-baseline
  the evals on each model change and grow the golden set rather than
  declaring it done.
- **Lesson.** Design human review so that its output is machine-readable
  from day one (claim, source checked, decision, decider, keyed by artifact
  ID). Then the humans are building the test suite whether they know it or
  not.
- **Evidence.** Product spec §6.2 model independence, §6.6, §10.2; content
  spec §8.

### Small process choices that paid off immediately

- **Tag and delete, don't archive.** Old code went to a git tag
  (`v0-legacy`) and was removed from the tree; only the docs got an
  `archive/` folder. Dead code in the tree confuses reviewers, test
  discovery, and every new reader. Reuse is by deliberate copy from the tag.
- **Trunk-based with short branches, PRs deferred.** Forty commits pushed
  to a branch for backup without opening a PR, because the AI code reviewer
  (Greptile) only reacts to PRs and its rules were not yet rewritten for the
  new design. Reviewer config is derived from the technical spec, so it
  waits for the technical spec.
- **Confirm shared-state actions, do local ones freely.** The agent asked
  before every push, API enablement, budget creation, and reminder, and did
  not ask before edits, commits, or tests. The owner never had to wonder
  whether something had left the laptop.
- **Persistent memory files.** Decisions, their reasons, and "where we
  stopped" live in plain markdown outside the repo, indexed by a one-line
  table of contents. The next session resumes without re-explanation. The
  repo holds what is derivable from the repo; memory holds only what is not.
- **Budget alert plus in-pipeline cost accounting.** Not either. The alert
  is the backstop; the weekly digest with per-call token sums is the real
  cost view.

### On multi-agent orchestration and sub-agents (so far: not needed)

- **Observation.** The entire spec phase ran as one agent in one long
  conversation with the owner. No sub-agents were spawned. The work was
  sequential by nature: each answer changed the next question.
- **Lesson (provisional).** Orchestration earns its place when work is
  parallel and independent: reviewing four spec documents against each
  other, running the review loop on several PRs, generating and validating
  chapter groupings for eighteen chapters at once. Spec writing with a
  human in the loop is not that. Reach for one agent with good memory
  first.
- **To revisit** when the technical spec review, the Greptile triage loop,
  and phase 1 implementation start. Expected candidates: a review loop
  agent that polls PRs and triages findings for a human decision; parallel
  sub-agents for per-chapter content generation and validation; a
  fidelity-eval runner.

### Human-agent collaboration, small things

- Rendering matters: the owner preferred the rendered markdown card over
  the raw file pane and said so. Ask which view someone wants before
  switching it.
- Late in the evening the owner said she could not review as closely and
  asked the agent to review its own requirements table "with a fine-tooth
  comb" and report gaps. That produced eighteen findings in three groups
  (fix without asking, add, needs a decision). Being explicit about which
  findings need the human is what made the list usable at 11pm.
- A question phrased as "is that right?" about what a push would do to
  `main` was worth a careful, literal answer before acting. The mental
  model gap (push equals merge) would have caused a real scare.


## 2026-09-13 · Day two: the content spec and the first sub-agent

### An independent reviewer catches what the author cannot

- **Observation.** After the owner and the agent had reviewed the product
  and content specs together over two days, the agent ran a single
  sub-agent with one instruction: read both documents completely and report
  only concrete inconsistencies. It returned eighteen findings in seven
  minutes. Several were things the authoring agent had introduced itself
  and could not see: a "soft" banned-word tier in one document that
  contradicted three absolute statements in the other; a message type
  tagged v1.0 in one table and v1.1 in every other place; a role whose
  daily position was undefined once learners could be at different points;
  cross-references to requirement IDs that had been renumbered.
- **Lesson.** The author of a document is the worst reviewer of its
  consistency, and that is as true of an agent as of a person. A reviewer
  with no memory of why anything was written, reading only what is on the
  page, is the cheapest strong check available. It is worth running before
  every "are we good to go" moment.
- **Lesson.** Scope the reviewer narrowly. "Report only concrete
  inconsistencies, quote both sides, suggest a one-line fix, do not edit"
  produced a list that could be applied in one pass. A general "review
  this" would have produced opinions.
- **Lesson.** The files changed under the reviewer while it read (the
  authoring agent kept fixing its own findings in parallel). The reviewer
  noticed the modification times, re-verified every finding against the
  current text, and dropped the ones already fixed. That is the behavior to
  ask for explicitly when review and editing overlap.
- **Evidence.** Commit 0810ad9, "Apply independent cross-spec review: 18
  findings."

### The technical spec review: 81 findings, and which ones would have hurt

- **Observation.** The same narrowly scoped reviewer pattern, applied to
  the first draft of the technical spec against both upstream specs,
  returned 81 findings. Roughly a third were cross-reference and naming
  slips. A third were mechanisms the content spec defined that the data
  model had not carried (the trace record had no shape; overrides had no
  record; fixed texts had no file). The last third were the ones that
  matter: Cloud Scheduler cannot trigger a Cloud Run *Job* with an OIDC
  token, only a Service; a Gmail refresh token minted while the OAuth
  consent screen is in "Testing" dies after seven days, which would have
  silently killed delivery on day eight; a single-task ingest with a
  one-hour timeout cannot process 85 hours of video; mail security
  scanners prefetch links, so unsubscribe on GET would have unsubscribed
  people; a base64 payload is not opaque, so the learner ID was in every
  URL; a lost Gmail response retried "byte-identically" is a duplicate
  email, because Gmail has no idempotency key.
- **Lesson.** An author's first architecture draft is optimistic about
  platform details it has not exercised. The reviewer caught platform
  behavior the author "knew" but had not checked. Each of these is cheap
  to fix in a document and expensive to discover in production.
- **Lesson.** Ask the reviewer to grade its own confidence. The prompt
  asked it to say when it was not sure; it did, on three items (embedding
  batch size, YouTube-hours quota on Vertex, timestamp origin for clipped
  windows), and those became contract tests rather than assertions.
- **Lesson.** Some findings are decisions, not fixes. Five became open
  questions for the owner (region, custom domain, OAuth flow, judge model,
  reactions-on-GET). Separating "fix" from "decide" is part of applying a
  review.
- **Lesson.** Rewrite, do not patch, when findings exceed a few dozen.
  Applying 81 edits to an 800-line document would have left seams; the
  rewrite took the findings as a checklist and produced a coherent
  document, then the content spec was aligned in one pass.
- **Evidence.** Commit a946d5f; technical spec §8.2, §8.4, §9, §13, D17–D20.

### How many review passes, and when to stop

- **Observation.** The technical spec went through two independent
  sub-agent reviews in sequence, each a fresh reader with no memory of the
  other or of the author's reasoning. Pass one returned 81 findings and
  led to a full rewrite. Pass two, on the rewrite, returned 35, and
  several of those were errors introduced by the rewrite itself: an
  "is the learner still active" check placed after the send instead of
  before it, a retry rule that contradicted the new forward-only state
  machine, a resend that shared the daily delivery key and would have
  blocked the day's lesson. The fix was a draft too.
- **Lesson.** The number of passes is not the rule; convergence is. Three
  signals say another pass is worth its cost: the finding count is still
  dropping steeply (81 to 35 is healthy; 81 to 70 means the process is
  broken); the last pass still found something that would break in
  production; and the findings are still about the original content
  rather than seams from the previous fix. Stop when a fresh reader finds
  nothing you would act on, or only cosmetics.
- **Lesson.** For a large artifact that is rewritten between passes, the
  third pass is usually where convergence happens, which is why "three"
  feels like a magic number. It is not a number; it is where the curve
  flattens for that size of change. A one-paragraph edit needs one pass.
- **Lesson.** Neither the human owner's read nor the author agent's first
  draft is sufficient, and neither is one independent pass. The owner
  finds what is wrong for the product; the independent reader finds what
  is wrong in the document; the second independent reader finds what the
  fix broke. Each catches a different class.
- **Cost.** Each pass on three documents totalling about 3,000 lines took
  eight to ten minutes and roughly 170k tokens. Against the cost of
  discovering "Scheduler cannot trigger a Job with OIDC" on deploy day,
  that is cheap, and the curve makes the stopping point visible.
- **Evidence.** Commits a946d5f (after pass one) and 4b6ec30 (after pass
  two); finding counts 81 → 35.

### When the human's question is better than the spec

- **Observation.** Three of the day's most consequential changes came from
  the owner asking a plain question the spec had glossed over: "what is the
  scoring algorithm?" (there was none; the confidence grade was the model's
  self-report), "what happens to the low entries, do we log them?" (nothing
  was recorded; the composition trace did not exist), and "is the banned
  list a bit restrictive?" (it was; a single tier that blocked sends).
- **Lesson.** A spec reads as complete until someone asks how a specific
  thing actually happens. Walking a reader through the document section by
  section, and answering every "how" with a mechanism rather than a
  reassurance, is the review. Each of those three answers became a section
  with a table and a test.

### Serverless as the lesson, not the label (running thread)

- **Observation.** The owner asked whether there was "a place for
  serverless" in the design. The design was already entirely serverless:
  Cloud Run Jobs and a Service that scale to zero, Firestore, Cloud
  Storage, Secret Manager, Pinecone serverless, a managed cron. The label
  had never been applied because each choice had been made on its own
  merits (zero idle cost, no instance, transactional create).
- **Lesson.** Serverless is less a platform than a set of habits the
  platform forces: stateless execution, idempotency answered from the
  store, cold starts accepted and measured, least privilege per component,
  observability without hosts, and event-driven flow where it earns its
  place. Each of these already had a mechanism in the spec before anyone
  called the architecture serverless. Learning the habits is the point;
  the label follows.
- **Thread to continue in implementation.** Record, as each lands: the
  first time a killed job recovers cleanly from the delivery record; the
  measured cold start of `links` and of `deliver`; the first double-send
  prevented by the transactional create; the first least-privilege
  denial caught in a contract test; and, in v2, the move from polling to
  Pub/Sub push for inbound replies.
- **Evidence.** Technical spec §1.1, D3, D8, D12.

### Small things

- The lesson count and the episode count were both written as targets and
  both had to be rewritten as outcomes of the grouping rules. A number in a
  spec is read as a limit unless the spec says it is not.
- "Tradition" was a hedge for "Hinduism." The owner asked for precision;
  the primer got better and the reference section (content spec §7.0) came
  out of the same question, with the teacher's own words cited to a
  timestamp.
- Pruning guidance from prompts as models improve, while keeping
  constraints, is now written policy (content spec §5.3). The owner raised
  it from the observation that natural-language instructions, in prompts
  and in skills alike, can hold a more capable model below what it could
  do.

## 2026-09-16 · Day three: convergence, simplification, and the first reviewed PR

### Review loops converge on completeness, not on simplicity

- **Observation.** Seven independent review passes on the technical spec
  found 81, 35, 27, 13, 11, 4, and 3 issues. Each finding was real and each
  fix was correct. The delivery mechanism went from one paragraph to a
  state machine with seven statuses, six document kinds, per-kind
  preconditions, a 180-second timeout sweep, welcome attempt numbers, an
  "uncertain" state for lost responses, key-rotation grace periods, and a
  dozen operator recovery commands. The owner read it and said: I think
  this might be over-complicated. She was right.
- **Lesson.** A reviewer's job is to find what is wrong; it has no
  incentive to find what is unnecessary. Every pass asked "what breaks?"
  and never "what could we not build?" Seven passes of that produce a
  design that is correct for a thousand learners and heavy for one. The
  question "is this proportionate to v1?" has to be asked by a person
  holding a complexity budget, and it has to be asked between passes, not
  after.
- **Lesson.** Distinguish the guarantee from the mechanism. The product
  spec's guarantees (never send twice, never skip silently, fidelity over
  completeness) are load-bearing. The mechanism that enforces them can be
  as small as one create-if-absent document and a failure notification
  when the only learner is also the operator who reads the notification.
  The elaborated machine is the right answer for v2 and belongs in a
  hardening backlog, not in v1.0.
- **Lesson.** Stop signals for a review loop, revised: the count is
  converging *and* the findings are no longer changing behavior *and* a
  human has judged the result proportionate. The third condition is the
  one the loop cannot supply.
- **Practical note.** Sub-agents reading three thousand lines stalled
  twice; giving them exact line ranges and a word cap made the later
  passes take under two minutes. Narrow the reader as the target narrows.
- **Evidence.** Commits 4755707 through 95d912d; the seven pass results in
  the session transcript; the owner's message that stopped the loop.

### Sub-agents stall on whole-file reads; give them line ranges

- **Observation.** The fifth review pass failed twice with "no progress for
  600 seconds" while reading three files totalling about 3,300 lines. The
  retry was told exact line ranges to read with offset and limit, and to
  keep its answer under a word cap. It finished in two and a half minutes.
  The sixth and seventh passes, scoped the same way, took under two minutes
  each.
- **Lesson.** As the review target narrows, narrow the reader. A sub-agent
  asked to "read all three documents" spends its budget on context it will
  not use and can stall before it writes a word. State the line ranges,
  the scenarios to trace, and the output cap.

### The simplification pass: keep the guarantee, shrink the mechanism

- **Observation.** After the owner stopped the review loop, the delivery
  section was cut from seven statuses to four, six document kinds to four,
  and a dozen recovery commands to three, in one pass with the owner
  choosing the line. Nothing was discarded: every removed mechanism went
  into an appendix with the scenario it addresses and the point at which it
  becomes worth building.
- **Lesson.** "Keep the guarantee, shrink the mechanism" is the move. The
  product guarantees (never send twice, never skip silently) did not
  change; the machinery that enforces them was sized to one learner who is
  also the operator. The appendix is what makes the cut safe: the work of
  seven reviews is scheduled against evidence rather than lost.
- **Evidence.** Technical spec §8 and Appendix B; commit 2a274db.

### The first PR under our own review rules

- **Observation.** The clean-slate PR, docs only, was reviewed by Greptile
  under the twelve rules derived from the technical spec. Score 0 of 5,
  four findings, every one real: a retry path that could double-send when
  two runs overlapped, a missed-window scan that only looked back two
  days, a product-spec claim that a forwarded link "opens for no one
  else" which a bearer token cannot deliver, and a timestamp contract
  stated two different ways in two specs. Each finding cited the rule it
  fired under and the spec section it contradicted. Fixed in one commit;
  re-review 5 of 5.
- **Lesson.** Rules written as "this document must be consistent with that
  section" work, on documents as well as code. The reviewer had the specs
  as context and used them. The one overclaim it caught in the product
  spec had survived seven independent passes that were reading for
  mechanism, not for promises.
- **Lesson.** Greptile does not post a new comment on re-review. It edits
  its original summary in place, increments "Reviews (N)", changes the
  last-reviewed commit, and reacts with a thumbs-up on the request. A
  triage loop that waits for a new comment waits forever. Detect the
  edit.
- **Evidence.** PR #1; commits 16307c3 and aa1487f.

### Phase 0 complete

- The specs and the review rules are on `main`; the v0 code is a tag.
  Sixteen calendar days from "let's redesign" to a merged clean slate,
  across four working sessions with the owner. The next PR is the first
  with code in it, and it will be reviewed the same way.

---

## Article outline (evolving)

Working title: *What a year of the Gita taught me about agents* (or less
grand). Themes, each mapping to entries above:

1. **Probe, then spec, then build.** The thirty-minute probe that deleted a
   pipeline.
2. **A spec is a conversation with a commit log.** Section-by-section
   review; reconcile requirements last; load-bearing sections.
3. **Green tests, real failures.** Why the first real call matters more
   than the hundredth mocked one.
4. **Provenance is a fidelity problem, not a licensing problem.** The
   GPT-edited "open" dataset.
5. **Humans are the eval set.** Reviewers who retire into tests; evals that
   track the model.
6. **Boring process, real leverage.** Tags over archive folders; trunk
   with deferred PRs; confirm-before-shared-state; memory files.
7. **When not to orchestrate, and the first time it paid off.** One agent,
   one conversation, until the work is parallel; then a single narrowly
   scoped reviewer sub-agent that found eighteen inconsistencies the author
   could not see.
8. **One reviewer is not enough, and neither is three by rule.** The
   owner, the author, and independent readers each catch a different
   class of error; the fix is a draft; stop on convergence, not on a
   count. The 81 → 35 → 27 → 13 → 11 → 4 → 3 curve, what each pass found
   in the previous pass's fixes, and why the loop converged on
   completeness rather than simplicity until a person stopped it.
9. **Serverless as habits, not a label.** Stateless, idempotent, cold-start
   aware, least-privilege, host-less observability; the design had all of
   them before anyone said the word. (Running thread; to be filled from
   implementation.)

Open questions for the article: how much of the nuance is specific to a
solo project with a single owner; what changed once Greptile and the triage
loop were live; whether sub-agents earned their place in implementation.
