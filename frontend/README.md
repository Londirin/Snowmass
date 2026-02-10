# Snowmass Pod Recommender Frontend

Static HTML + vanilla JS UI for the recommendation API.

## Run
1. Start backend on `http://127.0.0.1:8000`.
2. Open `frontend/index.html` in your browser.

The page submits user constraints/preferences to `/recommend` and renders:
- Morning brief
- Top 3 recommended pods with explanations
- Excluded pods with strict-filter reasons
