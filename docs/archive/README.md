# Archived v0 design documents

These four documents describe the original (2026-03 to 2026-05) design: an ingestion
pipeline for private Google Meet recordings (Drive → ffmpeg → Chirp 3 → Gemini
translation → Pinecone) and a Google ADK agent over them.

That design was superseded on 2026-09-12 by the redesign documented in `docs/`.
The v0 code is preserved at the git tag `v0-legacy`:

```bash
git show v0-legacy:ingestion/storage.py
git diff v0-legacy -- ingestion/
```

| File | What it was |
|---|---|
| `detailed_technical_design.md` | v0 architecture, module boundaries, observability conventions |
| `technology_decisions.md` | v0 technology rationale, including the 2026-05 architecture review |
| `task.md` | v0 eight-phase task plan (Phases 1–4.7 completed) |
| `SETUP_GUIDE.md` | v0 credential and environment setup |

Why it was superseded: the product moved from a private archive of family study
sessions to a daily Bhagavad Gita learning service over public teacher content, and
Gemini on Vertex AI proved able to transcribe and translate Telugu YouTube audio
directly from the URL, which removed most of the v0 pipeline.
