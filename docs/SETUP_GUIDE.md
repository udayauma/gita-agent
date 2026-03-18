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

## Checklist

- [ ] Enable 4 missing APIs (Speech-to-Text, Cloud Run, Secret Manager, Generative Language)
- [ ] Share Drive folder with `gita-ingest-worker@gita-agent-prod.iam.gserviceaccount.com`
- [ ] Create GCS bucket `gita-agent-prod-audio`
- [ ] Download service account JSON key for local dev
- [ ] Sign up for Pinecone and create `gita-videos` index
- [ ] Store secrets in Google Secret Manager
- [ ] Set up local Python environment and verify `adk web` runs
