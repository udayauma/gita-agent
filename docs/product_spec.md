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
| **Learner** | Udaya, and later people like her: curious, busy, no Sanskrit, wants English | A lesson that arrives, is short, is accurate, and shows its sources |
| **Operator** | Udaya, running the service | Add and remove learners, choose content, see that it is working, know what it costs |
| **Reviewer** | Udaya's father, informally | A way to spot-check that a lesson is faithful to the verse and the teacher |

The Reviewer persona has no product surface in v1. It exists because accuracy
review is how v1 earns the right to become v2.

## 4. Goals

1. **Deliver every morning.** A lesson arrives in each learner's inbox at their
   chosen local time, every day, for thirty consecutive days with zero missed or
   duplicated sends.
2. **Be faithful.** Every verse quoted matches the canonical text exactly. Every
   teacher passage is attributable to a specific video and timestamp. A reviewer
   who checks twenty lessons finds no fabricated content.
3. **Be readable.** A learner with no background reads a lesson in under five
   minutes and can say in one sentence what the verse means.
4. **Be sustainable.** The operator can see what the service costs each week
   without opening a billing console, and the cost stays within a known ceiling.
5. **Be honest about sources.** Every lesson names the translator, the teacher,
   and the recording it drew from, so a learner can go deeper on their own.

## 5. Non-goals for v1

| Non-goal | Why not now |
|---|---|
| Replying to a lesson and getting an answer | This is the v2 agent. It needs a conversational runtime, session state, and evaluation infrastructure that v1 does not. |
| Public signup or a landing page | v1 is private by decision. Udaya's website is a separate project and will announce the service when v2 is ready. |
| Channels other than email | Email is the simplest reliable channel. SMS is next, then others, once the lesson format is proven. |
| Telugu-language lessons | English is the whole point for the first learner. The Telugu transcript is stored, so a Telugu track is possible later. |
| Choosing your own path through the Gita | v1 walks the text in order. Topic-based or question-driven paths are v2 territory. |
| Multiple teachers per learner | One teacher pack per learner keeps the lesson coherent. Blending teachers is a later design question. |
| A web or mobile app | Email is the interface. There is nothing to log in to. |
| Rendering audio or video | Lessons are text. Links to the source video are included for anyone who wants to listen. |

## 6. The lesson

This is the product. Everything else exists to produce it.

### 6.1 What a lesson contains

Every lesson has the same five parts, in this order.

1. **Where we are.** One line: "Day 14 · Chapter 2, Verse 47." Progress orients
   the learner and makes gaps visible.
2. **The verse.** Sanskrit in Devanagari, then transliteration, then one
   public-domain English translation. Verbatim from the canon dataset, never
   generated. The translator is named.
3. **What it means.** Two to four plain-English sentences. Generated, but
   constrained to restate the translation and the teacher's explanation. No new
   claims.
4. **From the teacher.** A short passage, roughly 100 to 200 words, of the
   teacher explaining this verse or its idea, translated to English. Paraphrased
   from the transcript, with the video title and a timestamped link to the
   original so the learner can hear it in the teacher's voice.
5. **A question to carry.** One reflective question for the day. Generated.
   Short.

Then a footer: the sources used, the learner's progress, and an unsubscribe link.

### 6.2 What a lesson never does

- Never quotes a verse that is not in the canon dataset.
- Never attributes to the teacher something that is not in a transcript.
- Never presents generated text as a quotation.
- Never exceeds roughly 400 words in the body. If the teacher's material is
  rich, the lesson links to it rather than growing.
- Never sends twice for the same day, and never skips a day silently. If
  delivery fails, the operator is told.

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
2. The learner receives a **welcome email** the same day: what will arrive,
   when, from whom, how to stop, and the first lesson's date.
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
whom, failures, new videos ingested, tokens used, and estimated spend for the
week and month to date. This is the primary operational surface in v1. There is
no dashboard.

### 8.5 New teacher content appears

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
| P0-11 | Welcome email | A newly added learner receives a welcome email before their first lesson. |

### P1 — should follow soon after

| ID | Requirement | Notes |
|---|---|---|
| P1-1 | Per-learner pace options: weekdays only, every other day | Schema supports it in v1; UI is a config field. |
| P1-2 | Second default pack: Srimad Bhagavatam as a "story" track | Requires a lesson type that is not verse-anchored. |
| P1-3 | Operator-triggered "resend today's lesson" and "skip to lesson N" | For recovery and testing. |
| P1-4 | Include the original Telugu passage alongside the English in "From the teacher" | Stored already; a rendering option. |
| P1-5 | Alternate translation choice per learner | Dataset has several; lesson names whichever is used. |

### P2 — design for, do not build

| ID | Requirement | Design constraint on v1 |
|---|---|---|
| P2-1 | Reply to a lesson and converse (the v2 agent) | Every lesson carries a stable lesson ID and thread reference in headers. Transcript chunks are retrievable by verse and by semantic query. |
| P2-2 | SMS and other channels | Delivery is a channel abstraction with one adapter. Lesson content is channel-neutral text with a rendering step. |
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
| **v1.1** | Additional learners added by the operator; P1 items as chosen | The service works for more than one person |
| **v2** | Reply-to-lesson conversation (ADK agent); self-serve signup; SMS; public announcement via Udaya's website | The service works for people who do not know the operator |

## 13. Glossary

| Term | Meaning |
|---|---|
| **Canon** | The Bhagavad Gita text and translations from the `gita/gita` dataset |
| **Pack** | A named set of one teacher's recordings plus their generated transcripts and translations |
| **Manifest** | The file in the repo that describes a pack by playlist and video IDs, without content |
| **Lesson** | One email: verse, meaning, teacher passage, question, footer |
| **Idea** | The unit of a lesson: one verse or a short run of verses forming one thought |
| **Learner** | A person receiving lessons |
| **Operator** | The person running a deployment and managing learners |
| **Ops digest** | The weekly operator email summarizing sends, failures, ingestion, and cost |
