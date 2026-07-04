"""
Stock data processing script
- CATL A-share: merge adj_factor with existing daily data, compute qfq
- CATL H-share: fetch via yfinance with auto_adjust=True
- Moutai A-share: save raw daily data (adj_factor to be merged later)
"""
import json
import csv
import os
import subprocess
import sys

# Ensure yfinance is installed
def ensure_yfinance():
    try:
        import yfinance
    except ImportError:
        venv_pip = r"C:\Users\86198\.workbuddy\binaries\python\envs\default\Scripts\pip"
        subprocess.check_call([venv_pip, "install", "yfinance", "--quiet"])
        import yfinance

ensure_yfinance()
import yfinance as yf
import pandas as pd

BASE_DIR = r"C:\Users\86198\Desktop\quant-trials"

# ========== 1. CATL A-share: adj_factor -> qfq ==========
print("=" * 60)
print("1. Processing CATL A-share (300750.SZ) with adj_factor")
print("=" * 60)

# Read existing daily data
catl_daily = pd.read_csv(os.path.join(BASE_DIR, "CATL_300750_daily.csv"), dtype={"trade_date": str})
catl_daily = catl_daily.sort_values("trade_date").reset_index(drop=True)
print(f"   Daily records: {len(catl_daily)}")
print(f"   Date range: {catl_daily['trade_date'].iloc[0]} ~ {catl_daily['trade_date'].iloc[-1]}")

# CATL adj_factor (from Tushare API response)
catl_adj_data = [
    {"trade_date": r["trade_date"], "adj_factor": r["adj_factor"]}
    for r in json.loads(open(os.path.join(BASE_DIR, "catl_adj_factor.json"), "r").read())
] if os.path.exists(os.path.join(BASE_DIR, "catl_adj_factor.json")) else []

if not catl_adj_data:
    # Hardcode from API response (already fetched)
    adj_factors = {
        # 1.9125 period: 20250701 ~ 20250818
        **{d: 1.9125 for d in catl_daily["trade_date"] if d <= "20250818"},
        # 1.9194 period: 20250819 ~ 20260420
        **{d: 1.9194 for d in catl_daily["trade_date"] if "20250819" <= d <= "20260420"},
        # 1.9495 period: 20260421 ~ 20260703
        **{d: 1.9495 for d in catl_daily["trade_date"] if d >= "20260421"},
    }
    catl_daily["adj_factor"] = catl_daily["trade_date"].map(adj_factors)
else:
    adj_df = pd.DataFrame(catl_adj_data)
    catl_daily = catl_daily.merge(adj_df, on="trade_date", how="left")

print(f"   Adj factor unique values: {sorted(catl_daily['adj_factor'].unique())}")

# Compute qfq: adj_price = raw_price * adj_factor / max(adj_factor)
max_factor = catl_daily["adj_factor"].max()
print(f"   Max adj_factor (latest): {max_factor}")

catl_daily["adj_open"] = (catl_daily["open"] * catl_daily["adj_factor"] / max_factor).round(2)
catl_daily["adj_high"] = (catl_daily["high"] * catl_daily["adj_factor"] / max_factor).round(2)
catl_daily["adj_low"] = (catl_daily["low"] * catl_daily["adj_factor"] / max_factor).round(2)
catl_daily["adj_close"] = (catl_daily["close"] * catl_daily["adj_factor"] / max_factor).round(2)

# Verify: latest close should equal raw close
latest_row = catl_daily.iloc[-1]
print(f"   Verification (latest): raw_close={latest_row['close']}, adj_close={latest_row['adj_close']}, match={latest_row['close'] == latest_row['adj_close']}")

# Output qfq CSV
catl_qfq = catl_daily[["trade_date", "adj_open", "adj_high", "adj_low", "adj_close", "vol", "amount", "pct_chg", "adj_factor"]].copy()
catl_qfq.columns = ["trade_date", "open", "high", "low", "close", "volume", "amount", "pct_chg", "adj_factor"]
catl_qfq.to_csv(os.path.join(BASE_DIR, "CATL_300750_daily_qfq.csv"), index=False)
print(f"   Saved: CATL_300750_daily_qfq.csv ({len(catl_qfq)} rows)")

# ========== 2. CATL H-share: yfinance auto_adjust=True ==========
print()
print("=" * 60)
print("2. Fetching CATL H-share (3750.HK) via yfinance")
print("=" * 60)

catl_hk = yf.download("3750.HK", start="2025-07-01", end="2025-07-05", auto_adjust=True, progress=False)
if catl_hk.empty:
    # Try without date range first
    catl_hk = yf.download("3750.HK", start="2025-07-01", end="2026-07-05", auto_adjust=True, progress=False)

print(f"   H-share records: {len(catl_hk)}")
if not catl_hk.empty:
    print(f"   Date range: {catl_hk.index[0].strftime('%Y%m%d')} ~ {catl_hk.index[-1].strftime('%Y%m%d')}")

    # Flatten MultiIndex columns if present
    if isinstance(catl_hk.columns, pd.MultiIndex):
        catl_hk.columns = catl_hk.columns.get_level_values(0)

    # Rename columns
    catl_hk = catl_hk.reset_index()
    catl_hk["trade_date"] = catl_hk["Date"].dt.strftime("%Y%m%d")
    catl_hk_out = catl_hk[["trade_date", "Open", "High", "Low", "Close", "Volume"]].copy()
    catl_hk_out.columns = ["trade_date", "open", "high", "low", "close", "volume"]
    catl_hk_out = catl_hk_out.sort_values("trade_date").reset_index(drop=True)

    # Add empty columns for consistency
    catl_hk_out["amount"] = ""
    catl_hk_out["pct_chg"] = ((catl_hk_out["close"].pct_change()) * 100).round(4)
    catl_hk_out["adj_factor"] = ""

    catl_hk_out.to_csv(os.path.join(BASE_DIR, "CATL_3750HK_daily_qfq.csv"), index=False)
    print(f"   Saved: CATL_3750HK_daily_qfq.csv ({len(catl_hk_out)} rows)")
    print(f"   First 3 rows:")
    print(catl_hk_out.head(3).to_string(index=False))
else:
    print("   ERROR: yfinance returned empty data")

# ========== 3. Moutai A-share: save raw daily data ==========
print()
print("=" * 60)
print("3. Saving Moutai A-share (600519.SH) raw daily data")
print("=" * 60)

moutai_data = json.loads(open(os.path.join(BASE_DIR, "moutai_daily.json"), "r").read()) if os.path.exists(os.path.join(BASE_DIR, "moutai_daily.json")) else []

if not moutai_data:
    print("   ERROR: moutai_daily.json not found")
else:
    moutai_df = pd.DataFrame(moutai_data)
    moutai_df = moutai_df.sort_values("trade_date").reset_index(drop=True)
    moutai_df.to_csv(os.path.join(BASE_DIR, "Moutai_600519_daily_raw.csv"), index=False)
    print(f"   Raw records: {len(moutai_df)}")
    print(f"   Date range: {moutai_df['trade_date'].iloc[0]} ~ {moutai_df['trade_date'].iloc[-1]}")
    print(f"   Saved: Moutai_600519_daily_raw.csv (waiting for adj_factor)")

print()
print("Done!")
