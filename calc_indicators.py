"""
Calculate RSI, MACD, BB, ATR for CATL A-share and H-share
Output: indicator CSV files + visualization dashboard
"""
import pandas as pd
import numpy as np
import json
import os

BASE_DIR = r"C:\Users\86198\Desktop\quant-trials"

# ========== Indicator Functions ==========

def calc_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder's smoothing (EMA with alpha=1/period)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.round(2)

def calc_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, adjust=False).mean()
    hist = (dif - dea) * 2
    return dif.round(4), dea.round(4), hist.round(4)

def calc_bb(close, period=20, num_std=2):
    sma = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    bandwidth = ((upper - lower) / sma * 100).round(4)
    pct_b = ((close - lower) / (upper - lower) * 100).round(4)
    return upper.round(2), sma.round(2), lower.round(2), bandwidth, pct_b

def calc_atr(high, low, close, period=14):
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    return tr.round(4), atr.round(4)

# ========== Process A-share ==========
print("=" * 60)
print("Processing CATL A-share (300750.SZ)")
print("=" * 60)

df_a = pd.read_csv(os.path.join(BASE_DIR, "CATL_300750_daily_qfq.csv"), dtype={"trade_date": str})
df_a = df_a.sort_values("trade_date").reset_index(drop=True)

df_a["RSI_14"] = calc_rsi(df_a["close"])
df_a["MACD_DIF"], df_a["MACD_DEA"], df_a["MACD_HIST"] = calc_macd(df_a["close"])
df_a["BB_UP"], df_a["BB_MID"], df_a["BB_LOW"], df_a["BB_BW"], df_a["BB_PCTB"] = calc_bb(df_a["close"])
df_a["TR"], df_a["ATR_14"] = calc_atr(df_a["high"], df_a["low"], df_a["close"])

out_cols_a = ["trade_date", "open", "high", "low", "close", "volume",
              "RSI_14", "MACD_DIF", "MACD_DEA", "MACD_HIST",
              "BB_UP", "BB_MID", "BB_LOW", "BB_BW", "BB_PCTB", "ATR_14"]
df_a[out_cols_a].to_csv(os.path.join(BASE_DIR, "CATL_300750_indicators.csv"), index=False)
print(f"  Saved: CATL_300750_indicators.csv ({len(df_a)} rows)")
print(f"  Date range: {df_a['trade_date'].iloc[0]} ~ {df_a['trade_date'].iloc[-1]}")

# ========== Process H-share ==========
print()
print("=" * 60)
print("Processing CATL H-share (3750.HK)")
print("=" * 60)

df_h = pd.read_csv(os.path.join(BASE_DIR, "CATL_3750HK_daily_qfq.csv"), dtype={"trade_date": str})
df_h = df_h.sort_values("trade_date").reset_index(drop=True)

df_h["RSI_14"] = calc_rsi(df_h["close"])
df_h["MACD_DIF"], df_h["MACD_DEA"], df_h["MACD_HIST"] = calc_macd(df_h["close"])
df_h["BB_UP"], df_h["BB_MID"], df_h["BB_LOW"], df_h["BB_BW"], df_h["BB_PCTB"] = calc_bb(df_h["close"])
df_h["TR"], df_h["ATR_14"] = calc_atr(df_h["high"], df_h["low"], df_h["close"])

out_cols_h = ["trade_date", "open", "high", "low", "close", "volume",
              "RSI_14", "MACD_DIF", "MACD_DEA", "MACD_HIST",
              "BB_UP", "BB_MID", "BB_LOW", "BB_BW", "BB_PCTB", "ATR_14"]
df_h[out_cols_h].to_csv(os.path.join(BASE_DIR, "CATL_3750HK_indicators.csv"), index=False)
print(f"  Saved: CATL_3750HK_indicators.csv ({len(df_h)} rows)")
print(f"  Date range: {df_h['trade_date'].iloc[0]} ~ {df_h['trade_date'].iloc[-1]}")

# ========== Latest Values Summary ==========
print()
print("=" * 60)
print("Latest Indicator Values")
print("=" * 60)

last_a = df_a.iloc[-1]
last_h = df_h.iloc[-1]

print(f"\n  A-share ({last_a['trade_date']}):")
print(f"    Close: {last_a['close']}")
print(f"    RSI(14): {last_a['RSI_14']}")
print(f"    MACD DIF: {last_a['MACD_DIF']}, DEA: {last_a['MACD_DEA']}, HIST: {last_a['MACD_HIST']}")
print(f"    BB: Upper={last_a['BB_UP']}, Mid={last_a['BB_MID']}, Lower={last_a['BB_LOW']}")
print(f"    BB %B: {last_a['BB_PCTB']}, Bandwidth: {last_a['BB_BW']}")
print(f"    ATR(14): {last_a['ATR_14']}")

print(f"\n  H-share ({last_h['trade_date']}):")
print(f"    Close: {last_h['close']}")
print(f"    RSI(14): {last_h['RSI_14']}")
print(f"    MACD DIF: {last_h['MACD_DIF']}, DEA: {last_h['MACD_DEA']}, HIST: {last_h['MACD_HIST']}")
print(f"    BB: Upper={last_h['BB_UP']}, Mid={last_h['BB_MID']}, Lower={last_h['BB_LOW']}")
print(f"    BB %B: {last_h['BB_PCTB']}, Bandwidth: {last_h['BB_BW']}")
print(f"    ATR(14): {last_h['ATR_14']}")

# ========== Signal Analysis ==========
print()
print("=" * 60)
print("Signal Analysis")
print("=" * 60)

# RSI signal
def rsi_signal(rsi):
    if pd.isna(rsi):
        return "N/A"
    if rsi > 70:
        return "超买 (>70)"
    elif rsi < 30:
        return "超卖 (<30)"
    elif rsi > 50:
        return "偏强 (50-70)"
    else:
        return "偏弱 (30-50)"

# MACD signal
def macd_signal(dif, dea, hist):
    if pd.isna(dif):
        return "N/A"
    if dif > dea and hist > 0:
        return "金叉/多头 (DIF>DEA)"
    elif dif < dea and hist < 0:
        return "死叉/空头 (DIF<DEA)"
    else:
        return "转换中"

# BB signal
def bb_signal(pct_b):
    if pd.isna(pct_b):
        return "N/A"
    if pct_b > 100:
        return "突破上轨"
    elif pct_b > 80:
        return "接近上轨"
    elif pct_b < 0:
        return "跌破下轨"
    elif pct_b < 20:
        return "接近下轨"
    else:
        return "中性区间"

print(f"\n  A-share signals:")
print(f"    RSI: {rsi_signal(last_a['RSI_14'])}")
print(f"    MACD: {macd_signal(last_a['MACD_DIF'], last_a['MACD_DEA'], last_a['MACD_HIST'])}")
print(f"    BB: {bb_signal(last_a['BB_PCTB'])}")

print(f"\n  H-share signals:")
print(f"    RSI: {rsi_signal(last_h['RSI_14'])}")
print(f"    MACD: {macd_signal(last_h['MACD_DIF'], last_h['MACD_DEA'], last_h['MACD_HIST'])}")
print(f"    BB: {bb_signal(last_h['BB_PCTB'])}")

# ========== Export JSON for dashboard ==========
def df_to_chart_data(df, cols):
    result = {}
    for col in cols:
        vals = df[col].tolist()
        # Replace NaN with null
        result[col] = [None if (isinstance(v, float) and np.isnan(v)) else round(v, 4) if isinstance(v, (int, float)) else v for v in vals]
    return result

chart_data = {
    "a_share": {
        "dates": df_a["trade_date"].tolist(),
        "close": [round(v, 2) for v in df_a["close"].tolist()],
        "high": [round(v, 2) for v in df_a["high"].tolist()],
        "low": [round(v, 2) for v in df_a["low"].tolist()],
        "volume": [round(v, 2) for v in df_a["volume"].tolist()],
        **df_to_chart_data(df_a, ["RSI_14", "MACD_DIF", "MACD_DEA", "MACD_HIST",
                                   "BB_UP", "BB_MID", "BB_LOW", "BB_BW", "BB_PCTB", "ATR_14"])
    },
    "h_share": {
        "dates": df_h["trade_date"].tolist(),
        "close": [round(v, 2) for v in df_h["close"].tolist()],
        "high": [round(v, 2) for v in df_h["high"].tolist()],
        "low": [round(v, 2) for v in df_h["low"].tolist()],
        "volume": [round(v, 2) for v in df_h["volume"].tolist()],
        **df_to_chart_data(df_h, ["RSI_14", "MACD_DIF", "MACD_DEA", "MACD_HIST",
                                   "BB_UP", "BB_MID", "BB_LOW", "BB_BW", "BB_PCTB", "ATR_14"])
    }
}

with open(os.path.join(BASE_DIR, "catl_indicators_data.json"), "w", encoding="utf-8") as f:
    json.dump(chart_data, f, ensure_ascii=False)
print(f"\n  Saved: catl_indicators_data.json (for dashboard)")

print("\nDone!")
