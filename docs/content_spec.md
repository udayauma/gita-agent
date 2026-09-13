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
| Files used | `data/verse.json` (verse records), `data/chapters.json` (names, verse counts, `chapter_summary` as input to the chapter-opening drafts), `data/authors.json`, `archive/translation_old.json` |
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

**Chapter 13 numbering.** The dataset numbers chapter 13 as verses 1 to 35,
where standard 700-verse editions number the same text 0 to 34 (the extra
opening verse, *prakṛtiṁ puruṣaṁ caiva*, is verse 0 or omitted). The
canon store keeps the dataset's numbering. Two consequences: the "Where we
are" line for chapter 13 shows the dataset's numbers, and when a teacher
cites a chapter-13 verse, the reference resolver (§4.3, §4.5) tries both
`n` and `n+1` and lets the semantic match decide. The technical spec
carries the mapping table.

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
- **Review:** the operator reads a chapter's grouping in one sitting and
  edits by hand. In v1 this is Udaya. Review status is **per chapter**, and
  composition requires only that the chapter of the next lesson is
  reviewed, so the operator reviews ahead of the learner rather than the
  whole Gita up front: chapters 1 and 2 before day one, then a chapter
  ahead. The whole text is a few hours of review in total, spread over the
  first weeks.
- **It is not frozen.** A reviewer's grouping objection (v1.1), or the
  operator's own second thoughts after living with a chapter, produces a
  new sequence version. Because a learner's position is the last verse
  delivered (§3.4), a regrouping never skips or repeats a verse for anyone
  part-way through.
- **It ships with the repository.** The sequence, the chapter openings, and
  the primer for the default pack are derived from the public-domain canon
  and written by the operator, not from the teacher's content, so they are
  committed under `packs/<pack_id>/`. A self-hosting operator inherits the
  reviewed sequence and does not redo the review.
- **Store:** `sequence.json` in the pack: an ordered list of lessons, each
  with a lesson index, chapter, first and last verse, and the reason; a
  file version; and a review status per chapter with the reviewer and
  date. Composition refuses a lesson whose chapter is unreviewed (P0-27).

### 3.4 Chapter openings and the "Where we are" line

**"Where we are"** is rendered, not generated: `Day {n} of about {total} ·
Chapter {c}, Verse {v}` or `Verses {v1}–{v2}`. `total` is the sequence
length. It is a position, never a percentage or a streak.

**The sequence is shared; the position is per learner.** One sequence exists
per pack version and every learner on that pack walks the same one. What is
stored per learner (product spec P0-2, P0-5) is:

- the pack and sequence version they are currently on;
- the **last verse delivered** (chapter and verse), which is the position of
  record;
- the lesson index and the day count, derived from the two above and stored
  for convenience;
- the date of the last successful send, so a failed day does not advance;
- for the story track (v1.1), the last episode delivered, separately.

The next lesson for a learner is the first lesson in the current sequence
whose first verse comes after the learner's last delivered verse. Storing
the position as a verse rather than as an index is deliberate: if a
correction produces a new sequence version that regroups verses, a learner
part-way through resumes at the next verse they have not seen, and never
skips or repeats one. The day count shown in "Where we are" continues from
the learner's own count; it is not recomputed from the new sequence.

**Chapter openings** ("Where this sits") are eighteen short paragraphs, one
per chapter, plus one for lesson one that introduces the text itself: who is
speaking, to whom, where, and why. They are drafted by the model from the
chapter summary in `chapters.json` and the first lesson's verses, then
edited by the operator, stored in the pack as `chapter_openings.json`, and
versioned and reviewed like the sequence. Length guidance: 60 to 120
words, a soft bound (§5.2). Tone rules and the banned-word list apply. They never quote a verse; the verse
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
prompts:                    # versioned files under packs/<pack_id>/prompts/
  transcribe: transcribe_v1.txt
  paraphrase: paraphrase_v1.txt
  compose: compose_v1.txt
settings:                   # tuned in phase 1 on hand-checked samples; see §4.4, §4.5
  window_seconds: 600
  overlap_seconds: 30
  confidence:
    overlap_agreement_floor: null      # below this: low
    overlap_agreement_ceiling: null    # below this: medium
    tuned_on: null                     # date and video ID
  retrieval:
    relevance_threshold: null
    primary_over_secondary_margin: null
    neighbor_before_seconds: 60
    neighbor_after_seconds: 120
    tuned_on: null                     # date and the twenty verses used
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

The prompt is versioned (`transcribe_v1.txt` in the pack's `prompts/`
directory) and the version is stored on every segment.
Translation instructions include: prefer plain equivalents over ornate ones;
do not add adjectives the teacher did not use; keep the teacher's own
similes and examples exactly; where the teacher code-switches into English,
keep the English words as spoken.

The 30-second overlap is used twice. First, the two independent
transcriptions of the same audio are compared for agreement, which feeds
the confidence grade (§4.4). Then the duplicate is resolved by keeping the
segment whose window centre is nearer, so no passage is stored twice.

### 4.4 The segment record

One record per marker-delimited paragraph within a window:

| Field | Content |
|---|---|
| `pack_id`, `source_id`, `video_id` | Where it came from |
| `video_title`, `series_role` | For citation and retrieval preference |
| `start_s`, `end_s` | Offsets in seconds; the source link is `https://www.youtube.com/watch?v={video_id}&t={start_s}s` |
| `te` | Telugu text, verbatim |
| `en` | English translation, verbatim from the model output |
| `confidence` | `high` / `medium` / `low`, the minimum across the signals below, plus the individual signal values and the model's stated reason |
| `refs` | Scripture references detected in this segment |
| `model_id`, `prompt_version`, `ingested_at` | Provenance |

The store is the system of record. The vector index holds the English text
of each segment with its identifying fields as metadata and can be rebuilt
from the store at any time.

**How confidence is assigned.** The model's self-reported confidence (§4.3
item 3) is the starting point, never the whole answer, because models are
poorly calibrated about their own transcription. It is combined with
deterministic checks, and the strongest of those uses the window overlap:

| Signal | What it measures | Effect |
|---|---|---|
| Overlap agreement | The 30-second overlap between windows is transcribed twice, independently. Similarity of the two Telugu texts (character-level) and of the two English texts is computed for the overlapping region. This is the one objective measure of transcription stability we have. | Below a fixed floor: the affected segments are capped at `low`. Between floor and ceiling: capped at `medium`. |
| Parse integrity | Markers present and monotonic; Telugu and English sections both present; segment count roughly matches speech duration | Any failure: `low` for the whole window |
| Script check | Fraction of characters in the Telugu section that are Telugu script (code-switched English words are expected and allowed) | Far outside the expected range: `low` |
| Length ratio | English word count against Telugu character count, per segment, compared with the pack's running median | Far outside the range: `medium` at most |
| Degeneration | Repeated phrases, truncated output, or a window shorter than expected | `low` |
| Model self-report | `high` / `medium` / `low` with reason | Can only lower the result, never raise it above what the checks allow |

The final grade is the **minimum** across the signals. Thresholds are pack
settings, set once on the first ingested video by hand-checking twenty
segments of each grade, and recorded in the manifest with the date. The
individual signal values are stored on the segment alongside the grade so
that a reviewer or the ops digest can see why a segment was graded as it
was.

**Confidence handling.** `low` segments are stored and indexed but are never
selected for a lesson. `medium` segments may be selected; when one is, the
lesson is flagged in the ops digest so the operator can spot-check it. The
ops digest also reports the grade distribution per video, so a video that
transcribed badly, say because of poor audio, is visible as a whole.

### 4.5 Retrieval: how a verse finds its passage

**A worked example first: verse 2.47.** The lesson is 2.47 alone, "Thy right
is to work only, but never with its fruits." Retrieval does the following:

1. Looks for any segment in the pack whose `refs` contains `gita:2.47`.
   Suppose three exist: two in "Bhagavad Gita part 2" at 41:10 and 42:05,
   where the teacher recites the verse and explains it, and one in
   "Bhagavatam part 17" at 12:30, where he quotes it in passing while
   telling a story. All three are candidates, and they come first.
2. Builds a query from the verse: the Sivananda translation, the
   transliteration, and the key terms from the word meanings (*karma*,
   *phala*, *saṅga*, *akarma*), plus the chapter name. Runs it against the
   English text of every segment in the pack. Suppose it returns, above the
   threshold, the two Gita segments again, a segment from "Bhagavad Gita
   part 3" at 08:40 on attachment to results, and a Bhagavatam segment on
   Karna's duty that scores just above threshold.
3. Applies series preference. The Gita segments are `primary`, the
   Bhagavatam ones `secondary`. Unless a Bhagavatam segment beats the best
   Gita segment by the configured margin, the Gita wins. Here the 41:10
   segment wins: it has a direct reference and the highest similarity.
4. Pulls in the adjacent segments from the same video around 41:10, say
   40:30 to 43:00, so the passage is the teacher's full thought, not a
   fragment.
5. Hands that span, roughly 400 words of English, to composition, which
   paraphrases it to 100 to 200 words and cites "Bhagavad Gita part 2,
   41:10" with the timestamped link. The review appendix shows the span
   verbatim, Telugu and English.

If step 1 finds nothing and step 2 returns nothing above threshold, or only
`low`-confidence segments, the lesson goes out canon-only, with one plain
sentence where the teacher section would be, and the operator is flagged.
Every step above, including what was rejected and why, is written to the
lesson's composition trace (§4.6), so a canon-only morning can be explained
without guesswork.

The rules below are the general form of this example. They are a starting
point: the threshold and the preference margin are tuned in phase 1 on
twenty hand-checked verses (open question C3), and reviewer feedback in
v1.1 is what tells us whether the selection is right.

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
   in so the passage has its full context. This step is **positional, not
   semantic**: the segments immediately before and after the winner by
   timestamp are read from the store, because a teacher's thought runs
   across marker boundaries in time. Two bounds apply: a time window of
   roughly one minute before and two minutes after the winner, and a soft
   on-topic check that drops a neighbor whose similarity to the query falls
   far below the winner's, so a story that begins mid-window is not dragged
   in. The passage is then 100 to 200 words of English drawn from that span.
5. **Nothing above threshold, or only `low` confidence:** the lesson is sent
   canon-only, says so in one plain sentence in place of the teacher
   section, and is flagged (P0-11).

"From the teacher" is a **paraphrase** of the selected span, not a
quotation: the model condenses the translated span to 100 to 200 words in
the teacher's own line of thought, keeps the teacher's examples, and adds
nothing. The review appendix shows the span verbatim so the paraphrase can
be checked. The citation is the video title, the series, and the timestamped
link.

### 4.6 The composition trace

Every lesson, whether or not it has a teacher section, stores a
**composition trace** alongside its record. It is the debugging record for
"why did this lesson look like this," and it is distinct from the audit log
(§8), which records human judgments.

The trace holds:

| Item | Content |
|---|---|
| Query | The text and terms retrieval was run with, and the lesson's verses |
| Settings in force | Relevance threshold, series-preference margin, neighbor window, and the manifest version they came from |
| Candidates | Every segment considered: those with a direct reference, and every semantic match above the threshold plus the next few below it. For each: segment ID, video, timestamp, series role, similarity score, confidence grade with its signal values, and the **rule that accepted or rejected it** (`direct_ref`, `above_threshold`, `below_threshold`, `low_confidence`, `secondary_lost_margin`, `neighbor_off_topic`) |
| Selection | The winning segment, the neighbor span actually used, and the paraphrase's returned segment IDs |
| Outcome | `teacher_section` or `canon_only`, and for canon-only a single reason code: `no_candidates`, `all_below_threshold`, `all_low_confidence`, `paraphrase_failed_validation` |
| Provenance | Model ID and prompt versions for retrieval embedding, paraphrase, and composition |

**Low-confidence segments are never discarded.** They stay in the store and
the index, and they appear in the trace as candidates rejected for
`low_confidence` with their scores intact. That is how the operator can
tell "the teacher did not speak to this verse" apart from "he did, and the
transcription of that window was poor," which have different fixes.

**How the operator sees it.**

- An operator command prints the trace for any lesson ID in readable form.
- The ops digest lists every canon-only lesson of the week with its reason
  code, and the per-video confidence distribution (§4.4), so a pattern such
  as one badly recorded video is visible without digging.
- Every `medium`-confidence selection is listed in the digest for
  spot-checking.

**The fix path.** When a trace shows the right segment was rejected for
confidence, the remedy is to re-ingest that window, or that video, with the
current model and prompt. Re-ingestion writes new segments with a new grade
and provenance; the old ones are kept, marked superseded, and the next
lesson that touches the verse shows in its trace whether the fix worked.
Re-ingestion is an operator action and is idempotent per window.

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
| Where this sits | Guidance: 60–120 words (chapter openings only). Soft bound; see note below | Come from the pack file, not generated per send | Appear on any other lesson |
| What it means | 2–4 sentences | Restate the translation and the teacher's point in plain modern English; define any Sanskrit term used | Add claims absent from both; quote; give advice; mention the learner |
| A question to carry | 1 sentence, a question | Follow from the verse or the teacher's point | Instruct; assume anything about the learner's life |

"From the teacher" is not in this table because it is not generated in the
fidelity sense: it is the selected span **condensed** by a separate
paraphrase step whose only input is the span (§4.5, Appendix A). Its rules
are: 100 to 200 words, the teacher's own line of thought, his examples and
similes kept, nothing added, and the segment IDs it drew from returned so
the validator can confirm every one exists in the store. The review
appendix shows the span verbatim so the condensation can be checked.

Every generated field passes the checks in §5.4 before the lesson is sent.

**Soft bounds for reviewed content, hard bounds for per-send content.** The
chapter openings and the primer are drafted once, edited by the operator,
and marked reviewed; a human has already judged them. For those, the length
figures are guidance for the draft, and the validator only *warns* when one
runs long. It never blocks a reviewed artifact on length. "What it means"
and "A question to carry" are generated at send time with no human in
between, so their bounds are hard and the validator is their only reviewer.

### 5.3 Prompt principles

The composition prompt is versioned and stored on the lesson. It states,
in this order: the fidelity rules from product spec §6.2 as instructions;
the tone rules from §6.4; the banned-word list; the exact material it may
use, labeled; and the output shape. It says explicitly that the model's own
knowledge of the Gita is not to be used and that "the teacher" means only
the passage supplied. The v1 draft is Appendix A.

Three design choices in the prompt: composition never writes the teacher
section, which is a separate paraphrase step whose only input is the
selected span, so model knowledge cannot blend into the teacher's voice;
the verse block is supplied so the model can restate it, but the rendered
lesson takes the verse from the store, never from model output; and the
prompt is a file in the pack, so a wording change is a reviewed change
with a new prompt version on every lesson it produces.

**Prompt maintenance as models improve.** A prompt holds two kinds of
instruction and they age differently:

- **Constraints** say what must never happen: no model knowledge in the
  teacher section, no quoting, no advice, no generated Sanskrit, no banned
  words. These are policy. They do not cap the model's intelligence; they
  define the job, and they stay regardless of how capable the model is.
  Their enforcement lives in the validator (§5.4), not in prompt
  verbosity, so the prompt never has to be defensive.
- **Guidance** says how to do the job well: sentence length, ordering,
  phrasing hints. This is where over-specification hurts. A more capable
  model does better with the goal, the reason behind each rule, and the
  material than with step-by-step direction, and stale guidance can hold
  it below what it could do.

The policy: keep constraints, prune guidance, and let the evals decide.
Each guidance line in the prompt is a candidate for removal on every model
change: remove it, rerun the golden set, and if nothing regresses it stays
removed. Prefer stating the *reason* for a rule over adding more rules,
because models generalize from reasons. Prefer one or two examples of a
good "What it means" over a paragraph describing one. The prompt version
records what was pruned and when, so a regression can be traced to a
removed line.

### 5.4 Pre-send validation

A lesson is composed, validated, and only then sent. Any failure blocks the
send and is reported to the operator with the lesson ID.

| Check | Rule |
|---|---|
| Structure | All required parts present in order; chapter opening present only where required |
| Verse fidelity | Devanagari, transliteration, and translation byte-identical to the canon store |
| Attribution | Teacher section, when present, carries video ID, timestamp, and a link, and the cited segment exists in the store with the cited offsets |
| Retrieval-only | If the teacher section is present, the selected span has confidence `high` or `medium`, and every segment ID the paraphrase cites exists in the store within the selected span |
| Trace present | The composition trace (§4.6) is stored with the lesson and records an outcome and, for canon-only, a reason code |
| Generated boundaries | Generated fields contain no straight or curly double quotation marks |
| Banned words | No **hard-tier** banned word appears in any generated field after up to two regenerations (§5.5). Soft-tier hits are logged, never block. |
| Length | Per-send generated fields within their hard limits; body under roughly 400 words. Reviewed artifacts (chapter openings) only warn on length, never block |
| Provenance | Model ID, prompt version, canon pin, pack version, sequence version present |
| Links | Only the source link, the reaction links, and the unsubscribe link; every non-source link is a signed first-party URL |

### 5.5 The banned-word list

**Why a list exists.** The product spec's tone rule (§6.4) is "factual
first, plain, warm, unhurried, never preaching." A rule like that cannot be
tested; a judgment call on every lesson is exactly what a pre-send check
cannot make. But the failure has a recognizable signature. When a model is
asked to be warm and encouraging, it reaches for a small, predictable
vocabulary, and each of those words carries a claim the lesson must not
make: that the learner is being guided somewhere (*journey*), that a secret
is being revealed (*unlock*, *secret*), that transformation is on offer
(*transform*, *awaken*, *empower*), that the text is being sold (*ancient
wisdom*, *timeless*, *powerful*). The same vocabulary is the register of
the social-media Gita quotes the product exists to be an alternative to.

So the list is the tone rule made testable: a one-line, deterministic
check that catches the most common way the tone drifts, applied to the
only text the model writes freely. It does not make a lesson good. It
stops the most recognizable way a lesson goes bad, cheaply, before it is
sent. Everything subtler is what reviewers and reactions are for.

**How it is applied.** Generated text only: "Where this sits," "What it
means," "A question to carry," and the story-track equivalents. Whole
words and phrases, case-insensitive, including simple inflections
(`journey`, `journeys`; `transform`, `transformative`, `transformation`).

**Two tiers, so the list does not gate lessons it should not.**

| Tier | What is in it | On a hit |
|---|---|---|
| **Hard** | Words that carry a claim the lesson must never make: `unlock`, `secret`, `transform` (and inflections), `awaken`, `manifest`, `empower`, `journey`, `ancient wisdom`, `life-changing`, `unleash` | Regenerate (below). Blocks only if regeneration fails. |
| **Soft** | Everything else on the list: the vague-register words and the filler phrases | Never blocks. Logged on the lesson, counted in the ops digest per word, reviewed when a word keeps appearing. |

Reviewer feedback in v1.1 can promote a soft word to hard or demote a hard
one; either is a pack version bump with the audit entry that justified it.

**Regenerate before refusing.** A hard hit does not block the send by
itself. Composition is retried, up to two more times, with the offending
words named: "your draft used *X*; rewrite the same content without it."
The model was never attached to the word, so the first retry almost always
succeeds. Each attempt and its hits are recorded in the composition trace
(§4.6). Only if the third attempt still contains a hard word does the
lesson take the ordinary failure path: it is not sent, the operator is
notified the same day with the words and the drafts, the learner's
progress does not advance, and the same lesson is composed again tomorrow.
That is the fidelity-over-completeness rule applied honestly, and with
regeneration in front of it the gate should almost never close. The ops
digest reports how many lessons needed a retry and how many were blocked,
so if the list is too aggressive it shows up as a number, not a feeling.

```
HARD:  journey, unlock, empower, transform, awaken, manifest, secret,
       ancient wisdom, life-changing, unleash
SOFT:  embrace, mindful, mindfulness, elevate, powerful, profound,
       timeless, game-changer, harness, tap into, dive deep, deep dive,
       at the end of the day, in today's world, in our fast-paced lives,
       resonate, vibration, energy (in the spiritual sense),
       authentic self, inner peace (as a promise), true self,
       sacred journey, spiritual growth, level up, hack, superpower
```

**Why these words and not others.** The seed list came from the product
spec (§6.4) and was extended with phrases that mark the same register:
self-help framing (*level up*, *hack*, *superpower*, *game-changer*),
vague spiritual promise (*inner peace* as a promise, *authentic self*,
*resonate*, *energy* in the spiritual sense), and filler openers (*at the
end of the day*, *in today's world*, *in our fast-paced lives*). It is
deliberately a list of words that are common in that register and rare in
an honest restatement of a verse. A word that is ordinary English in this
context, such as *action* or *duty*, never goes on it, however often it
appears in bad copy.

**How it changes.** The list is a pack file so it can grow from reviewer
feedback and from reading lessons, without a code change. Adding a word is
a pack version bump. Removing one is the same, and the prompt-maintenance
policy (§5.3) applies: if a more capable model never reaches for a word,
the word can come off the list after a golden-set run shows no regression.

**What is exempt.** Words in quoted translations and in the teacher's
translated passage are exempt: those are sources, and a source is never
edited to satisfy a style rule. If the translation step introduces one of
these words where the teacher used a plain one, that is a translation
quality issue for the audit, not a banned-word hit.

## 6. The story track (v1.1)

### 6.1 Episodes

The Bhagavatam series is segmented into **episodes**, cut at topic
boundaries the model identifies from the transcript: a new story, a new
character, a return to the frame narrative, a shift from narration to
teaching. The unit is one story or one teaching, the way the unit of a
verse lesson is one idea (§3.1).

**Length is guidance, count is an outcome.** An episode is expected to run
about 8 to 15 minutes of discourse, and sixty-eight hours is expected to
yield somewhere around 350 to 450 episodes. Neither figure is a limit. A
story that takes twenty-five minutes is one episode; a teaching that takes
four is one episode. The validator reports episode lengths and the count
per video and flags outliers for a human eye; it never fails on either, and
no boundary is ever moved to hit a number. If the series has 600 stories,
there are 600 episodes. This is the same rule as the verse sequence
(§3.2 rule 6) and the same soft-bound treatment as other reviewed artifacts
(§5.2).

The episode list is a pack artifact, `episodes.json`, drafted by the model
per video, reviewed by the operator per video, versioned, and refused when
its video is unreviewed, exactly like the verse sequence. Review is ahead of
the learner: the first few videos before the story track is switched on,
then a video ahead.

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

### 7.0 Knowledge of Hinduism: a reference for the primer and the chapter openings

This section is background, codified so that the primer, the chapter
openings, and the operator's own understanding rest on the same account.
It is **not** a source for generated lesson text: "What it means" and the
question draw only on the verse and the teacher (§5.3). It is a source for
the operator when drafting and reviewing pack artifacts, and for the
reviewer when judging whether an opening paragraph is sound.

Provenance is marked. Statements marked **[T]** are what the default
teacher, Sri Chaganti Koteswara Rao, says in "Sampoorna Srimad Bhagavatam
part 1" (video `GAC7WRgkXfc`, roughly 2:00 to 7:30), as transcribed and
translated in the 2026-09-12 probe. Everything else is general scholarship
and the tradition's own self-description.

**The Vedas.** Four collections of Sanskrit, composed roughly 1500 to 500
BCE and transmitted orally with exceptional exactness before being written.
The tradition calls them *śruti*, "what was heard": revealed to seers, not
authored, and therefore the highest authority in Hinduism. Everything else,
including the Gita, is *smṛti*, "what is remembered," and answers to them.
**[T]** Sage Vyāsa divided the one mass of Vedic knowledge into four, seeing
that people of this age, short-lived and distracted by wealth and desire,
could not study the whole.

| Veda | What it holds | Who used it |
|---|---|---|
| Ṛgveda | 1,028 hymns of praise and invocation: to Agni, the fire that carries offerings to the gods; to Indra, Soma, Varuṇa and others. The oldest layer. Alongside the praise are hymns that ask the largest questions, such as the Nāsadīya hymn on whether even the gods know how the world began, and the Puruṣa hymn on the cosmos as one being. | The *hotṛ*, who recites |
| Sāmaveda | The same hymns set to melody for singing at the sacrifice | The *udgātṛ*, who sings |
| Yajurveda | The prose formulas spoken while the rites are performed | The *adhvaryu*, who performs |
| Atharvaveda | Hymns for daily life: healing, protection, marriage, the household; also speculative hymns | The *brahman* priest, who oversees |

**The four layers in each Veda.** Every Veda grows through four kinds of
text, in this order: *Saṃhitā* (the hymns themselves), *Brāhmaṇa*
(explanation of the rites), *Āraṇyaka* (the "forest" texts that read the
rites symbolically), and *Upaniṣad* (philosophy). So the Upanishads are not
a separate body of writing. They are the end of the Veda, which is what
*Vedānta* means.

**The two halves.** The tradition divides the whole into *karma-kāṇḍa*,
the portion on action and rite, and *jñāna-kāṇḍa*, the portion on
knowledge. **[T]** The teacher calls these the *pūrva bhāga*, the former
part, which explains the rites and procedures and the worldly and heavenly
rewards they bring, and the *uttara bhāga*, the latter part, which explains
the knowledge by which one need not enter a womb again: *jñānāt kevala
kaivalyam*, liberation through knowledge alone. **[T]** Through his
disciple Jaimini, Vyāsa had the former part systematized as *Pūrva
Mīmāṃsā*; he himself composed the *Brahma Sūtras*, the *Uttara Mīmāṃsā*, on
the latter.

**What the Vedas are about.** Three things held together: the relationship
between people, the gods, and the cosmos, maintained through *yajña*, the
fire sacrifice, with Agni as go-between; *ṛta*, the order that keeps the
cosmos, the seasons, and right conduct aligned, which the sacrifice sustains
and which later becomes *dharma*; and a growing set of questions about
origins, the one behind the many, and the power in the sacred word,
*brahman*, which the Upanishads take up as the ground of everything.

**The Upanishads.** The philosophical core: what the self (*ātman*) is,
what *brahman* is, and the teaching that they are not two. The oldest
dozen or so are the ones the Gita draws on most.

**Itihāsa and Purāṇa: the stories.** *Itihāsa*, "thus it was," names the
two epics, the *Rāmāyaṇa* and the *Mahābhārata*. The *Purāṇas*, "the
ancient," are the eighteen great narrative scriptures. **[T]** Vyāsa
composed the eighteen Purāṇas, and a Purāṇa must have five marks: *sarga*
(primary creation), *pratisarga* (secondary creation), *vaṃśa* (lineages),
*manvantara* (the ages of the Manus), and *vaṃśānucarita* (the history of
the lineages). **[T]** The elders gave a mnemonic for the eighteen:
*ma-dvayaṃ bha-dvayaṃ caiva bra-trayaṃ va-catuṣṭayam, a-nā-pa-liṅga-kū-skāni
purāṇāni pṛthak pṛthak*: two beginning with *Ma* (Mārkaṇḍeya, Matsya), two
with *Bha* (Bhāgavata, Bhaviṣya), three with *Bra* (Brahma, Brahmāṇḍa,
Brahmavaivarta), four with *Va* (Varāha, Viṣṇu, Vāmana, Vāyu), and then one
each for *A* (Agni), *Nā* (Nārada), *Pa* (Padma), *Liṅga*, *Ga* (Garuḍa),
*Kū* (Kūrma), *Ska* (Skanda). **[T]** The Bhāgavata, the teacher says,
stands apart from the other Purāṇas on a higher pedestal. It is the text of
the story track (§6).

**Where the Gita sits.** Inside the *Mahābhārata*, in the *Bhīṣma Parva*,
as the conversation between Arjuna and Krishna on the morning the war
begins: eighteen chapters, seven hundred verses. With the Upanishads and
the *Brahma Sūtras* it forms the *prasthāna-trayī*, the three foundations
on which every major school of Vedānta wrote its commentary. That is why
so many translators and commentators exist for it and why a lesson must
name which one it is using.

**What the Gita teaches, and why a lesson every day.** Arjuna's crisis is
concrete: family on both sides of the field, a duty he cannot see how to
carry out, fear, and grief, all on one morning. He is not a renunciant; he
is a person in the middle of his life who has to act and cannot see the
outcome. Krishna's answer runs through the whole text: act, because action
is unavoidable, but act without clinging to the result (*karma yoga*);
learn to tell the lasting from the passing (*jñāna*); hold steady in gain
and loss, praise and blame (*samatva*); and give the whole of it to
something larger than yourself (*bhakti*). It is a teaching about how to
work, how to hold relationships and obligations, how to meet difficulty,
and how to keep one's footing, addressed to someone who has to get up
tomorrow and do it again. That is why it is read a little at a time, every
day, rather than once. The daily lesson is not a summary of the Gita; it is
the Gita's own method.

### 7.1 Welcome primer (draft)

The welcome email opens with a one-line greeting, then the primer, then
the mechanics (§7.2). The greeting uses the learner's name when the
operator supplied one and plain "Welcome" when not. `{service_name}` is
the display name of the service as learners see it, a pack setting (open
question C5); it is not the repository name.

> {name}, welcome. Starting {first_lesson_date}, one short lesson from the
> Bhagavad Gita will arrive here each morning from {service_name}. Here is
> where it comes from, and why a little each day.
>
> The Bhagavad Gita is one conversation inside the much larger body of
> Hindu scripture. At the root are the four Vedas, the oldest texts of
> Hinduism, held to be heard by seers rather than composed: hymns of praise
> to the gods, the words and melodies of the fire sacrifice that kept the
> world in order, and, growing out of them, the first great questions about
> where everything comes from and what holds it together. Their closing
> portions, the Upanishads, turn those questions inward and ask what the
> self is and what lasts. Much later comes the Mahabharata, an epic about a family
> at war with itself. On the eve of its great battle, the warrior Arjuna
> loses his nerve and asks his charioteer, Krishna, what he should do.
> Krishna's answer is the Gita: seven hundred verses that gather the
> Upanishads' questions into one exchange between a person in trouble and a
> teacher who will not let him look away.
>
> Arjuna is not a monk. He has family on both sides of the field, a duty
> he cannot see how to carry out, fear, and grief, all at once, and he
> still has to act. That is why the Gita is read by people in the middle
> of their lives: it is about how to work without clinging to results, how
> to hold obligations and relationships, how to meet difficulty, and how to
> keep one's footing, told to someone who has to get up tomorrow and do it
> again.
>
> Hinduism, which its own texts call Sanātana Dharma, the enduring way, is
> vast and deep, and no one takes it in at once. These lessons walk one
> text slowly: one idea from the Gita each morning, in plain English, with
> the verse itself, a short passage explaining it, and a link to where that
> explanation came from. Depth comes from the daily habit, not from any
> single lesson, which is also how the Gita itself asks to be practised.
> Read it in five minutes, carry the question for the day, and let the
> rest go.

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

### 7.8 Subject lines

Subject lines carry information, not a slogan, so a learner can find a
lesson later. `{service_name}` is the pack setting, provisionally
"Today's Gita" (C5). *Gita* is used as the short form throughout;
*Bhagavad* alone is an adjective and is never used on its own.

| Message | Subject |
|---|---|
| Daily verse lesson | `{service_name}: Day {n} · Chapter {c}, Verse {v}` (or `Verses {v1}–{v2}`) |
| Story-track lesson (v1.1) | `{service_name}, stories: {n} · {episode_title}` |
| Welcome | `Welcome to {service_name}` |
| Review edition (v1.1) | `[Review] {service_name}: Day {n} · Chapter {c}, Verse {v}` |
| Reviewer welcome (v1.1) | `Reviewing {service_name}: what to expect` |
| Correction note (v1.1) | `{service_name}: a correction to Day {n}` |
| Unsubscribe confirmation | `{service_name}: you have been unsubscribed` |
| Ops digest | `{service_name} ops digest, week of {date}` |

## 8. Audit log and golden set

The audit log is one JSON record per line, in the repository under
`audit/`, keyed by lesson ID. It is the source of the golden set.

| Field | Content |
|---|---|
| `lesson_id` | The lesson's stable ID |
| `pack_version`, `sequence_version`, `canon_pin`, `model_id`, `prompt_version` | Copied from the lesson's provenance. The lesson's composition trace (§4.6) is reachable by the same lesson ID and is what the operator reads when judging a claim about the teacher section |
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
| C5 | ~~Service display name as learners see it.~~ **Resolved 2026-09-13: "Today's Gita"**, provisional, expected to be revisited during v1.0 testing. It is a pack setting (`service_name`), so changing it is a config edit, not code. The subject-line format is in §7.8. | Udaya | Resolved (provisional) |

## Appendix A. Composition prompt, v1 draft

Stored as `packs/<pack_id>/prompts/compose_v1.txt`. Two parts.

**Fixed instructions**

```
You compose one daily lesson on the Bhagavad Gita for a single reader who
does not read Sanskrit. You write only three things: WHAT IT MEANS,
A QUESTION TO CARRY, and nothing else. Every other part of the lesson is
supplied to you verbatim and you never alter it.

Rules of fact
- The only sources of fact are the VERSE block and the TEACHER block below.
- Do not use your own knowledge of the Gita, its commentators, or its
  history. If the TEACHER block is absent, you have only the VERSE block.
- Never quote. Never put quotation marks around anything you write.
- Never generate Sanskrit. Use a Sanskrit term only if it appears in the
  VERSE block or the TEACHER block, and give its meaning the first time.
- Say nothing the verse and the teacher passage do not support.

Rules of voice
- Factual first. Report what the verse says and what the teacher said.
  Do not embellish, do not add emotional color, do not tell the reader how
  to feel.
- Plain, warm, unhurried. Short sentences. One reader.
- Never give advice: no medical, legal, financial, relationship, or
  political guidance, no instructions about the reader's life.
- Never assert one interpretation as the only one. If the teacher's
  reading is one reading, present it as his.
- Never mention other religions or rank traditions.
- Do not address the reader except in the question, and there, ask rather
  than tell. Assume nothing about the reader's circumstances.
- Never use any word or phrase in the BANNED list, in any inflection.

Output
- WHAT IT MEANS: two to four sentences of plain modern English that
  restate the translation and, if present, the teacher's point.
- A QUESTION TO CARRY: one sentence, a question, following from the verse
  or the teacher's point.
- Return exactly these two fields in the JSON shape given. No preamble.
```

**Material for the day** (filled per lesson; every block labeled)

```
LESSON: Day {n} · Chapter {c}, Verse {v}
VERSE (verbatim, do not alter):
  Sanskrit: {devanagari}
  Transliteration: {transliteration}
  Translation ({translator}): {translation}
  Word meanings: {word_meanings}
TEACHER (translated passage, {teacher_name}, "{video_title}",
{start}–{end}; use only this):
  {selected_span_english}
   -- or, when canon-only --
TEACHER: none available for this verse.
BANNED: {banned_word_list}
Return: {"what_it_means": "...", "question": "..."}
```

The teacher-paraphrase prompt (`paraphrase_v1.txt`) is separate and
simpler: given only the span, in English with the Telugu alongside for
reference, condense it to 100 to 200 words in the teacher's own line of
thought, keep his examples and similes, add nothing, remove nothing that
carries the argument, and never use the model's own knowledge. It returns
the paraphrase and the list of segment IDs it drew from, which the
validator checks against the store.
