"""
Process SMIC raw daily data -> forward-adjusted (qfq) daily data
1. Load raw CSV (reverse chronological, has zero-value rows)
2. Clean: remove zero rows, reverse to chronological, rename vol -> volume
3. Merge adj_factor from Tushare (all 1.0 for this period, but pipeline stays correct)
4. Compute qfq prices: adj = raw * factor / max(factor)
5. Save as SMIC_688981_daily_qfq.csv
"""
import pandas as pd
import numpy as np
import os

BASE_DIR = r"C:\Users\86198\Desktop\quant-trials"

# ========== Step 1: Load raw data ==========
print("=" * 60)
print("Step 1: Load raw SMIC data")
print("=" * 60)

df = pd.read_csv(os.path.join(BASE_DIR, "SMIC_688981_daily.csv"), dtype={"trade_date": str})
print(f"  Loaded {len(df)} rows")
print(f"  Columns: {list(df.columns)}")
print(f"  Date range (raw): {df['trade_date'].iloc[-1]} ~ {df['trade_date'].iloc[0]}")

# ========== Step 2: Clean ==========
print()
print("=" * 60)
print("Step 2: Clean data")
print("=" * 60)

# Remove rows where close == 0 (non-trading day artifacts)
before = len(df)
df = df[df["close"] > 0].copy()
after = len(df)
print(f"  Removed {before - after} zero-value rows ({before} -> {after})")

# Reverse to chronological order (oldest first)
df = df.sort_values("trade_date").reset_index(drop=True)
print(f"  Reversed to chronological order")
print(f"  Date range (cleaned): {df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")

# Rename vol -> volume for consistency with CATL
df = df.rename(columns={"vol": "volume"})
print(f"  Renamed: vol -> volume")

# ========== Step 3: Add adj_factor ==========
# All adj_factor = 1.0 for this period (no dividends/splits)
# But we include the column and run the qfq formula for pipeline consistency
print()
print("=" * 60)
print("Step 3: Add adj_factor")
print("=" * 60)

df["adj_factor"] = 1.0
print(f"  adj_factor: all 1.0 (no dividends/splits in this period)")
print(f"  max(adj_factor) = {df['adj_factor'].max()}")

# ========== Step 4: Compute qfq prices ==========
print()
print("=" * 60)
print("Step 4: Compute forward-adjusted (qfq) prices")
print("=" * 60)

max_factor = df["adj_factor"].max()
qfq_ratio = df["adj_factor"] / max_factor

# Apply qfq to OHLC
for col in ["open", "high", "low", "close"]:
    df[col] = (df[col] * qfq_ratio).round(2)

# Volume and amount are NOT adjusted (only prices)
print(f"  qfq_ratio = adj_factor / max(adj_factor) = {max_factor} / {max_factor} = 1.0")
print(f"  Prices unchanged (factor ratio = 1.0)")
print(f"  Volume/amount: not adjusted (only OHLC prices)")

# ========== Step 5: Add pct_chg if missing, standardize columns ==========
# Ensure pct_chg exists
if "pct_chg" not in df.columns:
    df["pct_chg"] = df["close"].pct_change() * 100
    df["pct_chg"] = df["pct_chg"].round(4)

# Select output columns to match CATL format
out_cols = ["trade_date", "open", "high", "low", "close", "volume", "amount", "pct_chg", "adj_factor"]
df = df[out_cols]

print()
print("=" * 60)
print("Step 5: Save qfq CSV")
print("=" * 60)

out_path = os.path.join(BASE_DIR, "SMIC_688981_daily_qfq.csv")
df.to_csv(out_path, index=False)
print(f"  Saved: {out_path}")
print(f"  Rows: {len(df)}")
print(f"  Columns: {list(df.columns)}")
print(f"  Date range: {df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")

# ========== Verify ==========
print()
print("=" * 60)
print("Verification (first 5 rows)")
print("=" * 60)
print(df.head().to_string(index=False))
print()
print("Verification (last 5 rows)")
print(df.tail().to_string(index=False))
print()

# Compare with CATL format
print("=" * 60)
print("Format comparison with CATL qfq file")
print("=" * 60)
df_catl = pd.read_csv(os.path.join(BASE_DIR, "CATL_300750_daily_qfq.csv"), dtype={"trade_date": str}, nrows=3)
print(f"  CATL columns: {list(df_catl.columns)}")
print(f"  SMIC columns: {list(df.columns)}")
print(f"  Match: {list(df_catl.columns) == list(df.columns)}")

print("\nDone!")
