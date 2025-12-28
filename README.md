# Hinduism & Bhagavad Gita AI Agent

A sophisticated AI agent capable of answering questions about the Bhagavad Gita using personal video context. Built with Google ADK, Model Context Protocol (MCP), and Google Cloud.

## Project Structure

- **`docs/`**: Technical designs and task tracking.
- **`agent/`**: Brain of the application. Google ADK (Python) agent with reasoning logic.
- **`ingestion/`**: Async data pipeline. Fetches Google Meet videos from Drive, transcribes them (Cloud Speech-to-Text), and indexes them into Pinecone.
- **`mcp_server/`**: Connects the Agent to the Data. Implements the Model Context Protocol to serve video transcripts as "Tools".
- **`frontend/`**: React + TailwindCSS chat interface.

## Quick Start
*Detailed instructions coming soon during Implementation Phase.*
