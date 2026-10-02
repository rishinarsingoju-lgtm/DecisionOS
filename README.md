# DecisionOS

DecisionOS is a pharmaceutical supply-chain decision control system. It analyzes operational data, compares deterministic actions, independently verifies critical calculations, and leaves consequential decisions for human review.

## Project layout

- `frontend/` — Next.js operations interface.
- `backend/` — FastAPI, PostgreSQL, SQLAlchemy, Alembic, and deterministic decision services.
- `project_details.md` — product requirements and source of truth.
- `stitch_decisionos_enterprise_operations_console/` — original visual references.

## Local development

Configure PostgreSQL using blank-key placeholders in `backend/.env.example`; keep real local credentials only in the ignored `backend/.env` file. Apply the migration and seed the synthetic demo data using the commands in `backend/README.md`.

Run the backend from `backend/` with `python -m uvicorn app.main:app --reload --port 8000`. Run the frontend from `frontend/` with `npm run dev` (port 4000).