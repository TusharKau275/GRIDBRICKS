"""
Wind Forecast Monitor — FastAPI backend.

Loads wind generation actuals and forecasts at startup, then serves
JSON endpoints for the React frontend.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

try:
    from backend.analytics import (
        load_data,
        get_available_dates,
        build_forecast_vs_actual,
        compute_monthly_metrics,
        compute_horizon_error,
        get_uncertainty_band,
        compute_overall_metrics,
    )
    from backend.models import (
        HealthResponse,
        ForecastResponse,
        ForecastPoint,
        DayKPI,
        MetricsResponse,
        MetricDetail,
        HourMetric,
        WindLevelMetric,
        HorizonResponse,
        HorizonBucket,
        DatesResponse,
    )
except ModuleNotFoundError:
    from analytics import (
        load_data,
        get_available_dates,
        build_forecast_vs_actual,
        compute_monthly_metrics,
        compute_horizon_error,
        get_uncertainty_band,
        compute_overall_metrics,
    )
    from models import (
        HealthResponse,
        ForecastResponse,
        ForecastPoint,
        DayKPI,
        MetricsResponse,
        MetricDetail,
        HourMetric,
        WindLevelMetric,
        HorizonResponse,
        HorizonBucket,
        DatesResponse,
    )

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Wind Forecast Monitor",
    description="API for UK wind generation forecast analysis — January 2026",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data once at startup
ACTUALS, FORECASTS = load_data()


# ---------------------------------------------------------------------------
# Helper to safely serialise numpy/pandas types
# ---------------------------------------------------------------------------

def _safe(val):
    """Convert numpy types to Python natives for JSON serialisation."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if hasattr(val, "item"):
        return val.item()
    return val


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
def root():
    """Root endpoint welcoming visitors and linking to docs."""
    return {"message": "Wind Forecast Monitor API is running", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health", response_model=HealthResponse)
def health():
    """Simple health check returning data counts."""
    return HealthResponse(
        status="ok",
        actuals_count=len(ACTUALS),
        forecasts_count=len(FORECASTS),
    )

@app.get("/api/dates", response_model=DatesResponse)
def dates():
    """Return the list of delivery dates that have actual data."""
    return DatesResponse(dates=get_available_dates(ACTUALS))


@app.get("/api/forecast", response_model=ForecastResponse)
def forecast(
    date: str = Query(..., description="Delivery date YYYY-MM-DD"),
    cutoff_hour: int = Query(9, ge=0, le=23, description="Cutoff hour in UK time on D-1"),
):
    """
    Per half-hour forecast vs actual for a delivery day.

    Only forecasts published before the cutoff on D-1 are used.
    Includes an uncertainty band based on the month's P90 absolute error.
    """
    merged = build_forecast_vs_actual(ACTUALS, FORECASTS, date, cutoff_hour)
    p90 = get_uncertainty_band(ACTUALS, FORECASTS, cutoff_hour)

    points = []
    for _, row in merged.iterrows():
        fc = float(row["forecast"])
        points.append(ForecastPoint(
            startTime=row["startTime"].isoformat(),
            forecast=fc,
            actual=_safe(row.get("actual")),
            publishTime=row["publishTime"].isoformat(),
            error=_safe(row.get("error")),
            band_upper=round(fc + p90, 1) if p90 else None,
            band_lower=round(max(0, fc - p90), 1) if p90 else None,
        ))

    # Day-level KPI
    errors = merged["error"].dropna()
    day_kpi = DayKPI(
        mae=round(float(errors.abs().mean()), 1) if not errors.empty else None,
        rmse=round(float(np.sqrt((errors**2).mean())), 1) if not errors.empty else None,
        bias=round(float(errors.mean()), 1) if not errors.empty else None,
        n=int(len(errors)) if not errors.empty else None,
    )

    return ForecastResponse(
        date=date,
        cutoff_hour=cutoff_hour,
        points=points,
        kpi=day_kpi,
        uncertainty_mw=round(p90, 1),
    )


@app.get("/api/metrics", response_model=MetricsResponse)
def metrics(
    cutoff_hour: int = Query(9, ge=0, le=23, description="Cutoff hour in UK time on D-1"),
):
    """
    Monthly forecast accuracy metrics: overall, by hour of day, and by wind level.
    """
    result = compute_monthly_metrics(ACTUALS, FORECASTS, cutoff_hour)

    return MetricsResponse(
        cutoff_hour=cutoff_hour,
        overall=MetricDetail(**result["overall"]),
        by_hour=[HourMetric(**h) for h in result["by_hour"]],
        by_wind_level=[WindLevelMetric(**w) for w in result["by_wind_level"]],
    )


@app.get("/api/horizon-error", response_model=HorizonResponse)
def horizon_error():
    """
    Error statistics by forecast horizon bucket.

    Uses ALL forecasts (not cutoff-filtered) to show how accuracy
    degrades with longer lead times.
    """
    buckets = compute_horizon_error(ACTUALS, FORECASTS)
    return HorizonResponse(
        buckets=[HorizonBucket(**b) for b in buckets]
    )
