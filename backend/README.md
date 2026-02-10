# Snowmass Pod Recommender Backend

FastAPI service that recommends Snowmass ski pods using strict constraints and dual weather sources.

## Requirements
- Python 3.11+

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
uvicorn app.main:app --reload --port 8000
```

## Test
```bash
pytest
```

## Data Sources
- Open-Meteo hourly forecast API (no API key).
- Aspen Snowmass raw station feed: `https://weather.aspensnowmass.com/SNOWMASS-SUMMARY.HTM`
- Human-facing snow/grooming page (documentation only): `https://www.aspensnowmass.com/four-mountains/snowmass/snow-and-grooming-report`

## Env Flags
- `ASPEN_RAW_ENABLED=0` disables Aspen raw data fetching.

## Safety / Reliability
- Aspen raw client uses in-memory caching (5 min TTL).
- Aspen raw client includes a basic rate-limit guard (10s minimum between outbound requests).
- If Aspen feed fails, recommendation flow falls back to Open-Meteo-only scoring and lowers confidence.

## Future Work
- Integrate resort ops/lift status feeds.
- Add crowds estimation from historical + telemetry data.
- Move from pod-level recommendations to run-level routing.
- Collect user feedback labels to personalize scoring.
