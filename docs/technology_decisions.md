# Technology Decisions: Why We Chose What We Chose

This document explains the reasoning behind the key technology choices in the Gita Agent. The [detailed technical design](./detailed_technical_design.md) covers *what* we're building and *how*. This document covers *why*.

---

## 1. Vector Embeddings & Semantic Search

### The Problem

Our agent needs to answer questions like *"What does Krishna say about letting go of attachment?"* by searching through transcribed recordings of Bhagavad Gita discussions. Traditional keyword search (like SQL `LIKE '%attachment%'` or full-text search) would fail here because:

- The transcripts might use the word "vairagya" (the Sanskrit term for detachment) instead of "attachment."
- A passage might discuss the concept of letting go without ever using the word "attachment" — for example, *"One must act without clinging to the fruits of action."*
- Spiritual and philosophical discussions are rich in synonyms, metaphors, and indirect references. Keyword matching misses all of this.

### What Are Vector Embeddings?

An embedding is a way to represent text as a list of numbers (a "vector") that captures its *meaning*, not just its words. When we embed the sentence *"Krishna teaches Arjuna about non-attachment"* and the sentence *"Let go of your desire for outcomes"*, the resulting vectors will be *close together* in mathematical space — because they mean similar things — even though they share almost no words.

Think of it like plotting cities on a map. Paris and Lyon are close together (both in France, similar culture). Paris and Tokyo are far apart. Embeddings do the same thing for meaning: semantically similar text ends up near each other in a high-dimensional space.

### How This Powers the Agent

When a user asks *"What is karma yoga?"*, the system:

1. **Embeds the query** into a 768-dimensional vector using Google's `text-embedding-004` model.
2. **Searches Pinecone** for the transcript chunks whose embeddings are closest to the query vector (cosine similarity).
3. **Returns the top 5 most semantically relevant passages** — regardless of exact word matches.
4. **Passes these passages to the agent (Gemini)**, which synthesizes a grounded answer with citations.

This is called **Retrieval-Augmented Generation (RAG)** — the agent *retrieves* relevant context before *generating* a response. Without RAG, the agent would rely solely on its pre-trained knowledge, which knows about the Bhagavad Gita in general but has no access to the specific insights from your father's teachings.

### Why 768 Dimensions?

Google's `text-embedding-004` produces 768-dimensional vectors. Each dimension captures some aspect of meaning (topic, sentiment, formality, domain, etc.). More dimensions = more nuance in distinguishing meanings, but also more storage and compute. 768 is the standard sweet spot for Google's embedding models — accurate enough for our use case without being wasteful.

### Why Cosine Similarity?

We use cosine similarity (not Euclidean distance or dot product) because it measures the *angle* between two vectors, not their magnitude. This means a short query like "karma" and a long passage about karma will still match well — cosine cares about *direction* (meaning), not *length* (word count).

---

## 2. Pinecone (Vector Database)

### Why Do We Need a Vector Database at All?

Once we have embeddings, we need somewhere to store them and search through them quickly. You *could* store vectors in a regular database (PostgreSQL with pgvector, for example) or even in memory (using FAISS or NumPy), but a dedicated vector database is purpose-built for this workload.

### Why Pinecone Specifically?

| Option | Pros | Cons | Why Not |
|--------|------|------|---------|
| **Pinecone** (chosen) | Fully managed, serverless, free tier, fast similarity search, zero ops | Vendor lock-in, external dependency | — |
| **Chroma** | Open source, runs locally, simple API | No managed hosting, requires persistent storage on disk | Cloud Run is stateless — local DB files vanish between requests |
| **FAISS** (Facebook) | Blazing fast, in-memory, open source | No persistence, no managed service, must load entire index into RAM | Our Cloud Run containers are ephemeral — index would need to reload on every cold start |
| **pgvector** (PostgreSQL) | Familiar SQL, combines with relational data | Requires running a PostgreSQL instance 24/7, not scale-to-zero | Defeats the purpose of serverless — we'd pay for a DB even with zero traffic |
| **Weaviate / Qdrant** | Feature-rich, open source, self-hostable | More complex to set up, overkill for our scale | We have ~4 hours of video — maybe a few hundred chunks. We don't need a heavyweight solution |

### The Decisive Factor: Stateless Architecture

Cloud Run containers are ephemeral. When a request comes in, a container spins up. When it's idle, the container is destroyed. Any files written inside the container are lost.

This means we need our vector storage to live *outside* the container. Pinecone is accessed via API over the network — the Cloud Run service just makes HTTP calls to Pinecone. No local files, no state, no cold-start database loading.

### Pinecone's Free Tier

Pinecone's free tier supports approximately 100,000 vectors. Our 4 recordings (~4 hours of discussion) will produce roughly 300–600 text chunks, each generating one 768-dimensional vector. We're using less than 1% of the free tier capacity. Even if we add 50 more recordings in the future, we'll still be well within limits.

### HNSW: How Pinecone Searches Fast

Pinecone uses **HNSW (Hierarchical Navigable Small World)** graphs for similarity search. Instead of comparing our query vector against every single stored vector (which would be slow at scale), HNSW builds a multi-layered graph structure:

- **Top layers** have few, widely-spaced nodes — good for quickly narrowing down the region of the vector space.
- **Bottom layers** have many, densely-packed nodes — good for finding the exact nearest neighbors.

The search starts at the top layer and "navigates" down, getting more precise at each level. This gives us approximate nearest-neighbor search in logarithmic time — milliseconds even with millions of vectors.

For our scale (~500 vectors), this is overkill, but it means we'll never have performance problems even if the project grows significantly.

---

## 3. MCP (Model Context Protocol)

### What Is MCP?

MCP is an open standard (created by Anthropic, adopted broadly) that defines how LLMs communicate with external tools and data sources. Think of it as a USB-C port for AI — a universal interface that any LLM can use to plug into any data source.

### Why Not Just Call Pinecone Directly from the Agent?

We *could* write a plain Python function that queries Pinecone and pass it to the agent as a tool. In fact, Google ADK supports this with `FunctionTool`. So why bother with MCP?

**Separation of concerns.** MCP creates a clean boundary between:

- **The agent** (reasoning, conversation, answering questions) — knows *nothing* about Pinecone, embeddings, or vector search.
- **The MCP server** (data retrieval) — knows *nothing* about the agent, Gemini, or conversation history.

This separation gives us:

1. **Swappability**: If we later replace Pinecone with Chroma, Weaviate, or even a SQL database, we only change the MCP server code. The agent definition doesn't change at all.
2. **Reusability**: The same MCP server could be used by a different agent (Claude, GPT, a LangChain agent) without modification. MCP is framework-agnostic.
3. **Testability**: We can test the MCP server independently — feed it queries, verify it returns the right chunks — without needing to spin up the full agent.
4. **Security**: The MCP server can enforce access controls, rate limits, and data filtering without the agent needing to be aware of them.

### How MCP Tools Enable Grounded Responses

Without tools, an LLM generates responses purely from its training data. It might know about the Bhagavad Gita in general, but it has no idea what your father specifically said about Chapter 3 in July 2025.

MCP tools give the agent a way to *look things up* before responding. The flow is:

1. User asks a question.
2. The agent decides: "I should search the transcripts for relevant context."
3. The agent calls `search_transcripts(query="...", limit=5)` — an MCP tool.
4. The MCP server embeds the query, searches Pinecone, and returns the top 5 relevant passages.
5. The agent reads the passages and crafts a response *grounded in the actual transcript data*.
6. The response includes citations (session date, timestamp) so the user can verify.

This is fundamentally different from the agent just "knowing about" the Gita. The agent is *retrieving specific, personal context* from your recordings and using it to inform its answer.

### ADK Native MCP Support

Google ADK v1.0+ has built-in MCP support via `McpToolset`. This means we don't need to run MCP as a separate network service — ADK spawns the MCP server as a subprocess and communicates with it via stdio. For deployment, we can switch to HTTP-based MCP (SSE/Streamable HTTP) without changing the agent code.

---

## 4. Chirp 3 + Gemini 3 Flash (Two-Step Translation Pipeline)

### The Problem

Our recordings are in Telugu with English code-switching (switching between languages mid-sentence). We need to convert this audio into English text for embedding and search.

No single API does this end-to-end for Telugu:

- **Google Cloud Speech-to-Text (Chirp 3)**: Can transcribe Telugu audio to Telugu text. Can transcribe English audio to English text. Can even auto-detect which language is being spoken. But it **cannot translate** Telugu to English — it only transcribes within the same language.
- **Google Translate API**: Can translate Telugu text to English text. But it doesn't understand audio — it only works with text input. Also, it's a general-purpose translator that may lose the philosophical nuance of Gita discussions.
- **Gemini 3 Flash**: Can process audio directly and understands Telugu. But it lacks precise diarization (speaker identification) and word-level timestamps.

### Why Two Steps Instead of One?

**Step 1 (Chirp 3)** gives us what no other service can:
- **Diarization**: Identifying that Speaker 1 is Nanna (the Guru) and Speaker 2 is Udaya (the Student). This is critical — the agent needs to attribute quotes correctly ("Your father explained that..." vs. "You asked about...").
- **Word-level timestamps**: Every word is tagged with its exact time in the recording. This allows the agent to cite specific moments ("At 14:32 in the July 6 session, Nanna said...").
- **Automatic language detection**: Chirp 3 recognizes when speakers switch from Telugu to English and transcribes each segment in its original language.

**Step 2 (Gemini 3 Flash)** gives us:
- **Context-aware translation**: Unlike Google Translate, Gemini understands that "dharma" in a Bhagavad Gita discussion should be preserved as "dharma" (a commonly known Sanskrit term), not translated to "duty" or "righteousness" — which are only partial translations.
- **Speaker label preservation**: We instruct Gemini to keep the Speaker 1 / Speaker 2 labels intact through translation.
- **Natural English output**: Gemini produces fluent English, not the awkward phrasing that machine translation sometimes generates for Telugu.

### Why Not Gemini Direct (Option B)?

We could skip Chirp 3 entirely and send the audio directly to Gemini, asking it to produce English text. We've documented this as our fallback (Option B in the design doc). The trade-offs:

| Aspect | Option A (Chirp 3 + Gemini) | Option B (Gemini Direct) |
|--------|---------------------------|------------------------|
| Diarization | Yes (speaker labels) | No |
| Word timestamps | Yes (per-word) | No |
| Transcription accuracy | High (ASR-optimized model) | Good but may hallucinate |
| Translation quality | High (context-aware) | High |
| Complexity | Two API calls per chunk | One API call |
| Cost | Lower (STT pricing + LLM pricing) | Higher (all LLM token pricing) |

We chose Option A because speaker attribution and timestamps matter for this project. Knowing who said what — and being able to point to the exact moment — is important for a Bhagavad Gita learning tool.

---

## 5. Google ADK (Agent Development Kit)

### Why Use a Framework at All?

You *can* build an agent by writing raw API calls to Gemini, manually managing conversation history, implementing tool-calling logic, and building your own session management. But this is like building a web app without a framework — doable, but you'd be reinventing solved problems.

ADK provides:
- **Agent Runtime**: Manages conversation state, session history, and multi-turn interactions automatically.
- **Tool Integration**: Standardized way to give the agent tools (functions, MCP servers, other agents).
- **Built-in Dev UI**: `adk web` gives us a chat interface for free — no frontend code needed for the MVP.
- **Deployment Support**: One-command deployment to Cloud Run with `gcloud run deploy`.
- **Evaluation**: Built-in eval framework for testing agent quality against golden sets.

### Why ADK Over LangChain or LlamaIndex?

| Framework | Pros | Cons | Why Not |
|-----------|------|------|---------|
| **Google ADK** (chosen) | Native Gemini integration, built-in runtime + UI, MCP support, production-ready, Google-backed | Gemini-centric (less model flexibility) | — |
| **LangChain** | Model-agnostic, massive ecosystem, lots of tutorials | Heavy abstraction layers, "chain" paradigm can be confusing, frequent breaking changes | Over-engineered for our use case. We're using one model (Gemini) and two tools. LangChain's abstractions add complexity without proportional value. |
| **LlamaIndex** | Excellent for RAG specifically, great data connectors | More focused on data indexing than agent behavior, less mature agent runtime | Good for RAG but we need a full agent (reasoning + tools + conversation), not just a retrieval pipeline. |
| **CrewAI** | Multi-agent orchestration, role-based agents | Overkill for a single-agent system | We have one agent, not a crew. |
| **Raw Gemini API** | Maximum control, no framework overhead | Must build everything yourself (state, history, tool handling, UI) | Too much boilerplate for diminishing returns. |

### The Decisive Factor: Native Ecosystem

Since we're already using Gemini (model), GCS (storage), Cloud Run (deployment), and Cloud Speech-to-Text (transcription), staying within the Google ecosystem minimizes integration friction. ADK is built for this stack.

---

## 6. Cloud Run (Serverless)

### The Core Question: How Do We Run This?

We need to host two services:
1. **Agent Service**: Receives user questions, runs the ADK agent, returns answers.
2. **Ingestion Service**: Processes video recordings into embeddings (runs infrequently).

### Why Serverless?

This is a personal project with intermittent usage. You might ask the agent 5 questions on a Saturday, then not touch it for two weeks. Traditional hosting (a VM or always-on server) would charge you 24/7 for a machine that sits idle 99% of the time.

**Cloud Run's scale-to-zero** means:
- **No traffic = $0 compute cost.** The container only exists while handling a request.
- **Billing is per-millisecond of actual use.** A 2-second agent response costs fractions of a cent.
- **No maintenance.** No OS patches, no SSH, no firewall rules, no Docker daemon to manage.

### Why Not Other Options?

| Option | Monthly Cost (Idle) | Maintenance | Why Not |
|--------|-------------------|-------------|---------|
| **Cloud Run** (chosen) | $0 (scale to zero) | None | — |
| **GKE (Kubernetes)** | ~$70+ (minimum cluster) | High (nodes, networking, RBAC) | Massively overkill. Kubernetes is for teams running dozens of services, not a single personal agent. |
| **Compute Engine (VM)** | ~$10-25 (f1-micro to e2-small) | Medium (OS updates, SSH, monitoring) | Paying for a machine that sits idle. Also requires managing Docker, systemd, nginx, etc. |
| **App Engine** | $0 (scale to zero) | Low | Viable alternative, but less flexible than Cloud Run for containerized workloads. App Engine has more opinionated conventions. |
| **Cloud Functions** | $0 (scale to zero) | None | Good for simple functions, but our agent needs a long-running process (MCP server subprocess), which doesn't fit the functions model well. |
| **Run locally** | $0 | None | Works for development (we use `adk web` locally), but not accessible from anywhere and requires your laptop to be on. |

### The Stateless Constraint

Cloud Run containers are ephemeral — when a request finishes, the container may be shut down, and everything in its filesystem is lost. This is why we can't store vectors locally (FAISS, Chroma) and must use an external service (Pinecone). It's also why we store audio files in GCS rather than on the container's disk.

This constraint is actually a *feature*: it forces a clean architecture where all state lives in purpose-built external services, making the application more resilient and easier to reason about.

---

## 7. Gemini 3 Flash (Agent Model)

### Why Gemini 3 Flash Over Other Models?

| Model | Quality | Speed | Cost | Why Not |
|-------|---------|-------|------|---------|
| **Gemini 3 Flash** (chosen) | High | Fast | Low | — |
| **Gemini 3.1 Pro** | Highest | Slower | Higher | Overkill for our use case. Flash handles Gita Q&A well. Can upgrade later if quality is insufficient. |
| **Gemini 2.5 Pro** | High | Medium | Medium | Older generation. 3 Flash is faster, cheaper, and comparably capable for our needs. |
| **GPT-4o (OpenAI)** | High | Fast | Medium | Would lose native Google ecosystem integration (ADK, GCS, Speech-to-Text). Also introduces a second vendor and API key. |
| **Claude (Anthropic)** | High | Fast | Medium | Same ecosystem concern. Also, ADK is optimized for Gemini. |

### The Decisive Factors

1. **Ecosystem alignment**: Gemini integrates natively with ADK, requiring zero adapter code.
2. **Cost for personal use**: Flash is one of the cheapest frontier models available. For a personal project with low query volume, cost matters.
3. **Upgradability**: If Flash's quality isn't sufficient for nuanced Gita discussions, upgrading to 3.1 Pro is a one-line change in `agent.py` (`model="gemini-3.1-pro"`).

---

## Summary

Every technology choice in this project follows three principles:

1. **Managed over self-hosted**: Pinecone over FAISS, Cloud Run over VMs, Chirp 3 over self-hosted Whisper. We want to build an agent, not manage infrastructure.
2. **Pay-per-use over always-on**: Cloud Run (scale to zero), Pinecone (free tier), Gemini (per-token pricing). This is a personal project — cost efficiency matters.
3. **Ecosystem coherence**: Google ADK + Gemini + Cloud Run + GCS + Cloud Speech-to-Text. Staying within one ecosystem minimizes integration friction and authentication complexity.

These choices optimize for a single developer building a meaningful personal project — not for a team building a high-scale production system. If the project grows, the architecture supports upgrading individual components (e.g., Pinecone paid tier, Gemini 3.1 Pro, GKE) without rearchitecting the whole system.
