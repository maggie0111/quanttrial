"""
双均线交叉策略 — 完整执行脚本
运行后生成:
  1. dual_ma_strategy_report.html  (交互式HTML看板)
  2. dual_ma_insights.txt          (策略心得文字)
  3. dual_ma_experiment_results.csv (参数实验结果)
  4. dual_ma_window_results.csv     (时间窗口实验结果)
"""

import pandas as pd
import numpy as np
import json
import os

# ============================================================
# 配置
# ============================================================
INITIAL_CAPITAL = 100000
COMMISSION_RATE = 0.0003
SLIPPAGE = 0.0001
RISK_FREE_RATE = 0.02
SHORT_PERIOD = 5
LONG_PERIOD = 15

STOCKS = {
    'CATL': {'name': '宁德时代', 'file': 'CATL_300750_daily_qfq.csv', 'ts_code': '300750.SZ', 'sector': '动力电池'},
    'SMIC': {'name': '中芯国际', 'file': 'SMIC_688981_daily_qfq.csv', 'ts_code': '688981.SH', 'sector': '半导体'},
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. 数据加载
# ============================================================
def load_data(stock_key):
    cfg = STOCKS[stock_key]
    path = os.path.join(BASE_DIR, cfg['file'])
    df = pd.read_csv(path, dtype={'trade_date': str})
    df = df.sort_values('trade_date').reset_index(drop=True)
    df = df[df['close'] > 0].reset_index(drop=True)
    return df

# ============================================================
# 2. 均线计算
# ============================================================
def calc_ma(df, short=SHORT_PERIOD, long=LONG_PERIOD):
    df = df.copy()
    df['MA_short'] = df['close'].rolling(window=short).mean()
    df['MA_long']  = df['close'].rolling(window=long).mean()
    return df

# ============================================================
# 3. 信号生成
# ============================================================
def gen_signals(df):
    df = df.copy()
    prev_short = df['MA_short'].shift(1)
    prev_long  = df['MA_long'].shift(1)
    golden = (prev_short <= prev_long) & (df['MA_short'] > df['MA_long'])
    death  = (prev_short >= prev_long) & (df['MA_short'] < df['MA_long'])
    df['signal'] = 0
    df.loc[golden, 'signal'] = 1
    df.loc[death,  'signal'] = -1
    df['position'] = 0
    pos = 0
    for i in range(len(df)):
        sig = df.iloc[i]['signal']
        if sig == 1: pos = 1
        elif sig == -1: pos = 0
        df.iloc[i, df.columns.get_loc('position')] = pos
    return df

# ============================================================
# 4. 时间窗口截取
# ============================================================
def select_window(df, time_window='full', long_period=LONG_PERIOD):
    if isinstance(time_window, dict):
        mode = time_window.get('mode', 'custom')
    else:
        mode = time_window
    if mode == 'full':
        return df.reset_index(drop=True)
    n_total = len(df)
    if mode == 'recent_3m':
        cutoff = n_total - 63
    elif mode == 'recent_6m':
        cutoff = n_total - 126
    elif mode == 'recent_12m':
        cutoff = max(0, n_total - 252)
    elif mode == 'custom':
        start = time_window['start_date']
        end = time_window['end_date']
        mask = (df['trade_date'] >= start) & (df['trade_date'] <= end)
        first_idx = mask.idxmax() if mask.any() else 0
        warmup_idx = max(0, first_idx - long_period)
        return df.iloc[warmup_idx:].reset_index(drop=True)
    else:
        return df.reset_index(drop=True)
    cutoff = max(0, cutoff - long_period)
    return df.iloc[cutoff:].reset_index(drop=True)

# ============================================================
# 5. 回测引擎
# ============================================================
def backtest(df, initial_capital=INITIAL_CAPITAL, commission=COMMISSION_RATE, slippage=SLIPPAGE):
    capital = initial_capital
    shares = 0
    pos = 0
    strategy_value = []
    trades = []
    total_cost = 0
    for i in range(len(df)):
        sig = df.iloc[i]['signal']
        close = df.iloc[i]['close']
        date = df.iloc[i]['trade_date']
        if sig == 1 and pos == 0:
            fill_price = close * (1 + slippage)
            cost_per_share = fill_price * (1 + commission)
            shares = capital / cost_per_share
            cost_amount = capital - shares * fill_price
            total_cost += cost_amount + shares * fill_price * slippage
            capital = 0
            pos = 1
            trades.append({'date': date, 'action': 'BUY', 'close': close, 'fill_price': fill_price, 'shares': shares, 'cost': cost_amount})
        elif sig == -1 and pos == 1:
            fill_price = close * (1 - slippage)
            revenue_per_share = fill_price * (1 - commission)
            gross_revenue = shares * fill_price
            net_revenue = shares * revenue_per_share
            cost_amount = gross_revenue - net_revenue
            total_cost += cost_amount + shares * fill_price * slippage
            capital = net_revenue
            trades.append({'date': date, 'action': 'SELL', 'close': close, 'fill_price': fill_price, 'shares': shares, 'revenue': net_revenue, 'cost': cost_amount})
            shares = 0
            pos = 0
        daily_value = capital + shares * close
        strategy_value.append(daily_value)
    result = df.copy()
    result['strategy_value'] = strategy_value
    return result, trades, total_cost

def backtest_benchmark(df, initial_capital=INITIAL_CAPITAL, commission=COMMISSION_RATE, slippage=SLIPPAGE):
    close = df['close'].values
    fill_price = close[0] * (1 + slippage)
    cost_per_share = fill_price * (1 + commission)
    shares = initial_capital / cost_per_share
    buy_cost = initial_capital - shares * fill_price
    slippage_cost = shares * close[0] * slippage
    total_cost = buy_cost + slippage_cost
    benchmark_value = shares * close
    result = df.copy()
    result['benchmark_value'] = benchmark_value
    return result, total_cost

# ============================================================
# 6. 指标计算
# ============================================================
def calc_metrics(strategy_result, benchmark_result, initial_capital=INITIAL_CAPITAL, risk_free_rate=RISK_FREE_RATE):
    sv = strategy_result['strategy_value'].values
    bv = benchmark_result['benchmark_value'].values
    n_days = len(sv)
    total_return = sv[-1] / initial_capital - 1
    annual_return = (1 + total_return) ** (252 / n_days) - 1
    daily_ret_s = pd.Series(sv).pct_change().dropna()
    rf_daily = risk_free_rate / 252
    sharpe_s = (daily_ret_s.mean() - rf_daily) / daily_ret_s.std() * np.sqrt(252) if daily_ret_s.std() > 0 else 0
    running_max_s = pd.Series(sv).cummax()
    drawdown_s = 1 - pd.Series(sv) / running_max_s
    max_dd_s = drawdown_s.max()
    bm_return = bv[-1] / initial_capital - 1
    bm_annual = (1 + bm_return) ** (252 / n_days) - 1
    daily_ret_b = pd.Series(bv).pct_change().dropna()
    sharpe_b = (daily_ret_b.mean() - rf_daily) / daily_ret_b.std() * np.sqrt(252) if daily_ret_b.std() > 0 else 0
    running_max_b = pd.Series(bv).cummax()
    drawdown_b = 1 - pd.Series(bv) / running_max_b
    max_dd_b = drawdown_b.max()
    # --- 交易统计: 按时间顺序正确配对买卖信号 ---
    # 从信号列表中按顺序提取配对的 (买入, 卖出)
    all_signals = strategy_result[strategy_result['signal'] != 0].copy()
    paired_trades = []
    pending_buy = None
    for _, row in all_signals.iterrows():
        if row['signal'] == 1:
            if pending_buy is None:
                pending_buy = row
        elif row['signal'] == -1:
            if pending_buy is not None:
                paired_trades.append((pending_buy, row))
                pending_buy = None

    n_trades = len(paired_trades)
    profits = []
    holding_days = []
    for buy_row, sell_row in paired_trades:
        buy_idx = strategy_result[strategy_result['trade_date'] == buy_row['trade_date']].index[0]
        sell_idx = strategy_result[strategy_result['trade_date'] == sell_row['trade_date']].index[0]
        buy_price = buy_row['close']
        sell_price = sell_row['close']
        profit = (sell_price - buy_price) / buy_price
        profits.append(profit)
        holding_days.append(sell_idx - buy_idx)
    profits = np.array(profits) if profits else np.array([0])
    holding_days = np.array(holding_days) if holding_days else np.array([0])
    win_rate = (profits > 0).sum() / len(profits) * 100 if len(profits) > 0 else 0
    wins = profits[profits > 0]
    losses = profits[profits < 0]
    avg_win = wins.mean() if len(wins) > 0 else 0
    avg_loss = abs(losses.mean()) if len(losses) > 0 else 0
    pl_ratio = avg_win / avg_loss if avg_loss > 0 else float('inf')
    return {
        'total_return': total_return * 100,
        'annual_return': annual_return * 100,
        'bm_return': bm_return * 100,
        'bm_annual': bm_annual * 100,
        'excess_return': (total_return - bm_return) * 100,
        'max_drawdown': max_dd_s * 100,
        'bm_max_drawdown': max_dd_b * 100,
        'sharpe': sharpe_s,
        'bm_sharpe': sharpe_b,
        'win_rate': win_rate,
        'pl_ratio': pl_ratio,
        'n_trades': n_trades,
        'avg_holding_days': holding_days.mean() if len(holding_days) > 0 else 0,
    }

# ============================================================
# 7. 完整管线
# ============================================================
def run_strategy(stock_key, short=SHORT_PERIOD, long=LONG_PERIOD, time_window='full'):
    df = load_data(stock_key)
    df = calc_ma(df, short, long)
    df = gen_signals(df)
    df = select_window(df, time_window, long)
    result, trades, total_cost = backtest(df)
    result_bm, cost_bm = backtest_benchmark(df)
    metrics = calc_metrics(result, result_bm)
    metrics['total_cost'] = total_cost
    metrics['bm_cost'] = cost_bm
    metrics['stock'] = stock_key
    metrics['short'] = short
    metrics['long'] = long
    metrics['window'] = time_window
    metrics['n_days'] = len(df)
    return result, result_bm, trades, metrics

# ============================================================
# 8. 执行全部分析
# ============================================================
print("=" * 60)
print("双均线交叉策略 — 开始执行")
print("=" * 60)

# --- 默认参数回测 ---
results = {}
for sk in ['CATL', 'SMIC']:
    r, rb, t, m = run_strategy(sk)
    results[sk] = {'result': r, 'benchmark': rb, 'trades': t, 'metrics': m}
    cfg = STOCKS[sk]
    print(f"\n{cfg['name']} ({cfg['ts_code']}) — 5日/15日均线, 全周期")
    print(f"  交易日: {m['n_days']}天 | 交易次数: {m['n_trades']} | 胜率: {m['win_rate']:.1f}%")
    print(f"  策略收益: {m['total_return']:.2f}% | 基准收益: {m['bm_return']:.2f}% | 超额: {m['excess_return']:+.2f}%")
    print(f"  最大回撤: 策略{m['max_drawdown']:.2f}% vs 基准{m['bm_max_drawdown']:.2f}%")
    print(f"  夏普: 策略{m['sharpe']:.3f} vs 基准{m['bm_sharpe']:.3f}")

# --- 参数实验 ---
PARAM_GRID = [
    {'short': 5,  'long': 10},
    {'short': 5,  'long': 15},
    {'short': 5,  'long': 20},
    {'short': 10, 'long': 20},
    {'short': 10, 'long': 30},
    {'short': 20, 'long': 60},
]
exp_results = []
for sk in ['CATL', 'SMIC']:
    for p in PARAM_GRID:
        _, _, _, m = run_strategy(sk, short=p['short'], long=p['long'])
        exp_results.append(m)

exp_df = pd.DataFrame(exp_results)
exp_df.insert(0, '股票', exp_df['stock'].map(lambda k: STOCKS[k]['name']))
exp_df = exp_df[['股票', 'short', 'long', 'n_days', 'total_return', 'annual_return',
                 'bm_return', 'excess_return', 'max_drawdown', 'bm_max_drawdown',
                 'sharpe', 'bm_sharpe', 'win_rate', 'n_trades', 'total_cost']]
exp_df.columns = ['股票', '短均线', '长均线', '交易日数', '总收益率%', '年化收益率%',
                  '基准收益率%', '超额收益%', '最大回撤%', '基准回撤%', '夏普', '基准夏普',
                  '胜率%', '交易次数', '总成本(元)']
exp_df.to_csv(os.path.join(BASE_DIR, 'dual_ma_experiment_results.csv'), index=False, encoding='utf-8-sig')
print(f"\n参数实验完成: {len(exp_df)} 组结果已保存")

# --- 时间窗口实验 ---
WINDOWS = ['full', 'recent_3m', 'recent_6m', 'recent_12m']
WINDOW_NAMES = {'full': '全周期', 'recent_3m': '近3个月', 'recent_6m': '近6个月', 'recent_12m': '近12个月'}
win_results = []
for sk in ['CATL', 'SMIC']:
    for w in WINDOWS:
        _, _, _, m = run_strategy(sk, short=5, long=15, time_window=w)
        m['window_name'] = WINDOW_NAMES[w]
        win_results.append(m)

win_df = pd.DataFrame(win_results)
win_df.insert(0, '股票', win_df['stock'].map(lambda k: STOCKS[k]['name']))
win_df.insert(1, '时间窗口', win_df['window_name'])
win_df = win_df[['股票', '时间窗口', 'n_days', 'total_return', 'annual_return',
                 'bm_return', 'excess_return', 'max_drawdown', 'bm_max_drawdown',
                 'sharpe', 'bm_sharpe', 'win_rate', 'n_trades']]
win_df.columns = ['股票', '时间窗口', '交易日数', '总收益率%', '年化%', '基准%', '超额%',
                  '最大回撤%', '基准回撤%', '夏普', '基准夏普', '胜率%', '交易次数']
win_df.to_csv(os.path.join(BASE_DIR, 'dual_ma_window_results.csv'), index=False, encoding='utf-8-sig')
print(f"时间窗口实验完成: {len(win_df)} 组结果已保存")

# ============================================================
# 9. 生成 HTML 报告
# ============================================================
def df_to_chart_data(df, cols):
    """提取指定列转为 ECharts series data"""
    dates = df['trade_date'].tolist()
    series = {}
    for c in cols:
        if c in df.columns:
            vals = df[c].tolist()
            series[c] = [None if (isinstance(v, float) and np.isnan(v)) else round(float(v), 4) for v in vals]
    return dates, series

def date_fmt(trade_date_str):
    """YYYYMMDD -> YYYY-MM-DD"""
    if len(trade_date_str) == 8:
        return f"{trade_date_str[:4]}-{trade_date_str[4:6]}-{trade_date_str[6:8]}"
    return trade_date_str

# 为每支股票准备图表数据
chart_data = {}
for sk in ['CATL', 'SMIC']:
    r = results[sk]['result']
    rb = results[sk]['benchmark']
    m = results[sk]['metrics']
    trades = results[sk]['trades']
    cfg = STOCKS[sk]

    dates = [date_fmt(d) for d in r['trade_date'].tolist()]

    # 价格+均线
    close_data = [round(float(v), 2) for v in r['close']]
    ma_short_data = [round(float(v), 2) if not np.isnan(v) else None for v in r['MA_short']]
    ma_long_data = [round(float(v), 2) if not np.isnan(v) else None for v in r['MA_long']]

    # 买卖标记
    buy_points = []
    sell_points = []
    for _, row in r.iterrows():
        d = date_fmt(row['trade_date'])
        if row['signal'] == 1:
            buy_points.append({'coord': [d, round(float(row['close']) * 0.995, 2)], 'value': '买入'})
        elif row['signal'] == -1:
            sell_points.append({'coord': [d, round(float(row['close']) * 1.005, 2)], 'value': '卖出'})

    # 成交量 (红涨绿跌)
    vol_data = []
    for _, row in r.iterrows():
        color = '#FF4444' if row['pct_chg'] >= 0 else '#00AA00'
        vol_data.append({'value': round(float(row['volume']), 0), 'itemStyle': {'color': color}})

    # 净值对比
    sv_data = [round(float(v), 2) for v in r['strategy_value']]
    bv_data = [round(float(v), 2) for v in rb['benchmark_value']]

    # 回撤
    sv_series = pd.Series(r['strategy_value'].values)
    bv_series = pd.Series(rb['benchmark_value'].values)
    dd_s = ((1 - sv_series / sv_series.cummax()) * 100).round(2).tolist()
    dd_b = ((1 - bv_series / bv_series.cummax()) * 100).round(2).tolist()

    # 交易明细
    trade_list = []
    for t in trades:
        trade_list.append({
            'date': date_fmt(t['date']),
            'action': '买入' if t['action'] == 'BUY' else '卖出',
            'close': round(t['close'], 2),
            'fill_price': round(t['fill_price'], 4),
            'shares': round(t['shares'], 0),
            'cost': round(t.get('cost', 0), 2),
        })

    chart_data[sk] = {
        'name': cfg['name'],
        'ts_code': cfg['ts_code'],
        'sector': cfg['sector'],
        'dates': dates,
        'close': close_data,
        'ma_short': ma_short_data,
        'ma_long': ma_long_data,
        'buy_points': buy_points,
        'sell_points': sell_points,
        'vol_data': vol_data,
        'sv_data': sv_data,
        'bv_data': bv_data,
        'dd_s': dd_s,
        'dd_b': dd_b,
        'trades': trade_list,
        'metrics': m,
    }

# 参数实验表格数据
exp_table = []
for _, row in exp_df.iterrows():
    exp_table.append({
        '股票': row['股票'],
        '短均线': int(row['短均线']),
        '长均线': int(row['长均线']),
        '交易日数': int(row['交易日数']),
        '总收益率': round(row['总收益率%'], 2),
        '年化收益率': round(row['年化收益率%'], 2),
        '基准收益率': round(row['基准收益率%'], 2),
        '超额收益': round(row['超额收益%'], 2),
        '最大回撤': round(row['最大回撤%'], 2),
        '基准回撤': round(row['基准回撤%'], 2),
        '夏普': round(row['夏普'], 3),
        '基准夏普': round(row['基准夏普'], 3),
        '胜率': round(row['胜率%'], 1),
        '交易次数': int(row['交易次数']),
        '总成本': round(row['总成本(元)'], 2),
    })

# 时间窗口实验表格数据
win_table = []
for _, row in win_df.iterrows():
    win_table.append({
        '股票': row['股票'],
        '时间窗口': row['时间窗口'],
        '交易日数': int(row['交易日数']),
        '总收益率': round(row['总收益率%'], 2),
        '年化': round(row['年化%'], 2),
        '基准': round(row['基准%'], 2),
        '超额': round(row['超额%'], 2),
        '最大回撤': round(row['最大回撤%'], 2),
        '基准回撤': round(row['基准回撤%'], 2),
        '夏普': round(row['夏普'], 3),
        '基准夏普': round(row['基准夏普'], 3),
        '胜率': round(row['胜率%'], 1),
        '交易次数': int(row['交易次数']),
    })

# 参数实验柱状图数据
param_chart_data = {}
for sk in ['CATL', 'SMIC']:
    cfg = STOCKS[sk]
    sub = [e for e in exp_table if e['股票'] == cfg['name']]
    labels = [f"{e['短均线']}/{e['长均线']}" for e in sub]
    param_chart_data[sk] = {
        'labels': labels,
        'strategy_returns': [e['总收益率'] for e in sub],
        'benchmark_returns': [e['基准收益率'] for e in sub],
        'strategy_dd': [e['最大回撤'] for e in sub],
        'benchmark_dd': [e['基准回撤'] for e in sub],
        'name': cfg['name'],
    }

# 时间窗口柱状图数据
window_chart_data = {}
for sk in ['CATL', 'SMIC']:
    cfg = STOCKS[sk]
    sub = [w for w in win_table if w['股票'] == cfg['name']]
    labels = [w['时间窗口'] for w in sub]
    window_chart_data[sk] = {
        'labels': labels,
        'strategy_returns': [w['总收益率'] for w in sub],
        'benchmark_returns': [w['基准'] for w in sub],
        'excess': [w['超额'] for w in sub],
        'name': cfg['name'],
    }

# ============================================================
# 构建心得文字
# ============================================================
m_c = results['CATL']['metrics']
m_s = results['SMIC']['metrics']

# 找最优参数
best_catl = max([e for e in exp_table if e['股票'] == '宁德时代'], key=lambda x: x['总收益率'])
best_smic = max([e for e in exp_table if e['股票'] == '中芯国际'], key=lambda x: x['总收益率'])

insights = f"""双均线交叉策略 — 实验心得与总结

一、策略概述

双均线交叉策略是一种经典的趋势跟踪型策略，其核心逻辑是利用短期移动平均线（反映近期价格趋势，反应快但噪声多）与长期移动平均线（反映中长期趋势，滞后但稳定）的交叉关系来判断趋势方向。当短均线从下方上穿长均线时形成"金叉"，视为买入信号；当短均线从上方下穿长均线时形成"死叉"，视为卖出信号。

二、回测结果分析

1. 宁德时代（300750.SZ）— 默认参数 5日/15日
   - 回测区间：{m_c['n_days']:.0f}个交易日
   - 双均线策略总收益率：{m_c['total_return']:.2f}%，年化收益率：{m_c['annual_return']:.2f}%
   - 买入持有基准收益率：{m_c['bm_return']:.2f}%，年化：{m_c['bm_annual']:.2f}%
   - 超额收益：{m_c['excess_return']:+.2f}%（{'策略跑赢基准' if m_c['excess_return'] > 0 else '策略跑输基准'}）
   - 最大回撤：策略{m_c['max_drawdown']:.2f}% vs 基准{m_c['bm_max_drawdown']:.2f}%
   - 夏普比率：策略{m_c['sharpe']:.3f} vs 基准{m_c['bm_sharpe']:.3f}
   - 胜率：{m_c['win_rate']:.1f}%，交易次数：{m_c['n_trades']}次，平均持仓：{m_c['avg_holding_days']:.0f}天
   - 盈亏比：{m_c['pl_ratio']:.2f}，总交易成本：{m_c['total_cost']:.2f}元

2. 中芯国际（688981.SH）— 默认参数 5日/15日
   - 回测区间：{m_s['n_days']:.0f}个交易日
   - 双均线策略总收益率：{m_s['total_return']:.2f}%，年化收益率：{m_s['annual_return']:.2f}%
   - 买入持有基准收益率：{m_s['bm_return']:.2f}%，年化：{m_s['bm_annual']:.2f}%
   - 超额收益：{m_s['excess_return']:+.2f}%（{'策略跑赢基准' if m_s['excess_return'] > 0 else '策略跑输基准'}）
   - 最大回撤：策略{m_s['max_drawdown']:.2f}% vs 基准{m_s['bm_max_drawdown']:.2f}%
   - 夏普比率：策略{m_s['sharpe']:.3f} vs 基准{m_s['bm_sharpe']:.3f}
   - 胜率：{m_s['win_rate']:.1f}%，交易次数：{m_s['n_trades']}次，平均持仓：{m_s['avg_holding_days']:.0f}天
   - 盈亏比：{m_s['pl_ratio']:.2f}，总交易成本：{m_s['total_cost']:.2f}元

三、参数实验分析

通过对6组不同均线参数组合（5/10、5/15、5/20、10/20、10/30、20/60）的回测对比，我们发现：

1. 宁德时代最优参数组合为 {best_catl['短均线']}/{best_catl['长均线']}日，总收益率 {best_catl['总收益率']:.2f}%，超额收益 {best_catl['超额收益']:+.2f}%。
2. 中芯国际最优参数组合为 {best_smic['短均线']}/{best_smic['长均线']}日，总收益率 {best_smic['总收益率']:.2f}%，超额收益 {best_smic['超额收益']:+.2f}%。
3. 短周期参数（如5/10）产生的交易信号更频繁，交易次数多，交易成本侵蚀明显；长周期参数（如20/60）信号少但更可靠，适合中长线投资。
4. 不同股票的最优参数不同，说明参数选择需要与个股的波动特征相匹配。

四、时间窗口实验分析

通过对比全周期、近3个月、近6个月、近12个月四个时间窗口的表现，可以观察到：
1. 不同市场阶段策略表现差异显著，趋势行情中策略表现优于震荡行情。
2. 在单边上涨或下跌阶段，金叉/死叉信号能有效捕捉趋势反转，策略可能跑赢买入持有。
3. 在震荡行情中，频繁的假信号导致反复止损，策略可能跑输买入持有。
4. 时间窗口选择应覆盖不同市场环境，避免仅在单一行情下评估策略效果。

五、双均线策略适用场景

1. 趋势行情（牛市/熊市）中表现优异，金叉/死叉能有效捕捉趋势反转。
2. 震荡行情中频繁假信号，反复止损导致收益为负甚至跑输买入持有。
3. 长周期均线组合（如20/60）信号少但更可靠，适合中长线投资者。
4. 短周期均线组合（如5/10）信号多但噪声大，交易成本侵蚀明显。

六、参数选择心得

1. 短均线周期过短会导致信号过于频繁，交易成本侵蚀收益。
2. 长均线周期过长会导致信号滞后，错过行情起点。
3. 均线周期选择应结合个股波动率和持仓周期偏好。
4. 建议：波动大的股票用较长周期，波动小的用较短周期。

七、策略局限与改进方向

1. 单一指标策略局限性大，容易在震荡市亏损。
2. 可加入成交量、MACD、RSI等辅助指标过滤假信号。
3. 可加入止损/止盈机制控制风险。
4. 可尝试动态调仓而非满仓/空仓二选一。
5. 交易成本（手续费万三+滑点万一）对高频策略影响显著，需用超额收益覆盖。
6. 与买入持有对比：若策略无法跑赢买入持有，说明趋势判断未带来正增益。

八、核心结论

双均线策略的核心价值在于趋势识别和风险规避。在单边行情中，它能有效捕捉趋势并在反转时及时退出；但在震荡市中，频繁的假信号和交易成本会侵蚀收益。因此，策略的有效性高度依赖市场环境和参数选择，没有放之四海而皆准的最优参数，需根据具体股票和市场阶段灵活调整。对于普通投资者而言，双均线策略更适合作为趋势判断的辅助工具，而非唯一的交易依据。
"""

with open(os.path.join(BASE_DIR, 'dual_ma_insights.txt'), 'w', encoding='utf-8') as f:
    f.write(insights)
print("策略心得已保存: dual_ma_insights.txt")

# ============================================================
# 生成 HTML
# ============================================================
# 将数据嵌入 JSON
all_data = {
    'chart_data': chart_data,
    'exp_table': exp_table,
    'win_table': win_table,
    'param_chart': param_chart_data,
    'window_chart': window_chart_data,
}
data_json = json.dumps(all_data, ensure_ascii=False, default=str)

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>双均线交叉策略 — 量化回测报告</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Microsoft YaHei', 'SimHei', sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
.header {{ background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 30px 40px; text-align: center; }}
.header h1 {{ font-size: 28px; margin-bottom: 8px; }}
.header p {{ font-size: 14px; opacity: 0.85; }}
.container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
.section {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); margin-bottom: 24px; overflow: hidden; }}
.section-header {{ background: #e8eaf6; padding: 14px 24px; border-left: 4px solid #3f51b5; font-size: 18px; font-weight: bold; color: #1a237e; }}
.section-body {{ padding: 24px; }}
.chart-container {{ width: 100%; }}
.chart {{ width: 100%; }}
.metrics-table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
.metrics-table th {{ background: #3f51b5; color: white; padding: 10px 12px; text-align: center; }}
.metrics-table td {{ padding: 8px 12px; text-align: center; border-bottom: 1px solid #e0e0e0; }}
.metrics-table tr:nth-child(even) {{ background: #f5f5f5; }}
.metrics-table .positive {{ color: #FF0000; font-weight: bold; }}
.metrics-table .negative {{ color: #00AA00; font-weight: bold; }}
.data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
.data-table th {{ background: #455a64; color: white; padding: 8px; text-align: center; position: sticky; top: 0; }}
.data-table td {{ padding: 6px 8px; text-align: center; border-bottom: 1px solid #e0e0e0; }}
.data-table tr:nth-child(even) {{ background: #fafafa; }}
.trade-table {{ max-height: 300px; overflow-y: auto; }}
.stock-tabs {{ display: flex; gap: 4px; margin-bottom: 16px; }}
.stock-tab {{ padding: 8px 24px; background: #e0e0e0; border-radius: 6px 6px 0 0; cursor: pointer; font-size: 14px; transition: all 0.2s; }}
.stock-tab.active {{ background: #3f51b5; color: white; }}
.stock-panel {{ display: none; }}
.stock-panel.active {{ display: block; }}
.insights {{ white-space: pre-wrap; font-size: 14px; line-height: 1.8; color: #444; }}
.insights h2 {{ color: #1a237e; font-size: 16px; margin-top: 16px; margin-bottom: 8px; }}
.footer {{ text-align: center; padding: 20px; color: #999; font-size: 12px; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 16px; }}
.summary-card {{ background: linear-gradient(135deg, #e3f2fd 0%, #f3e5f5 100%); border-radius: 8px; padding: 16px; text-align: center; }}
.summary-card .label {{ font-size: 12px; color: #666; margin-bottom: 4px; }}
.summary-card .value {{ font-size: 22px; font-weight: bold; color: #1a237e; }}
.summary-card .sub {{ font-size: 11px; color: #999; }}
</style>
</head>
<body>

<div class="header">
  <h1>双均线交叉策略 — 量化回测报告</h1>
  <p>课程作业 TASK2 | 作者: 郭美杰 | 股票池: 宁德时代(300750.SZ) + 中芯国际(688981.SH)</p>
  <p>回测参数: 初始资金10万 | 手续费万三 | 滑点万一 | 红涨绿跌(A股惯例)</p>
</div>

<div class="container">

  <!-- 策略概述 -->
  <div class="section">
    <div class="section-header">策略概述</div>
    <div class="section-body">
      <p style="font-size:14px; line-height:1.8;">
        双均线交叉策略 (Dual Moving Average Crossover) 是一种经典的趋势跟踪型策略。其核心逻辑是利用短期移动平均线与长期移动平均线的交叉关系判断趋势方向：
      </p>
      <ul style="margin:12px 0 12px 24px; font-size:14px; line-height:2;">
        <li><b>金叉 (Golden Cross)</b>：短均线从下方上穿长均线 → 买入信号，趋势转强</li>
        <li><b>死叉 (Death Cross)</b>：短均线从上方下穿长均线 → 卖出信号，趋势转弱</li>
        <li><b>交易成本</b>：手续费万三(双边) + 滑点万一(双边)，单次完整交易成本约0.08%</li>
        <li><b>基准对比</b>：买入持有策略(首日买入，末日卖出)，同样扣除交易成本</li>
      </ul>
    </div>
  </div>

  <!-- 各股票详情 -->
  <div class="section">
    <div class="section-header">默认参数回测 (5日/15日均线, 全周期)</div>
    <div class="section-body">
      <div class="stock-tabs">
        <div class="stock-tab active" onclick="switchStock('CATL')">宁德时代 (300750.SZ)</div>
        <div class="stock-tab" onclick="switchStock('SMIC')">中芯国际 (688981.SH)</div>
      </div>
"""

for sk in ['CATL', 'SMIC']:
    cd = chart_data[sk]
    m = cd['metrics']
    active = 'active' if sk == 'CATL' else ''
    html += f"""
      <div class="stock-panel {active}" id="panel-{sk}">
        <!-- 指标卡片 -->
        <div class="summary-grid">
          <div class="summary-card">
            <div class="label">策略总收益率</div>
            <div class="value" style="color:{'#FF0000' if m['total_return']>=0 else '#00AA00'}">{m['total_return']:.2f}%</div>
            <div class="sub">基准 {m['bm_return']:.2f}%</div>
          </div>
          <div class="summary-card">
            <div class="label">超额收益</div>
            <div class="value" style="color:{'#FF0000' if m['excess_return']>=0 else '#00AA00'}">{m['excess_return']:+.2f}%</div>
            <div class="sub">策略 - 基准</div>
          </div>
          <div class="summary-card">
            <div class="label">最大回撤</div>
            <div class="value" style="color:#FF4444">{m['max_drawdown']:.2f}%</div>
            <div class="sub">基准 {m['bm_max_drawdown']:.2f}%</div>
          </div>
          <div class="summary-card">
            <div class="label">夏普比率</div>
            <div class="value">{m['sharpe']:.3f}</div>
            <div class="sub">基准 {m['bm_sharpe']:.3f}</div>
          </div>
          <div class="summary-card">
            <div class="label">胜率</div>
            <div class="value">{m['win_rate']:.1f}%</div>
            <div class="sub">{m['n_trades']}笔交易</div>
          </div>
          <div class="summary-card">
            <div class="label">盈亏比</div>
            <div class="value">{m['pl_ratio']:.2f}</div>
            <div class="sub">平均持仓{m['avg_holding_days']:.0f}天</div>
          </div>
        </div>

        <!-- 图表 -->
        <div class="chart-container">
          <div id="chart-price-{sk}" class="chart" style="height:450px;"></div>
          <div id="chart-vol-{sk}" class="chart" style="height:180px;"></div>
          <div id="chart-nav-{sk}" class="chart" style="height:350px;"></div>
          <div id="chart-dd-{sk}" class="chart" style="height:280px;"></div>
        </div>

        <!-- 指标对比表 -->
        <h3 style="margin:20px 0 10px; color:#1a237e;">量化指标对比</h3>
        <table class="metrics-table">
          <thead>
            <tr><th>指标</th><th>双均线策略</th><th>买入持有(基准)</th><th>差值</th></tr>
          </thead>
          <tbody>
            <tr><td>总收益率</td><td>{m['total_return']:.2f}%</td><td>{m['bm_return']:.2f}%</td><td style="color:{'#FF0000' if m['excess_return']>=0 else '#00AA00'}">{m['excess_return']:+.2f}%</td></tr>
            <tr><td>年化收益率</td><td>{m['annual_return']:.2f}%</td><td>{m['bm_annual']:.2f}%</td><td>{m['annual_return']-m['bm_annual']:+.2f}%</td></tr>
            <tr><td>最大回撤</td><td>{m['max_drawdown']:.2f}%</td><td>{m['bm_max_drawdown']:.2f}%</td><td>{m['max_drawdown']-m['bm_max_drawdown']:+.2f}%</td></tr>
            <tr><td>夏普比率</td><td>{m['sharpe']:.3f}</td><td>{m['bm_sharpe']:.3f}</td><td>{m['sharpe']-m['bm_sharpe']:+.3f}</td></tr>
            <tr><td>胜率</td><td>{m['win_rate']:.1f}%</td><td>—</td><td>—</td></tr>
            <tr><td>盈亏比</td><td>{m['pl_ratio']:.2f}</td><td>—</td><td>—</td></tr>
            <tr><td>交易次数</td><td>{m['n_trades']}</td><td>1</td><td>—</td></tr>
            <tr><td>平均持仓天数</td><td>{m['avg_holding_days']:.0f}天</td><td>全部</td><td>—</td></tr>
            <tr><td>总交易成本</td><td>{m['total_cost']:.2f}元</td><td>{m['bm_cost']:.2f}元</td><td>{m['total_cost']-m['bm_cost']:+.2f}元</td></tr>
          </tbody>
        </table>

        <!-- 交易明细 -->
        <h3 style="margin:20px 0 10px; color:#1a237e;">交易明细</h3>
        <div class="trade-table">
          <table class="data-table">
            <thead><tr><th>序号</th><th>日期</th><th>操作</th><th>收盘价</th><th>成交价</th><th>股数</th><th>手续费</th></tr></thead>
            <tbody>
"""

    for i, t in enumerate(cd['trades']):
        action_color = '#FF0000' if t['action'] == '买入' else '#00AA00'
        html += f'<tr><td>{i+1}</td><td>{t["date"]}</td><td style="color:{action_color};font-weight:bold">{t["action"]}</td><td>{t["close"]:.2f}</td><td>{t["fill_price"]:.4f}</td><td>{t["shares"]:.0f}</td><td>{t["cost"]:.2f}</td></tr>'

    html += """
            </tbody>
          </table>
        </div>
      </div>
"""

html += """
    </div>
  </div>
"""

# 参数实验
html += """
  <!-- 参数实验 -->
  <div class="section">
    <div class="section-header">参数实验 — 不同均线周期对比</div>
    <div class="section-body">
      <div class="chart-container">
        <div id="chart-param-return" class="chart" style="height:400px;"></div>
        <div id="chart-param-dd" class="chart" style="height:400px;"></div>
      </div>
      <h3 style="margin:20px 0 10px; color:#1a237e;">参数实验汇总表</h3>
"""

html += '<div class="trade-table"><table class="data-table"><thead><tr>'
cols = ['股票','短均线','长均线','交易日数','总收益率','年化收益率','基准收益率','超额收益','最大回撤','基准回撤','夏普','基准夏普','胜率','交易次数','总成本']
for c in cols:
    html += f'<th>{c}</th>'
html += '</tr></thead><tbody>'
for e in exp_table:
    html += '<tr>'
    for c in cols:
        key_map = {'交易日数':'交易日数','总收益率':'总收益率','年化收益率':'年化收益率','基准收益率':'基准收益率',
                   '超额收益':'超额收益','最大回撤':'最大回撤','基准回撤':'基准回撤','夏普':'夏普','基准夏普':'基准夏普',
                   '胜率':'胜率','交易次数':'交易次数','总成本':'总成本'}
        k = key_map.get(c, c)
        val = e.get(k, '')
        if isinstance(val, float):
            val = f'{val:.2f}'
        if c == '超额收益':
            color = '#FF0000' if float(e.get('超额收益', 0)) >= 0 else '#00AA00'
            html += f'<td style="color:{color}">{val}</td>'
        else:
            html += f'<td>{val}</td>'
    html += '</tr>'
html += '</tbody></table></div>'
html += """
    </div>
  </div>
"""

# 时间窗口实验
html += """
  <!-- 时间窗口实验 -->
  <div class="section">
    <div class="section-header">时间窗口实验 — 不同市场阶段对比</div>
    <div class="section-body">
      <div class="chart-container">
        <div id="chart-window-return" class="chart" style="height:400px;"></div>
        <div id="chart-window-excess" class="chart" style="height:400px;"></div>
      </div>
      <h3 style="margin:20px 0 10px; color:#1a237e;">时间窗口实验汇总表</h3>
"""

html += '<div class="trade-table"><table class="data-table"><thead><tr>'
wcols = ['股票','时间窗口','交易日数','总收益率','年化','基准','超额','最大回撤','基准回撤','夏普','基准夏普','胜率','交易次数']
for c in wcols:
    html += f'<th>{c}</th>'
html += '</tr></thead><tbody>'
for w in win_table:
    html += '<tr>'
    for c in wcols:
        k = c
        val = w.get(k, '')
        if isinstance(val, float):
            val = f'{val:.2f}'
        if c == '超额':
            color = '#FF0000' if float(w.get('超额', 0)) >= 0 else '#00AA00'
            html += f'<td style="color:{color}">{val}</td>'
        else:
            html += f'<td>{val}</td>'
    html += '</tr>'
html += '</tbody></table></div>'
html += """
    </div>
  </div>
"""

# 策略心得
html += """
  <!-- 策略心得 -->
  <div class="section">
    <div class="section-header">策略心得与总结</div>
    <div class="section-body">
      <div class="insights" id="insights-text"></div>
    </div>
  </div>
"""

html += """
  <div class="footer">
    双均线交叉策略回测报告 | 生成时间: 2026-07-11 | 数据源: Tushare 前复权日线
  </div>
</div>

<script>
const DATA = """ + data_json + """;

// 心得文字
document.getElementById('insights-text').textContent = `""" + insights.replace('`', '\\`').replace('\\', '\\\\') + """`;

// 切换股票
function switchStock(sk) {
  document.querySelectorAll('.stock-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.stock-panel').forEach(p => p.classList.remove('active'));
  event.target.classList.add('active');
  document.getElementById('panel-' + sk).classList.add('active');
  // 重新渲染图表
  setTimeout(() => renderStockCharts(sk), 100);
}

function renderStockCharts(sk) {
  const cd = DATA.chart_data[sk];
  const dates = cd.dates;

  // 1. 价格+均线+信号
  const priceChart = echarts.init(document.getElementById('chart-price-' + sk));
  priceChart.setOption({
    title: { text: cd.name + ' (' + cd.ts_code + ') — 双均线策略 (5日/15日)', left: 'center', fontSize: 14 },
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { data: ['收盘价','MA5','MA15','买入','卖出'], top: 30 },
    grid: { left: '5%', right: '3%', bottom: '8%', top: '15%' },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: '价格(元)', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 5 }],
    series: [
      { name: '收盘价', type: 'line', data: cd.close, itemStyle: { color: '#333' }, lineStyle: { width: 1.2 } },
      { name: 'MA5', type: 'line', data: cd.ma_short, itemStyle: { color: '#FF6B6B' }, lineStyle: { width: 1.5 }, connectNulls: true },
      { name: 'MA15', type: 'line', data: cd.ma_long, itemStyle: { color: '#4ECDC4' }, lineStyle: { width: 1.5 }, connectNulls: true },
      { name: '买入', type: 'scatter', data: cd.buy_points.map(p => p.coord), symbol: 'triangle', symbolSize: 12, itemStyle: { color: '#FF0000' }, tooltip: { formatter: '买入' } },
      { name: '卖出', type: 'scatter', data: cd.sell_points.map(p => p.coord), symbol: 'pin', symbolSize: 12, itemStyle: { color: '#00AA00' }, tooltip: { formatter: '卖出' } },
    ]
  });

  // 2. 成交量
  const volChart = echarts.init(document.getElementById('chart-vol-' + sk));
  volChart.setOption({
    title: { text: '成交量 (红涨绿跌)', left: 'center', fontSize: 12 },
    tooltip: { trigger: 'axis' },
    grid: { left: '5%', right: '3%', bottom: '8%', top: '15%' },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: '成交量(手)' },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 15, bottom: 5 }],
    series: [{ type: 'bar', data: cd.vol_data, name: '成交量' }]
  });

  // 3. 净值对比
  const navChart = echarts.init(document.getElementById('chart-nav-' + sk));
  navChart.setOption({
    title: { text: cd.name + ' — 策略净值 vs 买入持有', left: 'center', fontSize: 14 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['双均线策略','买入持有(基准)','初始资金'], top: 30 },
    grid: { left: '5%', right: '3%', bottom: '8%', top: '15%' },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: '净值(元)', scale: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 5 }],
    series: [
      { name: '双均线策略', type: 'line', data: cd.sv_data, itemStyle: { color: '#5470C6' }, lineStyle: { width: 2 } },
      { name: '买入持有(基准)', type: 'line', data: cd.bv_data, itemStyle: { color: '#91CC75' }, lineStyle: { width: 2, type: 'dashed' } },
      { name: '初始资金', type: 'line', data: dates.map(() => 100000), itemStyle: { color: '#999' }, lineStyle: { width: 1, type: 'dotted' }, symbol: 'none' },
    ]
  });

  // 4. 回撤对比
  const ddChart = echarts.init(document.getElementById('chart-dd-' + sk));
  ddChart.setOption({
    title: { text: cd.name + ' — 最大回撤对比', left: 'center', fontSize: 14 },
    tooltip: { trigger: 'axis' },
    legend: { data: ['双均线回撤','买入持有回撤'], top: 30 },
    grid: { left: '5%', right: '3%', bottom: '8%', top: '15%' },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: '回撤(%)', inverse: true },
    dataZoom: [{ type: 'inside' }, { type: 'slider', height: 20, bottom: 5 }],
    series: [
      { name: '双均线回撤', type: 'line', data: cd.dd_s, areaStyle: { color: 'rgba(84,112,198,0.3)' }, itemStyle: { color: '#5470C6' } },
      { name: '买入持有回撤', type: 'line', data: cd.dd_b, itemStyle: { color: '#91CC75' }, lineStyle: { type: 'dashed' } },
    ]
  });
}

// 渲染默认股票
renderStockCharts('CATL');

// 参数实验柱状图
const paramReturnChart = echarts.init(document.getElementById('chart-param-return'));
const catlParam = DATA.param_chart.CATL;
const smicParam = DATA.param_chart.SMIC;
paramReturnChart.setOption({
  title: { text: '不同均线参数 — 总收益率对比', left: 'center', fontSize: 14 },
  tooltip: { trigger: 'axis' },
  legend: { data: ['宁德时代-策略','宁德时代-基准','中芯国际-策略','中芯国际-基准'], top: 30 },
  grid: { left: '5%', right: '3%', bottom: '10%', top: '15%' },
  xAxis: { type: 'category', data: catlParam.labels, name: '短/长均线' },
  yAxis: { type: 'value', name: '收益率(%)' },
  series: [
    { name: '宁德时代-策略', type: 'bar', data: catlParam.strategy_returns, itemStyle: { color: '#5470C6' } },
    { name: '宁德时代-基准', type: 'bar', data: catlParam.benchmark_returns, itemStyle: { color: '#91CC75' } },
    { name: '中芯国际-策略', type: 'bar', data: smicParam.strategy_returns, itemStyle: { color: '#FF6B6B' } },
    { name: '中芯国际-基准', type: 'bar', data: smicParam.benchmark_returns, itemStyle: { color: '#4ECDC4' } },
  ]
});

const paramDDChart = echarts.init(document.getElementById('chart-param-dd'));
paramDDChart.setOption({
  title: { text: '不同均线参数 — 最大回撤对比', left: 'center', fontSize: 14 },
  tooltip: { trigger: 'axis' },
  legend: { data: ['宁德时代-策略','宁德时代-基准','中芯国际-策略','中芯国际-基准'], top: 30 },
  grid: { left: '5%', right: '3%', bottom: '10%', top: '15%' },
  xAxis: { type: 'category', data: catlParam.labels, name: '短/长均线' },
  yAxis: { type: 'value', name: '回撤(%)' },
  series: [
    { name: '宁德时代-策略', type: 'bar', data: catlParam.strategy_dd, itemStyle: { color: '#5470C6' } },
    { name: '宁德时代-基准', type: 'bar', data: catlParam.benchmark_dd, itemStyle: { color: '#91CC75' } },
    { name: '中芯国际-策略', type: 'bar', data: smicParam.strategy_dd, itemStyle: { color: '#FF6B6B' } },
    { name: '中芯国际-基准', type: 'bar', data: smicParam.benchmark_dd, itemStyle: { color: '#4ECDC4' } },
  ]
});

// 时间窗口柱状图
const windowReturnChart = echarts.init(document.getElementById('chart-window-return'));
const catlWin = DATA.window_chart.CATL;
const smicWin = DATA.window_chart.SMIC;
windowReturnChart.setOption({
  title: { text: '不同时间窗口 — 总收益率对比', left: 'center', fontSize: 14 },
  tooltip: { trigger: 'axis' },
  legend: { data: ['宁德时代-策略','宁德时代-基准','中芯国际-策略','中芯国际-基准'], top: 30 },
  grid: { left: '5%', right: '3%', bottom: '10%', top: '15%' },
  xAxis: { type: 'category', data: catlWin.labels, name: '时间窗口' },
  yAxis: { type: 'value', name: '收益率(%)' },
  series: [
    { name: '宁德时代-策略', type: 'bar', data: catlWin.strategy_returns, itemStyle: { color: '#5470C6' } },
    { name: '宁德时代-基准', type: 'bar', data: catlWin.benchmark_returns, itemStyle: { color: '#91CC75' } },
    { name: '中芯国际-策略', type: 'bar', data: smicWin.strategy_returns, itemStyle: { color: '#FF6B6B' } },
    { name: '中芯国际-基准', type: 'bar', data: smicWin.benchmark_returns, itemStyle: { color: '#4ECDC4' } },
  ]
});

const windowExcessChart = echarts.init(document.getElementById('chart-window-excess'));
windowExcessChart.setOption({
  title: { text: '不同时间窗口 — 超额收益 (策略 - 基准)', left: 'center', fontSize: 14 },
  tooltip: { trigger: 'axis' },
  legend: { data: ['宁德时代','中芯国际'], top: 30 },
  grid: { left: '5%', right: '3%', bottom: '10%', top: '15%' },
  xAxis: { type: 'category', data: catlWin.labels, name: '时间窗口' },
  yAxis: { type: 'value', name: '超额收益(%)' },
  series: [
    { name: '宁德时代', type: 'bar', data: catlWin.excess,
      itemStyle: { color: function(p) { return p.value >= 0 ? '#FF0000' : '#00AA00'; } } },
    { name: '中芯国际', type: 'bar', data: smicWin.excess,
      itemStyle: { color: function(p) { return p.value >= 0 ? '#FF0000' : '#00AA00'; } } },
  ]
});

// 响应式
window.addEventListener('resize', () => {
  document.querySelectorAll('.chart').forEach(el => {
    const inst = echarts.getInstanceByDom(el);
    if (inst) inst.resize();
  });
});
</script>
</body>
</html>
"""

html_path = os.path.join(BASE_DIR, 'dual_ma_strategy_report.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"\nHTML报告已生成: {html_path}")
print(f"文件大小: {os.path.getsize(html_path) / 1024:.1f} KB")
print("\n全部完成 ✓")
