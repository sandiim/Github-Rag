# GitHub Repository RAG

A single-user local web app that indexes public or private GitHub repositories and answers questions with commit-pinned file and line citations.

## Run locally

1. Copy `.env.example` to `.env` and keep your existing GitHub and model credentials there. Add local values for `DATABASE_URL`, `OLLAMA_BASE_URL`, and `EMBEDDING_MODEL` if they are not already present.
2. Start PostgreSQL: `docker compose up -d postgres`.
3. Start the API:

   ```powershell
   cd backend
   alembic upgrade head
   uvicorn app.main:app --reload
   ```

4. In a second terminal, start the ingestion worker (from the repository root):

   ```powershell
   cd backend
   python -m app.worker
   ```

5. In a third terminal, start the web app:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

Vite proxies `/repositories` requests to FastAPI at `http://127.0.0.1:8000` during local development.
Adding a repository returns immediately with a queued job. Keep the worker terminal running to download and index files. If it is stopped, the library shows “Waiting for worker”; restart it to resume queued jobs. Failed jobs remain visible with a Retry action. A rebuild keeps the prior index available until a replacement succeeds.

## Verify

```powershell
cd backend; alembic upgrade head; python -m pytest -q
cd ..\frontend; npm test -- --run; npm run build
```
