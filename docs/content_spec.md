# Gita Agent — Content Specification (v1)

| | |
|---|---|
| **Status** | Draft for review |
| **Owner** | Udaya Pillalamarri |
| **Answers to** | `docs/product_spec.md` §6, §7, §8.1, §8.5, §9 (P0-5, P0-8, P0-9, P0-11, P0-12, P0-19 to P0-23, P0-26, P0-27) |
| **Date** | 2026-09-12 |

---

## 1. Purpose and scope

The product spec says what a lesson is and what it never does. This document
says where every word in a lesson comes from, how the content is prepared,
reviewed, and versioned, and what the fixed texts say. It is the contract
between the product spec and the technical spec: the technical spec builds
the machinery, this document defines the material the machinery handles.

Everything here is data, not code. The record shapes are given at the level
a reviewer needs to judge fidelity; exact storage schemas live in the
technical spec.

Out of scope: the v2 agent, channels other than email, any teacher other
than the default. Adding a teacher pack later means writing a manifest, not
changing this document.

## 2. The canon

### 2.1 Source and pin

| | |
|---|---|
| Repository | `github.com/gita/gita` |
| License | Unlicense (covers the compilation; see §2.5 for translator rights) |
| Pinned commit | `c6fce39595445768876ddbb8d1268a9c935e1d2b` (main, 2023-01-29) |
| Files used | `data/verse.json`, `data/chapters.json`, `data/authors.json`, `archive/translation_old.json` |
| Files **not** used | `data/translation.json` (machine-rewritten, §2.4), `data/commentary.json` (28 MB of modern commentaries with unclear rights; not needed by the lesson design) |

The pin is recorded in the canon store and named in every lesson's footer as
the canon version. Upgrading the pin is an operator action with a diff
(product spec §7.1).

### 2.2 The verse record

One record per verse, 701 in total across 18 chapters. Fields carried into
the canon store, verbatim from `verse.json`:

| Field | Content | Use in a lesson |
|---|---|---|
| `chapter_number`, `verse_number` | e.g. 2, 47 | "Where we are" line, footer |
| `text` | Devanagari, with the trailing verse marker `।।2.47।।` | Verse section, first line |
| `transliteration` | IAST-style, e.g. `karmaṇy-evādhikāras te mā phaleṣhu kadāchana` | Verse section, second line |
| `word_meanings` | word-by-word gloss, e.g. `karmaṇi—in prescribed duties; eva—only; …` | Long-form page (v1.1) and review appendix; not in the email |

The loader copies these fields without modification. It does not normalize
transliteration, does not strip the verse marker, and does not "fix"
anything. If a record looks wrong, the fix is an upstream issue or a
documented override in the pack, never a silent edit.

### 2.3 Chapters

From `chapters.json`, used for the "Where we are" line, the chapter-opening
paragraphs (§3.4), and lesson counts.

| Ch. | Verses | Name | Meaning |
|---|---|---|---|
| 1 | 47 | Arjuna Viṣāda Yoga | Arjuna's dilemma |
| 2 | 72 | Sāṅkhya Yoga | Transcendental knowledge |
| 3 | 43 | Karma Yoga | The path of selfless action |
| 4 | 42 | Jñāna Karma Sannyāsa Yoga | Knowledge and the disciplines of action |
| 5 | 29 | Karma Sannyāsa Yoga | The path of renunciation |
| 6 | 47 | Dhyāna Yoga | The path of meditation |
| 7 | 30 | Jñāna Vijñāna Yoga | Self-knowledge and realization |
| 8 | 28 | Akṣara Brahma Yoga | The imperishable absolute |
| 9 | 34 | Rāja Vidyā Yoga | The royal knowledge |
| 10 | 42 | Vibhūti Yoga | Divine glories |
| 11 | 55 | Viśvarūpa Darśana Yoga | The cosmic form |
| 12 | 20 | Bhakti Yoga | The yoga of devotion |
| 13 | 35 | Kṣetra Kṣetrajña Vibhāga Yoga | The field and the knower of the field |
| 14 | 27 | Guṇa Traya Vibhāga Yoga | The three qualities of nature |
| 15 | 20 | Puruṣottama Yoga | The supreme person |
| 16 | 24 | Daivāsura Sampad Vibhāga Yoga | Divine and undivine natures |
| 17 | 28 | Śraddhā Traya Vibhāga Yoga | The three kinds of faith |
| 18 | 78 | Mokṣa Sannyāsa Yoga | Liberation through renunciation |

The dataset's chapter names use a Hindi-influenced transliteration
(`Karm Yog`); the canon store keeps the dataset's spelling as the record and
lessons render the IAST form above, which is a fixed table in the pack, not
generated.

### 2.4 Translation records and the two files

The dataset ships two translation files. Only one is the translators' work.

- `data/translation.json` was rewritten in January 2023 by running every
  English entry through OpenAI `text-davinci-003` with a "fix grammar"
  prompt (`scripts/fix_grammar.py` in the repo). All 3,505 English entries
  changed. This file is never loaded.
- `archive/translation_old.json` holds the originals. This is the only
  translation source from the dataset.

**Loader rules for the originals**, and nothing else:

1. Keep only entries where `lang == "english"`.
2. Strip the leading verse-number prefix, which appears as `2.47 `, `2.47. `,
   or `2.47.  ` at the start of the text. The regular expression is
   `^\s*\d+\.\d+\.?\s*`.
3. Trim surrounding whitespace.
4. Store the result verbatim, including the translator's archaic forms
   (`thy`, `thou`) and the occasional typographical slip in the source (for
   example Gambirananda 18.66 reads "I sahll free you"). A slip is reported
   in the fidelity audit and handled as a pack override with a note; the
   canon record itself is not edited.

Each translation is its own record: verse, translator, source, source
version, text, and rights status. A lesson uses exactly one and names it.

### 2.5 Translators, sources, and rights

| Translator | Year | Where from | Style | Rights status | Use |
|---|---|---|---|---|---|
| Swami Sivananda | 1942 | `gita/gita` originals | Prose, some `thy`/`thou` | Very likely public domain in India (author d. 1963, India term life+60 ended 2024); US status not verified | **v1 default** (confirmed 2026-09-13) |
| Shri Purohit Swami | 1935 | `gita/gita` originals | Prose, `thou`, freer | Very likely public domain (author d. 1941) | Alternate |
| Swami Gambirananda | 1984 | `gita/gita` originals | Literal, scholarly | Advaita Ashrama; likely copyrighted | Review appendix only; never in a public lesson |
| Swami Adidevananda | c. 1990s | `gita/gita` originals | Ramanuja tradition | Sri Ramakrishna Math; likely copyrighted | Review appendix only |
| Dr. S. Sankaranarayan | 1985 | `gita/gita` originals | Literal, Abhinavagupta tradition | Likely copyrighted | Review appendix only |
| Annie Besant | 1895 (4th ed. 1922) | Wikisource, `Bhagavad-Gita (Besant 4th)` | Prose, `thy`/`thou`, close to the Sanskrit | Public domain; Wikisource transcription CC BY-SA | Leading candidate for v2 public use; decided in the v2 spec |
| K. T. Telang | 1882 | Wikisource, Sacred Books of the East vol. 8 | Prose with parenthetical glosses | Public domain; Wikisource transcription CC BY-SA | Candidate; heavier to read |
| Edwin Arnold | 1885 | Wikisource | Verse | Public domain | Not for lessons; verse form fights the "factual first" tone |

"Very likely" and "likely" are an engineer's reading, not a legal opinion.
Product spec open question 6 stays open until the v2 default has a
confirmed status. For v1, which is private, any of the eight may be used.

### 2.6 Side by side: the same three verses in five translations

Read these as a learner would. This is the material for choosing the
default. Sanskrit and transliteration are from the verse record.

**2.47** · *karmaṇy-evādhikāras te mā phaleṣhu kadāchana · mā karma-phala-hetur bhūr mā te saṅgo 'stvakarmaṇi*

| Translator | Text |
|---|---|
| Sivananda | Thy right is to work only, but never with its fruits; let not the fruits of action be thy motive, nor let thy attachment be to inaction. |
| Purohit Swami | But thou hast only the right to work, but none to the fruit thereof. Let not then the fruit of thy action be thy motive; nor yet be thou enamored of inaction. |
| Gambirananda | Your right is for action alone, never for the results. Do not become the agent of the results of action. May you not have any inclination for inaction. |
| Besant | Thy business is with the action only, never with its fruits; so let not the fruit of action be thy motive, nor be thou to inaction attached. |
| Telang | Your business is with action alone; not by any means with fruit. Let not the fruit of action be your motive (to action). Let not your attachment be (fixed) on inaction. |

**4.7** · *yadā yadā hi dharmasya glānir bhavati bhārata · abhyutthānam adharmasya tadātmānaṁ sṛijāmyaham*

| Translator | Text |
|---|---|
| Sivananda | Whenever there is decline of righteousness, O Arjuna, and rise of unrighteousness, then I manifest Myself. |
| Purohit Swami | Whenever spirituality decays and materialism is rampant, then, O Arjuna, I reincarnate Myself! |
| Gambirananda | O scion of the Bharata dynasty, whenever there is a decline one virtue and increase of vice, then do I manifest Myself. |
| Besant | Whenever there is decay of righteousness, O Bhârata, and there is exaltation of unrighteousness, then I Myself come forth; |
| Telang | Whensoever, O descendant of Bharata! piety languishes, and impiety is in the ascendant, I create myself. |

**18.66** · *sarva-dharmān parityajya mām ekaṁ śharaṇaṁ vraja · ahaṁ tvāṁ sarva-pāpebhyo mokṣhayiṣhyāmi mā śhuchaḥ*

| Translator | Text |
|---|---|
| Sivananda | Abandoning all duties, take refuge in Me alone: I will liberate thee from all sins; grieve not. |
| Purohit Swami | Give up then thy earthly duties, surrender thyself to Me only. Do not be anxious; I will absolve thee from all thy sin. |
| Gambirananda | Abandoning all forms of rites and duties, take refuge in Me alone. I sahll free you from all sins. (Therefore) do not grieve. |
| Besant | Abandoning all duties come unto Me alone for shelter; sorrow not, I will liberate thee from all sins. |
| Telang | Forsaking all duties, come to me as (your) sole refuge. I will release you from all sins. Be not grieved. |

**Observations, for the decision.**

- Sivananda and Besant are the closest to each other and to the Sanskrit,
  and both read as plain prose. Besant is public domain beyond doubt;
  Sivananda is very likely so in India.
- Purohit paraphrases ("spirituality decays and materialism is rampant" for
  *dharmasya glānih*), which is readable but is interpretation, and 6.2's
  "never asserts one interpretation" rule sits uneasily with it as a default.
- Gambirananda and Telang are the most literal and the hardest to read cold;
  they are excellent in the long form and the review appendix.
- Every translator except Gambirananda uses `thy`/`thou`. The lesson does
  not modernize any of them: the quotation is the quotation. "What it means"
  is where plain modern English lives.

**Decision (2026-09-13): Sivananda is the v1 default.** Confirmed by Udaya
after reading the three verses above. The v2 public-use default (product
spec open question 6) is deliberately **not decided now**: it will be made
when the v2 product spec is written, with v1 experience and reviewer
feedback in hand. Besant is the leading candidate for that decision because
it reads as well as Sivananda and carries no rights doubt; Sivananda stays
an alternate either way.

## 3. The lesson sequence

### 3.1 The unit

One idea per lesson: one verse, or a short run of consecutive verses that
form a single thought (product spec §6.3, open question 1 resolved).

### 3.2 Grouping rules

The sequence is produced once per pack version, not per send. Rules:

1. A lesson holds 1 to 3 consecutive verses. Four is allowed only where the
   verses are a single enumerated list that cannot be cut (for example the
   list of divine qualities in 16.1–3, or the long enumerations of chapter
   10), and every such exception is listed in the sequence file with a
   reason.
2. A lesson never crosses a chapter boundary.
3. A verse that is a question and the verse that answers it stay together
   when they are adjacent.
4. A speaker change (Sanjaya narrating, Arjuna asking, Krishna answering)
   is a natural cut. The dataset's Devanagari carries the speaker markers
   in the text where they occur.
5. Verses that only make sense in context, such as the second half of a
   sentence, are never a lesson on their own.
6. The lesson count is an outcome of rules 1 to 5, not a constraint on
   them. The rules are expected to produce roughly 350 to 400 lessons, and
   that expectation is used only as a sanity check: the validator reports
   the count and flags a chapter whose count looks far from expected for a
   human to look at. There is no programmatic cutoff, and no verse is ever
   merged into a neighbor to hit a number. If the text has 420 ideas, there
   are 420 lessons.

### 3.3 How the grouping is made and reviewed

- **Draft:** the model proposes the grouping for one chapter at a time,
  given the chapter's verses with translation and word meanings, the rules
  above, and the target. Output is a list of `[first_verse, last_verse,
  one-line reason]`.
- **Check:** a deterministic validator enforces rules 1 and 2, reports the
  count per chapter and in total against the rule 6 expectation without
  failing on it, and lists every group of size 3 or more for a human eye.
- **Review:** the operator reads every chapter's grouping once, in a single
  sitting per chapter, and edits by hand. This is a few hours of work for
  the whole Gita and it is done once. Reviewers (v1.1) can raise a grouping
  objection like any other feedback; the fix is a new sequence version.
- **Store:** `sequence.json` in the pack: an ordered list of lessons, each
  with a lesson index, chapter, first and last verse, and the reason. The
  file carries a version and a review status. Composition refuses an
  unreviewed sequence (P0-27).

### 3.4 Chapter openings and the "Where we are" line

**"Where we are"** is rendered, not generated: `Day {n} of about {total} ·
Chapter {c}, Verse {v}` or `Verses {v1}–{v2}`. `total` is the sequence
length. It is a position, never a percentage or a streak.

**Chapter openings** ("Where this sits") are eighteen short paragraphs, one
per chapter, plus one for lesson one that introduces the text itself: who is
speaking, to whom, where, and why. They are drafted by the model from the
chapter summary in `chapters.json` and the first lesson's verses, then
edited by the operator, stored in the pack as `chapter_openings.json`, and
versioned and reviewed like the sequence. Length: 60 to 120 words. Tone
rules and the banned-word list apply. They never quote a verse; the verse
follows immediately below.

## 4. Teacher content packs

### 4.1 Manifest

A pack is a directory in the repository under `packs/<pack_id>/` containing
`manifest.yaml` and the reviewed artifacts (`sequence.json`,
`chapter_openings.json`, `primer.md`). Generated content never lives here.

```yaml
pack_id: chaganti-gita-telugu
version: 1
teacher:
  name: Sri Chaganti Koteswara Rao
  honorific: Chaganti garu
  language: te
  channel: https://www.youtube.com/channel/UCqflEyvGNPkadoPNocTRQnQ
canon_pin: c6fce39595445768876ddbb8d1268a9c935e1d2b
default_translation: sivananda
sources:
  - id: gita
    type: youtube_playlist
    role: primary            # searched first for verse lessons
    order: 1
    playlist_id: PL2N6khFUCtEk6B47wtyt8uKNZCJcPX-St
    title: Bhagavad Gita by Sri Chaganti Koteswara Rao Garu
    expected_videos: 8
  - id: gita-bhakti-yogam
    type: youtube_playlist
    role: primary
    order: 2
    playlist_id: PL2N6khFUCtEk8jnkI9Qu24Rk6rVNqssKT
    title: Bhagavad Gita Bhakti Yogam by Sri Chaganti Koteswara Rao Garu
    expected_videos: 8
  - id: geeta-vaibhavam
    type: youtube_playlist
    role: primary
    order: 3
    playlist_id: PL2N6khFUCtElri2H32yFzqPdazXlZubza
    title: Geeta Vaibhavam by Sri Chaganti Koteswara Rao Garu
    expected_videos: 1
  - id: bhagavatam
    type: youtube_playlist
    role: secondary          # searched for verse lessons; drives the story track
    order: 4
    playlist_id: PL2N6khFUCtEmQiwvQve8wtTOBtJoPShF4
    title: Sampoorna Srimad Bhagavatam by Sri Chaganti Koteswara Rao Garu
    expected_videos: 40
rights_attestation: >
  I confirm that I have the right to use the content listed above for
  generating private study material delivered to learners I enroll, and I
  understand this service does not verify that right.
attested_by: Udaya Pillalamarri
attested_on: 2026-09-12
```

`expected_videos` is a sanity check for the weekly poll, not a limit: the
poll reports when a playlist grows or shrinks.

### 4.2 The rights warning, verbatim

Shown in the operator documentation and printed by the ingestion command
whenever a manifest is registered or its attestation changes. The wording is
fixed here so every surface says the same thing (product spec §7.2):

> This service does not verify your right to use the content you add. By
> adding it you confirm that you hold that right. Generated transcripts and
> lessons will be delivered to whoever you enroll, so treat this as
> publishing.

A manifest without `rights_attestation`, `attested_by`, and `attested_on`
is refused.

### 4.3 Ingestion: windows and the transcription contract

Each video is processed in **windows of 10 minutes with 30 seconds of
overlap** on each side, sent to the model directly from the YouTube URL
with start and end offsets. Ten minutes keeps each call well inside the
model's comfortable range for audio, keeps a failed window cheap to retry,
and gives the confidence signal enough granularity to be useful.

The model is asked for, in one call:

1. A verbatim **Telugu transcript** of the window, in Telugu script, with a
   `[mm:ss]` marker roughly every 30 seconds of speech, offsets relative to
   the video start.
2. A **faithful English translation**, paragraph by paragraph, keeping the
   same markers. Sanskrit verses and scriptural names are transliterated in
   IAST in italics and followed by their meaning in parentheses. No
   summarizing, no commentary, no omissions.
3. A **confidence** for the window: `high`, `medium`, or `low`, with a
   one-line reason when not high (noise, crosstalk, an unfamiliar quotation,
   a passage the model could not parse).
4. A list of **scripture references** the teacher makes in the window, as
   `text:chapter.verse` where identifiable (for example `gita:2.47`), or
   the name of the text when not.

The prompt is versioned. The prompt version is stored on every segment.
Translation instructions include: prefer plain equivalents over ornate ones;
do not add adjectives the teacher did not use; keep the teacher's own
similes and examples exactly; where the teacher code-switches into English,
keep the English words as spoken.

Overlap is resolved by keeping the segment whose window centre is nearer.

### 4.4 The segment record

One record per marker-delimited paragraph within a window:

| Field | Content |
|---|---|
| `pack_id`, `source_id`, `video_id` | Where it came from |
| `video_title`, `series_role` | For citation and retrieval preference |
| `start_s`, `end_s` | Offsets in seconds; the source link is `https://www.youtube.com/watch?v={video_id}&t={start_s}s` |
| `te` | Telugu text, verbatim |
| `en` | English translation, verbatim from the model output |
| `confidence` | `high` / `medium` / `low`, plus reason |
| `refs` | Scripture references detected in this segment |
| `model_id`, `prompt_version`, `ingested_at` | Provenance |

The store is the system of record. The vector index holds the English text
of each segment with its identifying fields as metadata and can be rebuilt
from the store at any time.

**Confidence handling.** `low` segments are stored and indexed but are never
selected for a lesson. `medium` segments may be selected; when one is, the
lesson is flagged in the ops digest so the operator can spot-check it.

### 4.5 Retrieval: how a verse finds its passage

For a verse lesson, the query is built from the lesson's verses: the
translation text, the transliteration, the key Sanskrit terms from the word
meanings, and the chapter name. Retrieval runs across the whole pack.

Selection, in order:

1. **Direct reference wins.** If any segment's `refs` contains a verse in the
   lesson, those segments are candidates first.
2. **Semantic match next.** Otherwise the top candidates by similarity, with
   a fixed **relevance threshold** below which nothing is selected. The
   threshold is a pack setting, tuned once on twenty hand-checked verses
   and recorded in the manifest.
3. **Series preference.** Among candidates above threshold, a `primary`
   series segment is preferred over a `secondary` one unless the secondary
   scores materially higher (a fixed margin, also a pack setting). This
   keeps the Gita discourses as the usual lens and lets the Bhagavatam speak
   when it clearly does.
4. **Adjacent segments** from the same video around the winner are pulled
   in so the passage has its full context; the passage is then 100 to 200
   words of English drawn from that span.
5. **Nothing above threshold, or only `low` confidence:** the lesson is sent
   canon-only, says so in one plain sentence in place of the teacher
   section, and is flagged (P0-11).

"From the teacher" is a **paraphrase** of the selected span, not a
quotation: the model condenses the translated span to 100 to 200 words in
the teacher's own line of thought, keeps the teacher's examples, and adds
nothing. The review appendix shows the span verbatim so the paraphrase can
be checked. The citation is the video title, the series, and the timestamped
link.

## 5. Lesson composition

### 5.1 Inputs and outputs

Inputs: the lesson's verse records and chosen translation, the chapter
opening if this is a chapter's first lesson, the selected transcript span
with its citation, the pack's tone rules and banned-word list, and the
learner's position.

Outputs: the three generated parts, each as a separate field, plus the
rendered lesson. Generated fields are the only fields the model writes.

### 5.2 Rules for the generated parts

| Part | Length | Must | Must not |
|---|---|---|---|
| Where this sits | 60–120 words (chapter openings only) | Come from the pack file, not generated per send | Appear on any other lesson |
| What it means | 2–4 sentences | Restate the translation and the teacher's point in plain modern English; define any Sanskrit term used | Add claims absent from both; quote; give advice; mention the learner |
| A question to carry | 1 sentence, a question | Follow from the verse or the teacher's point | Instruct; assume anything about the learner's life |

Every generated field passes the checks in §5.4 before the lesson is sent.

### 5.3 Prompt principles

The composition prompt is versioned and stored on the lesson. It states,
in this order: the fidelity rules from product spec §6.2 as instructions;
the tone rules from §6.4; the banned-word list; the exact material it may
use, labeled; and the output shape. It says explicitly that the model's own
knowledge of the Gita is not to be used and that "the teacher" means only
the passage supplied.

### 5.4 Pre-send validation

A lesson is composed, validated, and only then sent. Any failure blocks the
send and is reported to the operator with the lesson ID.

| Check | Rule |
|---|---|
| Structure | All required parts present in order; chapter opening present only where required |
| Verse fidelity | Devanagari, transliteration, and translation byte-identical to the canon store |
| Attribution | Teacher section, when present, carries video ID, timestamp, and a link, and the cited segment exists in the store with the cited offsets |
| Retrieval-only | If the teacher section is present, the selected span has confidence `high` or `medium` |
| Generated boundaries | Generated fields contain no straight or curly double quotation marks |
| Banned words | No banned word or phrase appears in any generated field, case-insensitive, whole-word |
| Length | Body under roughly 400 words; generated fields within their limits |
| Provenance | Model ID, prompt version, canon pin, pack version, sequence version present |
| Links | Only the source link, the reaction links, and the unsubscribe link; every non-source link is a signed first-party URL |

### 5.5 The banned-word list

Applied to generated text only. Whole words and phrases, case-insensitive,
including simple inflections (`journey`, `journeys`; `transform`,
`transformative`, `transformation`).

```
journey, unlock, empower, transform, embrace, mindful, mindfulness,
elevate, awaken, manifest, secret, powerful, profound, timeless,
ancient wisdom, life-changing, game-changer, unleash, harness,
tap into, dive deep, deep dive, at the end of the day, in today's world,
in our fast-paced lives, resonate, vibration, energy (in the spiritual
sense), authentic self, inner peace (as a promise), true self,
sacred journey, spiritual growth, level up, hack, superpower
```

The list is a pack file so it can grow from reviewer feedback without a
code change. Words in quoted translations and in the teacher's translated
passage are exempt: those are sources.

## 6. The story track (v1.1)

### 6.1 Episodes

The Bhagavatam series is segmented into **episodes** of roughly 8 to 15
minutes of discourse, cut at topic boundaries the model identifies from the
transcript (a new story, a new character, a return to the frame narrative).
Sixty-eight hours yields roughly 350 to 450 episodes. The episode list is a
pack artifact, `episodes.json`, drafted by the model per video, validated
for length, reviewed by the operator, versioned, and refused when
unreviewed, exactly like the verse sequence.

### 6.2 Template

A story lesson has four parts: **Where we are** (`Story {n} of about
{total} · Part {video_number}, {episode_title}`), **From the teacher** (a
150 to 250 word paraphrase of the episode span with the timestamped link),
**What it means** (2–4 sentences), **A question to carry**. No verse
section, because there is no Gita verse. All fidelity, tone, and validation
rules apply unchanged.

## 7. Fixed texts

These are content, not code. They live in the pack, carry a version, and
are reviewed. Drafts follow; Udaya edits them in place.

### 7.1 Welcome primer (draft)

> The Bhagavad Gita is one conversation inside a much larger body of
> writing. At the root are the Vedas, the oldest texts of the tradition,
> concerned mostly with ritual and the order of the world. Their closing
> portions, the Upanishads, turn inward and ask what the self is and what
> lasts. Much later comes the Mahabharata, an epic about a family at war
> with itself. On the eve of its great battle, the warrior Arjuna loses his
> nerve and asks his charioteer, Krishna, what he should do. Krishna's
> answer is the Gita: seven hundred verses that gather the Upanishads'
> questions into one exchange between a person in trouble and a teacher who
> will not let him look away.
>
> The tradition is vast and deep, and no one takes it in at once. This
> service walks one text slowly: one idea from the Gita each morning, in
> plain English, with the verse itself and a short passage from a teacher
> explaining it. Depth comes from the daily habit, not from any single
> lesson. Read it in five minutes, carry the question for the day, and let
> the rest go.

### 7.2 Welcome mechanics (template)

> You will receive one lesson each morning at {delivery_time}
> ({timezone}), from {operator_name} at this address. The first arrives on
> {first_lesson_date}. Each takes under five minutes to read. Every lesson
> has a link to the original recording and three small reactions at the
> bottom; use them or ignore them. To stop at any time, use the link at the
> foot of any lesson. Nothing else will ever be sent.

### 7.3 Reviewer welcome (v1.1, draft)

> {operator_name} has asked you to review daily Bhagavad Gita lessons for
> accuracy. Each morning you will receive the lesson exactly as a learner
> sees it, followed by the source material it was built from: the teacher's
> original Telugu passage, the English translation, the recording and
> timestamp, and the verse record. The teacher is {teacher_name}; the
> lessons draw on {series_list}.
>
> Your job is to judge whether the lesson is faithful to the verse and to
> the teacher, not whether you agree with the teacher. Each edition asks a
> few specific questions. Reply to the email with your answers or with
> anything else that is wrong. If you do not reply, we take it as no
> objection. To stop receiving these, use the link at the foot of any
> edition.

### 7.4 Reviewer banner and questions (v1.1)

Banner, above every review edition:

> You are receiving this as a reviewer. Below is the lesson exactly as a
> learner sees it, followed by the source material it was built from. If
> anything is unfaithful to the verse or to the teacher, reply to this
> email and say so. If it is fine, you need not reply. Pack: {pack_name}.
> Teacher: {teacher_name}.

Questions, after the appendix, each answerable with yes or no:

1. Is the passage under "From the teacher" a fair account of what the
   teacher says between {start} and {end} in "{video_title}"?
2. Does the English translation in the appendix match the Telugu above it?
3. Does "What it means" say anything the verse and the teacher do not?
4. Anything else?

### 7.5 Unsubscribe confirmation

> You will not receive further lessons. Your place in the sequence is kept
> in case you return; reply to this email if you would like to. Nothing
> else will be sent.

### 7.6 Correction note (template, v1.1)

> A correction to the lesson of {date}, {reference}: {one sentence stating
> what was wrong and what is right}. The source is {citation}. Nothing else
> in that lesson changes.

### 7.7 Reaction row and thank-you page

Labels: **Got it** · **Unclear** · **Loved it**. Thank-you page, one line:
"Noted, thank you." followed by an optional single-line box labeled "One
sentence more, if you like" and a Send button. Nothing else on the page.

## 8. Audit log and golden set

The audit log is one JSON record per line, in the repository under
`audit/`, keyed by lesson ID. It is the source of the golden set.

| Field | Content |
|---|---|
| `lesson_id` | The lesson's stable ID |
| `pack_version`, `sequence_version`, `canon_pin`, `model_id`, `prompt_version` | Copied from the lesson's provenance |
| `reviewer` | `operator` in v1.0; a reviewer handle in v1.1 |
| `kind` | `fidelity` / `translation` / `interpretive` / `confirmed_good` / `grouping` / `tone` |
| `claim` | What was said, in the reviewer's words |
| `part` | `verse` / `meaning` / `teacher` / `question` / `opening` |
| `source_checked` | What the operator looked at: transcript segment IDs, recording timestamp, canon record |
| `decision` | `corrected` / `rejected` / `logged` / `confirmed` |
| `correction` | The change made to the pack, if any, and the new pack version |
| `decided_by`, `decided_on` | Who and when |

A lesson enters the golden set when its record has `decision` of
`confirmed` or `corrected`. The golden set is a derived file, regenerated
from the log, never edited by hand.

## 9. Versioning and the correction flow

- **Canon pin** changes only by the operator's upgrade action with a diff.
- **Pack version** increments whenever any pack artifact changes: manifest,
  sequence, chapter openings, primer, banned-word list, episodes, thresholds.
- **Every lesson records** the canon pin and pack version it was composed
  from. A correction produces a new pack version; learners who have not yet
  reached the affected lesson receive the corrected version; learners who
  have receive, at most, a correction note.
- **Transcripts are never edited.** A translation correction adds an
  override record pointing at the segment, with the corrected English and
  the audit entry that justified it. The original model output stays in the
  store beside it.

## 10. Open questions

| # | Question | Who | Blocking? |
|---|---|---|---|
| C1 | ~~Default translation for v1?~~ **Resolved 2026-09-13: Sivananda.** The v2 public-use default is deferred to the v2 product spec (product spec open question 6); Besant is the leading candidate, Sivananda the alternate. | Udaya | Resolved for v1 |
| C2 | Chapter openings and the primer: Udaya edits the drafts in §3.4 and §7.1 before the first send? | Udaya | Yes, before day 1 |
| C3 | Relevance threshold and series-preference margin: tuned on which twenty verses? Proposal: the first lesson of each chapter plus 2.47 and 18.66. | Operator | No; set during phase 1 |
| C4 | Reaction labels: keep "Got it / Unclear / Loved it"? | Udaya | No |
