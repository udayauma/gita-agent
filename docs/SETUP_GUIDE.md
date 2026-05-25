# Project Setup Guide: Credentials & Configuration

This guide walks you through all the setup needed to run the Gita Agent.

---

## Part 1: GCP Project (Already Created)

**Project**: `gita-agent-prod` (Project ID: `gita-agent-prod`)

The project already exists with:
-   `udayauma@gmail.com` as Owner
-   `gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com` as Editor

### 1.1 Enable Missing APIs

Run this command in Cloud Shell or your local terminal (with `gcloud` authenticated):

```bash
gcloud services enable \
    speech.googleapis.com \
    run.googleapis.com \
    secretmanager.googleapis.com \
    generativelanguage.googleapis.com \
    --project=gita-agent-prod
```

Or enable each manually in the GCP Console:
1.  Go to [APIs & Services > Library](https://console.cloud.google.com/apis/library?project=gita-agent-prod)
2.  Search for and enable each:
    -   **Cloud Speech-to-Text API** (for Chirp 3 transcription)
    -   **Cloud Run Admin API** (for deploying the agent)
    -   **Secret Manager API** (for storing API keys)
    -   **Generative Language API** (for Gemini 3 Flash)

### 1.2 Share Google Drive Folder with Service Account

The ingestion pipeline needs to download recordings from your Google Drive. Share the folder with the service account:

1.  Open your Google Drive and navigate to the **"Bhagavad Gita Sessions"** folder
    ([Direct Link](https://drive.google.com/drive/u/0/folders/1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA))
2.  Right-click the folder name **"Bhagavad Gita Sessions"** and select **"Share"** → **"Share"**
3.  In the "Add people, groups, and calendar events" field, paste:
    ```
    gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com
    ```
4.  Set the permission to **"Viewer"** (read-only access is sufficient)
5.  **Uncheck** "Notify people" (service accounts can't receive emails)
6.  Click **"Share"**

**Verification**: After sharing, you should see `gita-ingest-worker` listed under "People with access" on the folder's sharing settings.

### 1.3 Create Cloud Storage Bucket

The ingestion pipeline uploads extracted audio files to GCS for Chirp 3 processing.

```bash
gsutil mb -p gita-agent-prod -l us-central1 gs://gita-agent-prod-audio
```

Or in the GCP Console:
1.  Go to [Cloud Storage > Buckets](https://console.cloud.google.com/storage/browser?project=gita-agent-prod)
2.  Click **"Create"**
3.  Name: `gita-agent-prod-audio`
4.  Location: `us-central1` (or your preferred region)
5.  Storage class: Standard
6.  Access control: Uniform
7.  Click **"Create"**

### 1.4 Service Account Authentication

**For Cloud Run (Staging)**: Uses **Workload Identity** — no JSON key file needed. Cloud Run services bind directly to the `gita-ingest-worker` service account.

**For Local Development**: You need a JSON key file.
1.  Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceAccounts?project=gita-agent-prod)
2.  Click on `gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com`
3.  Go to the **Keys** tab
4.  Click **Add Key** → **Create new key** → **JSON** → **Create**
5.  Save the downloaded file as `service-account.json` in the project root
6.  **IMPORTANT**: This file is in `.gitignore` — never commit it!

Set the environment variable for local use:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="./service-account.json"
```

---

## Part 2: Pinecone Vector Database

1.  Go to [Pinecone.io](https://www.pinecone.io/) and sign up (free tier).
2.  Create an **Index**:
    -   **Name**: `gita-videos`
    -   **Dimensions**: `768` (matches Google's `text-embedding-004`)
    -   **Metric**: `cosine`
    -   **Cloud**: `AWS` (free tier) or `GCP`
3.  Go to **API Keys** (left menu) and copy your API key.

---

## Part 3: Google Secret Manager

Store all secrets in Secret Manager for the Cloud Run services to access.

```bash
# Pinecone API Key
echo -n "YOUR_PINECONE_API_KEY" | \
    gcloud secrets create pinecone-api-key \
    --data-file=- \
    --project=gita-agent-prod

# Gemini API Key
echo -n "YOUR_GEMINI_API_KEY" | \
    gcloud secrets create google-api-key \
    --data-file=- \
    --project=gita-agent-prod
```

Grant the service account access to read secrets:
```bash
gcloud secrets add-iam-policy-binding pinecone-api-key \
    --member="serviceAccount:gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=gita-agent-prod

gcloud secrets add-iam-policy-binding google-api-key \
    --member="serviceAccount:gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=gita-agent-prod
```

---

## Part 4: Local Development Environment

```bash
# Clone the repository
git clone https://github.com/udayauma/gita-agent.git
cd gita-agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure local environment
cp .env.example .env
# Edit .env with your keys:
#   GOOGLE_API_KEY=your-gemini-api-key
#   PINECONE_API_KEY=your-pinecone-api-key
#   GOOGLE_APPLICATION_CREDENTIALS=./service-account.json

# Verify ADK works
cd agent
adk web --port 8000
# Visit http://localhost:8000
```

---

## Part 5: Ingestion as a Cloud Run Job

The ingestion pipeline runs as a **Cloud Run Job** (not a Service) — see `docs/technology_decisions.md` § 8 for the rationale. Same code path runs locally (`python -m ingestion.orchestrator`) and inside the deployed Job container; the Dockerfile entrypoint is the same Python invocation.

### 5.1 Local Smoke Test

Before deploying, verify the image builds and the CLI runs:

```bash
cd /path/to/gita-agent

# Build the image
docker build . -f Dockerfile.ingestion -t gita-ingest:local

# Run --help to confirm the entrypoint works (no real API calls)
docker run --rm gita-ingest:local --help

# Optionally: dry-run against your actual env (requires creds + env vars passed in)
docker run --rm \
    -e GCP_PROJECT_ID=gita-agent-prod \
    -e GCS_AUDIO_BUCKET=gita-agent-prod-audio \
    -e DRIVE_FOLDER_ID=1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA \
    -e GOOGLE_APPLICATION_CREDENTIALS=/secrets/service-account.json \
    -v $(pwd)/service-account.json:/secrets/service-account.json:ro \
    gita-ingest:local --dry-run
```

### 5.2 Deploy the Cloud Run Job

```bash
gcloud run jobs deploy ingest-recordings \
    --source . \
    --region us-central1 \
    --project gita-agent-prod \
    --service-account gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com \
    --memory 2Gi \
    --cpu 2 \
    --task-timeout 60m \
    --max-retries 0 \
    --set-env-vars="GCP_PROJECT_ID=gita-agent-prod,GCS_AUDIO_BUCKET=gita-agent-prod-audio,DRIVE_FOLDER_ID=1hWMRJRvw5di8WF7WpDPH1a311FAIpbPA,PINECONE_INDEX_NAME=gita-videos" \
    --set-secrets="GOOGLE_API_KEY=google-api-key:latest,PINECONE_API_KEY=pinecone-api-key:latest"
```

Notes:
-   `--source .` triggers Cloud Build to build from `Dockerfile.ingestion` (auto-detected by name? — if Cloud Build doesn't pick it up, add `--dockerfile Dockerfile.ingestion`).
-   `--task-timeout 60m` is generous; a single ~1-hour MP4 typically completes in 5–10 minutes (download + Chirp 3 LRO + Gemini translation dominate).
-   `--max-retries 0` because the orchestrator handles per-video errors internally; we don't want Cloud Run retrying the *entire* batch on a single transient failure.
-   The service account already has Editor role on the project, which covers Speech-to-Text, Storage, Secret Manager, and Drive access.

### 5.3 Trigger an Ingestion Run

Manual one-shot (recommended after uploading a new recording to Drive):

```bash
gcloud run jobs execute ingest-recordings \
    --region us-central1 \
    --project gita-agent-prod \
    --wait
```

`--wait` blocks until the job completes and prints exit status. Without it, the command returns immediately and you'd track progress via `gcloud run jobs executions list`.

To process a specific video (e.g., re-process after a bug fix), pass CLI args via `--args`:

```bash
gcloud run jobs execute ingest-recordings \
    --region us-central1 \
    --args="--video-id=nanna_udaya_2025_07_06,--force-reindex" \
    --wait
```

### 5.4 Observing a Run

-   **Live logs**: `gcloud run jobs executions logs read EXECUTION_ID --region us-central1`
-   **Execution status**: `gcloud run jobs executions list --region us-central1`
-   **Cloud Console**: [Cloud Run → Jobs → ingest-recordings](https://console.cloud.google.com/run/jobs?project=gita-agent-prod)
-   **Cloud Trace** (after Phase 4.7 observability lands): traces appear under service name `ingest-recordings` with end-to-end spans for download → embed.

### 5.5 Optional: Scheduled Trigger

To run automatically on a cron (e.g., scan Drive every Sunday at 8am):

```bash
gcloud scheduler jobs create http ingest-weekly \
    --schedule="0 8 * * 0" \
    --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/gita-agent-prod/jobs/ingest-recordings:run" \
    --http-method=POST \
    --oauth-service-account-email=gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com \
    --location us-central1
```

Not required for MVP — manual `gcloud run jobs execute` is fine while recordings come in irregularly.

---

## Checklist

- [ ] Enable 4 missing APIs (Speech-to-Text, Cloud Run, Secret Manager, Generative Language)
- [ ] Share Drive folder with `gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com`
- [ ] Create GCS bucket `gita-agent-prod-audio`
- [ ] Download service account JSON key for local dev
- [ ] Sign up for Pinecone and create `gita-videos` index
- [ ] Store secrets in Google Secret Manager
- [ ] Set up local Python environment and verify `adk web` runs
- [ ] (Phase 4.6.3) Smoke-test `Dockerfile.ingestion` locally: `docker build . -f Dockerfile.ingestion -t gita-ingest:local && docker run --rm gita-ingest:local --help`
- [ ] (Phase 7) Deploy ingestion as a Cloud Run Job via the command in § 5.2
