# Snowmass Pod Recommender Frontend

Static HTML + vanilla JS UI served by FastAPI at `/` (same-origin API calls).

## Run
1. Start app with `make dev` from repository root.
2. Open `http://127.0.0.1:8000`.

The page supports:
- Constraint + preference inputs
- Data source status panel (`/sources/status`)
- Recommendation rendering from `/recommend`
- Excluded pod reasons
