# Snowmass Pod Recommendation MVP

Production-style MVP for recommending **Snowmass ski pods** using strict user constraints and Open-Meteo hourly forecasts.

## Project Structure
- `backend/`: FastAPI API, terrain dataset, scoring logic, tests.
- `frontend/`: Static HTML/CSS/JS single-page UI.

## Quickstart
### 1) Setup backend
```bash
make setup-backend
```

### 2) Run backend
```bash
make run-backend
```
Backend URL: `http://127.0.0.1:8000`

### 3) Run tests
```bash
make test-backend
```

### 4) Open frontend
Open `frontend/index.html` in your browser. The page calls `http://127.0.0.1:8000/recommend`.

## API
- `GET /health` → `{"ok": true}`
- `POST /recommend` → top 3 pod recommendations (with best 2-hour window, reasons, and excluded pods)

## Recommendation Design
1. Apply strict hard constraints first.
2. Pull forecast hours from Open-Meteo.
3. Score each pod per hour and select best contiguous 2-hour window.
4. Return top pods with explainability bullets (2–5).
5. If weather unavailable, use neutral assumptions and reduce confidence.

## Future Work
- Resort operations feed integration (lifts, closures, grooming reports).
- Better crowd modeling and dynamic congestion penalties.
- Run-level route suggestions beyond pod-level.
- Feedback-driven personalization from user labels.

## Example cURL requests
```bash
curl -s http://127.0.0.1:8000/health
```
Expected behavior: returns service liveness payload.

```bash
curl -s -X POST http://127.0.0.1:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{
    "max_difficulty":"blue",
    "groomers_only":true,
    "no_moguls":true,
    "low_visibility_only":false,
    "prefer_trees":1.0,
    "prefer_groomers":1.5,
    "avoid_crowds":1.0,
    "target_datetime":"2026-02-09T07:00:00-05:00",
    "time_horizon_hours":6
  }'
```
Expected behavior: favors safer, groomed blue terrain and excludes steep/mogul-heavy pods.

```bash
curl -s -X POST http://127.0.0.1:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{
    "max_difficulty":"black",
    "groomers_only":false,
    "no_moguls":false,
    "low_visibility_only":true,
    "prefer_trees":1.8,
    "prefer_groomers":0.7,
    "avoid_crowds":1.2,
    "time_horizon_hours":8
  }'
```
Expected behavior: removes highly exposed pods and prioritizes tree-covered terrain for visibility.

```bash
curl -s -X POST http://127.0.0.1:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{
    "max_difficulty":"green",
    "groomers_only":true,
    "no_moguls":true,
    "low_visibility_only":true,
    "prefer_trees":1.2,
    "prefer_groomers":2.0,
    "avoid_crowds":0.8,
    "time_horizon_hours":4
  }'
```
Expected behavior: returns a narrow set of beginner-friendly pods with low confidence if fewer than 3 survive.

## Run Checklist
- [ ] `make setup-backend`
- [ ] `make run-backend`
- [ ] `make test-backend`
- [ ] Open `frontend/index.html`
