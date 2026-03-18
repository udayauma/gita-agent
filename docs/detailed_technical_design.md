# Technical Design: Hinduism & Bhagavad Gita Agent

## 1. Executive Summary

An AI agent designed to answer natural language queries about Hinduism, specifically the Bhagavad Gita, utilizing personal video context from recorded sessions between a father ("Nanna" / Guru) and daughter (Udaya / Student). The agent is built on **Google Agent Development Kit (ADK)** with **Gemini 3 Flash**, uses a two-stage translation pipeline (**Chirp 3** for Telugu/English transcription + **Gemini** for English translation), stores context as vector embeddings in **Pinecone**, and exposes transcript search via a native **MCP tool** integrated directly into the ADK agent. The MVP frontend is the built-in **`adk web`** development UI.

---

## 2. System Architecture

### 2.1 High-Level Architecture

```mermaid
graph TD
    User[User] -->|Chat| ADKWEB["adk web (Built-in Dev UI)"]
    ADKWEB -->|Session API| Runtime[Google ADK Runtime]

    subgraph "Google Cloud Run - Staging"
        Runtime -->|Orchestrates| Agent["Gita Agent<br/>(Gemini 3 Flash)"]
        Agent -->|Native MCP Tool| MCPTool["search_transcripts()"]
        Agent -->|Native MCP Tool| MCPMeta["get_video_metadata()"]
        MCPTool -->|Similarity Search| VDB[(Pinecone Vector DB)]
        MCPMeta -->|Metadata Lookup| VDB
    end

    subgraph "Data Ingestion Pipeline (Local / Cloud Run Job)"
        Drive[Google Drive<br/>Bhagavad Gita Sessions] -->|Download MP4| Ingest[Ingestion Service<br/>FastAPI]
        Ingest -->|ffmpeg| Audio[Audio Extraction<br/>WAV/FLAC]
        Audio -->|Upload| GCS[Cloud Storage Bucket]
        GCS -->|BatchRecognize| STT[Chirp 3<br/>Speech-to-Text V2]
        STT -->|Telugu + English Text| Trans[Gemini 3 Flash<br/>Translation to English]
        Trans -->|English Text| Embed[Embedding<br/>text-embedding-004]
        Embed -->|Upsert Vectors| VDB
    end
```

### 2.2 Agent Query Flow

```mermaid
sequenceDiagram
    participant U as User
    participant ADK as ADK Runtime (adk web)
    participant Agent as Gita Agent (Gemini 3 Flash)
    participant MCP as MCP Tool (search_transcripts)
    participant P as Pinecone

    U->>ADK: "What does Krishna say about duty?"
    ADK->>Agent: Forward query with session context
    Agent->>Agent: Decide to use search_transcripts tool
    Agent->>MCP: search_transcripts(query="Krishna duty dharma", limit=5)
    MCP->>MCP: Embed query via text-embedding-004
    MCP->>P: Similarity search (top 5 chunks)
    P-->>MCP: Ranked chunks with metadata
    MCP-->>Agent: Return chunks + timestamps + speaker labels
    Agent->>Agent: Synthesize answer from chunks + Gita knowledge
    Agent-->>ADK: Response with citations
    ADK-->>U: Display answer + source references
```

### 2.3 Data Ingestion Pipeline Flow

```mermaid
sequenceDiagram
    participant U as User / CLI
    participant API as Ingestion API (FastAPI)
    participant W as Background Worker
    participant GD as Google Drive
    participant GCS as Cloud Storage
    participant STT as Chirp 3 (Speech-to-Text V2)
    participant LLM as Gemini 3 Flash
    participant P as Pinecone

    U->>API: POST /api/v1/ingest {folder_id, force_reindex}
    API->>API: Create job record, return job_id
    API-->>U: 202 Accepted {job_id}
    API->>W: Enqueue job (BackgroundTasks)

    W->>GD: List MP4 files in folder
    GD-->>W: File list (4 recordings, ~3.26 GB)

    loop For each video file
        W->>GD: Download MP4
        W->>W: ffmpeg: extract audio (MP4 → FLAC)
        W->>GCS: Upload audio to gs://gita-agent-prod-audio/
        W->>STT: BatchRecognizeRequest (Chirp 3, te-IN, diarization)
        STT-->>W: Transcribed text (Telugu + English mixed) with speaker labels
        W->>LLM: Translate Telugu portions to English
        LLM-->>W: Full English text with speaker labels preserved
        W->>W: Chunk text (500 tokens, 50 token overlap)
        W->>P: Upsert embeddings (text-embedding-004) + metadata
    end

    U->>API: GET /api/v1/jobs/{job_id}
    API-->>U: {status: "completed", files_processed: 4}
```

### 2.4 Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent Framework | Google ADK (Python) v1.0+ | Native Gemini integration, built-in runtime, MCP support |
| Agent Model | Gemini 3 Flash | Fast, cost-effective, strong reasoning for personal use |
| Transcription | Chirp 3 (Speech-to-Text V2) | Best multilingual ASR, diarization, auto language detection |
| Translation | Gemini 3 Flash | Handles Telugu→English naturally, preserves context |
| Vector DB | Pinecone (Serverless, Free Tier) | Managed, stateless access, ~100k vectors sufficient |
| Embedding Model | text-embedding-004 | Google's latest, 768 dimensions, multilingual |
| Frontend (MVP) | `adk web` built-in UI | Zero frontend code, instant chat interface |
| Deployment | Cloud Run (Staging) | Scale-to-zero, personal use, cost-efficient |
| Secrets | Google Secret Manager | Native Cloud Run integration |

---

## 3. Data Processing Pipeline: Deep Dive

*Goal: Robust, observable pipeline that converts Telugu/English video recordings into searchable English text embeddings.*

### 3.1 Source Data

| Recording | Date | Size | Format |
|-----------|------|------|--------|
| Nanna / Udaya - 2025/07/06 14:22 EDT | Jul 6, 2025 | 1 GB | MP4 (Google Meet) |
| Nanna / Udaya - 2025/07/20 19:57 EDT | Jul 20, 2025 | 640.9 MB | MP4 (Google Meet) |
| Nanna / Udaya - 2025/08/03 18:59 EDT | Aug 3, 2025 | 668.3 MB | MP4 (Google Meet) |
| Nanna / Udaya - 2025/08/17 12:05 EDT | Aug 17, 2025 | 952 MB | MP4 (Google Meet) |

**Total**: 4 recordings, ~3.26 GB, two speakers (Nanna = Guru, Udaya = Student), Telugu/English code-switching.

**Google Drive Folder ID**: `1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA`

### 3.2 Ingestion Service API

**Framework**: FastAPI with `BackgroundTasks` (MVP). Upgradeable to Google Cloud Tasks for scale.

**Why async?** A 1-hour video takes minutes to transcribe. Synchronous HTTP would time out (60s limit). The API acknowledges immediately; a background worker does the heavy lifting.

**Endpoint 1: Trigger Ingestion**
-   `POST /api/v1/ingest`
-   **Request**:
    ```json
    {
      "source_folder_id": "1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA",
      "file_types": ["mp4"],
      "force_reindex": false
    }
    ```
-   **Response** (202 Accepted):
    ```json
    {
      "job_id": "job_abc123",
      "status": "queued",
      "files_found": 4
    }
    ```
-   **Logic**: Scans Drive folder for MP4 files, skips already-indexed files (unless `force_reindex`), queues each for processing.

**Endpoint 2: Check Status**
-   `GET /api/v1/jobs/{job_id}`
-   **Response**:
    ```json
    {
      "job_id": "job_abc123",
      "status": "processing",
      "progress": {
        "total_files": 4,
        "completed": 2,
        "current_file": "Nanna / Udaya - 2025/08/03 18:59 EDT - Recording",
        "current_step": "translation"
      }
    }
    ```

**Endpoint 3: List Indexed Videos**
-   `GET /api/v1/videos`
-   **Response**: List of all processed videos with metadata (title, date, duration, chunk count).

### 3.3 Step 1: Audio Extraction

**Tool**: `ffmpeg-python` (Python wrapper around ffmpeg).

```
ffmpeg -i input.mp4 -vn -acodec flac -ar 16000 -ac 1 output.flac
```

-   `-vn`: Discard video track entirely.
-   `-acodec flac`: Lossless audio (best quality for STT).
-   `-ar 16000`: 16kHz sample rate (optimal for Chirp 3).
-   `-ac 1`: Mono (speech doesn't benefit from stereo).

**Output**: ~50-100 MB FLAC per 1-hour recording (vs. ~800 MB MP4).

**Upload**: Extracted audio is uploaded to `gs://gita-agent-prod-audio/{video_id}/audio.flac`.

### 3.4 Step 2: Transcription (Chirp 3)

**Service**: Google Cloud Speech-to-Text V2 API.
**Model**: `chirp_3` — latest generation, enhanced multilingual ASR with automatic language detection.
**Library**: `google-cloud-speech` (Python client).

**Why Chirp 3 over Chirp 2?**
-   Enhanced accuracy and speed over Chirp 2.
-   Automatic language detection — handles Telugu/English code-switching without manual language tagging.
-   Native diarization — distinguishes Speaker 1 (Nanna) from Speaker 2 (Udaya).
-   Word-level timestamps for citation back to source video.

**Configuration**:
```python
from google.cloud.speech_v2 import SpeechClient
from google.cloud.speech_v2.types import cloud_speech

config = cloud_speech.RecognitionConfig(
    auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
    language_codes=["te-IN", "en-US"],  # Telugu + English
    model="chirp_3",
    features=cloud_speech.RecognitionFeatures(
        enable_word_time_offsets=True,
        diarization_config=cloud_speech.SpeakerDiarizationConfig(
            min_speaker_count=1,
            max_speaker_count=3,
        ),
        enable_automatic_punctuation=True,
    ),
)

request = cloud_speech.BatchRecognizeRequest(
    recognizer=f"projects/gita-agent-prod/locations/global/recognizers/_",
    config=config,
    files=[cloud_speech.BatchRecognizeFileMetadata(
        uri="gs://gita-agent-prod-audio/{video_id}/audio.flac"
    )],
    recognition_output_config=cloud_speech.RecognitionOutputConfig(
        gcs_output_config=cloud_speech.GcsOutputConfig(
            uri="gs://gita-agent-prod-audio/{video_id}/transcript/"
        ),
    ),
)
```

**Output**: JSON with mixed Telugu/English text, speaker labels, and word timestamps.

### 3.5 Step 3: Translation (Gemini 3 Flash)

**Why not use a dedicated translation API?**
Chirp 3 does not support Telugu→English translation. Google Translate API could work but loses contextual nuance (spiritual/philosophical terminology). Gemini 3 Flash understands context and can preserve meaning of terms like "dharma", "karma", "atman" while translating conversational Telugu.

**Approach**: Send transcribed chunks to Gemini with a structured prompt.

```python
translation_prompt = """You are translating a conversation about the Bhagavad Gita
between a father (Guru/Nanna) and daughter (Student/Udaya).

The text below contains Telugu and English mixed speech (code-switching).
Translate ALL Telugu portions to English. Keep English portions as-is.
Preserve speaker labels (Speaker 1, Speaker 2).
Preserve spiritual/philosophical terms in their original Sanskrit where
commonly known (e.g., dharma, karma, atman, moksha, yoga).

Transcribed text:
{chunk_text}

Output the fully translated English text with speaker labels preserved."""
```

**Chunking for Translation**: Process in ~2000-word segments to stay within context limits and maintain coherence.

**Fallback**: If Gemini translation encounters issues, fall back to Google Translate API (`googletrans` or Cloud Translation V3) as Option B.

### 3.6 Step 4: Chunking & Embedding

**Chunking Strategy**:
-   **Chunk size**: 500 tokens (~375 words).
-   **Overlap**: 50 tokens between adjacent chunks (preserves cross-boundary context).
-   **Boundary**: Split on sentence boundaries where possible (not mid-sentence).
-   **Metadata per chunk**:
    ```json
    {
      "video_id": "nanna_udaya_2025_07_06",
      "video_title": "Nanna / Udaya - 2025/07/06 14:22 EDT - Recording",
      "chunk_index": 3,
      "start_time_seconds": 245.5,
      "end_time_seconds": 312.8,
      "speakers": ["Speaker 1", "Speaker 2"],
      "source_language": "te-IN",
      "session_date": "2025-07-06"
    }
    ```

**Embedding Model**: `text-embedding-004` (Google, 768 dimensions, multilingual).

**Pinecone Upsert**:
```python
from pinecone import Pinecone

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("gita-videos")

index.upsert(vectors=[
    {
        "id": f"{video_id}_chunk_{i}",
        "values": embedding_vector,  # 768-dim float array
        "metadata": chunk_metadata
    }
    for i, (embedding_vector, chunk_metadata) in enumerate(chunks)
])
```

**Pinecone Index Configuration**:
-   **Name**: `gita-videos`
-   **Dimensions**: 768 (matches text-embedding-004)
-   **Metric**: Cosine similarity
-   **Tier**: Serverless (Free Tier — supports ~100k vectors, sufficient for 4+ hours of video)

---

## 4. MCP Integration Strategy

*Decoupling data fetch from agent reasoning via native ADK MCP tool support.*

### 4.1 ADK Native MCP Support

Google ADK v1.0+ natively supports MCP tools via `McpToolset`. This eliminates the need for a standalone MCP server process — the ADK agent directly consumes MCP tools.

**Key benefit**: The agent, MCP tools, and Pinecone queries all live in one deployable unit.

*Reference: [ADK MCP Tools Documentation](https://google.github.io/adk-docs/tools-custom/mcp-tools/)*

### 4.2 MCP Server: `gita-context-server`

We build a lightweight MCP server that the ADK agent connects to via `StdioServerParameters` (local process) or `SseConnectionParams` (remote, for Cloud Run).

```python
from mcp.server.lowlevel import Server
from mcp import types as mcp_types
from pinecone import Pinecone
import google.generativeai as genai

app = Server("gita-context-server")

@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [
        mcp_types.Tool(
            name="search_transcripts",
            description="Search Bhagavad Gita session transcripts by semantic similarity. "
                        "Returns relevant passages from recorded conversations between "
                        "Nanna (Guru) and Udaya (Student) about the Bhagavad Gita.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "limit": {"type": "integer", "description": "Max results", "default": 5}
                },
                "required": ["query"]
            }
        ),
        mcp_types.Tool(
            name="get_video_metadata",
            description="Get metadata for a specific Bhagavad Gita recording session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "video_id": {"type": "string", "description": "Video identifier"}
                },
                "required": ["video_id"]
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[mcp_types.TextContent]:
    if name == "search_transcripts":
        query_embedding = genai.embed_content(
            model="models/text-embedding-004",
            content=arguments["query"]
        )["embedding"]
        results = index.query(
            vector=query_embedding,
            top_k=arguments.get("limit", 5),
            include_metadata=True
        )
        formatted = format_results(results)
        return [mcp_types.TextContent(type="text", text=formatted)]

    elif name == "get_video_metadata":
        metadata = get_metadata(arguments["video_id"])
        return [mcp_types.TextContent(type="text", text=str(metadata))]
```

### 4.3 Agent Definition with MCP Tools

```python
# agent/agent.py
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

root_agent = LlmAgent(
    model="gemini-3-flash",
    name="gita_agent",
    description="An AI agent specializing in the Bhagavad Gita, with access to "
                "personal video recordings of father-daughter discussions.",
    instruction="""You are a knowledgeable guide on the Bhagavad Gita and Hindu philosophy.
    You have access to transcribed recordings of Bhagavad Gita teaching sessions
    between Nanna (the Guru/father) and Udaya (the Student/daughter).

    When answering questions:
    1. ALWAYS use the search_transcripts tool first to find relevant passages.
    2. Ground your answers in the retrieved context from the recordings.
    3. Cite which session and approximate timestamp when referencing a passage.
    4. If the recordings don't contain relevant information, say so and provide
       general knowledge about the topic from the Bhagavad Gita.
    5. Preserve Sanskrit terms (dharma, karma, atman, moksha) and explain them.
    6. Distinguish between what Nanna (Guru) said vs. Udaya (Student) said.""",
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="python",
                    args=["-m", "mcp_server.server"],
                ),
                timeout=30,
            ),
        ),
    ],
)
```

---

## 5. Deployment Architecture

### 5.1 Environment: Staging Only

**GCP Project**: `gita-agent-prod` (Project Number: `881793829896`)
**Purpose**: Personal use, staging environment. No production environment for now.

### 5.2 Cloud Run (Serverless)

**Why Cloud Run?**
1.  **Scale to Zero**: No traffic = $0 compute cost. Billed per millisecond of use.
2.  **Zero Maintenance**: No OS patches, no server management.
3.  **Simple Deployment**: `gcloud run deploy` from a Docker container.

**Stateless Design**: Cloud Run containers are ephemeral. All persistent state lives in Pinecone (vectors) and GCS (audio files). The agent service is fully stateless.

### 5.3 Deployment Diagram

```mermaid
graph TD
    subgraph "Developer Machine"
        Code[Source Code] -->|git push| GH[GitHub: gita-agent]
    end

    subgraph "Google Cloud - gita-agent-prod"
        subgraph "Cloud Run Services"
            AgentSvc["Agent Service<br/>(ADK + MCP Server)<br/>Port 8080"]
            IngestSvc["Ingestion Service<br/>(FastAPI)<br/>Port 8081"]
        end

        subgraph "Storage"
            GCS_Audio["GCS Bucket<br/>gita-agent-prod-audio"]
            SM["Secret Manager<br/>API Keys"]
        end

        subgraph "Monitoring"
            CL["Cloud Logging<br/>(Structured)"]
            CM["Cloud Monitoring<br/>(Alerts)"]
        end
    end

    subgraph "External Services"
        Pinecone["Pinecone<br/>(Free Tier)"]
        Gemini["Gemini API<br/>(3 Flash)"]
        STT["Speech-to-Text V2<br/>(Chirp 3)"]
        GDrive["Google Drive<br/>(Recordings)"]
    end

    AgentSvc -->|Query| Pinecone
    AgentSvc -->|LLM| Gemini
    AgentSvc -->|Logs| CL
    IngestSvc -->|Download| GDrive
    IngestSvc -->|Upload Audio| GCS_Audio
    IngestSvc -->|Transcribe| STT
    IngestSvc -->|Translate| Gemini
    IngestSvc -->|Upsert| Pinecone
    AgentSvc -->|Read| SM
    IngestSvc -->|Read| SM
```

### 5.4 Secrets Management (Google Secret Manager)

| Secret Name | Value | Used By |
|-------------|-------|---------|
| `pinecone-api-key` | Pinecone API key | Agent Service, Ingestion Service |
| `google-api-key` | Gemini API key (for `google-genai` SDK) | Agent Service (ADK), Ingestion Service (translation + embedding) |
| `drive-folder-id` | `1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA` | Ingestion Service (configurable, not truly secret) |

**Note on GCP Service Authentication**: The Cloud Run services will use **Workload Identity** — the service binds directly to the `gita-ingest-worker` service account without a JSON key file. This is more secure than downloading a key. The service account already has Editor role, which grants access to Speech-to-Text, Cloud Storage, Drive API, and Secret Manager.

**Accessing Secrets in Code**:
```python
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/gita-agent-prod/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

### 5.5 APIs Required

| API | Status | Action Needed |
|-----|--------|---------------|
| Google Drive API | Enabled | None |
| Cloud Storage API | Enabled | None |
| Cloud Logging API | Enabled | None |
| Cloud Monitoring API | Enabled | None |
| Cloud Text-to-Speech API | Enabled (not needed) | Can disable — we need Speech-to-**Text**, not Text-to-Speech |
| **Cloud Speech-to-Text API** | **Not Enabled** | **Enable before implementation** |
| **Cloud Run Admin API** | **Not Enabled** | **Enable before deployment** |
| **Secret Manager API** | **Not Enabled** | **Enable before implementation** |
| **Generative Language API** | **Not Enabled** | **Enable for Gemini 3 Flash access** |

**Enable command**:
```bash
gcloud services enable \
    speech.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    generativelanguage.googleapis.com \
    --project=gita-agent-prod
```

### 5.6 CI/CD (Future)

Not in scope for MVP. Manual deployment via `gcloud run deploy`. When ready:
-   GitHub Actions → Google Cloud Build → Cloud Run deploy.
-   Triggered on push to `main` branch.

---

## 6. Frontend (MVP)

### `adk web` — Built-in Development UI

For the MVP, we use the ADK's built-in web interface. No frontend code is needed.

**Run locally**:
```bash
cd gita-agent/agent
adk web --port 8000
```

This launches a chat interface at `http://localhost:8000` with:
-   Text input for queries.
-   Message history (session-aware).
-   Tool call visibility (see when `search_transcripts` is invoked).

**Limitations**: Development-only, not suitable for sharing publicly. A custom frontend (React, Mesop, or Streamlit) can be built later as a separate phase.

---

## 7. Testing Strategy: Test-Driven Development

### 7.1 TDD Approach

Tests are written **before** implementation for each component. The cycle is: write test → see it fail (red) → implement → see it pass (green) → refactor.

### 7.2 Test Specifications by Component

**Ingestion Service Tests** (`tests/test_ingestion.py`):
| Test | Description |
|------|-------------|
| `test_extract_audio_produces_valid_flac` | Given a valid MP4, ffmpeg produces a mono 16kHz FLAC file |
| `test_extract_audio_rejects_corrupt_mp4` | Corrupt MP4 raises `AudioExtractionError`, job marked `failed` |
| `test_extract_audio_handles_silent_track` | Silent audio produces empty transcript, logs warning, skips embedding |
| `test_ingest_endpoint_returns_202` | POST /api/v1/ingest returns 202 with job_id |
| `test_ingest_skips_already_indexed` | Files already in Pinecone are skipped unless force_reindex=True |
| `test_job_status_tracks_progress` | GET /api/v1/jobs/{id} returns current step and file count |
| `test_drive_folder_listing` | Service account can list files in the shared Drive folder |

**Transcription Tests** (`tests/test_transcription.py`):
| Test | Description |
|------|-------------|
| `test_chirp3_returns_telugu_text` | Given Telugu audio, Chirp 3 returns text with `te-IN` language code |
| `test_chirp3_detects_english_segments` | English segments in mixed audio are detected and transcribed correctly |
| `test_diarization_identifies_two_speakers` | Output contains at least two distinct speaker labels |
| `test_word_timestamps_are_sequential` | Word-level timestamps are monotonically increasing |

**Translation Tests** (`tests/test_translation.py`):
| Test | Description |
|------|-------------|
| `test_gemini_translates_telugu_to_english` | Telugu text is translated to coherent English |
| `test_english_passthrough` | Already-English text is returned unchanged |
| `test_sanskrit_terms_preserved` | Terms like "dharma", "karma", "atman" are kept in Sanskrit |
| `test_speaker_labels_preserved` | Speaker 1 / Speaker 2 labels survive translation |
| `test_fallback_to_translate_api` | On Gemini failure, falls back to Cloud Translation API |

**Chunking & Embedding Tests** (`tests/test_chunking.py`):
| Test | Description |
|------|-------------|
| `test_chunk_size_within_limit` | No chunk exceeds 500 tokens |
| `test_chunk_overlap` | Adjacent chunks share ~50 tokens of overlap |
| `test_chunk_splits_on_sentence_boundary` | Chunks don't split mid-sentence |
| `test_embedding_dimension` | Embedding vectors are exactly 768 dimensions |
| `test_metadata_attached_to_chunk` | Each chunk has video_id, timestamps, speaker labels |

**MCP Server Tests** (`tests/test_mcp_server.py`):
| Test | Description |
|------|-------------|
| `test_search_transcripts_returns_results` | Valid query returns ranked chunks from Pinecone |
| `test_search_transcripts_empty_query` | Empty string returns empty results, no error |
| `test_get_video_metadata_valid_id` | Known video_id returns title, date, chunk count |
| `test_get_video_metadata_invalid_id` | Unknown video_id returns helpful error message |
| `test_tool_listing` | MCP server exposes exactly 2 tools |

**Agent Integration Tests** (`tests/test_agent.py`):
| Test | Description |
|------|-------------|
| `test_agent_uses_search_tool` | Agent calls search_transcripts for a Gita question |
| `test_agent_cites_sources` | Response includes session date and/or timestamp references |
| `test_agent_handles_no_results` | When no relevant chunks found, agent says so gracefully |
| `test_agent_distinguishes_speakers` | Agent can reference what "Nanna said" vs. "Udaya asked" |

### 7.3 Golden Set

20 QA pairs, manually verified, covering:
-   Direct Gita questions ("What is dharma according to Chapter 2?")
-   Contextual questions ("What did Nanna explain about karma yoga?")
-   Edge cases ("Tell me about quantum physics" — should say not in recordings)
-   Multi-turn conversations (follow-up questions referencing prior context)

### 7.4 Validation & Fuzz Testing

**Bad Data Handling**:
1.  Corrupt MP4s: Pipeline detects invalid headers, marks job as `failed` (not crashed).
2.  Silent audio: STT returns empty → log warning, skip embedding.
3.  Very long recordings: Graceful chunking, no OOM.

**Fuzz Testing** (using `hypothesis` library):
-   Random JSON payloads for `POST /api/v1/ingest`.
-   Malformed `job_id` strings for `GET /api/v1/jobs/{id}`.
-   Text fuzzing: Queries with emojis, 100k characters, SQL injection patterns → agent handles gracefully.

---

## 8. Project Structure

```
gita-agent/
├── agent/
│   ├── __init__.py
│   ├── agent.py              # ADK agent definition (root_agent)
│   └── .env                  # Local dev: GOOGLE_API_KEY
├── mcp_server/
│   ├── __init__.py
│   ├── server.py             # MCP server (gita-context-server)
│   ├── pinecone_client.py    # Pinecone query logic
│   └── embeddings.py         # text-embedding-004 wrapper
├── ingestion/
│   ├── __init__.py
│   ├── main.py               # FastAPI app
│   ├── audio.py              # ffmpeg audio extraction
│   ├── transcription.py      # Chirp 3 STT logic
│   ├── translation.py        # Gemini translation logic
│   ├── chunking.py           # Text chunking + embedding
│   └── drive.py              # Google Drive API client
├── tests/
│   ├── __init__.py
│   ├── test_ingestion.py
│   ├── test_transcription.py
│   ├── test_translation.py
│   ├── test_chunking.py
│   ├── test_mcp_server.py
│   └── test_agent.py
├── docs/
│   ├── detailed_technical_design.md   # This document
│   ├── task.md                        # Task tracking
│   └── SETUP_GUIDE.md                # Credential setup
├── Dockerfile                # For Cloud Run deployment
├── requirements.txt          # Python dependencies
├── pyproject.toml            # Project config + test config
└── README.md
```

---

## 9. Dependencies

```
# Core
google-adk>=1.0.0
google-cloud-speech>=2.0.0
google-cloud-storage>=2.0.0
google-generativeai>=0.8.0
pinecone-client>=3.0.0
mcp>=1.0.0
fastapi>=0.110.0
uvicorn>=0.27.0
ffmpeg-python>=0.2.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
hypothesis>=6.0.0
httpx>=0.27.0          # For testing FastAPI endpoints

# Utilities
python-dotenv>=1.0.0
structlog>=24.0.0      # Structured logging
```

---

## 10. Appendix: Fallback Strategy (Option B)

If the two-step pipeline (Chirp 3 + Gemini translation) proves difficult to maintain, we can switch to **Option B: Gemini Direct**.

```
Video → ffmpeg → Audio (WAV) → Gemini 3 Flash (multimodal audio) → English text → Embed → Pinecone
```

**Trade-offs**:
-   Simpler (single API call).
-   No diarization or word timestamps.
-   Potential hallucination in transcription.
-   Higher cost per audio hour (Gemini token pricing vs. STT pricing).

This fallback requires minimal code changes — replace the `transcription.py` + `translation.py` modules with a single `gemini_transcribe.py` module.
