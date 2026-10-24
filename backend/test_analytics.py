"""
Unit tests for the wind forecast analytics engine.

Key test: verifying that the cutoff logic correctly excludes forecasts
published after the decision deadline.
"""

import pandas as pd
import numpy as np
import pytest
from backend.analytics import (
    get_latest_forecasts,
    _compute_cutoff_utc,
    compute_overall_metrics,
    build_forecast_vs_actual,
)


# ---------------------------------------------------------------------------
# Fixtures: small synthetic datasets for deterministic testing
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_forecasts():
    """
    Create synthetic forecasts for 2026-01-05 (delivery day).
    Decision cutoff at 09:00 UK on 2026-01-04.

    Jan 2026: UK is in GMT (UTC+0), so 09:00 UK = 09:00 UTC.
    """
    rows = [
        # Target: 2026-01-05 00:00 UTC
        # This forecast was published at 07:00 on D-1 → BEFORE cutoff → eligible
        ("2026-01-05 00:00:00+00:00", "2026-01-04 07:00:00+00:00", 5000),
        # This forecast was published at 08:30 on D-1 → BEFORE cutoff → eligible (later, should be picked)
        ("2026-01-05 00:00:00+00:00", "2026-01-04 08:30:00+00:00", 5200),
        # This forecast was published at 10:00 on D-1 → AFTER cutoff → must NOT be used
        ("2026-01-05 00:00:00+00:00", "2026-01-04 10:00:00+00:00", 9999),
        # Target: 2026-01-05 00:30 UTC — only one eligible forecast
        ("2026-01-05 00:30:00+00:00", "2026-01-04 06:00:00+00:00", 4800),
        # This forecast is AFTER cutoff → must NOT be used
        ("2026-01-05 00:30:00+00:00", "2026-01-04 12:00:00+00:00", 8888),
    ]
    df = pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"])
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    return df


@pytest.fixture
def sample_actuals():
    """Actuals for the same two half-hours."""
    rows = [
        ("2026-01-05 00:00:00+00:00", 5100),
        ("2026-01-05 00:30:00+00:00", 4900),
    ]
    df = pd.DataFrame(rows, columns=["startTime", "generation"])
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCutoffComputation:
    def test_cutoff_gmt(self):
        """In January UK is GMT, so 09:00 UK = 09:00 UTC."""
        cutoff = _compute_cutoff_utc("2026-01-05", 9)
        assert cutoff.hour == 9
        assert cutoff.day == 4  # D-1

    def test_cutoff_different_hour(self):
        cutoff = _compute_cutoff_utc("2026-01-05", 12)
        assert cutoff.hour == 12
        assert cutoff.day == 4


class TestLatestForecastSelection:
    def test_picks_latest_before_cutoff(self, sample_forecasts):
        """The 08:30 forecast should be selected, not the 07:00 or 10:00 one."""
        result = get_latest_forecasts(sample_forecasts, "2026-01-05", cutoff_hour=9)

        # Should have 2 rows (one per target half-hour)
        assert len(result) == 2

        # For the 00:00 slot, the selected publishTime should be 08:30
        slot_0 = result[result["startTime"].dt.hour == 0].iloc[0]
        assert slot_0["publishTime"].hour == 8
        assert slot_0["publishTime"].minute == 30
        # The forecast value should be 5200, not 9999
        assert slot_0["generation"] == 5200

    def test_excludes_post_cutoff_forecast(self, sample_forecasts):
        """
        CRITICAL: Prove that a later forecast (10:00, value 9999) is NOT used
        even though it exists in the data. This guards against lookahead bias.
        """
        result = get_latest_forecasts(sample_forecasts, "2026-01-05", cutoff_hour=9)

        # No forecast value should be 9999 (the post-cutoff forecast)
        assert 9999 not in result["generation"].values
        # No forecast value should be 8888 either
        assert 8888 not in result["generation"].values

    def test_single_eligible_forecast(self, sample_forecasts):
        """For the 00:30 slot, only the 06:00 forecast is eligible."""
        result = get_latest_forecasts(sample_forecasts, "2026-01-05", cutoff_hour=9)
        slot_30 = result[result["startTime"].dt.minute == 30].iloc[0]
        assert slot_30["generation"] == 4800
        assert slot_30["publishTime"].hour == 6

    def test_no_forecasts_for_wrong_date(self, sample_forecasts):
        """Querying a date with no data should return empty."""
        result = get_latest_forecasts(sample_forecasts, "2026-01-10", cutoff_hour=9)
        assert result.empty


class TestErrorMetrics:
    def test_basic_metrics(self):
        errors = pd.Series([100, -200, 300, -100, 50])
        m = compute_overall_metrics(errors)
        assert m["mae"] == pytest.approx(150.0, abs=0.1)
        assert m["bias"] == pytest.approx(30.0, abs=0.1)
        assert m["n"] == 5

    def test_empty_series(self):
        m = compute_overall_metrics(pd.Series(dtype=float))
        assert m["mae"] is None
        assert m["n"] is None

    def test_all_nan(self):
        m = compute_overall_metrics(pd.Series([np.nan, np.nan]))
        assert m["mae"] is None


class TestBuildForecastVsActual:
    def test_merge_produces_errors(self, sample_actuals, sample_forecasts):
        merged = build_forecast_vs_actual(
            sample_actuals, sample_forecasts, "2026-01-05", cutoff_hour=9
        )
        assert len(merged) == 2
        assert "error" in merged.columns

        # For slot 00:00: forecast=5200, actual=5100 → error=100
        slot_0 = merged[merged["startTime"].dt.hour == 0].iloc[0]
        assert slot_0["error"] == pytest.approx(100.0)

        # For slot 00:30: forecast=4800, actual=4900 → error=-100
        slot_30 = merged[merged["startTime"].dt.minute == 30].iloc[0]
        assert slot_30["error"] == pytest.approx(-100.0)
