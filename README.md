# Snowmass Pod Recommendation MVP

Production-style MVP for recommending **Snowmass ski pods** using strict user constraints, Open-Meteo hourly forecast data, and Aspen Snowmass raw station data.

## Project Structure
- `backend/`: FastAPI API, terrain dataset, data clients, scoring logic, tests.
- `frontend/`: Static HTML/CSS/JS single-page UI served by FastAPI (same origin).

## Data Sources
1. **Open-Meteo** (programmatic): hourly forecast for temperature, precipitation, wind, and cloud cover.
2. **Aspen Snowmass raw station feed** (programmatic): `https://weather.aspensnowmass.com/SNOWMASS-SUMMARY.HTM`
3. **Snow & Grooming report page** (human-facing): `https://www.aspensnowmass.com/four-mountains/snowmass/snow-and-grooming-report`
   - We reference this page for users/documentation.
   - We do **not** scrape it for brittle run-level grooming extraction in this MVP.

## Quickstart
### 1) Setup backend env
```bash
make setup-backend
```

### 2) Run full app (API + frontend) on one port
```bash
make dev
```
App URL: `http://127.0.0.1:8000`

### 3) Run tests
```bash
make test-backend
```

## Feature Flag
Disable Aspen raw ingest when needed:
```bash
ASPEN_RAW_ENABLED=0 make dev
```
When disabled/unavailable, recommendations fall back to Open-Meteo-only logic and confidence is lowered.

## API
- `GET /health`
- `GET /snow_report/raw`
- `GET /sources/status`
- `POST /recommend`

## Future Work
- Resort operations feed integration (lifts/closures).
- Better crowd modeling and dynamic congestion penalties.
- Run-level route suggestions beyond pod-level.
- Feedback-driven personalization from user labels.
