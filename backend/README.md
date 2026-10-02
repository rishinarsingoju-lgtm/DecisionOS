# DecisionOS Backend

The API uses PostgreSQL through SQLAlchemy. Demo business records are synthetic; the seeded CDSCO-shaped batch alert is explicitly planted and is not an official regulatory finding. External network sources are optional, and missing or stale source data is returned as such.

## Local setup

1. Create a PostgreSQL database and role, then copy `.env.example` to `.env` and set `DATABASE_URL` with that role's credentials. Never commit `.env`.
2. From the repository root, install dependencies with `python -m pip install -r backend/requirements.txt` using the selected project environment.
3. From `backend/`, apply the schema and seed the synthetic scenario:

```powershell
python -m alembic upgrade head
python scripts/seed_synthetic_data.py
```

4. Start the API from `backend/`:

```powershell
python -m uvicorn app.main:app --reload --port 8000
```

5. Start the Next.js frontend from `frontend/` with `npm run dev`; it reads the API at `http://127.0.0.1:8000` by default. Set `NEXT_PUBLIC_DECISIONOS_API_URL` to override it.

The API has no authentication and must remain on a trusted local/demo network. Approval records human review only; it never executes procurement, redistribution, or quarantine operations. Live WHO/CDSCO/NPPA ingestion is not configured by the seed. Open-Meteo can be queried through its optional adapter; absent observations are omitted.

## Tests

From `backend/`, run `python -m pytest -q`. Tests use an isolated SQLite in-memory database and do not require local PostgreSQL credentials.