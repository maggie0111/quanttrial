"""
Process CATL A-share (qfq) + fetch CATL H-share (yfinance auto_adjust)
"""
import os, sys, subprocess
import pandas as pd

# Ensure yfinance is installed
try:
    import yfinance
except ImportError:
    venv_pip = r"C:\Users\86198\.workbuddy\binaries\python\envs\default\Scripts\pip"
    subprocess.check_call([venv_pip, "install", "yfinance", "--quiet"])
    import yfinance
import yfinance as yf

BASE_DIR = r"C:\Users\86198\Desktop\quant-trials"

# ========== 1. CATL A-share: adj_factor -> qfq ==========
print("=" * 60)
print("1. Processing CATL A-share (300750.SZ) with adj_factor")
print("=" * 60)

catl_daily = pd.read_csv(os.path.join(BASE_DIR, "CATL_300750_daily.csv"), dtype={"trade_date": str})
catl_daily = catl_daily.sort_values("trade_date").reset_index(drop=True)
print(f"   Daily records: {len(catl_daily)}")
print(f"   Date range: {catl_daily['trade_date'].iloc[0]} ~ {catl_daily['trade_date'].iloc[-1]}")

# Hardcoded adj_factor from Tushare API response
# 3 periods: 1.9125 (until 20250818), 1.9194 (until 20260420), 1.9495 (after)
def get_adj_factor(date):
    if date <= "20250818":
        return 1.9125
    elif date <= "20260420":
        return 1.9194
    else:
        return 1.9495

catl_daily["adj_factor"] = catl_daily["trade_date"].apply(get_adj_factor)
max_factor = catl_daily["adj_factor"].max()
print(f"   Adj factor periods: 1.9125 | 1.9194 | 1.9495")
print(f"   Max adj_factor (latest): {max_factor}")

# qfq: adj_price = raw_price * adj_factor / max_factor
catl_daily["adj_open"] = (catl_daily["open"] * catl_daily["adj_factor"] / max_factor).round(2)
catl_daily["adj_high"] = (catl_daily["high"] * catl_daily["adj_factor"] / max_factor).round(2)
catl_daily["adj_low"] = (catl_daily["low"] * catl_daily["adj_factor"] / max_factor).round(2)
catl_daily["adj_close"] = (catl_daily["close"] * catl_daily["adj_factor"] / max_factor).round(2)

# Verify: latest close should equal raw close
latest = catl_daily.iloc[-1]
print(f"   Verify: raw_close={latest['close']}, adj_close={latest['adj_close']}, match={latest['close'] == latest['adj_close']}")

# Check for adj_factor jumps (dividend events)
jumps = catl_daily[catl_daily["adj_factor"] != catl_daily["adj_factor"].shift(1)]
print(f"   Adj factor jump dates: {jumps['trade_date'].tolist()}")

# Save qfq CSV
catl_qfq = catl_daily[["trade_date", "adj_open", "adj_high", "adj_low", "adj_close", "vol", "amount", "pct_chg", "adj_factor"]].copy()
catl_qfq.columns = ["trade_date", "open", "high", "low", "close", "volume", "amount", "pct_chg", "adj_factor"]
catl_qfq.to_csv(os.path.join(BASE_DIR, "CATL_300750_daily_qfq.csv"), index=False)
print(f"   Saved: CATL_300750_daily_qfq.csv ({len(catl_qfq)} rows)")

# ========== 2. CATL H-share: yfinance auto_adjust=True ==========
print()
print("=" * 60)
print("2. Fetching CATL H-share (3750.HK) via yfinance")
print("=" * 60)

catl_hk = yf.download("3750.HK", start="2025-07-01", end="2026-07-05", auto_adjust=True, progress=False)
print(f"   H-share records: {len(catl_hk)}")

if not catl_hk.empty:
    if isinstance(catl_hk.columns, pd.MultiIndex):
        catl_hk.columns = catl_hk.columns.get_level_values(0)
    catl_hk = catl_hk.reset_index()
    catl_hk["trade_date"] = catl_hk["Date"].dt.strftime("%Y%m%d")
    catl_hk_out = catl_hk[["trade_date", "Open", "High", "Low", "Close", "Volume"]].copy()
    catl_hk_out.columns = ["trade_date", "open", "high", "low", "close", "volume"]
    catl_hk_out = catl_hk_out.sort_values("trade_date").reset_index(drop=True)
    catl_hk_out["amount"] = ""
    catl_hk_out["pct_chg"] = ((catl_hk_out["close"].pct_change()) * 100).round(4)
    catl_hk_out["adj_factor"] = ""
    catl_hk_out.to_csv(os.path.join(BASE_DIR, "CATL_3750HK_daily_qfq.csv"), index=False)
    print(f"   Saved: CATL_3750HK_daily_qfq.csv ({len(catl_hk_out)} rows)")
    print(f"   Date range: {catl_hk_out['trade_date'].iloc[0]} ~ {catl_hk_out['trade_date'].iloc[-1]}")
    print(f"   First 3 rows:")
    print(catl_hk_out.head(3).to_string(index=False))
else:
    print("   ERROR: yfinance returned empty data")

print("\nDone!")
