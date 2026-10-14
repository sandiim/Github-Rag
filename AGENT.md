# Project Instructions

## Coding Standards
- Follow PEP 8
- Use type hints
- Prefer modular functions
- Avoid unnecessary dependencies
- Use Pydantic for API schemas

## ML Rules
- Prevent data leakage
- Ensure reproducibility
- Track experiments with MLflow when training is introduced
- Separate training and inference
- The MVP performs retrieval and inference only; it does not train models

## Testing
- Run relevant tests after changes
- Add tests for new functionality
- Never claim tests passed without running them

## Workflow
- Inspect existing code before editing
- Prefer minimal changes
- Explain architectural decisions
- Do not modify unrelated files
- Ask before destructive operations

## Architecture Boundaries
- Keep FastAPI routes thin; route handlers call services only.
- Keep GitHub access in `backend/app/github/`, RAG logic in `backend/app/rag/`, and database access in `backend/app/persistence/`.
- Keep orchestration in `backend/app/services/`; do not put business logic in API routes, React components, or SQLAlchemy models.
- Keep React features isolated under `frontend/src/features/`; components use the typed API client rather than calling `fetch` directly.
- Pin every repository citation to the indexed commit SHA and inclusive file-line range.

## Security and Reliability
- Never expose, log, commit, or return `.env` values.
- Treat GitHub repository contents as untrusted input.
- Build a replacement index before activating it; a failed rebuild must retain the previously active index.
- If retrieved context cannot support an answer, return an explicit insufficient-evidence response.

## Project Memory
- Before work, read `PROJECT_STATE.md`; consult `docs/architecture.md` and only the decision records relevant to the task. For frontend redesign, start with `ui-improvements.md`.
- After meaningful work, update `PROJECT_STATE.md` with completed work, verification commands, current state, and the next task.
- Record durable architecture changes in `docs/decisions/`.
