# GitHub Repository RAG

A single-user local web app that indexes public or private GitHub repositories and answers questions with commit-pinned file and line citations.

## Run locally

1. Copy `.env.example` to `.env` and set your GitHub token. Keep `.env` private. The example uses Ollama's local OpenAI-compatible endpoint for answers and local Ollama for embeddings.
2. Create the app-specific 8K-context model alias: `ollama create github-rag-llama3.1:8k -f ollama/Modelfile` (requires `llama3.1:latest` installed). Also install the embedding model if needed: `ollama pull nomic-embed-text:latest`.
3. Start PostgreSQL: `docker compose up -d postgres`.
4. Start the API:

   ```powershell
   cd backend
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

5. In a second terminal, start the ingestion worker (from the repository root):

   ```powershell
   cd backend
   python -m app.worker
   ```

6. In a third terminal, start the web app:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Vite proxies `/repositories` requests to FastAPI at `http://127.0.0.1:8000` during local development.
Adding a repository returns immediately with a queued job. Keep the worker terminal running to download and index files. If it is stopped, the library shows “Waiting for worker”; restart it to resume queued jobs. Failed jobs remain visible with a Retry action. A rebuild keeps the prior index available until a replacement succeeds.
R Markdown (`.rmd`/`.Rmd`) files are eligible for indexing. For a repository indexed before this change, use Rebuild in the library; the updated selection-policy version reindexes it even if its commit has not changed. Restart the API after changing `.env` so new chats use the 8K model alias.

## Verify

```powershell
cd backend; alembic upgrade head; python -m pytest -q
cd ..\frontend; npm test -- --run; npm run build
```
