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
7. **When not to orchestrate.** One agent, one conversation, until the
   work is parallel. (To be written after phase 1.)

Open questions for the article: how much of the nuance is specific to a
solo project with a single owner; what changed once Greptile and the triage
loop were live; whether sub-agents earned their place in implementation.
