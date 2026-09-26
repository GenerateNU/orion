"""
Shared helper for DataFrame-backed models.

Pipeline data (sensor readings, vehicle states) lives in pandas DataFrames instead of lists of Pydantic objects,
since we can have millions of rows and per-object validation/memory overhead adds up fast.
Each model is a column schema (name -> dtype) plus the set of required columns, and validate_frame() does the job Pydantic used to:
fail loudly on missing or null required columns, fill in optional ones, and coerce dtypes -- once per frame instead of once per row.
"""
import pandas as pd


def validate_frame(df: pd.DataFrame, schema: dict[str, str], required: set[str]) -> pd.DataFrame:
    """Return a copy of df with exactly the schema's columns, in schema order, cast to the schema's dtypes."""
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing required column(s): {', '.join(sorted(missing))}")

    out = df.copy()
    for col, dtype in schema.items():
        if col not in out.columns:
            out[col] = None  # becomes NaN / <NA> / NaT once cast below
        if dtype.startswith("datetime64"):
            # naive timestamps are assumed to already be UTC
            out[col] = pd.to_datetime(out[col], utc=True).astype(dtype)
        else:
            out[col] = out[col].astype(dtype)

    nulls = [col for col in sorted(required) if out[col].isna().any()]
    if nulls:
        raise ValueError(f"null value(s) in required column(s): {', '.join(nulls)}")

    return out[list(schema)]
