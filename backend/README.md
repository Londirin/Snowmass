# Snowmass Pod Recommender Backend

FastAPI service that recommends Snowmass ski pods using strict user constraints and forecast-driven scoring.

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
uvicorn app.main:app --reload
```

## Test
```bash
pytest
```

## Notes
- Forecast source: Open-Meteo hourly endpoint.
- Snowmass location constants: `lat=39.2094`, `lon=-106.9495`.
- On weather failures, the API uses neutral assumptions and lowers confidence.

## Future Work
- Integrate resort ops/lift status feeds.
- Add crowds estimation from historical + telemetry data.
- Move from pod-level recommendations to run-level routing.
- Collect user feedback labels to personalize scoring.
