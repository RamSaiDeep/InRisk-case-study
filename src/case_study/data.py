"""Load and quality-check the ERA5-Land extract for pincode 380006."""

from __future__ import annotations

import pandas as pd

from . import config


REQUIRED = ["date", "ssrd_kwh_m2", "temperature_c", "precipitation_mm"]


def load_daily(path: str = config.MASTER_CSV) -> pd.DataFrame:
    """Return the daily ERA5-Land series with calendar helper columns."""
    df = pd.read_csv(path, parse_dates=["date"])
    missing = set(REQUIRED) - set(df.columns)
    if missing:
        raise ValueError(f"master file is missing columns: {sorted(missing)}")

    df = df.loc[:, REQUIRED].sort_values("date").reset_index(drop=True)
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    df["doy"] = df["date"].dt.dayofyear
    return df


def quality_report(df: pd.DataFrame) -> dict:
    """Checks worth stating in the report before any number is trusted."""
    expected_days = (
        pd.Timestamp(f"{config.YEAR_END}-12-31") - pd.Timestamp(f"{config.YEAR_START}-01-01")
    ).days + 1
    gaps = pd.date_range(df["date"].min(), df["date"].max(), freq="D").difference(df["date"])

    return {
        "rows": len(df),
        "expected_days": expected_days,
        "missing_dates": len(gaps),
        "nulls": int(df[REQUIRED].isna().sum().sum()),
        "duplicate_dates": int(df["date"].duplicated().sum()),
        "ssrd_negative": int((df["ssrd_kwh_m2"] < 0).sum()),
        "ssrd_above_clear_sky": int((df["ssrd_kwh_m2"] > 9.0).sum()),
        "temp_range_c": (round(df["temperature_c"].min(), 1), round(df["temperature_c"].max(), 1)),
        "years_covered": int(df["year"].nunique()),
    }
