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

In v1, a reviewer gives feedback by replying to the email. The operator reads the
reply and records it in the fidelity audit log. In v2 the agent reads reviewer
replies itself. The role carries forward unchanged.

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
   voice. The link is mandatory; a lesson without it is not sent.
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

Plain, warm, unhurried. The lesson speaks to one person. It does not preach,
does not hedge every sentence, and does not use the words "journey" or "unlock."
Sanskrit terms appear with their meaning the first time they are used in a
lesson.

### 6.5 The long-form page (v1.1)

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

**Who can see it.** Anyone with the link, and in practice only people who
received the lesson. The long form contains the teacher's full passage, and
§7.2 commits this project to never redistributing a teacher's work, so in v1:

- URLs are unguessable; the lesson ID in the URL is a random token, not a
  sequence number.
- There is no index page or listing of lessons.
- Every page instructs search engines not to index it.

This keeps the long form private to recipients without building
authentication. It is adequate while v1 is private.

**In v2 the page goes away and the agent takes over.** Once a learner can
reply to a lesson, the long form is no longer a link. The agent offers it in
conversation: "Would you like the teacher's full passage on this verse, in
English and the original Telugu, with the source?" and provides it only to the
enrolled learner who asks, on the channel they are using, adapted to that
channel's length. Nothing sits at a public URL. The teacher's words are shared
one-to-one, on request, the way a tutor reads a passage aloud, rather than
published. Long-form pages created during v1.1 remain link-private for the
learners who received them and are not created for new lessons after v2
launches.

### 6.6 The review edition

Reviewers receive the learner's lesson unchanged, followed by a clearly marked
appendix:

- The teacher's original Telugu passage that "From the teacher" was drawn from,
  and the English translation the service produced, verbatim.
- The transcript segments used, each with video ID and timestamp.
- The exact canon record for the verse, including the translator's name and
  the dataset version.
- A one-line instruction: reply to this email with anything that is wrong.

The review edition is a rendering option on the same lesson, not a separate
lesson. Nothing in the appendix is generated; it is the raw material.

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

The Bhagavad Gita text, translations, and verse metadata come from the open
`gita/gita` dataset (Unlicense), the same data behind bhagavadgita.io. It is
loaded once into the service's own store and versioned there, so a change
upstream never silently changes a lesson.

### 7.2 Teacher content packs

A **pack** is a named set of recordings by one teacher, plus the transcripts and
translations the service produces from them. Packs are the "bring your own
content" mechanism: an operator can point the service at any public YouTube
playlist.

**The repository ships manifests, never content.** A manifest lists the
playlist and video IDs and describes the pack. The transcripts and translations
are generated by the operator's own deployment into the operator's own storage.
The teacher's work is never redistributed by this project.

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
| Teacher pack | Sri Chaganti Koteswara Rao, "Bhagavad Gita" playlist (8 videos, 8.5 h) |
| Translation | The dataset's default English translation, named in every lesson |
| Pace | One lesson per day |
| Delivery time | 07:00 in the learner's timezone |
| Channel | Email |

A learner added with only an email address and a timezone receives a correct,
complete lesson the next morning. This is a hard requirement, not a convenience.

### 7.4 Content order

The default teacher's "Bhagavad Gita" playlist is ingested first because it
maps directly onto the canon. The much larger "Sampoorna Srimad Bhagavatam"
series (40 videos, 68 h) is a different text, the Purana of Krishna's life, and
does not align to Gita verses. It becomes a second pack and a candidate for a
separate "story" track in a later version. It is not part of v1 lessons.

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

### 8.5 Reviewer receives and answers (v1.1)

1. The operator adds a reviewer with an email address. A reviewer is not
   required to be a learner.
2. Each morning the reviewer receives the review edition of that day's lesson,
   at the same time as the learners on the same pack.
3. If something is wrong, the reviewer replies to the email in plain language.
   No form, no account.
4. The operator reads the reply and records it in the fidelity audit log, with
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
| P0-9 | Teacher content ingestion from a public YouTube playlist | Given a playlist manifest, when ingestion runs, then every video is transcribed and translated, stored, and marked complete. Running ingestion again processes nothing. |
| P0-10 | Weekly ops digest | Every week the operator receives one email with sends, failures, videos ingested, tokens used, and estimated cost. |
| P0-12 | Reaction row per §6.7 | Every lesson email has three reaction links. Tapping one records the reaction for that lesson and learner within one minute and shows a thank-you page with an optional one-sentence box. No learner identifier appears in the URL. The latest reaction wins. Reactions appear in the next ops digest. |
| P0-11 | Welcome email per §8.1 | A newly added learner receives a welcome email before their first lesson. It contains the primer (Vedas, Upanishads, Mahabharata, Gita) in no more than two paragraphs, and the mechanics. The primer text is part of the content pack and is identical for every learner. |

### P1 — should follow soon after

| ID | Requirement | Notes |
|---|---|---|
| P1-0 | Reviewer role and review edition per §3, §6.6, §8.5 | Operator-managed review list; review edition is a rendering option on the same lesson; feedback by email reply, logged manually. |
| P1-0b | Long-form lesson page per §6.5, linked from every email footer | Static, generated with the email, never edited after publication. |
| P1-1 | Per-learner pace options: weekdays only, every other day | Schema supports it in v1; UI is a config field. |
| P1-2 | Second default pack: Srimad Bhagavatam as a "story" track | Requires a lesson type that is not verse-anchored. |
| P1-3 | Operator-triggered "resend today's lesson" and "skip to lesson N" | For recovery and testing. |
| P1-4 | Include the original Telugu passage alongside the English in "From the teacher" | Stored already; a rendering option. |
| P1-5 | Alternate translation choice per learner | Dataset has several; lesson names whichever is used. |

### P2 — design for, do not build

| ID | Requirement | Design constraint on v1 |
|---|---|---|
| P2-0 | Every lesson has a stable ID and a reserved long-form URL from v1.0 | Required so v1.1's long-form page and v2's reply threading attach to lessons already sent. |
| P2-1 | Reply to a lesson and converse (the v2 agent), on whichever channel the lesson arrived | Every lesson carries a stable lesson ID and a channel-specific thread reference (email headers, SMS conversation, Slack thread). Transcript chunks are retrievable by verse and by semantic query. |
| P2-1b | Reviewer replies read and triaged by the agent | Review edition messages carry the lesson ID; the audit log format is machine-readable from day one. |
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
| 1 | Lesson unit: one verse per day, or one idea (1–3 verses) per day as proposed in §6.3? | Udaya | Yes, before content pack grouping is built |
| 2 | Should the Telugu original appear in v1 lessons by default, or stay P1? | Udaya | No |
| 3 | Is Udaya's father willing to be the fidelity reviewer for the 20-lesson audit? | Udaya | No, but it shapes the audit plan |
| 4 | Sender identity: which address and domain do lessons come from? Affects deliverability and is a setup step. | Udaya, technical spec | Yes, before first send |
| 5 | Monthly cost ceiling for the GCP budget alert. | Udaya | No |

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
| **Reviewer** | A person on the operator's review list who receives the review edition and replies with corrections |
| **Review edition** | The learner's lesson plus an appendix of the raw source material behind it |
| **Long form** | The static page for a lesson with the full verse record, context, and the teacher's complete passage |
| **Operator** | The person running a deployment and managing learners and reviewers |
| **Ops digest** | The weekly operator email summarizing sends, failures, ingestion, and cost |
