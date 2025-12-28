# Project Setup Guide: Credentials & Keys

This guide will walk you through obtaining the necessary API keys to run the Gita Agent.

## Part 1: Google Cloud Platform (GCP) Setup
*We need GCP for accessing your Google Drive files and using the Speech-to-Text service.*

### 1. Create a Project
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Log in with your Google Account.
3.  Click the project dropdown (top left) and select **"New Project"**.
4.  Name it `gita-agent-prod` and click **Create**.
5.  *Note: You may need to enable billing, but we will stay within free/low-cost tiers.*

### 2. Enable APIs
1.  In the Search bar at the top, type **"Google Drive API"**.
    -   Click it -> Click **Enable**.
2.  Search for **"Cloud Speech-to-Text API"**.
    -   Click it -> Click **Enable**.

### 3. Create Service Account (Your "Robot" User)
1.  Go to **IAM & Admin** > **Service Accounts** (left menu).
2.  Click **+ Create Service Account**.
3.  **Name**: `gita-ingest-worker`.
4.  **Grant Access**: Select **Project** > **Editor** (simplest for now) or **Viewer**.
5.  Click **Done**.

### 4. Download Key (JSON)
1.  Click on the email address of the service account you just created.
2.  Go to the **Keys** tab (top bar).
3.  Click **Add Key** > **Create new key**.
4.  Select **JSON** and click **Create**.
5.  **Save this file!** This is your master key. Rename it to `service-account.json`.

---

## Part 2: Pinecone Vector Database
*This is the "Brain Memory" where we store the video content.*

1.  Go to [Pinecone.io](https://www.pinecone.io/) and click **Sign Up Free**.
2.  Log in (you can use your Google info).
3.  Create a **Index**:
    -   **Name**: `gita-videos`
    -   **Dimensions**: `768` (Standard for Google embeddings).
    -   **Metric**: `cosine`.
    -   **Cloud**: `GCP` (if available) or `AWS` (Free tier is usually on AWS, which is fine).
4.  Go to **API Keys** (left menu).
5.  Copy your **API Key**.

---

## Part 3: Configuration (Action Item)
Once you have these two items:
1.  `service-account.json` file.
2.  Pinecone API Key (string).

Let me know, and I will show you where to place them in the project!
