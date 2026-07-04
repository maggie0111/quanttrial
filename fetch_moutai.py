"""
Fetch Moutai A-share (600519.SS) via yfinance with auto_adjust=True
Tushare adj_factor API is rate-limited (1/hour), using yfinance as alternative.
Also saves the raw Tushare daily data for reference.
"""
import os, sys
import pandas as pd
import yfinance as yf

BASE_DIR = r"C:\Users\86198\Desktop\quant-trials"

print("=" * 60)
print("Fetching Moutai A-share (600519.SS) via yfinance")
print("=" * 60)

# yfinance uses .SS for Shanghai Stock Exchange, .SZ for Shenzhen
moutai = yf.download("600519.SS", start="2025-07-01", end="2026-07-05", auto_adjust=True, progress=False)
print(f"   Records: {len(moutai)}")

if not moutai.empty:
    # Flatten MultiIndex columns if present
    if isinstance(moutai.columns, pd.MultiIndex):
        moutai.columns = moutai.columns.get_level_values(0)

    moutai = moutai.reset_index()
    moutai["trade_date"] = moutai["Date"].dt.strftime("%Y%m%d")
    moutai_out = moutai[["trade_date", "Open", "High", "Low", "Close", "Volume"]].copy()
    moutai_out.columns = ["trade_date", "open", "high", "low", "close", "volume"]
    moutai_out = moutai_out.sort_values("trade_date").reset_index(drop=True)

    # Add empty/derived columns for consistency with spec
    moutai_out["amount"] = ""
    moutai_out["pct_chg"] = ((moutai_out["close"].pct_change()) * 100).round(4)
    moutai_out["adj_factor"] = ""  # yfinance auto_adjust, no explicit factor

    # Round prices to 2 decimal places
    for col in ["open", "high", "low", "close"]:
        moutai_out[col] = moutai_out[col].round(2)

    moutai_out.to_csv(os.path.join(BASE_DIR, "Moutai_600519_daily_qfq.csv"), index=False)
    print(f"   Saved: Moutai_600519_daily_qfq.csv ({len(moutai_out)} rows)")
    print(f"   Date range: {moutai_out['trade_date'].iloc[0]} ~ {moutai_out['trade_date'].iloc[-1]}")
    print(f"   First 3 rows:")
    print(moutai_out.head(3).to_string(index=False))
    print(f"   Last 3 rows:")
    print(moutai_out.tail(3).to_string(index=False))

    # Basic validation
    print(f"\n   Validation:")
    print(f"   - All prices > 0: {(moutai_out[['open','high','low','close']] > 0).all().all()}")
    print(f"   - low <= open <= high: {((moutai_out['low'] <= moutai_out['open']) & (moutai_out['open'] <= moutai_out['high'])).all()}")
    print(f"   - low <= close <= high: {((moutai_out['low'] <= moutai_out['close']) & (moutai_out['close'] <= moutai_out['high'])).all()}")
else:
    print("   ERROR: yfinance returned empty data")

print("\nDone!")
