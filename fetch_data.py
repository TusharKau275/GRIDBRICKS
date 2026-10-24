"""
Download wind actuals (FUELHH) and wind forecasts (WINDFOR) from Elexon BMRS
for January 2026 and save them as CSV files in ./data

Run:  pip install requests pandas
      python fetch_data.py
"""
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
OUT = Path("data")
OUT.mkdir(exist_ok=True)

TARGET_START = "2026-01-01T00:00:00Z"
TARGET_END = "2026-02-01T00:00:00Z"  # exclusive


def get_json(url, params, retries=4):
    for attempt in range(retries):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 200:
                data = r.json()
                return data["data"] if isinstance(data, dict) and "data" in data else data
            print(f"  HTTP {r.status_code}: {r.text[:200]}")
        except requests.RequestException as e:
            print(f"  request error: {e}")
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed: {url} {params}")


def daterange(start: date, end: date, step_days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=step_days), end)
        yield cur, nxt
        cur = nxt


def fetch_actuals():
    rows = []
    for a, b in daterange(date(2026, 1, 1), date(2026, 2, 1), 7):
        print(f"FUELHH {a} -> {b}")
        params = {
            "settlementDateFrom": a.isoformat(),
            "settlementDateTo": (b - timedelta(days=1)).isoformat(),
            "fuelType": "WIND",
            "format": "json",
        }
        rows += get_json(f"{BASE}/FUELHH/stream", params)
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df = (
        df[(df["startTime"] >= TARGET_START) & (df["startTime"] < TARGET_END)]
        .drop_duplicates(subset=["startTime"], keep="last")
        .sort_values("startTime")
    )
    df[["startTime", "generation"]].to_csv(OUT / "wind_actuals.csv", index=False)
    print(f"actuals: {len(df)} rows")


def fetch_forecasts():
    # Forecasts are published up to ~14 days ahead, so start earlier than 1 Jan.
    rows = []
    for a, b in daterange(date(2025, 12, 15), date(2026, 2, 1), 1):
        print(f"WINDFOR published {a}")
        params = {
            "publishDateTimeFrom": f"{a.isoformat()}T00:00:00Z",
            "publishDateTimeTo": f"{b.isoformat()}T00:00:00Z",
            "format": "json",
        }
        rows += get_json(f"{BASE}/WINDFOR/stream", params)
    df = pd.DataFrame(rows)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = (
        df[(df["startTime"] >= TARGET_START) & (df["startTime"] < TARGET_END)]
        .drop_duplicates(subset=["startTime", "publishTime"], keep="last")
        .sort_values(["startTime", "publishTime"])
    )
    df[["startTime", "publishTime", "generation"]].to_csv(
        OUT / "wind_forecasts.csv", index=False
    )
    print(f"forecasts: {len(df)} rows")


if __name__ == "__main__":
    fetch_actuals()
    fetch_forecasts()
    print("Done. Files saved in ./data")
