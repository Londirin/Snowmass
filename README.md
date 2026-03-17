# Snowmass Pod Recommendation MVP

Production-style MVP for recommending Snowmass ski pods using strict user constraints and Open-Meteo hourly forecasts.

For the simplest local launch on this computer, start with [START_HERE.md](./START_HERE.md).

## Project Structure
- `backend/`: FastAPI API, terrain dataset, scoring logic, tests.
- `frontend/`: Static HTML/CSS/JS single-page UI.

## Run locally
This project has two small parts:
- The backend is the brain. It picks the best Snowmass pod based on your settings and weather.
- The frontend is the page you open in your browser.

On Windows:
1. Install Python 3.11 from [python.org](https://www.python.org/downloads/windows/).
2. Open PowerShell in this folder.
3. Install backend packages:
```powershell
python -m pip install -r .\backend\requirements.txt
```
4. Start the backend:
```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir .\backend
```
5. In a second PowerShell window, start the frontend:
```powershell
node .\frontend\server.js
```
6. Open [http://127.0.0.1:3000](http://127.0.0.1:3000)
7. Quick checks:
   - Backend health: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
   - Frontend: [http://127.0.0.1:3000](http://127.0.0.1:3000)

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
- `GET /health` -> `{"ok": true}`
- `POST /recommend` -> top 3 pod recommendations (with best 2-hour window, reasons, and excluded pods)

## Recommendation Design
1. Apply strict hard constraints first.
2. Pull forecast hours from Open-Meteo.
3. Score each pod per hour and select best contiguous 2-hour window.
4. Return top pods with explainability bullets (2-5).
5. If weather unavailable, use neutral assumptions and reduce confidence.

## Future Work
- Resort operations feed integration (lifts, closures, grooming reports).
- Better crowd modeling and dynamic congestion penalties.
- Run-level route suggestions beyond pod-level.
- Feedback-driven personalization from user labels.
