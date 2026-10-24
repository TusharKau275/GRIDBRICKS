"""
Core analytics engine for wind forecast accuracy analysis.

Handles all data loading, forecast selection (respecting decision cutoff),
and error metric computation.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, time
from zoneinfo import ZoneInfo

# UK timezone for decision cutoff logic
UK_TZ = ZoneInfo("Europe/London")
UTC_TZ = ZoneInfo("UTC")

# Data directory relative to this file's parent
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load and parse the CSV files at startup. Called once."""
    actuals = pd.read_csv(
        DATA_DIR / "wind_actuals.csv",
        parse_dates=["startTime"],
    )
    forecasts = pd.read_csv(
        DATA_DIR / "wind_forecasts.csv",
        parse_dates=["startTime", "publishTime"],
    )

    # Ensure timezone-aware UTC datetimes
    for col in ["startTime"]:
        actuals[col] = pd.to_datetime(actuals[col], utc=True)
    for col in ["startTime", "publishTime"]:
        forecasts[col] = pd.to_datetime(forecasts[col], utc=True)

    # Sort for efficient lookups
    forecasts.sort_values(["startTime", "publishTime"], inplace=True)
    actuals.sort_values("startTime", inplace=True)

    return actuals, forecasts


def get_available_dates(actuals: pd.DataFrame) -> list[str]:
    """Return sorted list of delivery dates (YYYY-MM-DD) that have actuals."""
    # Convert to UK time to get the delivery date
    uk_dates = actuals["startTime"].dt.tz_convert(UK_TZ).dt.date.unique()
    return sorted([d.isoformat() for d in uk_dates])


def _compute_cutoff_utc(delivery_date: str, cutoff_hour: int) -> pd.Timestamp:
    """
    Compute the UTC timestamp for the decision cutoff.

    The cutoff is at cutoff_hour:00 UK time on D-1 (the day before delivery).
    For example, for delivery_date=2026-01-05 and cutoff_hour=9,
    the cutoff is 2026-01-04 09:00 UK time.
    """
    d = datetime.strptime(delivery_date, "%Y-%m-%d").date()
    d_minus_1 = d - pd.Timedelta(days=1)
    cutoff_uk = datetime.combine(d_minus_1, time(cutoff_hour, 0), tzinfo=UK_TZ)
    return pd.Timestamp(cutoff_uk).tz_convert(UTC_TZ)


def get_latest_forecasts(
    forecasts: pd.DataFrame,
    delivery_date: str,
    cutoff_hour: int = 9,
) -> pd.DataFrame:
    """
    For each target half-hour on the delivery date, pick the latest forecast
    whose publishTime <= the decision cutoff (cutoff_hour UK time on D-1).

    Returns a DataFrame with columns: startTime, generation (forecast), publishTime.
    """
    cutoff_utc = _compute_cutoff_utc(delivery_date, cutoff_hour)

    # Filter to delivery day and forecasts before cutoff
    d = pd.Timestamp(delivery_date, tz=UTC_TZ)
    d_next = d + pd.Timedelta(days=1)
    mask = (
        (forecasts["startTime"] >= d)
        & (forecasts["startTime"] < d_next)
        & (forecasts["publishTime"] <= cutoff_utc)
    )
    eligible = forecasts.loc[mask].copy()

    if eligible.empty:
        return pd.DataFrame(columns=["startTime", "generation", "publishTime"])

    # For each target slot, pick the forecast with the latest publishTime
    idx = eligible.groupby("startTime")["publishTime"].idxmax()
    latest = eligible.loc[idx].reset_index(drop=True)
    latest.sort_values("startTime", inplace=True)
    return latest


def build_forecast_vs_actual(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    delivery_date: str,
    cutoff_hour: int = 9,
) -> pd.DataFrame:
    """
    Merge the latest eligible forecast with actuals for a given delivery date.

    Returns DataFrame with: startTime, forecast, actual (nullable), publishTime, error.
    """
    latest = get_latest_forecasts(forecasts, delivery_date, cutoff_hour)
    if latest.empty:
        return pd.DataFrame(
            columns=["startTime", "forecast", "actual", "publishTime", "error"]
        )

    latest = latest.rename(columns={"generation": "forecast"})

    # Merge with actuals
    merged = latest.merge(
        actuals.rename(columns={"generation": "actual"}),
        on="startTime",
        how="left",
    )
    merged["error"] = merged["forecast"] - merged["actual"]
    return merged


def compute_overall_metrics(errors: pd.Series) -> dict:
    """
    Compute summary error metrics from a series of (forecast - actual) errors.
    Returns dict with mae, rmse, bias, mape_approx, p50, p90, p95.
    """
    clean = errors.dropna()
    if clean.empty:
        return {k: None for k in ["mae", "rmse", "bias", "p50", "p90", "p95", "n"]}

    abs_err = clean.abs()
    return {
        "mae": round(float(abs_err.mean()), 1),
        "rmse": round(float(np.sqrt((clean**2).mean())), 1),
        "bias": round(float(clean.mean()), 1),
        "p50": round(float(abs_err.quantile(0.50)), 1),
        "p90": round(float(abs_err.quantile(0.90)), 1),
        "p95": round(float(abs_err.quantile(0.95)), 1),
        "n": int(len(clean)),
    }


def compute_monthly_metrics(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    cutoff_hour: int = 9,
) -> dict:
    """
    Compute error metrics across the entire month for the given cutoff.

    Returns: overall metrics, by_hour breakdown, and by_wind_level breakdown.
    """
    dates = get_available_dates(actuals)
    all_merged = []
    for d in dates:
        merged = build_forecast_vs_actual(actuals, forecasts, d, cutoff_hour)
        if not merged.empty:
            all_merged.append(merged)

    if not all_merged:
        return {"overall": compute_overall_metrics(pd.Series(dtype=float)),
                "by_hour": [], "by_wind_level": []}

    df = pd.concat(all_merged, ignore_index=True)
    overall = compute_overall_metrics(df["error"])

    # --- Error by hour of day (UK time) ---
    df["hour_uk"] = df["startTime"].dt.tz_convert(UK_TZ).dt.hour
    by_hour = []
    for hour, grp in df.groupby("hour_uk"):
        m = compute_overall_metrics(grp["error"])
        m["hour"] = int(hour)
        by_hour.append(m)

    # --- Error by wind level bucket (terciles based on actual generation) ---
    valid = df.dropna(subset=["actual"]).copy()
    by_wind_level = []
    if not valid.empty:
        terciles = valid["actual"].quantile([1 / 3, 2 / 3]).values
        conditions = [
            valid["actual"] <= terciles[0],
            (valid["actual"] > terciles[0]) & (valid["actual"] <= terciles[1]),
            valid["actual"] > terciles[1],
        ]
        labels = ["Low", "Medium", "High"]
        valid["wind_level"] = np.select(conditions, labels, default="Unknown")
        for level in labels:
            grp = valid[valid["wind_level"] == level]
            m = compute_overall_metrics(grp["error"])
            m["wind_level"] = level
            # Add range info for context
            if level == "Low":
                m["range"] = f"≤ {terciles[0]:.0f} MW"
            elif level == "Medium":
                m["range"] = f"{terciles[0]:.0f}–{terciles[1]:.0f} MW"
            else:
                m["range"] = f"> {terciles[1]:.0f} MW"
            by_wind_level.append(m)

    return {"overall": overall, "by_hour": by_hour, "by_wind_level": by_wind_level}


def compute_horizon_error(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
) -> list[dict]:
    """
    Compute error statistics by forecast horizon bucket.

    Horizon = startTime - publishTime (in hours).
    Uses ALL forecast-actual pairs (not just the cutoff-filtered ones)
    to show how accuracy degrades with longer lead times.
    """
    merged = forecasts.merge(
        actuals.rename(columns={"generation": "actual"}),
        on="startTime",
        how="inner",
    )
    merged["error"] = merged["generation"] - merged["actual"]
    merged["horizon_hours"] = (
        (merged["startTime"] - merged["publishTime"]).dt.total_seconds() / 3600
    )

    # Create horizon buckets
    bins = [0, 6, 12, 18, 24, 36, 48, 72, float("inf")]
    labels = ["0-6h", "6-12h", "12-18h", "18-24h", "24-36h", "36-48h", "48-72h", "72h+"]
    merged["horizon_bucket"] = pd.cut(
        merged["horizon_hours"], bins=bins, labels=labels, right=False
    )

    results = []
    for bucket in labels:
        grp = merged[merged["horizon_bucket"] == bucket]
        if grp.empty:
            continue
        m = compute_overall_metrics(grp["error"])
        m["bucket"] = bucket
        results.append(m)

    return results


def get_uncertainty_band(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    cutoff_hour: int = 9,
) -> float:
    """
    Compute the P90 absolute error across all delivery days for the month.
    Used to display an uncertainty band on the forecast chart.
    """
    metrics = compute_monthly_metrics(actuals, forecasts, cutoff_hour)
    p90 = metrics["overall"].get("p90")
    return p90 if p90 is not None else 0.0
