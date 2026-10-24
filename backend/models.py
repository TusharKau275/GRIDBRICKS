"""
Pydantic response models for all API endpoints.
"""

from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    actuals_count: int
    forecasts_count: int


class ForecastPoint(BaseModel):
    """A single half-hour slot with forecast, actual, and uncertainty."""
    startTime: str
    forecast: float
    actual: Optional[float] = None
    publishTime: str
    error: Optional[float] = None
    band_upper: Optional[float] = None
    band_lower: Optional[float] = None


class DayKPI(BaseModel):
    """Summary metrics for a single delivery day."""
    mae: Optional[float] = None
    rmse: Optional[float] = None
    bias: Optional[float] = None
    n: Optional[int] = None


class ForecastResponse(BaseModel):
    date: str
    cutoff_hour: int
    points: list[ForecastPoint]
    kpi: DayKPI
    uncertainty_mw: float


class MetricDetail(BaseModel):
    mae: Optional[float] = None
    rmse: Optional[float] = None
    bias: Optional[float] = None
    p50: Optional[float] = None
    p90: Optional[float] = None
    p95: Optional[float] = None
    n: Optional[int] = None


class HourMetric(MetricDetail):
    hour: int


class WindLevelMetric(MetricDetail):
    wind_level: str
    range: Optional[str] = None


class MetricsResponse(BaseModel):
    cutoff_hour: int
    overall: MetricDetail
    by_hour: list[HourMetric]
    by_wind_level: list[WindLevelMetric]


class HorizonBucket(MetricDetail):
    bucket: str


class HorizonResponse(BaseModel):
    buckets: list[HorizonBucket]


class DatesResponse(BaseModel):
    dates: list[str]
