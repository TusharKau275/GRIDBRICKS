# Wind Forecast Monitor 🌬️

A full-stack web application for monitoring UK national wind generation forecasts and quantifying their accuracy, designed for energy traders making day-ahead market decisions.

> **Live app:** [https://frontend-nine-psi-28.vercel.app/](https://frontend-nine-psi-28.vercel.app/)

---

## What it does

UK energy utilities buy electricity on the **day-ahead market**. Decisions for delivery day **D** are typically made by **09:00 UK time on D-1**. This app helps traders:

1. **See the latest wind forecast** available at decision time — and understand how confident to be in it.
2. **Quantify forecast accuracy** across the whole month so they can add an appropriate safety margin.

## Screenshots

| Forecast Page | Accuracy Page |
|---|---|
| Interactive chart of forecast vs actual with P90 uncertainty band | KPI cards, error by hour, by wind level, and by forecast horizon |

---

## Project Structure

```
GRIDWORKS/
├── backend/                  # Python FastAPI backend
│   ├── main.py               # FastAPI app with all endpoints
│   ├── analytics.py          # Core data logic & metrics
│   ├── models.py             # Pydantic response models
│   ├── test_analytics.py     # Unit tests (pytest)
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile
│   └── __init__.py
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx           # Root with routing
│   │   ├── api.js            # API client
│   │   ├── components.jsx    # Shared UI components
│   │   ├── index.css         # Design system
│   │   ├── main.jsx          # Entry point
│   │   └── pages/
│   │       ├── ForecastPage.jsx   # Page 1: Daily forecast
│   │       └── AccuracyPage.jsx   # Page 2: Monthly accuracy
│   ├── index.html
│   ├── vercel.json           # Vercel SPA config
│   ├── Dockerfile
│   └── package.json
├── data/                     # CSV data files
│   ├── wind_actuals.csv      # Half-hourly actual generation
│   └── wind_forecasts.csv    # Multiple forecasts per slot
├── docker-compose.yml
├── Procfile                  # Heroku/Render deployment
├── .gitignore
└── README.md
```

## API Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/health` | Health check with data counts |
| `GET /api/dates` | Available delivery dates |
| `GET /api/forecast?date=YYYY-MM-DD&cutoff_hour=9` | Forecast vs actual for a day |
| `GET /api/metrics?cutoff_hour=9` | Monthly accuracy metrics |
| `GET /api/horizon-error` | Error by forecast horizon |

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend
```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000
```

### Frontend (in a second terminal)
```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

### Run Tests
```bash
python -m pytest backend/test_analytics.py -v
```

---

## Running with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000

---

## Deployment

### Frontend → Vercel
- **Live URL:** [https://frontend-nine-psi-28.vercel.app/](https://frontend-nine-psi-28.vercel.app/)
1. Connect the `frontend/` directory to Vercel.
2. Set env var `VITE_API_URL` to your backend URL.
3. `vercel.json` handles SPA routing.

### Backend → Render / Heroku
- **Render:** Create a Web Service pointing to the repo root. It will detect the `Procfile`.
- **Heroku:** `git push heroku main` — uses the `Procfile`.
- Ensure the `data/` directory is included in the deploy.

---

## Key Assumptions

| Assumption | Detail |
|---|---|
| **Decision cutoff** | Default 09:00 UK time on D-1 (configurable) |
| **Timezone** | All display times are UK time (`Europe/London`). January 2026 = GMT (UTC+0). |
| **Scope** | National UK wind only, January 2026 only |
| **Forecast selection** | For each target half-hour, the latest forecast published ≤ cutoff is used |
| **Error definition** | `error = forecast − actual` (positive = over-forecast) |
| **Wind level buckets** | Terciles of actual generation: Low / Medium / High |
| **Uncertainty band** | ± P90 absolute error computed across the full month |

---

## Use of AI Tools

This project was developed with the assistance of modern AI developer tooling, combining automated generation with human technical oversight, domain-specific validation, and code review.

### Tools Utilized
- **Google Antigravity / Gemini**: Primary agentic coding assistant for full-stack scaffolding, architectural design, Pandas vectorization, API schema definition, and interactive UI component development.
- **LLM-Assisted Code Generation & Refactoring**: Used to generate unit test suites (`pytest`), Docker containerization configurations, and vanilla CSS design system tokens.

### How AI Was Applied
1. **Architecture & API Design**:
   - Drafting clean RESTful contracts between the FastAPI backend and React frontend.
   - Structuring Pydantic V2 response models with float sanitization (`NaN`/`Inf` handling for JSON compliance).
2. **Domain Logic & Data Analytics (`analytics.py`)**:
   - Vectorized Pandas operations for zero-lookahead forecast selection (`publishTime <= cutoff_utc` grouped by target settlement period).
   - Empirical statistical calculations: MAE, RMSE, systematic bias, and historical P90 absolute error bands.
   - Timezone reconciliation between UTC timestamps and UK local time (`Europe/London`).
3. **Frontend & Visualizations**:
   - Building Recharts components including the day-ahead `ComposedChart` with shaded uncertainty intervals.
   - Crafting custom dark-mode CSS tokens, glassmorphic card layouts, and responsive metric grids.
4. **Testing & QA**:
   - Generating edge-case unit tests in `backend/test_analytics.py` to prevent data leakage and ensure mathematical accuracy.
5. **DevOps & Documentation**:
   - Authoring `docker-compose.yml`, multi-stage Dockerfiles, deployment configurations (`Procfile`, `vercel.json`), and comprehensive technical documentation.

### Human Verification & Quality Control
- **Market Rules & Anti-Lookahead Logic**: Rigorously verified that forecast filtering strictly excludes any publications after the D-1 09:00 cutoff.
- **Mathematical Accuracy**: Cross-checked formulas for MAE, RMSE, bias, and percentile calculation against manual numpy calculations.
- **Bug Fixes & Refactoring**: Resolved package import paths across monorepo and container environments, and tuned React `useMemo` hooks for smooth cutoff slider interaction.
- **Security & Best Practices**: Audited CORS settings, environment variable bindings, and removed all secrets and hardcoded credentials.

---

