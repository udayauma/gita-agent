# Gita Agent — Product Specification (v1)

| | |
|---|---|
| **Status** | Draft for review |
| **Owner** | Udaya Pillalamarri |
| **Version** | v1 (private MVP) |
| **Date** | 2026-09-12 |
| **Related** | `docs/content_spec.md`, `docs/technical_spec.md`, `docs/task_plan.md` (to follow) |

---

## 1. Problem

The Bhagavad Gita is worth learning, and many people want to. The barrier is not
interest, it is access. The primary text is Sanskrit. The best teachers explain it
in long, dense discourses, often in a regional language, at a level that assumes
years of grounding. A learner who cannot read Sanskrit and cannot sit through a
ninety-minute Telugu lecture is left with two bad options: give up, or rely on
unattributed quotes on social media with no way to know whether they are accurate.

The cost of not solving this is that people who want to learn simply do not,
and the ones who try absorb a distorted version.

**Who has this problem.** Udaya has it personally. Her father reads Sanskrit and
studies the source texts; she cannot follow when he explains them. The people she
would like to share this with have less time than she does.

## 2. What we are building

A service that sends one short Bhagavad Gita lesson by email every morning, in
plain English, at the learner's pace, with every claim traceable to its source.

Each lesson is built from two layers:

- **The canon.** The verse itself, in Sanskrit, transliteration, and a
  public-domain English translation. Sequenced in order, chapter by chapter.
- **The lens.** A teacher's explanation of that verse, drawn from recorded
  discourses that have been transcribed and translated. The default teacher is
  Sri Chaganti Koteswara Rao, whose Telugu discourses are the content Udaya's
  father recommended.

The learner does nothing after signing up. The lesson arrives. Reading it takes
under five minutes.

## 3. Who it is for

**v1 is private.** The only learners are Udaya and people she personally adds.
There is no public signup, no announcement, and no expectation that anyone
outside that circle uses it. The purpose of v1 is to prove that the lessons are
accurate, readable, and reliably delivered, and to build the evaluation habit
before anyone else depends on it.

**v2 opens the door.** External learners, self-serve signup, and the ability to
reply to a lesson and have a conversation about it arrive in v2. v1 is designed
so that v2 attaches without rework, but v1 does not build any of it.

### Personas

| Persona | Who | What they need |
|---|---|---|
| **Learner** | Udaya, and later people like her: curious, busy, no Sanskrit, wants English | A lesson that arrives, is short, is accurate, shows its sources, and links to the original recording and to a longer form for anyone who wants to go deeper |
| **Operator** | Udaya, running the service | Add and remove learners and reviewers, choose content, see that it is working, know what it costs |
| **Reviewer** | People more learned than the learner: Udaya's father first, then others she trusts, such as scholars at the local temple | The same lesson plus the source material behind it, so they can judge whether it is faithful to the verse and to the teacher, and a simple way to say so |

**Reviewer is a role, not a person.** The operator keeps a review list. Anyone on
it receives the *review edition* of each lesson: the learner's lesson followed by
an appendix the learner never sees, with the teacher's original Telugu passage,
the transcript excerpt it was drawn from, and the exact canon record for the
verse. A person can be both a learner and a reviewer.

A reviewer gives feedback by replying to the email. The operator reads the
reply and records it in the fidelity audit log.

**The reviewer role exists only in v1 and v1.1, and only over email.** It is
retired at v2. What reviewers produce is not retired: every correction and
every lesson they confirm as faithful goes into the fidelity golden set, so
that by v2 their judgment runs automatically as evals on every model or prompt
change (§6.2, model independence). Reviewers stop being people on a list and
become the test suite.

**Timing.** v1.0 sends to Udaya alone. Reviewers and additional learners are
added in v1.1, once thirty days of clean delivery have shown the lesson is worth
a reviewer's time.

## 4. Goals

1. **Deliver every morning.** A lesson arrives in each learner's inbox at their
   chosen local time, every day, for thirty consecutive days with zero missed or
   duplicated sends.
2. **Be faithful.** Every verse quoted matches the canonical text exactly. Every
   teacher passage is attributable to a specific video and timestamp. A reviewer
   who checks twenty lessons finds no fabricated content.
3. **Be readable.** A learner with no background reads a lesson in under five
   minutes and can say in one sentence what the verse means.
4. **Be sustainable.** Two distinct mechanisms, both required:
   - *Visibility* is built into the service. Every Gemini call's token usage is
     recorded and priced, and the weekly ops digest email (§8.4, P0-10) reports
     spend for the week and month to date. The operator never opens a billing
     console to know what the service cost.
   - *The ceiling* is a GCP budget alert on the project, set by the operator as
     a one-time setup step at an amount well above expected spend. It is a
     backstop against a runaway job between digests, not the primary cost
     view. The amount is open question 5.
5. **Be honest about sources.** Every lesson names the translator, the teacher,
   and the recording it drew from, so a learner can go deeper on their own.

## 5. Non-goals for v1

| Non-goal | Why not now |
|---|---|
| Replying to a lesson and getting an answer | This is the v2 agent. It needs a conversational runtime, session state, and evaluation infrastructure that v1 does not. |
| Public signup or a landing page | v1 is private by decision. Udaya's website is a separate project and will announce the service when v2 is ready. |
| Channels other than email | Email is the simplest reliable channel for a daily push. SMS is next, then Slack and others. In v2 these matter more than in v1: replying to a text or a Slack message is lower friction than replying to an email, so the interactive mode should meet the learner on the lowest-friction surface they have. v1 builds the channel abstraction two-way so that adding a channel adds both delivery and reply routing. |
| Telugu-language lessons | English is the whole point for the first learner. The Telugu transcript is stored alongside the English translation in the operator's own storage (§7.2), so a Telugu track is possible later without re-ingesting anything. |
| Choosing your own path through the Gita | v1 walks the text in order. Topic-based or question-driven paths are v2 territory. |
| Multiple teachers per learner | One teacher pack per learner keeps the lesson coherent. Blending teachers is a later design question. |
| A web or mobile app | Email is the interface. There is nothing to log in to. In v2 a minimal web surface arrives for self-serve signup, onboarding, and preferences (P2-3, §12), announced from Udaya's website. Even then the lesson and the conversation happen on messaging channels the learner already uses, such as email, SMS, or Slack, not in an app of ours. A full app is not planned for any version. |
| Rendering audio or video | Lessons are text. Links to the source video are included for anyone who wants to listen. |
| Running on any cloud other than Google Cloud | The stack is Gemini on Vertex AI, Cloud Run, Cloud Scheduler, and Cloud Storage. Abstracting all four for AWS or Azure is a large tax for a hypothetical operator. GCP only, by design, in every version (§7.2). |

## 6. The lesson

This is the product. Everything else exists to produce it.

### 6.1 What a lesson contains

Every lesson has the same five parts, in this order.

1. **Where we are.** One line giving position and scale: "Day 14 of about 380 ·
   Chapter 2, Verse 47." It is a position, not a score. There is no percentage
   and no streak, so it reads the same on day one as on day three hundred.
   Lesson one says "Day 1 of about 380 · Chapter 1, Verse 1" and that is
   correct and complete.

   **Chapter openings.** Lesson one, and the first lesson of every chapter,
   adds a short *Where this sits* paragraph directly under this line: what the
   chapter is about, what came before it, and why it begins where it does. For
   lesson one this is the learner's introduction to the text itself: who is
   speaking, to whom, and where. This paragraph is generated once per chapter
   as part of the content pack, reviewed like any other content, and is the
   same for every learner.
2. **The verse.** Sanskrit in Devanagari, then transliteration, then one
   public-domain English translation. Verbatim from the canon dataset, never
   generated. The translator is named.
3. **What it means.** Two to four plain-English sentences. Generated, but
   constrained to restate the translation and the teacher's explanation. No new
   claims.
4. **From the teacher.** A short passage, roughly 100 to 200 words, of the
   teacher explaining this verse or its idea, translated to English. Paraphrased
   from the transcript, with the video title and a **timestamped link to the
   original YouTube recording** so the learner can hear it in the teacher's
   voice. For sources that have a public address, which is every v1.0 source, the
link is mandatory and a lesson without it is not sent. For source types
without one (§7.2), the lesson names the recording and its timestamp instead.
5. **A question to carry.** One reflective question for the day. Generated.
   Short.

Then a footer: the sources used, a **reaction row** of three tap targets (see
§6.7), a **"read more" link** to the lesson's long-form page (see §6.5), and an
unsubscribe link. Progress is not repeated in the footer; the "Where we are"
line is the single place it appears.

### 6.1.1 Short form and long form

The email is deliberately the short form. It is what a busy learner reads in
five minutes. For the learner who wants to go deeper that day, the lesson
points outward in two ways:

- **To the source.** The timestamped YouTube link in "From the teacher."
- **To the long form.** A page for the same lesson with the full teacher
  passage in English and Telugu, every transcript segment that touched this
  verse with its timestamp, the neighboring verses, and more than one
  translation. The long form is generated from the same material as the email;
  it is not a different lesson.

In v1.0 the email carries the source link only, and every lesson is minted with
a stable ID and a URL slot so that the long-form page can be attached in v1.1
without changing anything already sent.

### 6.2 What a lesson never does

These rules are the fidelity contract. They are written as absolutes on
purpose: tests are derived from them, the review rules for every pull request
are derived from them, and a lesson that violates any one of them is not sent.
They apply in every version, and they matter most in v2, when learners the
operator has never met are on the list.

**Fidelity**

- Never quotes a verse that is not in the canon dataset. The Sanskrit,
  transliteration, and translation are copied from the canon record, never
  generated, never "corrected."
- Never generates Sanskrit. Every Devanagari or transliterated term in a
  lesson comes from the canon record or from the teacher's transcript.
- Never attributes to the teacher something that is not in a transcript. The
  teacher passage is drawn from the transcript store for a specific video and
  timestamp, or it does not appear.
- Never draws on the model's own knowledge of the Gita or its commentators
  for the teacher section. The model knows the Gita well, and the easiest
  failure is a plausible passage the teacher never said. If the store has
  nothing for a verse, the lesson says so and carries the canon layer only.
- Never guesses when confidence is low. If a transcript segment or its
  translation is uncertain, the lesson omits it, sends with the canon layer,
  and flags the lesson to the operator. Fidelity beats completeness.
- Never presents generated text as a quotation, and never blurs the boundary
  between the teacher's words and generated text. Each part of the lesson is
  labeled. "What it means" and "A question to carry" are generated and say
  nothing the verse and the teacher passage do not support.
- Never depends on the model for accuracy. The model composes; the canon
  store and the transcript store are the only sources of fact. A more capable
  model produces a better-written lesson under the same rules; it does not
  earn looser rules. Every lesson records the model and prompt version that
  produced it, and a model change is a reviewed change: it passes the same
  fidelity audit as content before it reaches a learner.

**Voice**

- Never gives directive advice. The lesson offers a question, not an
  instruction. No medical, legal, financial, relationship, or political
  guidance, even where the verse seems to invite it.
- Never asserts one interpretation as the only one. Where translations or
  schools differ, the lesson either says so in a sentence or stays with the
  teacher's reading, attributed to the teacher.
- Never proselytizes, ranks traditions, or comments on other religions.
- Never speaks to the learner's personal circumstances. It does not know
  them, and in v1 it must not pretend to.
- Never adapts content automatically from reactions or feedback. Reactions
  inform the operator. Content changes go through review.

**Reach and privacy**

- Never sends to anyone who is not on the list, and never reveals one
  learner's existence, address, progress, or reactions to another.
- Never includes third-party trackers, tracking pixels, or external scripts.
  The only links in a lesson are the source recording on YouTube, the
  long-form page, the reaction row, and unsubscribe. All but the recording are
  first-party.
- Never sends outside the learner's configured delivery window.
- Never sends anything other than the welcome email, the daily lesson, a
  correction note when one is needed, and the unsubscribe confirmation. No
  promotions, no re-engagement messages, no surveys beyond the reaction row.

**Delivery and immutability**

- Never exceeds roughly 400 words in the body. If the teacher's material is
  rich, the lesson links to it rather than growing.
- Never sends twice for the same day, and never skips a day silently. If
  delivery fails, the operator is told and the learner's progress does not
  advance.
- Never changes a lesson after it is sent. Corrections go into the content
  pack for learners who have not reached that lesson yet. If a lesson that
  was already sent had a material error, the fix is a short correction note
  the next morning, never a silent edit and never a resend.

**Reserved for v2.** When learners can reply, the agent is not a counselor.
If a learner brings distress into the conversation, the agent responds with
care and points to a person. The v2 spec defines this before any external
learner is added; it is listed here so that it is not forgotten.

### 6.3 Pace and sequence

The unit of a lesson is **one idea**, which is one verse or a small run of
consecutive verses that form a single thought. The Gita has 700 verses, so one
verse a day would take almost two years, and many verses only make sense in
pairs or triples. Grouping by idea yields roughly 350 to 400 lessons, about a
year at one a day.

The grouping is fixed in advance as part of the content pack, not decided each
morning. Two learners on the same pack see the same sequence.

Pace is one lesson per day in v1. It is a per-learner setting so that "every
other day" or "weekdays only" can be added without a schema change.

### 6.4 Tone

**Factual first.** The lesson reports what the verse says and what the
teacher said. It does not embellish, does not add emotional color, and does
not tell the learner how to feel. "What it means" restates; it does not
inspire. The only place the lesson addresses the learner directly is the
closing question, and even there it asks rather than tells.

**Then plain, warm, unhurried.** Warmth comes from plainness and patience, not
from adjectives. The lesson speaks to one person in short sentences. It does
not preach. It does not hedge every sentence. Sanskrit terms appear with their
meaning the first time they are used in a lesson.

**Banned words.** Certain words are what a model reaches for when asked to be
encouraging, and each carries a claim the lesson must not make: that the
learner is being guided somewhere, that a secret is being revealed, that
transformation is on offer. They never appear in generated text. The seed list
is *journey, unlock, empower, transform, embrace, mindful, elevate, awaken,
manifest, secret, powerful, profound, timeless, ancient wisdom*. The content
spec owns the full list; it is a one-line test, not a judgment call. Words in
this list may still appear inside a quoted translation or the teacher's
translated passage, because those are sources, not generated text.

### 6.5 The long-form page (v1.1 only)

Each lesson has a long-form page, reachable from the "read more" link in the
email footer. It exists for the learner who has time that day, and for
reviewers. It contains:

- The verse record in full: Devanagari, transliteration, word-by-word meaning
  where the canon has it, and every translation in the dataset, each named.
- The neighboring verses, so the idea is seen in context.
- The teacher's full passage on this idea, English and Telugu side by side,
  with a timestamped link for each transcript segment.
- The same reflective question.

**Where it lives.** It is a web page at a stable URL derived from the lesson's
ID, served from the operator's own deployment. It is static HTML, generated at
the same time as the email from the same material, and it never changes after
publication. There is no login. In v1.1 it is hosted with the service; when
Udaya's website exists the pages can move there and the original URLs
redirect, so links in lessons already sent keep working.

**Who can see it: only the recipient.** The long form contains the teacher's
full passage, and §7.2 commits this project to never redistributing a
teacher's work. So the page is private to the person the lesson was sent to,
not merely unlisted:

- The "read more" link carries a signed token for that lesson and that
  recipient, the same mechanism as the reaction row (§6.7). The page is served
  only when the token is valid. A forwarded link opens for no one else.
- There is no unsigned URL for a page, no index page, and no listing of
  lessons.
- Every page instructs search engines not to index it, as a second layer.
- Tokens are revoked when the learner unsubscribes.

This is authentication without an account: the email itself is the
credential, which is the right level for a private v1.

**Long-form pages exist only in v1.** They are a v1.1 feature and are retired
at v2 launch. At that point no new pages are generated, existing pages are
taken down, and the "read more" link is dropped from the lesson. The long form
survives as something the agent offers in conversation: "Would you like the
teacher's full passage on this verse, in English and the original Telugu, with
the source?" It is provided only to the enrolled learner who asks, on the
channel they are using, adapted to that channel's length. The teacher's words
are shared one-to-one, on request, the way a tutor reads a passage aloud,
never published at a URL.

### 6.6 The review edition (v1 and v1.1 only, email only)

| Version | Reviewers |
|---|---|
| v1.0 | None. Udaya is the only learner and does her own checking. |
| v1.1 | Reviewers added by the operator receive the review edition by email. |
| v2 | Retired. The review edition is no longer produced. The golden set built from v1 reviewer feedback runs as automated evals instead. |

**The reviewer is told, every time.** A review edition opens with a short
banner above the lesson, before anything else: "You are receiving this as a
reviewer. Below is the lesson exactly as a learner sees it, followed by the
source material it was built from. If anything is unfaithful to the verse or
to the teacher, reply to this email and say so. If it is fine, you need not
reply." The banner names the pack and the teacher so the reviewer knows whose
words they are judging.

Reviewers also receive a **reviewer welcome email** when the operator adds
them (§8.5), which explains the role once, in full.

Below the banner, reviewers receive the learner's lesson unchanged, followed
by a clearly marked appendix:

- The teacher's original Telugu passage that "From the teacher" was drawn from,
  and the English translation the service produced, verbatim.
- The transcript segments used, each with video ID and timestamp.
- The exact canon record for the verse, including the translator's name and
  the dataset version.
- A one-line instruction: reply to this email with anything that is wrong.

The review edition is a rendering option on the same lesson, not a separate
lesson. Nothing in the appendix is generated; it is the raw material.

**How reviewers give feedback.** There is exactly one mechanism:

1. The reviewer replies to the review-edition email in plain language. No
   form, no account, no reaction row on the review edition. Silence means no
   objection.
2. The operator reads the reply and records it in the fidelity audit log
   against the lesson ID: what was wrong, which part of the lesson, and the
   correction if there is one. Lessons a reviewer explicitly confirms as
   faithful are recorded too.
3. Corrections go into the content pack for learners who have not yet
   reached that lesson. Lessons already sent are never edited (§6.2).
4. The audit log is machine-readable and is the source of the fidelity
   golden set (P2-1b). Nothing about reviewer feedback is automated in v1 or
   v1.1; the operator is the loop.

### 6.7 Learner feedback in v1

Every lesson email ends with a **reaction row**: three tap targets, each one
link. The default labels are *Got it*, *Unclear*, and *Loved it*. Three is
deliberate: enough to distinguish "worked", "did not work", and "worth more
of", and few enough that a weekly digest can show them per lesson without
becoming noise.

- Tapping a reaction records it against the lesson and the learner, then shows
  a one-line thank-you page. That page offers an optional single text box for
  one more sentence. Nothing else is asked.
- Each link carries a signed, single-purpose token identifying the lesson and
  learner. No email address or learner identifier appears in any URL.
- A learner can change their reaction by tapping another; the latest wins.
- Free-form feedback beyond one sentence is a plain email reply, read by the
  operator, the same path reviewers use.
- Reactions and any one-sentence notes appear in the weekly ops digest per
  lesson, so the operator sees which lessons landed and which confused.

The reaction endpoint and the unsubscribe endpoint are the same small web
surface; both receive a signed link and record an event. This is the only web
surface in v1.

The reaction row is channel-neutral in design: on SMS in v2 it becomes "reply
1, 2, or 3", and in Slack it becomes emoji reactions on the message, routed
through the same two-way channel abstraction (P2-2).

## 7. Content

### 7.1 Canon

The Bhagavad Gita text, transliteration, translations, and verse metadata come
from the open `gita/gita` dataset on GitHub (Unlicense), the same data behind
bhagavadgita.io: 18 chapters, 701 verse records, and five English
translations by named translators.

**Pinned, not frozen.** The canon is loaded from a specific upstream commit,
recorded by hash, into the service's own store and versioned there. A lesson
always names the canon version it was built from. Upstream changes are picked
up deliberately, never silently:

- Upstream is close to static. Its main branch has not changed since January
  2023 (checked 2026-09-12); unmerged feature branches exist for new
  translations and languages.
- The ops digest reports, once a month, whether upstream main has moved past
  the pinned commit.
- Upgrading the pin is an operator action. It runs a canon diff that lists
  every verse record that would change and every lesson in the pack that
  depends on one, and it goes through the same review as content. Lessons
  already sent are unaffected (§6.2, immutability).

**Which translation text is used.** The dataset's current
`data/translation.json` is not the translators' text. In January 2023 every
English entry was rewritten by an OpenAI model (text-davinci-003) with a
"fix grammar" prompt; all 3,505 English entries changed, including
modernizing "thy" to "your" and rewording sentences. The originals are
preserved in the dataset at `archive/translation_old.json`. This service loads
the **originals** and never the rewritten file. Attributing a machine-edited
sentence to Swami Sivananda would be exactly the misattribution §6.2 forbids.
The loader strips the leading verse-number prefix present in the original
records and does nothing else to the text.

**Why this dataset, and what else exists.** `gita/gita` was chosen as the
structural spine because it is the only open source found with all of:
verse-level JSON, Devanagari, IAST transliteration, word meanings, chapter
metadata, and several named English translations, under a permissive license.
A survey on 2026-09-12 found no better spine, but it found better
*translation* sources, and the canon is therefore layered: the Sanskrit,
transliteration, and word meanings come from the spine; each English
translation is a separate record with its own provenance and rights status,
whichever source it came from. The alternatives and their trade-offs are
recorded in the content spec. In brief: `vedicscriptures/bhagavad-gita` has
the same lineage with 22 text commentators, but it is GPL-3.0, so vendoring it
would put copyleft files in this repository, and, more importantly, several of
its commentaries (Prabhupada, Chinmayananda, modern translations of the
classical commentators) are copyrighted by their publishers, which no
repository license can override; its marginal value here is low because this
product's lens is spoken discourse, not text commentary; Wikisource carries three verified public-domain
translations (Telang 1882, Arnold 1885, Besant 1895) under CC BY-SA; GRETIL
carries a scholarly Sanskrit e-text derived from the critical edition with no
stated reuse terms; Gita Supersite (IIT Kanpur) is the academic origin of
most of these but publishes no license.

**Translator rights are not uniform.** The dataset is Unlicense, but that
covers the compilation, not the translators' copyright. Of the five English
translators, Shri Purohit Swami (1935) and Swami Sivananda (1942) are the
oldest and the safest to treat as public domain; Swami Gambirananda, Swami
Adidevananda, and Dr. S. Sankaranarayan are late-twentieth-century
publications whose rights likely remain with their publishers. For a private
v1 this is not a blocker. Before v2 sends lessons to the public, the default
translation must be one whose status is confirmed. The content spec names the
default and records the reasoning; this is open question 6.

### 7.2 Teacher content packs

A **pack** is a named set of sources by one teacher, plus the transcripts and
translations the service produces from them. Packs are the "bring your own
content" mechanism.

**Source types.** A pack lists one or more sources, each with a type. The pack
format and the transcript store are source-agnostic from v1.0: a stored
segment holds text, language, timestamps, and a reference to its source, and
neither the store nor the lesson depends on where the segment came from.
Only the ingestion step is per type, and v1.0 implements exactly one.

| Source type | Example | How it is ingested | Version |
|---|---|---|---|
| Public YouTube playlist or video | The default teacher's playlists | Sent to the model directly from the URL, in windows | **v1.0, the only type implemented** |
| Audio or video files the operator owns | Recordings in the operator's own cloud storage | Same model call with the file instead of the URL | P1 |
| Podcast feed | An RSS feed of discourses | Feed poll, then the file path above | P2 |
| Text | A transcript, PDF, or book the operator has rights to | No transcription; chunked and stored directly | P2 |
| Other video hosts, unlisted or private videos | Vimeo, a teacher's private upload | Not planned; depends on each host's access rules | Not planned |

The "listen to the source" link in a lesson (§6.1) is mandatory for YouTube
sources and optional for source types that have no public address.

**Rights travel with the pack, and the warning is explicit.** Every manifest
carries a one-line attestation that the person adding it has the right to use
the listed content for this purpose. The service will not ingest a pack
without it, and it never verifies it. That second fact is stated to the
person, in plain words, at the moment they add content, in every version:

> This service does not verify your right to use the content you add. By
> adding it you confirm that you hold that right. Generated transcripts and
> lessons will be delivered to whoever you enroll, so treat this as
> publishing.

In v1 the warning appears in the operator documentation and in the
ingestion command's output when a new pack is registered. In v2, adding
content is still an operator action (see "Who may bring content" below), and
any operator-facing surface that accepts a pack shows the same warning and
requires acknowledgment before the content is accepted. The wording is fixed in the
content spec so that every surface says the same thing. "Bring your own
content" means your own, and the service says so out loud.

**The repository ships manifests, never content.** A manifest lists the
playlist and video IDs and describes the pack. The transcripts and translations
are generated by the operator's own deployment into the operator's own storage.
The teacher's work is never redistributed by this project.

**Whose cloud.** Two roles must not be confused here:

- A **learner** needs no cloud account, no install, and no setup. They give
  an email address and receive lessons from a deployment that someone else
  runs. This is true in every version, including external learners in v2,
  who are learners on the operator's deployment.
- An **operator** runs a deployment, and that requires a Google Cloud
  project. The service is built on GCP only, by design: Gemini on Vertex AI,
  Cloud Run, Cloud Scheduler, and Cloud Storage. There is no AWS or Azure
  option and none is planned; supporting them would mean abstracting the
  model provider, the job runner, the scheduler, and storage for a
  hypothetical. The setup guide tells a prospective operator, before anything
  else, that a GCP project with billing is a prerequisite. In v1 there is one
  operator.

**Who may bring content.** In v1, only the operator adds packs, into their
own project. In v2, learners on the hosted deployment do **not** add their
own content: doing so would place a stranger's content, cost, and rights
exposure on the operator's project. Bring-your-own content in v2 remains an
operator capability, which any person can obtain by running their own
deployment from this repository. Whether a hosted learner may ever add
content is a later decision with its own spec.

**Where generated content lives.** The Telugu transcript and the English
translation are produced together and stored together, one record per video
segment, in cloud storage owned by the operator's own project. That store is
the system of record. A chunked, embedded copy of the English goes into the
vector index so that lesson composition can find the teacher's passage for a
verse; the index is derived data and can be rebuilt from the store. The exact
layout and schema are defined in the technical spec.

### 7.3 Defaults are mandatory

If an operator configures nothing, the service works. The defaults are:

| Layer | Default |
|---|---|
| Canon | `gita/gita` dataset, pinned version |
| Teacher pack | Sri Chaganti Koteswara Rao: the "Bhagavad Gita" playlist (8 videos, 8.5 h) and the "Sampoorna Srimad Bhagavatam" series (40 videos, 68 h), see §7.4 |
| Translation | The dataset's default English translation, named in every lesson |
| Pace | One lesson per day |
| Delivery time | 07:00 in the learner's timezone |
| Channel | The channel matching the contact the learner provided. In v1 that is always email, because the operator adds learners by email address. |

A learner added with only an email address and a timezone receives a correct,
complete lesson the next morning. This is a hard requirement, not a convenience.

**Defaults across versions.** Canon, teacher pack, translation, pace, and
delivery time have the same defaults in every version. Only the channel
default changes shape in v2: a learner who signs up with a phone number
defaults to SMS, one who connects Slack defaults to Slack, and one who
provides more than one contact chooses at signup, with email as the
tie-break. Whatever the channel, a learner who provides nothing beyond a
contact and a timezone still receives a complete lesson using every other
default.

### 7.4 The default teacher's two series

The default teacher pack contains two of Sri Chaganti Koteswara Rao's series,
both recommended by Udaya's father, and both are part of v1:

| Series | Size | What it is | Role in lessons |
|---|---|---|---|
| Bhagavad Gita playlist | 8 videos, 8.5 h | Discourse on the Gita itself | Primary lens for verse lessons. Ingested first. |
| Sampoorna Srimad Bhagavatam | 40 videos, 68 h | Discourse on the Bhagavata Purana: Krishna's life and the devotional stories | Secondary lens for verse lessons from v1.0; its own story track from v1.1 |

**v1.0: both series are ingested, and verse lessons retrieve across both.**
When a verse lesson looks for "From the teacher," it searches the whole pack.
The Bhagavatam discourses speak constantly about karma, devotion, and
Krishna, so for many verses the most relevant passage will come from there.
The lesson names the series, video, and timestamp it drew from, as always.
Where no passage in either series is relevant enough, the retrieval threshold
does not select one, and the lesson carries the canon layer only (§6.2). The
Bhagavatam is never forced onto a verse it does not speak to.

**v1.1: the story track.** A second lesson type walks the Bhagavatam in order,
one episode at a time, not anchored to a verse: where we are in the series,
the teacher's passage in English, what it means, a question. It uses the same
pipeline, the same fidelity rules, and a different template. Sixty-eight
hours is roughly four hundred episodes. The story track is a **daily second
track, opt-in, off by default, delivered as its own email** at the learner's
delivery time, so a learner can read the verse in the morning and the story
whenever suits them. The two tracks keep separate progress. Composition cost
is a fraction of a cent per lesson; the constraint is the learner's
attention, which is why it is opt-in. Ingestion of the full series happens
in v1.0 regardless, so the story track is a template and a schedule, not new
content work.

## 8. User journeys

### 8.1 Operator adds a learner

1. The operator adds a learner with, at minimum, an email address and a
   timezone. Optional: name, delivery time, pace, pack.
2. The learner receives a **welcome email** the same day. It has two parts:
   - **A primer**, one or two paragraphs, orienting the learner in the
     tradition before the first lesson arrives: the Vedas as the root, the
     Upanishads as their philosophical core, the Mahabharata as the epic, and
     the Gita as the conversation inside it that distils the whole. It should
     say plainly that the tradition is vast and deep, that this service walks
     one text slowly, and that depth comes from the daily habit rather than
     from any single lesson. The primer is written once as part of the
     content pack, reviewed like any other content, and is the same for every
     learner.
   - **The mechanics**: what will arrive, when, from whom, how long it takes to
     read, how to stop, and the date of the first lesson.
3. The next morning at the delivery time, lesson one arrives.

Adding a learner is a configuration change made by the operator, not a form. In
v1 there is exactly one operator.

### 8.2 The daily lesson

1. At the learner's delivery time, the next lesson in the sequence is composed
   and sent.
2. The learner reads it. There is nothing to click, though the source links are
   there.
3. The learner's progress advances by one.

If a lesson cannot be sent, it is retried within the hour. If it still fails,
the operator is notified, and the learner's progress does not advance, so the
same lesson is sent the next day rather than skipped.

### 8.3 Learner stops

Every email carries an unsubscribe link. Clicking it stops delivery
immediately, sends one confirmation, and preserves the learner's progress in
case they return. No further email is sent for any reason.

### 8.4 Operator checks on the service

Once a week the operator receives an **ops digest** email: lessons sent and to
whom, failures, reactions and one-sentence notes per lesson, new videos
ingested, tokens used, and estimated spend for the week and month to date. This is the primary operational surface in v1. There is
no dashboard.

### 8.5 Reviewer receives and answers (v1.1 only, email only)

1. The operator adds a reviewer with an email address. A reviewer is not
   required to be a learner. Email is the only channel for reviewers; the
   role does not extend to SMS or Slack and is retired at v2.
2. The reviewer receives a **reviewer welcome email** the same day. It says,
   in plain terms: you have been asked to review daily Bhagavad Gita lessons
   for accuracy; each morning you will receive the lesson as a learner sees
   it plus the source material behind it; your job is to judge whether the
   lesson is faithful to the verse and to the teacher, not whether you agree
   with the teacher; reply to any email to give feedback; no reply means no
   objection; here is how to stop. It names the operator, the pack, and the
   teacher.
3. Each morning the reviewer receives the review edition of that day's lesson,
   at the same time as the learners on the same pack. Every review edition
   opens with the reviewer banner (§6.6).
4. If something is wrong, the reviewer replies to the email in plain language.
   No form, no account.
5. The operator reads the reply and records it in the fidelity audit log, with
   the lesson ID. If the lesson needs correcting, the correction goes into the
   content pack so that the next learner to reach that lesson gets the fixed
   version.

Reviewers can stop the same way learners do, with the unsubscribe link.

### 8.6 New teacher content appears

Once a week, the service checks each configured playlist for videos it has not
yet processed, processes them, and mentions them in the next ops digest. No
operator action is needed. Already-processed videos are never reprocessed.

## 9. Requirements

### P0 — v1 does not ship without these

| ID | Requirement | Acceptance criteria |
|---|---|---|
| P0-1 | Daily lesson delivery by email at the learner's local time | Given an active learner with delivery time 07:00 Asia/Kolkata, when 07:00 IST arrives, then a lesson email is sent within 5 minutes. Given the same learner, when the day's send has already succeeded, then no second email is sent that day. |
| P0-2 | Lesson structure per §6.1 | Every lesson contains all five parts in order, plus the footer. A lesson missing any part is not sent and is reported. |
| P0-3 | Verse fidelity | The Sanskrit, transliteration, and translation in a lesson are byte-identical to the canon store for that verse. |
| P0-4 | Teacher attribution | Every "From the teacher" passage links to a video ID and a timestamp at which the transcript contains the source material. |
| P0-5 | Sequential progress per learner | Two learners on the same pack at different start dates each receive the sequence from lesson 1. Progress is stored per learner and survives restarts. |
| P0-6 | Mandatory defaults per §7.3 | A learner configured with only email and timezone receives a complete lesson using the default canon and pack. |
| P0-7 | Unsubscribe | Every email has an unsubscribe link. Clicking it stops all future email within one minute and preserves progress. |
| P0-8 | Failure visibility | A failed send is retried at least once within the hour. A send that still fails produces an operator notification the same day, and the learner's progress does not advance. |
| P0-9 | Teacher content ingestion from a pack whose sources are public YouTube playlists or videos (the only v1.0 source type, §7.2) | Given a pack manifest with the rights attestation, when ingestion runs, then every video is transcribed and translated, stored with its source reference, and marked complete. Running ingestion again processes nothing. A manifest without the attestation is refused. |
| P0-10 | Weekly ops digest | Every week the operator receives one email with sends, failures, videos ingested, tokens used, and estimated cost. |
| P0-12 | Reaction row per §6.7 | Every lesson email has three reaction links. Tapping one records the reaction for that lesson and learner within one minute and shows a thank-you page with an optional one-sentence box. No learner identifier appears in the URL. The latest reaction wins. Reactions appear in the next ops digest. |
| P0-11 | Welcome email per §8.1 | A newly added learner receives a welcome email before their first lesson. It contains the primer (Vedas, Upanishads, Mahabharata, Gita) in no more than two paragraphs, and the mechanics. The primer text is part of the content pack and is identical for every learner. |

### P1 — should follow soon after

| ID | Requirement | Notes |
|---|---|---|
| P1-0 | Reviewer role and review edition per §3, §6.6, §8.5 | Operator-managed review list; email only; review edition is a rendering option on the same lesson; feedback by email reply, logged manually into the golden set. Retired at v2. |
| P1-0b | Long-form lesson page per §6.5, linked from every email footer via a recipient-signed link | Static, generated with the email, never edited after publication. Served only with a valid token; no unsigned URL; not indexed; tokens revoked on unsubscribe. v1 only; retired at v2 launch. |
| P1-1 | Per-learner pace options: weekdays only, every other day | Schema supports it in v1; UI is a config field. |
| P1-2 | Bhagavatam story track per §7.4: a second lesson type walking the series in order | Content is already ingested in v1.0; this adds a template, an episode sequence, and a schedule. Cadence is open question 7. |
| P1-3 | Operator-triggered "resend today's lesson" and "skip to lesson N" | For recovery and testing. |
| P1-4 | Include the original Telugu passage alongside the English in "From the teacher" | Stored already; a rendering option. |
| P1-5 | Alternate translation choice per learner | Dataset has several; lesson names whichever is used. |

### P2 — design for, do not build

| ID | Requirement | Design constraint on v1 |
|---|---|---|
| P2-0 | Every lesson has a stable ID from v1.0, and a reserved long-form URL slot during v1 | The ID is permanent and is what v2's reply threading and the agent's "full passage" offer key on. The URL slot is used only by the v1.1 long-form page and is dropped at v2 launch. |
| P2-1 | Reply to a lesson and converse (the v2 agent), on whichever channel the lesson arrived | Every lesson carries a stable lesson ID and a channel-specific thread reference (email headers, SMS conversation, Slack thread). Transcript chunks are retrievable by verse and by semantic query. |
| P2-1b | Reviewer feedback becomes automated evals | The v1 audit log is machine-readable from day one, keyed by lesson ID, so that confirmed-good lessons and corrections seed the fidelity golden set that replaces human reviewers at v2. |
| P2-2 | SMS, Slack, and other channels, for delivery and for replies | The channel abstraction is two-way from v1: each adapter defines outbound send and inbound reply routing keyed by lesson ID, even though v1 implements only email outbound. Lesson content is channel-neutral text with a per-channel rendering step, so a text-length rendering exists as a design case from the start. |
| P2-3 | Self-serve signup and public launch | Learner records carry a status and a consent timestamp from day one. |
| P2-4 | Multiple operators / multi-tenant | Every record is scoped to an operator ID even though v1 has one. |
| P2-5 | Telugu-language lessons | Telugu transcript is stored verbatim next to the English. |

## 10. Success metrics

v1 is private, so the metrics are about reliability and fidelity, not growth.

| Metric | Target | How measured | When |
|---|---|---|---|
| Delivery reliability | 30 consecutive days, 0 missed, 0 duplicate sends per learner | Delivery records | 30 days after first send |
| Fidelity audit | 20 lessons reviewed by Udaya and her father; 0 fabricated verses, 0 misattributed teacher passages, ≤1 meaning error | Manual review log in the repo | Days 15 and 30 |
| Readability | Udaya can state the verse's meaning in one sentence after reading, for ≥18 of 20 audited lessons | Same review log | Days 15 and 30 |
| Engagement (self-reported) | Udaya reads ≥5 of 7 lessons each week | Weekly note | Weekly |
| Reaction signal | ≥4 of 7 lessons each week receive a reaction; "Unclear" on any lesson is reviewed within the week | Reaction records via ops digest | Weekly |
| Ingestion completeness | Default Gita pack fully ingested; every video has transcript, translation, and completion marker | Ops digest | End of phase 1 |
| Cost | Weekly spend visible in the digest; monthly total under the agreed ceiling | Ops digest, GCP budget | Monthly |

**Exit criterion for v1:** thirty days of clean delivery and a fidelity audit
with no fabricated content. Meeting it is the signal to start v2.

## 11. Open questions

| # | Question | Who | Blocking? |
|---|---|---|---|
| 1 | ~~Lesson unit: one verse per day, or one idea (1–3 verses) per day as proposed in §6.3?~~ **Resolved 2026-09-12: one idea per lesson.** How ideas are grouped and reviewed is defined in the content spec. | Udaya | Resolved |
| 2 | Should the Telugu original appear in v1 lessons by default, or stay P1? | Udaya | No |
| 3 | Is Udaya's father willing to be the fidelity reviewer for the 20-lesson audit? | Udaya | No, but it shapes the audit plan |
| 4 | Sender identity: which address and domain do lessons come from? Affects deliverability and is a setup step. | Udaya, technical spec | Yes, before first send |
| 5 | Monthly cost ceiling for the GCP budget alert. | Udaya | No |
| 6 | Default English translation for v2 public use: Purohit Swami (1935) or Sivananda (1942), and whether the three later translators are offered at all. Needs a rights check, not a taste call. | Udaya, content spec | Not for v1; yes before v2 |
| 7 | ~~Story track cadence (§7.4): weekend lessons alongside the verse track, or a daily opt-in second track?~~ **Resolved 2026-09-12: a daily second track, opt-in, default off, sent as its own email.** Composition cost is a fraction of a cent per lesson; the constraint is learner attention, hence opt-in. | Udaya | Resolved |

## 12. Phasing

| Phase | Delivers | Proves |
|---|---|---|
| **v1.0** | Ingestion of the default Gita pack; canon loaded; lesson composition; email delivery to Udaya; unsubscribe; ops digest | The lesson is accurate and delivery is reliable |
| **v1.1** | Reviewer role and review edition; long-form lesson page; additional learners added by the operator; other P1 items as chosen | The lesson survives expert review, and the service works for more than one person |
| **v2** | Reply-to-lesson conversation (ADK agent) on low-friction channels: SMS and Slack alongside email; long form offered by the agent in conversation instead of a page link (§6.5); self-serve signup and preferences web surface; public announcement via Udaya's website | The service works for people who do not know the operator, and talking to it is as easy as answering a text |

## 13. Glossary

| Term | Meaning |
|---|---|
| **Canon** | The Bhagavad Gita text and translations from the `gita/gita` dataset |
| **Pack** | A named set of one teacher's recordings plus their generated transcripts and translations |
| **Manifest** | The file in the repo that describes a pack by playlist and video IDs, without content |
| **Lesson** | One email: verse, meaning, teacher passage, question, footer |
| **Idea** | The unit of a lesson: one verse or a short run of verses forming one thought |
| **Learner** | A person receiving lessons |
| **Reviewer** | A person on the operator's review list who receives the review edition by email and replies with corrections. v1 and v1.1 only; retired at v2 in favor of automated evals |
| **Review edition** | The learner's lesson plus an appendix of the raw source material behind it |
| **Long form** | The static page for a lesson with the full verse record, context, and the teacher's complete passage |
| **Operator** | The person running a deployment and managing learners and reviewers |
| **Ops digest** | The weekly operator email summarizing sends, failures, ingestion, and cost |
