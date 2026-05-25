# Task: Hinduism & Bhagavad Gita Query Agent

## Phase 1: Design
- [x] Define System Architecture
    - [x] High-level Architecture Diagram (Mermaid)
    - [x] Agent Query Flow (Sequence Diagram)
    - [x] Data Ingestion Pipeline Flow (Sequence Diagram)
    - [x] Deployment Architecture Diagram (Mermaid)
    - [x] Component Breakdown (ADK, MCP, Ingestion, Frontend)
    - [x] Architecture Decisions Table (framework, model, DB, embedding, deployment)
- [x] Clarify Requirements & Data Sources
    - [x] Source data: 4 Google Meet recordings (~3.26 GB), Telugu/English code-switching
    - [x] Translation pipeline: Chirp 3 transcription + Gemini 3 Flash translation (Option A)
    - [x] Fallback: Gemini direct audio→English (Option B), documented in Appendix
    - [x] No raw transcript storage — vector embeddings only (Pinecone)
    - [x] Two speakers: Nanna (Guru/father) and Udaya (Student/daughter)
- [x] Design Data Ingestion Pipeline
    - [x] Google Drive API Integration (service account viewer access)
    - [x] Ingestion API Specs (POST /ingest, GET /jobs/{id}, GET /videos)
    - [x] Audio Extraction (ffmpeg → mono 16kHz FLAC)
    - [x] Transcription (Chirp 3, te-IN + en-US, diarization, word timestamps)
    - [x] Translation (Gemini 3 Flash, Telugu → English, Sanskrit term preservation)
    - [x] Chunking Strategy (500 tokens, 50 overlap, sentence boundaries)
    - [x] Embedding (text-embedding-004, 768 dimensions)
    - [x] Pinecone upsert with metadata (video_id, timestamps, speakers, date)
- [x] Design MCP Integration
    - [x] `gita-context-server` Specification
    - [x] Tool: `search_transcripts(query, limit)` — Pinecone similarity search
    - [x] Tool: `get_video_metadata(video_id)` — metadata retrieval
    - [x] ADK native MCP support via `McpToolset` + `StdioConnectionParams`
- [x] Plan Deployment Strategy
    - [x] Cloud Run (Staging only, personal use)
    - [x] Google ADK v1.0+ with Gemini 3 Flash
    - [x] Secrets Management (Google Secret Manager — 3 secrets)
    - [x] Workload Identity for Cloud Run (no JSON key in staging)
    - [x] API Gap Analysis (4 APIs to enable)
- [x] Frontend Design
    - [x] MVP: `adk web` built-in dev UI (zero frontend code)
- [x] Testing Strategy
    - [x] TDD approach — tests written before implementation
    - [x] 30+ test cases across 6 test files
    - [x] Golden Set (20 QA pairs, human-verified)
    - [x] Fuzz Testing (`hypothesis` library)
    - [x] Validation (corrupt MP4, silence, edge cases)
- [x] Draft & finalize `detailed_technical_design.md`

---

## Phase 2: Prerequisites (Manual — Udaya)

These are tasks that require manual action in the GCP Console, Google Drive, or Pinecone UI.

- [ ] **GCP: Enable Missing APIs**
    - [ ] Enable Cloud Speech-to-Text API (`speech.googleapis.com`)
    - [ ] Enable Cloud Run Admin API (`run.googleapis.com`)
    - [ ] Enable Secret Manager API (`secretmanager.googleapis.com`)
    - [ ] Enable Generative Language API (`generativelanguage.googleapis.com`)
    - [ ] *(Optional)* Disable Cloud Text-to-Speech API (enabled but not needed)
    - [ ] Verify all 4 APIs show as "Enabled" in APIs & Services dashboard
- [ ] **Google Drive: Share Folder with Service Account**
    - [ ] Open "Bhagavad Gita Sessions" folder in Drive
    - [ ] Share with `gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com`
    - [ ] Set permission to **Viewer** (read-only)
    - [ ] Uncheck "Notify people"
    - [ ] Verify service account appears in "People with access"
- [ ] **GCS: Create Audio Storage Bucket**
    - [ ] Create bucket `gita-agent-prod-audio` in `us-central1`
    - [ ] Storage class: Standard, Access control: Uniform
    - [ ] Verify `gita-ingest-worker` service account has write access (Editor role covers this)
- [ ] **Pinecone: Create Vector Index**
    - [ ] Sign up at Pinecone.io (free tier)
    - [ ] Create index: name=`gita-videos`, dimensions=`768`, metric=`cosine`
    - [ ] Copy API key
- [ ] **Google Secret Manager: Store Secrets**
    - [ ] Create secret `pinecone-api-key` with Pinecone API key value
    - [ ] Create secret `google-api-key` with Gemini API key value
    - [ ] Grant `gita-ingest-worker` the `secretmanager.secretAccessor` role on both secrets
- [ ] **Local: Service Account Key for Development**
    - [ ] Download JSON key for `gita-ingest-worker` service account
    - [ ] Save as `service-account.json` in project root (gitignored)
- [ ] **Obtain Gemini API Key**
    - [ ] Get API key from Google AI Studio (https://aistudio.google.com/apikey)

---

## Phase 3: Environment Setup

- [x] Git Setup & Version Control
    - [x] Initialize Git repo
    - [x] Connect to GitHub remote (`udayauma/gita-agent`)
    - [x] Set up project directory structure
- [ ] **Local Development Environment**
    - [ ] Create Python virtual environment (`python -m venv .venv`)
    - [ ] Create `requirements.txt` with all dependencies
    - [ ] Create `pyproject.toml` with pytest configuration
    - [ ] Install dependencies (`pip install -r requirements.txt`)
    - [ ] Create `.env.example` template file
    - [ ] Create `.env` with local credentials (GOOGLE_API_KEY, PINECONE_API_KEY, GOOGLE_APPLICATION_CREDENTIALS)
    - [ ] Add `.env`, `service-account.json`, `.venv/` to `.gitignore`
    - [ ] Install ffmpeg locally (`brew install ffmpeg` on macOS)
    - [ ] Verify `adk web` runs locally (hello-world agent)
- [ ] **Structured Logging Setup**
    - [ ] Configure `structlog` with JSON output for Cloud Run compatibility
    - [ ] Create shared logging config module (`shared/logging.py` or similar)

---

## Phase 4: Implementation — Ingestion Service (TDD)

Each sub-component follows: write test → red → implement → green → refactor.

### 4.1 Audio Extraction
- [x] Write `tests/test_ingestion.py::test_extract_audio_produces_valid_flac`
- [x] Write `tests/test_ingestion.py::test_extract_audio_rejects_corrupt_mp4`
- [x] Write `tests/test_ingestion.py::test_extract_audio_handles_silent_track`
- [x] Implement `ingestion/audio.py` — ffmpeg wrapper (MP4 → mono 16kHz FLAC)
- [x] Run tests → all green

### 4.2 Google Drive Integration
- [x] Write `tests/test_ingestion.py::test_drive_folder_listing`
- [x] Implement `ingestion/drive.py` — list files in shared folder, download MP4s
- [x] Run tests → all green

### 4.3 Transcription (Chirp 3)
- [x] Write `tests/test_transcription.py::test_chirp3_returns_telugu_text`
- [x] Write `tests/test_transcription.py::test_chirp3_detects_english_segments`
- [x] Write `tests/test_transcription.py::test_diarization_identifies_two_speakers`
- [x] Write `tests/test_transcription.py::test_word_timestamps_are_sequential`
- [x] Implement `ingestion/transcription.py` — Chirp 3 BatchRecognize, LRO polling, result parsing
- [x] Run tests → all green

### 4.4 Translation (Gemini 3 Flash)
- [x] Write `tests/test_translation.py::test_gemini_translates_telugu_to_english`
- [x] Write `tests/test_translation.py::test_english_passthrough`
- [x] Write `tests/test_translation.py::test_sanskrit_terms_preserved`
- [x] Write `tests/test_translation.py::test_speaker_labels_preserved`
- [x] Write `tests/test_translation.py::test_fallback_to_translate_api`
- [x] Implement `ingestion/translation.py` — Gemini translation prompt, chunked processing, fallback
- [x] Run tests → all green

### 4.5 Chunking & Embedding
- [x] Write `tests/test_chunking.py::test_chunk_size_within_limit`
- [x] Write `tests/test_chunking.py::test_chunk_overlap`
- [x] Write `tests/test_chunking.py::test_chunk_splits_on_sentence_boundary`
- [x] Write `tests/test_chunking.py::test_embedding_dimension`
- [x] Write `tests/test_chunking.py::test_metadata_attached_to_chunk`
- [x] Implement `ingestion/chunking.py` — text splitter, embedding via text-embedding-004, Pinecone upsert
- [x] Run tests → all green

### 4.6 Ingestion Orchestrator + Cloud Run Job (replaces FastAPI service — pivoted 2026-05-24)

Originally planned as a FastAPI service with `BackgroundTasks`. Pivoted to a CLI/Cloud Run Job because:
(a) `BackgroundTasks` doesn't survive Cloud Run container teardown on scale-to-zero;
(b) in-memory job state is lost on cold start;
(c) the agent never *triggers* ingestion — the user does, manually, when a new recording lands in Drive.
Cloud Run Jobs are purpose-built for this batch-execution shape. See `docs/technology_decisions.md` § 8.

#### 4.6.1 Storage module (cashes IOU from Phase 4.3)
- [x] Write `tests/test_storage.py::test_upload_file_writes_to_correct_uri`
- [x] Write `tests/test_storage.py::test_download_json_returns_parsed_dict`
- [x] Write `tests/test_storage.py::test_list_blobs_returns_uris_under_prefix`
- [x] Write `tests/test_storage.py::test_sentinel_write_and_check`
- [x] Implement `ingestion/storage.py` — `upload_file`, `download_json`, `list_blobs`, `delete_prefix`, `write_sentinel`, `sentinel_exists`
- [x] Update `ingestion/transcription.py` to call `storage.download_json` (replace the placeholder) and to resolve the actual Chirp 3 output filename from `BatchRecognizeResponse.results[uri].uri` instead of the hardcoded `transcript.json`
- [x] Run tests → all green

#### 4.6.2 Orchestrator + CLI
- [x] Write `tests/test_orchestrator.py::test_process_video_runs_full_pipeline_in_order`
- [x] Write `tests/test_orchestrator.py::test_is_already_indexed_checks_sentinel`
- [x] Write `tests/test_orchestrator.py::test_scan_and_process_skips_already_indexed`
- [x] Write `tests/test_orchestrator.py::test_force_reindex_bypasses_sentinel`
- [x] Write `tests/test_orchestrator.py::test_dry_run_lists_without_processing`
- [x] Write `tests/test_orchestrator.py::test_pipeline_step_failure_writes_no_sentinel`
- [x] Implement `ingestion/orchestrator.py`:
    - [x] `process_video(drive_file, *, force_reindex=False) -> ProcessingResult` — runs the 6-step pipeline
    - [x] `is_already_indexed(video_id) -> bool` — checks `gs://{bucket}/{video_id}/.indexed` GCS sentinel
    - [x] `scan_and_process(*, force_reindex=False, video_id_filter=None, dry_run=False)` — lists Drive folder, diffs against sentinels, processes the new set
    - [x] Writes the `.indexed` sentinel only after `chunk_and_embed` reports `total_vectors_upserted > 0`
    - [x] argparse CLI entrypoint: `python -m ingestion.orchestrator` (default: scan + process new); flags `--video-id X`, `--force-reindex`, `--dry-run`
- [x] Run tests → all green

#### 4.6.3 Cloud Run Job artifacts
- [x] Write `Dockerfile.ingestion` — Python 3.13-slim, install ffmpeg, copy ingestion/, `ENTRYPOINT ["python", "-m", "ingestion.orchestrator"]`
- [x] Prune `fastapi`, `uvicorn`, `httpx` from `requirements.txt` (verified no remaining imports)
- [x] Verify CLI entrypoint works locally via `python -m ingestion.orchestrator --help`
- [ ] Build image locally and smoke-test (requires Docker Desktop running): `docker build . -f Dockerfile.ingestion -t gita-ingest:local && docker run --rm gita-ingest:local --help`
- [x] Document the `gcloud run jobs deploy ingest-recordings` invocation in `docs/SETUP_GUIDE.md` § 5.2 (region, service account, env vars, secret bindings for `PINECONE_API_KEY` + `GOOGLE_API_KEY`)
- [x] Document the manual-trigger workflow: `gcloud run jobs execute ingest-recordings --region=us-central1 --wait` (§ 5.3)

### 4.7 Observability Instrumentation (added per 2026-05-23 architecture review)
- [ ] Add `opentelemetry-sdk`, `opentelemetry-exporter-gcp-trace`, and `opentelemetry-instrumentation` to `requirements.txt`
- [ ] Add `ingestion/observability.py` — initialize TracerProvider with Cloud Trace exporter, configure structlog → OTel log correlation
- [ ] Write `tests/test_observability.py::test_tracer_initializes_with_cloud_trace_exporter`
- [ ] Write `tests/test_observability.py::test_spans_are_emitted_with_correct_attributes`
- [ ] Instrument `ingestion/drive.py` — span `drive.download` with `video_id`, `size_bytes` attributes
- [ ] Instrument `ingestion/audio.py` — span `audio.extract` with `duration_seconds`, `output_codec`
- [ ] Instrument `ingestion/transcription.py` — span `transcription.batch_recognize` with `video_id`, `audio_uri`, plus LRO polling sub-span
- [ ] Verify traces appear in Cloud Trace console after a local pipeline run
- [ ] Run all observability tests → all green

### 4.8 Ingestion Integration Test
- [ ] Process one real recording end-to-end (smallest file: Jul 20, 640.9 MB)
- [ ] Verify vectors appear in Pinecone index with correct metadata
- [ ] Verify Cloud Trace spans cover the full pipeline (download → embed)
- [ ] Process remaining 3 recordings
- [ ] Verify total vector count in Pinecone is reasonable (~hundreds of chunks)

---

## Phase 5: Implementation — MCP Server (TDD)

### 5.1 Pinecone Search
- [ ] Write `tests/test_mcp_server.py::test_search_transcripts_returns_results`
- [ ] Write `tests/test_mcp_server.py::test_search_transcripts_empty_query`
- [ ] Implement `mcp_server/pinecone_client.py` — query wrapper
- [ ] Implement `mcp_server/embeddings.py` — text-embedding-004 wrapper
- [ ] Run tests → all green

### 5.2 Metadata Retrieval
- [ ] Write `tests/test_mcp_server.py::test_get_video_metadata_valid_id`
- [ ] Write `tests/test_mcp_server.py::test_get_video_metadata_invalid_id`
- [ ] Implement metadata retrieval logic (query Pinecone for distinct video_ids + metadata)
- [ ] Run tests → all green

### 5.3 MCP Server
- [ ] Write `tests/test_mcp_server.py::test_tool_listing`
- [ ] Implement `mcp_server/server.py` — MCP server with `search_transcripts` and `get_video_metadata`
- [ ] Verify MCP server starts and responds to `list_tools` and `call_tool`
- [ ] Run all MCP tests → all green

---

## Phase 6: Implementation — Agent (TDD)

### 6.1 Agent Definition
- [ ] Implement `agent/agent.py` — `root_agent` with `LlmAgent`, Gemini 3 Flash, `McpToolset`
- [ ] Implement `agent/__init__.py`
- [ ] Create `agent/.env` with `GOOGLE_API_KEY`
- [ ] Verify `adk run` starts the agent and connects to MCP server

### 6.2 Agent Integration Tests
- [ ] Write `tests/test_agent.py::test_agent_uses_search_tool`
- [ ] Write `tests/test_agent.py::test_agent_cites_sources`
- [ ] Write `tests/test_agent.py::test_agent_handles_no_results`
- [ ] Write `tests/test_agent.py::test_agent_distinguishes_speakers`
- [ ] Run tests → all green

### 6.3 Golden Set Validation (via ADK AgentEvaluator — updated 2026-05-23)
- [ ] Capture 20 golden conversations through `adk web` UI (10 direct Gita questions, 5 contextual, 3 edge cases, 2 multi-turn)
- [ ] Save each as a `.evalset.json` file under `tests/evalsets/`
- [ ] Write `tests/test_agent_eval.py` using `AgentEvaluator.evaluate()` inside pytest
- [ ] Configure metrics: `final_response_match_v2` (LLM-as-judge), `hallucinations_v1` (grounding), and a tool-trajectory check that asserts `search_transcripts` was called
- [ ] Target: 80%+ pass rate on grounded answers, zero hallucinations on edge cases
- [ ] Iterate on agent instruction prompt if needed; commit goldens alongside code so CI can re-run them

### 6.4 Local End-to-End Test
- [ ] Launch `adk web --port 8000`
- [ ] Ask 5+ questions via the chat UI
- [ ] Verify tool calls appear in the UI (search_transcripts invoked)
- [ ] Verify citations reference correct sessions and timestamps
- [ ] Verify Nanna vs. Udaya speaker attribution works

---

## Phase 7: Deployment (Staging)

### 7.1 Containerization
- [ ] Write `Dockerfile.agent` for the Agent Service (ADK + MCP server, port 8080)
- [ ] `Dockerfile.ingestion` is already authored in Phase 4.6.3 — just confirm it builds clean
- [ ] Build and test both images locally (`docker build` + `docker run`)
- [ ] Verify agent responds correctly inside its container; verify ingestion image runs `--help` clean

### 7.2 Cloud Run Deployment (Service for Agent, Job for Ingestion)
- [ ] Deploy Agent as a Cloud Run **Service**: `gcloud run deploy gita-agent`
    - [ ] Set service account to `gita-ingest-worker`
    - [ ] Configure Secret Manager env bindings (`PINECONE_API_KEY`, `GOOGLE_API_KEY`)
    - [ ] Memory/CPU: 512MB / 1 vCPU minimum
    - [ ] Min instances = 0 (scale to zero); max instances = 1 (personal use)
- [ ] Deploy Ingestion as a Cloud Run **Job**: `gcloud run jobs deploy ingest-recordings`
    - [ ] Same service account, same secret bindings
    - [ ] Env vars: `GCP_PROJECT_ID`, `GCS_AUDIO_BUCKET`, `DRIVE_FOLDER_ID`, `PINECONE_INDEX_NAME`
    - [ ] Memory/CPU: 2GB / 2 vCPU (transcription + embedding burst)
    - [ ] Task timeout: 1 hour
- [ ] Verify Agent Service starts and passes health check
- [ ] Verify Ingestion Job runs end-to-end via `gcloud run jobs execute ingest-recordings --wait`
- [ ] Test agent from Cloud Run URL

### 7.3 Monitoring & Alerting
- [ ] Verify structured logs appear in Cloud Logging for both Agent Service and Ingestion Job
- [ ] Verify Cloud Trace receives spans from both (Phase 4.7 OTel work)
- [ ] Create log-based metric for errors (severity=ERROR)
- [ ] Create alert policy: notify on >5 errors in 5 minutes (Agent only — Job failures are visible from `gcloud run jobs executions list`)

### 7.4 Staging End-to-End Validation
- [ ] Trigger ingestion via `gcloud run jobs execute` (smoke test against one recording first, then full set)
- [ ] Query agent via Cloud Run Agent Service URL
- [ ] Verify full flow: user question → agent → MCP tool → Pinecone → response with citations
- [ ] Run Golden Set against staging endpoint
- [ ] Document any discrepancies vs. local testing

---

## Phase 8: Polish & Documentation

- [ ] Update `README.md` with final architecture, setup instructions, and usage
- [ ] Update `SETUP_GUIDE.md` if any steps changed during implementation
- [ ] Clean up any TODO/FIXME comments in code
- [ ] Ensure all tests pass (`pytest` from project root)
- [ ] Final commit and push to GitHub
