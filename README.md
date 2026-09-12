# Gita Agent

A service that sends one short Bhagavad Gita lesson by email every morning, in plain
English, at the learner's pace, with every claim traceable to its source.

Each lesson combines two layers:

- **The canon** — the verse in Sanskrit, transliteration, and a public-domain English
  translation, from the open [`gita/gita`](https://github.com/gita/gita) dataset.
- **The lens** — a teacher's explanation of that verse, transcribed and translated from
  recorded discourses. The default teacher is Sri Chaganti Koteswara Rao (Telugu).

The repository ships the pipeline, the canon loader, and pack **manifests** (playlist
IDs). It never ships a teacher's content; each deployment generates its own transcripts
into its own storage.

## Status

**v1 (private MVP) — in design.** Specs are being written before code. See `docs/`.

| Document | Purpose |
|---|---|
| [`docs/product_spec.md`](docs/product_spec.md) | What we are building, for whom, and what a lesson is |
| `docs/content_spec.md` | Canon, teacher packs, defaults *(to follow)* |
| `docs/technical_spec.md` | Architecture, protocols, data model, tests *(to follow)* |
| `docs/task_plan.md` | Phased, test-first implementation plan *(to follow)* |
| [`docs/archive/`](docs/archive/) | The superseded v0 design (code at git tag `v0-legacy`) |

## Stack (planned)

Python 3.13 · Gemini on Vertex AI · Cloud Run Jobs + Cloud Scheduler · Pinecone · email.
No agent framework in v1; Google ADK arrives in v2 for reply-to-lesson conversation.

## License

Apache-2.0 (pending; see `chore/add-license`).
