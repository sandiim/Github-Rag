# Agent entry point

- Read `PROJECT_STATE.md` for current status and the next task. Read `README.md` for local startup and verification commands.
- For a specific change, read only the relevant parts of `docs/architecture.md`, `docs/decisions/`, or `ui-improvements.md`; do not load every document by default.
- Follow the project conventions in `AGENT.md`. Preserve `.env` and unrelated working-tree edits. Never expose or commit secrets.
- Keep FastAPI routes thin, integrations within their modules, and frontend API calls in the typed client. Add focused tests for behavior changes and run relevant checks before claiming success.
- Update `PROJECT_STATE.md` after meaningful milestones, including what was verified and what remains open.
