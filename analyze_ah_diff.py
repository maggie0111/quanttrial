"""
Analyze CATL A-share vs H-share indicator differences for report writing.
Output: key statistics, divergence events, and comparison summary.
"""
import pandas as pd
import json

BASE = r"C:\Users\86198\Desktop\quant-trials"

a = pd.read_csv(f"{BASE}/CATL_300750_indicators.csv")
h = pd.read_csv(f"{BASE}/CATL_3750HK_indicators.csv")

# Merge on trade_date
merged = pd.merge(a, h, on='trade_date', suffixes=('_A', '_H'), how='inner')

report = {}

# 1. Overview statistics
report['data_range'] = {
    'A_share': f"{a['trade_date'].min()} ~ {a['trade_date'].max()} ({len(a)} days)",
    'H_share': f"{h['trade_date'].min()} ~ {h['trade_date'].max()} ({len(h)} days)",
    'merged_days': len(merged)
}

# 2. RSI comparison
report['RSI'] = {
    'A_mean': round(merged['RSI_14_A'].mean(), 2),
    'H_mean': round(merged['RSI_14_H'].mean(), 2),
    'A_std': round(merged['RSI_14_A'].std(), 2),
    'H_std': round(merged['RSI_14_H'].std(), 2),
    'A_max': round(merged['RSI_14_A'].max(), 2),
    'A_max_date': str(merged.loc[merged['RSI_14_A'].idxmax(), 'trade_date']),
    'H_max': round(merged['RSI_14_H'].max(), 2),
    'H_max_date': str(merged.loc[merged['RSI_14_H'].idxmax(), 'trade_date']),
    'A_min': round(merged['RSI_14_A'].min(), 2),
    'A_min_date': str(merged.loc[merged['RSI_14_A'].idxmin(), 'trade_date']),
    'H_min': round(merged['RSI_14_H'].min(), 2),
    'H_min_date': str(merged.loc[merged['RSI_14_H'].idxmin(), 'trade_date']),
    'A_oversold_days': int((merged['RSI_14_A'] < 30).sum()),
    'H_oversold_days': int((merged['RSI_14_H'] < 30).sum()),
    'A_overbought_days': int((merged['RSI_14_A'] > 70).sum()),
    'H_overbought_days': int((merged['RSI_14_H'] > 70).sum()),
    'correlation': round(merged['RSI_14_A'].corr(merged['RSI_14_H']), 4),
    'mean_abs_diff': round((merged['RSI_14_A'] - merged['RSI_14_H']).abs().mean(), 2),
}

# 3. MACD comparison
report['MACD'] = {
    'A_DIF_mean': round(merged['MACD_DIF_A'].mean(), 2),
    'H_DIF_mean': round(merged['MACD_DIF_H'].mean(), 2),
    'A_HIST_max': round(merged['MACD_HIST_A'].max(), 2),
    'A_HIST_max_date': str(merged.loc[merged['MACD_HIST_A'].idxmax(), 'trade_date']),
    'H_HIST_max': round(merged['MACD_HIST_H'].max(), 2),
    'H_HIST_max_date': str(merged.loc[merged['MACD_HIST_H'].idxmax(), 'trade_date']),
    'A_HIST_min': round(merged['MACD_HIST_A'].min(), 2),
    'A_HIST_min_date': str(merged.loc[merged['MACD_HIST_A'].idxmin(), 'trade_date']),
    'H_HIST_min': round(merged['MACD_HIST_H'].min(), 2),
    'H_HIST_min_date': str(merged.loc[merged['MACD_HIST_H'].idxmin(), 'trade_date']),
    'DIF_correlation': round(merged['MACD_DIF_A'].corr(merged['MACD_DIF_H']), 4),
}

# Find golden cross / death cross events for each
def find_crosses(df, suffix=''):
    dif = df[f'MACD_DIF{suffix}'].values
    dea = df[f'MACD_DEA{suffix}'].values
    dates = df['trade_date'].values
    crosses = []
    for i in range(1, len(dif)):
        if pd.isna(dif[i]) or pd.isna(dea[i]) or pd.isna(dif[i-1]) or pd.isna(dea[i-1]):
            continue
        if dif[i-1] < dea[i-1] and dif[i] > dea[i]:
            crosses.append({'date': str(dates[i]), 'type': 'golden_cross'})
        elif dif[i-1] > dea[i-1] and dif[i] < dea[i]:
            crosses.append({'date': str(dates[i]), 'type': 'death_cross'})
    return crosses

report['MACD']['A_crosses'] = find_crosses(merged, '_A')
report['MACD']['H_crosses'] = find_crosses(merged, '_H')

# 4. Bollinger Bands comparison
report['BB'] = {
    'A_bw_mean': round(merged['BB_BW_A'].mean(), 2),
    'H_bw_mean': round(merged['BB_BW_H'].mean(), 2),
    'A_bw_min': round(merged['BB_BW_A'].min(), 2),
    'A_bw_min_date': str(merged.loc[merged['BB_BW_A'].idxmin(), 'trade_date']),
    'H_bw_min': round(merged['BB_BW_H'].min(), 2),
    'H_bw_min_date': str(merged.loc[merged['BB_BW_H'].idxmin(), 'trade_date']),
    'A_bw_max': round(merged['BB_BW_A'].max(), 2),
    'A_bw_max_date': str(merged.loc[merged['BB_BW_A'].idxmax(), 'trade_date']),
    'H_bw_max': round(merged['BB_BW_H'].max(), 2),
    'H_bw_max_date': str(merged.loc[merged['BB_BW_H'].idxmax(), 'trade_date']),
    'A_pctB_mean': round(merged['BB_PCTB_A'].mean(), 2),
    'H_pctB_mean': round(merged['BB_PCTB_H'].mean(), 2),
    'A_touch_upper_days': int((merged['BB_PCTB_A'] > 100).sum()),
    'H_touch_upper_days': int((merged['BB_PCTB_H'] > 100).sum()),
    'A_touch_lower_days': int((merged['BB_PCTB_A'] < 0).sum()),
    'H_touch_lower_days': int((merged['BB_PCTB_H'] < 0).sum()),
    'bw_correlation': round(merged['BB_BW_A'].corr(merged['BB_BW_H']), 4),
}

# 5. ATR comparison
# Calculate ATR as percentage of close
merged['ATR_pct_A'] = merged['ATR_14_A'] / merged['close_A'] * 100
merged['ATR_pct_H'] = merged['ATR_14_H'] / merged['close_H'] * 100
report['ATR'] = {
    'A_mean': round(merged['ATR_14_A'].mean(), 2),
    'H_mean': round(merged['ATR_14_H'].mean(), 2),
    'A_pct_mean': round(merged['ATR_pct_A'].mean(), 2),
    'H_pct_mean': round(merged['ATR_pct_H'].mean(), 2),
    'A_max': round(merged['ATR_14_A'].max(), 2),
    'A_max_date': str(merged.loc[merged['ATR_14_A'].idxmax(), 'trade_date']),
    'H_max': round(merged['ATR_14_H'].max(), 2),
    'H_max_date': str(merged.loc[merged['ATR_14_H'].idxmax(), 'trade_date']),
    'A_pct_max': round(merged['ATR_pct_A'].max(), 2),
    'H_pct_max': round(merged['ATR_pct_H'].max(), 2),
    'A_min': round(merged['ATR_14_A'].min(), 2),
    'H_min': round(merged['ATR_14_H'].min(), 2),
    'correlation': round(merged['ATR_14_A'].corr(merged['ATR_14_H']), 4),
}

# 6. Key divergence periods - find days where A and H RSI differ by >15
big_div = merged[(merged['RSI_14_A'] - merged['RSI_14_H']).abs() > 15]
report['RSI_divergences'] = []
for _, row in big_div.iterrows():
    report['RSI_divergences'].append({
        'date': str(row['trade_date']),
        'A_RSI': round(row['RSI_14_A'], 2),
        'H_RSI': round(row['RSI_14_H'], 2),
        'diff': round(row['RSI_14_A'] - row['RSI_14_H'], 2),
        'direction': 'A>H' if row['RSI_14_A'] > row['RSI_14_H'] else 'H>A'
    })

# 7. Price correlation
report['price'] = {
    'close_correlation': round(merged['close_A'].corr(merged['close_H']), 4),
    'pct_chg_correlation': round(merged['close_A'].pct_change().corr(merged['close_H'].pct_change()), 4),
}

# 8. Latest values
last_row = merged.iloc[-1]
report['latest'] = {
    'date': str(last_row['trade_date']),
    'A_close': round(last_row['close_A'], 2),
    'H_close': round(last_row['close_H'], 2),
    'A_RSI': round(last_row['RSI_14_A'], 2),
    'H_RSI': round(last_row['RSI_14_H'], 2),
    'A_MACD_HIST': round(last_row['MACD_HIST_A'], 2),
    'H_MACD_HIST': round(last_row['MACD_HIST_H'], 2),
    'A_BB_PCTB': round(last_row['BB_PCTB_A'], 2),
    'H_BB_PCTB': round(last_row['BB_PCTB_H'], 2),
    'A_ATR': round(last_row['ATR_14_A'], 2),
    'H_ATR': round(last_row['ATR_14_H'], 2),
    'A_ATR_pct': round(last_row['ATR_14_A'] / last_row['close_A'] * 100, 2),
    'H_ATR_pct': round(last_row['ATR_14_H'] / last_row['close_H'] * 100, 2),
}

print(json.dumps(report, indent=2, ensure_ascii=False))
