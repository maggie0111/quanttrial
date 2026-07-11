"""Generate dual_ma_strategy.ipynb from the spec."""
import json

cells = []

def md(source):
    if isinstance(source, str):
        source = source.split('\n')
        source = [s + '\n' for s in source]
    cells.append({"cell_type": "markdown", "metadata": {}, "source": source})

def code(source):
    if isinstance(source, str):
        source = source.split('\n')
        source = [s + '\n' for s in source]
    cells.append({
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source
    })

# ============================================================
# Cell 1: Title
# ============================================================
md("""# 双均线交叉策略 — 量化回测实验

**课程作业 TASK2** | 作者: 郭美杰

本 Notebook 完整实现了双均线交叉策略 (Dual Moving Average Crossover)，包含：
1. 加载已存储的股价数据
2. 计算短/长周期均线
3. 生成金叉/死叉交易信号
4. 可视化（股价 + 均线 + 买卖标记）
5. 回测引擎 + 买入持有基准对比
6. 量化指标计算（收益率、夏普、回撤、胜率等）
7. 参数实验与时间窗口实验
8. 策略总结

**股票池**: 宁德时代 (300750.SZ) + 中芯国际 (688981.SH)  
**数据**: 前复权日线行情，已存储为本地 CSV  
**可视化**: matplotlib 内联渲染，红涨绿跌（A股惯例）""")

# ============================================================
# Cell 2: Imports & Config
# ============================================================
code("""import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ---- 中文字体 ----
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# ---- 红涨绿跌配色 (A股惯例) ----
COLOR_UP   = '#FF4444'
COLOR_DOWN = '#00AA00'
COLOR_BUY  = '#FF0000'
COLOR_SELL = '#00AA00'
COLOR_MA_S = '#FF6B6B'   # 短均线 - 红
COLOR_MA_L = '#4ECDC4'   # 长均线 - 青
COLOR_STRATEGY = '#5470C6'  # 策略净值 - 蓝
COLOR_BENCHMARK = '#91CC75' # 买入持有 - 绿

# ---- 回测参数 ----
INITIAL_CAPITAL = 100000      # 初始资金 (元)
COMMISSION_RATE = 0.0003      # 手续费万三 (双边)
SLIPPAGE       = 0.0001       # 滑点万一 (双边)
RISK_FREE_RATE = 0.02         # 无风险利率年化 2%

# ---- 均线参数 ----
SHORT_PERIOD = 5
LONG_PERIOD  = 15

# ---- 股票配置 ----
STOCKS = {
    'CATL': {
        'name': '宁德时代',
        'file': 'CATL_300750_daily_qfq.csv',
        'ts_code': '300750.SZ',
        'sector': '动力电池',
    },
    'SMIC': {
        'name': '中芯国际',
        'file': 'SMIC_688981_daily_qfq.csv',
        'ts_code': '688981.SH',
        'sector': '半导体',
    },
}

print("环境初始化完成 ✓")""")

# ============================================================
# Cell 3: Section 1 header
# ============================================================
md("""---
## 1. 数据加载与预处理

加载两支股票的前复权日线 CSV，统一列名和排序方向。""")

# ============================================================
# Cell 4: load_data + display
# ============================================================
code("""def load_data(stock_key):
    \"\"\"加载股票前复权日线数据\"\"\"
    cfg = STOCKS[stock_key]
    df = pd.read_csv(cfg['file'], dtype={'trade_date': str})
    # 确保时间正序
    df = df.sort_values('trade_date').reset_index(drop=True)
    # 清洗: 删除 close<=0 的行
    df = df[df['close'] > 0].reset_index(drop=True)
    return df

# 加载
df_catl = load_data('CATL')
df_smic = load_data('SMIC')

print(f"宁德时代: {len(df_catl)} 个交易日, "
      f"{df_catl['trade_date'].iloc[0]} ~ {df_catl['trade_date'].iloc[-1]}")
print(f"中芯国际: {len(df_smic)} 个交易日, "
      f"{df_smic['trade_date'].iloc[0]} ~ {df_smic['trade_date'].iloc[-1]}")

df_catl.head(10)""")

# ============================================================
# Cell 5: SMIC preview
# ============================================================
code("""df_smic.head(10)""")

# ============================================================
# Cell 6: Data validation
# ============================================================
md("""### 1.1 数据校验""")
code("""def validate_data(df, name):
    \"\"\"校验数据完整性\"\"\"
    checks = []
    checks.append(('close > 0', (df['close'] > 0).all()))
    checks.append(('low <= open <= high', ((df['low'] <= df['open']) & (df['open'] <= df['high'])).all()))
    checks.append(('low <= close <= high', ((df['low'] <= df['close']) & (df['close'] <= df['high'])).all()))
    checks.append(('volume >= 0', (df['volume'] >= 0).all()))
    checks.append(('trade_date 无重复', df['trade_date'].is_unique))
    checks.append(('无 NaN', not df[['open','high','low','close','volume']].isna().any().any()))
    print(f"\\n--- {name} 数据校验 ---")
    for desc, ok in checks:
        print(f"  {'✓' if ok else '✗'} {desc}")
    return all(ok for _, ok in checks)

validate_data(df_catl, '宁德时代')
validate_data(df_smic, '中芯国际')""")

# ============================================================
# Cell 7: Section 2
# ============================================================
md("""---
## 2. 均线计算

简单移动平均线 (SMA)：过去 N 个交易日收盘价的算术平均值。

$$SMA_N(t) = \\frac{1}{N} \\sum_{i=0}^{N-1} close(t-i)$$

- **短均线 (MA_short)**：反映近期趋势，反应快但噪声多
- **长均线 (MA_long)**：反映中长期趋势，滞后但稳定""")

# ============================================================
# Cell 8: calc_ma
# ============================================================
code("""def calc_ma(df, short=SHORT_PERIOD, long=LONG_PERIOD):
    \"\"\"计算短均线和长均线\"\"\"
    df = df.copy()
    df['MA_short'] = df['close'].rolling(window=short).mean()
    df['MA_long']  = df['close'].rolling(window=long).mean()
    return df

df_catl_ma = calc_ma(df_catl)
df_smic_ma = calc_ma(df_smic)

# 查看均线数据 (跳过前 long_period-1 行的 NaN)
df_catl_ma[['trade_date', 'close', 'MA_short', 'MA_long']].dropna().head(15)""")

# ============================================================
# Cell 9: MA visualization
# ============================================================
md("""### 2.1 均线走势预览""")
code("""def plot_ma_preview(df, stock_key, short=SHORT_PERIOD, long=LONG_PERIOD):
    cfg = STOCKS[stock_key]
    dates = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(dates, df['close'], color='#333333', linewidth=1.2, label='收盘价', zorder=1)
    ax.plot(dates, df['MA_short'], color=COLOR_MA_S, linewidth=1.5, label=f'MA{short}', zorder=2)
    ax.plot(dates, df['MA_long'], color=COLOR_MA_L, linewidth=1.5, label=f'MA{long}', zorder=2)
    
    ax.set_title(f'{cfg[\"name\"]} ({cfg[\"ts_code\"]}) — {short}日/{long}日均线', fontsize=14)
    ax.set_xlabel('日期')
    ax.set_ylabel('价格 (元)')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    plt.show()

plot_ma_preview(df_catl_ma, 'CATL')
plot_ma_preview(df_smic_ma, 'SMIC')""")

# ============================================================
# Cell 10: Section 3
# ============================================================
md("""---
## 3. 交易信号生成

| 信号 | 条件 | 操作 | 含义 |
|------|------|------|------|
| **金叉 (Golden Cross)** | 昨日 MA_short ≤ MA_long，今日 MA_short > MA_long | **买入** | 短均线上穿长均线，趋势转强 |
| **死叉 (Death Cross)** | 昨日 MA_short ≥ MA_long，今日 MA_short < MA_long | **卖出** | 短均线下穿长均线，趋势转弱 |
| 无交叉 | 以上条件均不满足 | **持有** | 维持当前仓位 |""")

# ============================================================
# Cell 11: gen_signals
# ============================================================
code("""def gen_signals(df):
    \"\"\"生成金叉/死叉交易信号\"\"\"
    df = df.copy()
    prev_short = df['MA_short'].shift(1)
    prev_long  = df['MA_long'].shift(1)

    golden = (prev_short <= prev_long) & (df['MA_short'] > df['MA_long'])
    death  = (prev_short >= prev_long) & (df['MA_short'] < df['MA_long'])

    df['signal'] = 0
    df.loc[golden, 'signal'] = 1     # 买入
    df.loc[death,  'signal'] = -1    # 卖出

    # 持仓状态追踪
    df['position'] = 0
    pos = 0
    for i in range(len(df)):
        sig = df.iloc[i]['signal']
        if sig == 1:
            pos = 1
        elif sig == -1:
            pos = 0
        df.iloc[i, df.columns.get_loc('position')] = pos

    return df

df_catl_sig = gen_signals(df_catl_ma)
df_smic_sig = gen_signals(df_smic_ma)

for name, df in [('CATL', df_catl_sig), ('SMIC', df_smic_sig)]:
    n_buy  = (df['signal'] == 1).sum()
    n_sell = (df['signal'] == -1).sum()
    print(f"{STOCKS[name]['name']}: 买入信号 {n_buy} 次, 卖出信号 {n_sell} 次")""")

# ============================================================
# Cell 12: Signal detail table
# ============================================================
code("""# 查看所有买卖信号点
def show_signals(df, stock_key):
    cfg = STOCKS[stock_key]
    signals = df[df['signal'] != 0][['trade_date', 'close', 'MA_short', 'MA_long', 'signal']].copy()
    signals['操作'] = signals['signal'].map({1: '买入', -1: '卖出'})
    signals = signals.drop(columns=['signal'])
    signals.columns = ['日期', '收盘价', '短均线', '长均线', '操作']
    print(f"\\n--- {cfg['name']} 交易信号明细 ---")
    return signals.reset_index(drop=True)

show_signals(df_catl_sig, 'CATL')""")

# ============================================================
# Cell 13: SMIC signals
# ============================================================
code("""show_signals(df_smic_sig, 'SMIC')""")

# ============================================================
# Cell 14: Section 4 - Visualization
# ============================================================
md("""---
## 4. 可视化 — 股价、均线与交易信号

三图联动：上方价格+均线+买卖标记，中间成交量，下方持仓状态。""")

# ============================================================
# Cell 15: plot_signal_chart
# ============================================================
code("""def plot_strategy_chart(df, stock_key, short=SHORT_PERIOD, long=LONG_PERIOD):
    \"\"\"绘制股价+均线+买卖信号+成交量+持仓状态\"\"\"
    cfg = STOCKS[stock_key]
    dates = pd.to_datetime(df['trade_date'], format='%Y%m%d')
    
    fig, axes = plt.subplots(3, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [5, 2, 1]},
                             sharex=True)
    
    # --- 主图: 价格 + 均线 + 信号 ---
    ax1 = axes[0]
    ax1.plot(dates, df['close'], color='#333333', linewidth=1.2, label='收盘价', zorder=1)
    ax1.plot(dates, df['MA_short'], color=COLOR_MA_S, linewidth=1.5, label=f'MA{short}', zorder=2)
    ax1.plot(dates, df['MA_long'], color=COLOR_MA_L, linewidth=1.5, label=f'MA{long}', zorder=2)
    
    # 买入标记
    buy_mask = df['signal'] == 1
    if buy_mask.any():
        ax1.scatter(dates[buy_mask], df.loc[buy_mask, 'close'] * 0.995,
                    marker='^', color=COLOR_BUY, s=120, zorder=5, label='买入', edgecolors='darkred')
    # 卖出标记
    sell_mask = df['signal'] == -1
    if sell_mask.any():
        ax1.scatter(dates[sell_mask], df.loc[sell_mask, 'close'] * 1.005,
                    marker='v', color=COLOR_SELL, s=120, zorder=5, label='卖出', edgecolors='darkgreen')
    
    ax1.set_title(f'{cfg[\"name\"]} ({cfg[\"ts_code\"]}) — 双均线策略 ({short}日/{long}日)', fontsize=14)
    ax1.set_ylabel('价格 (元)')
    ax1.legend(loc='best', fontsize=10, ncol=5)
    ax1.grid(True, alpha=0.3)
    
    # --- 成交量图 ---
    ax2 = axes[1]
    colors = [COLOR_UP if p >= 0 else COLOR_DOWN for p in df['pct_chg']]
    ax2.bar(dates, df['volume'], color=colors, width=1, alpha=0.8)
    ax2.set_ylabel('成交量 (手)')
    ax2.grid(True, alpha=0.3)
    
    # --- 持仓状态 ---
    ax3 = axes[2]
    ax3.fill_between(dates, df['position'], step='mid', alpha=0.4, color=COLOR_STRATEGY)
    ax3.step(dates, df['position'], where='mid', color=COLOR_STRATEGY, linewidth=1.5)
    ax3.set_ylabel('持仓')
    ax3.set_yticks([0, 1])
    ax3.set_yticklabels(['空仓', '持仓'])
    ax3.set_xlabel('日期')
    ax3.grid(True, alpha=0.3)
    
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    plt.show()

plot_strategy_chart(df_catl_sig, 'CATL')""")

# ============================================================
# Cell 16: SMIC chart
# ============================================================
code("""plot_strategy_chart(df_smic_sig, 'SMIC')""")

# ============================================================
# Cell 17: Section 5 - Backtest
# ============================================================
md("""---
## 5. 回测引擎

### 5.1 交易成本模型

| 项目 | 费率 | 说明 |
|------|------|------|
| 手续费 | 万三 (0.03%) | 双边收取 |
| 滑点 | 万一 (0.01%) | 买入价上浮，卖出价下浮 |
| 印花税 | 0 | 本作业不考虑 |
| 单次完整交易成本 | ≈ 万八 (0.08%) | 买入+卖出各扣一次 |""")

# ============================================================
# Cell 18: backtest
# ============================================================
code("""def backtest(df, initial_capital=INITIAL_CAPITAL,
               commission=COMMISSION_RATE, slippage=SLIPPAGE):
    \"\"\"
    双均线策略回测引擎
    
    返回:
      result: DataFrame, 含每日净值、持仓、交易记录
      trades: list, 交易明细
    \"\"\"
    capital = initial_capital
    shares = 0
    pos = 0  # 0=空仓, 1=持仓
    
    strategy_value = []
    trades = []
    total_cost = 0
    
    for i in range(len(df)):
        sig = df.iloc[i]['signal']
        close = df.iloc[i]['close']
        date = df.iloc[i]['trade_date']
        
        # 买入
        if sig == 1 and pos == 0:
            fill_price = close * (1 + slippage)
            cost_per_share = fill_price * (1 + commission)
            shares = capital / cost_per_share
            cost_amount = capital - shares * fill_price  # 手续费部分
            total_cost += cost_amount + shares * fill_price * slippage  # 滑点+手续费
            capital = 0
            pos = 1
            trades.append({
                'date': date, 'action': 'BUY',
                'close': close, 'fill_price': fill_price,
                'shares': shares, 'cost': cost_amount,
            })
        
        # 卖出
        elif sig == -1 and pos == 1:
            fill_price = close * (1 - slippage)
            revenue_per_share = fill_price * (1 - commission)
            gross_revenue = shares * fill_price
            net_revenue = shares * revenue_per_share
            cost_amount = gross_revenue - net_revenue  # 手续费
            total_cost += cost_amount + shares * fill_price * slippage  # 滑点+手续费
            capital = net_revenue
            trades.append({
                'date': date, 'action': 'SELL',
                'close': close, 'fill_price': fill_price,
                'shares': shares, 'revenue': net_revenue, 'cost': cost_amount,
            })
            shares = 0
            pos = 0
        
        # 记录每日净值
        daily_value = capital + shares * close
        strategy_value.append(daily_value)
    
    result = df.copy()
    result['strategy_value'] = strategy_value
    result['position'] = result['position']  # 已有
    
    return result, trades, total_cost

# 运行回测
result_catl, trades_catl, cost_catl = backtest(df_catl_sig)
result_smic, trades_smic, cost_smic = backtest(df_smic_sig)

print(f"宁德时代: {len(trades_catl)//2} 笔完整交易, 总交易成本 {cost_catl:.2f} 元")
print(f"中芯国际: {len(trades_smic)//2} 笔完整交易, 总交易成本 {cost_smic:.2f} 元")""")

# ============================================================
# Cell 19: Trade detail
# ============================================================
code("""# 查看交易明细
def show_trades(trades, stock_key):
    cfg = STOCKS[stock_key]
    print(f"\\n--- {cfg['name']} 交易明细 ---")
    for i, t in enumerate(trades):
        action = '买入' if t['action'] == 'BUY' else '卖出'
        print(f"  {i+1}. {t['date']} {action} | "
              f"收盘价 {t['close']:.2f} | 成交价 {t['fill_price']:.4f} | "
              f"股数 {t['shares']:.0f}" + 
              (f" | 手续费 {t['cost']:.2f}" if 'cost' in t else ""))

show_trades(trades_catl, 'CATL')
show_trades(trades_smic, 'SMIC')""")

# ============================================================
# Cell 20: Benchmark
# ============================================================
md("""### 5.2 买入持有策略 (基准对比)

首日全仓买入，持有至末日。同样扣除手续费和滑点，确保对比公平。""")

code("""def backtest_benchmark(df, initial_capital=INITIAL_CAPITAL,
                       commission=COMMISSION_RATE, slippage=SLIPPAGE):
    \"\"\"买入持有策略回测\"\"\"
    close = df['close'].values
    
    # 首日买入
    fill_price = close[0] * (1 + slippage)
    cost_per_share = fill_price * (1 + commission)
    shares = initial_capital / cost_per_share
    buy_cost = initial_capital - shares * fill_price  # 手续费
    slippage_cost = shares * close[0] * slippage
    total_cost = buy_cost + slippage_cost
    
    # 逐日净值
    benchmark_value = shares * close
    
    result = df.copy()
    result['benchmark_value'] = benchmark_value
    result['benchmark_position'] = 1
    
    return result, total_cost

result_catl_bm, cost_catl_bm = backtest_benchmark(df_catl_sig)
result_smic_bm, cost_smic_bm = backtest_benchmark(df_smic_sig)

print(f"宁德时代 买入持有: 成本 {cost_catl_bm:.2f} 元")
print(f"中芯国际 买入持有: 成本 {cost_smic_bm:.2f} 元")""")

# ============================================================
# Cell 21: Section 6 - Metrics
# ============================================================
md("""---
## 6. 量化指标计算""")

# ============================================================
# Cell 22: calc_metrics
# ============================================================
code("""def calc_metrics(strategy_result, benchmark_result,
                   initial_capital=INITIAL_CAPITAL,
                   risk_free_rate=RISK_FREE_RATE):
    \"\"\"计算双均线策略与买入持有基准的各项指标\"\"\"
    sv = strategy_result['strategy_value'].values
    bv = benchmark_result['benchmark_value'].values
    n_days = len(sv)
    
    # --- 策略指标 ---
    total_return = sv[-1] / initial_capital - 1
    annual_return = (1 + total_return) ** (252 / n_days) - 1
    
    daily_ret_s = pd.Series(sv).pct_change().dropna()
    rf_daily = risk_free_rate / 252
    sharpe_s = (daily_ret_s.mean() - rf_daily) / daily_ret_s.std() * np.sqrt(252) if daily_ret_s.std() > 0 else 0
    
    running_max_s = pd.Series(sv).cummax()
    drawdown_s = 1 - pd.Series(sv) / running_max_s
    max_dd_s = drawdown_s.max()
    
    # --- 基准指标 ---
    bm_return = bv[-1] / initial_capital - 1
    bm_annual = (1 + bm_return) ** (252 / n_days) - 1
    
    daily_ret_b = pd.Series(bv).pct_change().dropna()
    sharpe_b = (daily_ret_b.mean() - rf_daily) / daily_ret_b.std() * np.sqrt(252) if daily_ret_b.std() > 0 else 0
    
    running_max_b = pd.Series(bv).cummax()
    drawdown_b = 1 - pd.Series(bv) / running_max_b
    max_dd_b = drawdown_b.max()
    
    # --- 交易统计 ---
    trades = strategy_result[strategy_result['signal'] != 0]
    buy_dates = trades[trades['signal'] == 1]['trade_date'].values
    sell_dates = trades[trades['signal'] == -1]['trade_date'].values
    
    n_trades = min(len(buy_dates), len(sell_dates))
    
    # 逐笔盈亏
    profits = []
    holding_days = []
    for i in range(n_trades):
        buy_idx = strategy_result[strategy_result['trade_date'] == buy_dates[i]].index[0]
        sell_idx = strategy_result[strategy_result['trade_date'] == sell_dates[i]].index[0]
        buy_price = strategy_result.loc[buy_idx, 'close']
        sell_price = strategy_result.loc[sell_idx, 'close']
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
    
    metrics = {
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
    return metrics

# 计算指标
m_catl = calc_metrics(result_catl, result_catl_bm)
m_smic = calc_metrics(result_smic, result_smic_bm)

def display_metrics(m, stock_key):
    cfg = STOCKS[stock_key]
    print(f"\\n{'='*60}")
    print(f"  {cfg['name']} ({cfg['ts_code']}) — 双均线(5/15) vs 买入持有")
    print(f"{'='*60}")
    print(f"  {'指标':<20} {'双均线策略':>14} {'买入持有':>14} {'差值':>14}")
    print(f"  {'-'*60}")
    print(f"  {'总收益率':<18} {m['total_return']:>13.2f}% {m['bm_return']:>13.2f}% {m['excess_return']:>+13.2f}%")
    print(f"  {'年化收益率':<17} {m['annual_return']:>13.2f}% {m['bm_annual']:>13.2f}% {m['annual_return']-m['bm_annual']:>+13.2f}%")
    print(f"  {'最大回撤':<18} {m['max_drawdown']:>13.2f}% {m['bm_max_drawdown']:>13.2f}% {m['max_drawdown']-m['bm_max_drawdown']:>+13.2f}%")
    print(f"  {'夏普比率':<18} {m['sharpe']:>14.3f} {m['bm_sharpe']:>14.3f} {m['sharpe']-m['bm_sharpe']:>+14.3f}")
    print(f"  {'胜率':<20} {m['win_rate']:>13.1f}% {'—':>14} {'—':>14}")
    print(f"  {'盈亏比':<19} {m['pl_ratio']:>14.2f} {'—':>14} {'—':>14}")
    print(f"  {'交易次数':<18} {m['n_trades']:>14} {'1':>14} {'—':>14}")
    print(f"  {'平均持仓天数':<15} {m['avg_holding_days']:>10.0f}天 {'全部':>14} {'—':>14}")
    print()

display_metrics(m_catl, 'CATL')
display_metrics(m_smic, 'SMIC')""")

# ============================================================
# Cell 23: Net value comparison
# ============================================================
md("""### 6.1 净值曲线对比""")
code("""def plot_net_value(strategy_result, benchmark_result, stock_key,
                    short=SHORT_PERIOD, long=LONG_PERIOD):
    cfg = STOCKS[stock_key]
    dates = pd.to_datetime(strategy_result['trade_date'], format='%Y%m%d')
    
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(dates, strategy_result['strategy_value'],
            color=COLOR_STRATEGY, linewidth=1.5, label='双均线策略')
    ax.plot(dates, benchmark_result['benchmark_value'],
            color=COLOR_BENCHMARK, linewidth=1.5, linestyle='--', label='买入持有(基准)')
    ax.axhline(y=INITIAL_CAPITAL, color='#999999', linestyle=':', linewidth=1, label='初始资金')
    
    # 标注最终收益
    final_s = strategy_result['strategy_value'].iloc[-1]
    final_b = benchmark_result['benchmark_value'].iloc[-1]
    ret_s = (final_s / INITIAL_CAPITAL - 1) * 100
    ret_b = (final_b / INITIAL_CAPITAL - 1) * 100
    ax.annotate(f'策略 {ret_s:+.1f}%', xy=(dates.iloc[-1], final_s),
                fontsize=11, color=COLOR_STRATEGY, fontweight='bold',
                xytext=(-80, 10), textcoords='offset points')
    ax.annotate(f'基准 {ret_b:+.1f}%', xy=(dates.iloc[-1], final_b),
                fontsize=11, color=COLOR_BENCHMARK, fontweight='bold',
                xytext=(-80, -20), textcoords='offset points')
    
    ax.set_title(f'{cfg[\"name\"]} — 策略净值 vs 买入持有 ({short}日/{long}日)', fontsize=14)
    ax.set_xlabel('日期')
    ax.set_ylabel('净值 (元)')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    plt.show()

plot_net_value(result_catl, result_catl_bm, 'CATL')
plot_net_value(result_smic, result_smic_bm, 'SMIC')""")

# ============================================================
# Cell 24: Drawdown comparison
# ============================================================
md("""### 6.2 回撤对比""")
code("""def plot_drawdown(strategy_result, benchmark_result, stock_key):
    cfg = STOCKS[stock_key]
    dates = pd.to_datetime(strategy_result['trade_date'], format='%Y%m%d')
    
    sv = strategy_result['strategy_value']
    bv = benchmark_result['benchmark_value']
    dd_s = (1 - sv / sv.cummax()) * 100
    dd_b = (1 - bv / bv.cummax()) * 100
    
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.fill_between(dates, dd_s, 0, color=COLOR_STRATEGY, alpha=0.4, label='双均线策略回撤')
    ax.plot(dates, dd_s, color=COLOR_STRATEGY, linewidth=1)
    ax.plot(dates, dd_b, color=COLOR_BENCHMARK, linewidth=1.5, linestyle='--', label='买入持有回撤')
    
    ax.set_title(f'{cfg[\"name\"]} — 最大回撤对比', fontsize=14)
    ax.set_xlabel('日期')
    ax.set_ylabel('回撤 (%)')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.invert_yaxis()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    fig.autofmt_xdate(rotation=45)
    plt.tight_layout()
    plt.show()

plot_drawdown(result_catl, result_catl_bm, 'CATL')
plot_drawdown(result_smic, result_smic_bm, 'SMIC')""")

# ============================================================
# Cell 25: Section 7 - Full pipeline
# ============================================================
md("""---
## 7. 一键运行 — 完整策略管线

封装为 `run_strategy()` 函数，输入股票和均线参数即可输出全部结果。""")

# ============================================================
# Cell 26: run_strategy
# ============================================================
code("""def run_strategy(stock_key, short=SHORT_PERIOD, long=LONG_PERIOD,
                   time_window='full', verbose=True):
    \"\"\"
    完整策略管线: 加载 → 均线 → 信号 → 截取窗口 → 回测 → 指标
    \"\"\"
    cfg = STOCKS[stock_key]
    
    # 1. 加载数据
    df = load_data(stock_key)
    
    # 2. 计算均线 (在全量数据上计算, 避免截取后均线无效)
    df = calc_ma(df, short, long)
    
    # 3. 生成信号
    df = gen_signals(df)
    
    # 4. 时间窗口截取 (含预热期)
    df = select_window(df, time_window, long)
    
    # 5. 回测
    result, trades, total_cost = backtest(df)
    
    # 6. 基准
    result_bm, cost_bm = backtest_benchmark(df)
    
    # 7. 指标
    metrics = calc_metrics(result, result_bm)
    metrics['total_cost'] = total_cost
    metrics['bm_cost'] = cost_bm
    metrics['stock'] = stock_key
    metrics['short'] = short
    metrics['long'] = long
    metrics['window'] = time_window
    metrics['n_days'] = len(df)
    
    if verbose:
        display_metrics(metrics, stock_key)
    
    return result, result_bm, trades, metrics

print("run_strategy() 定义完成 ✓")""")

# ============================================================
# Cell 27: Section 8 - Experiments
# ============================================================
md("""---
## 8. 参数实验 — 不同均线周期

固定股票，变化均线参数组合，观察收益、胜率、回撤的变化。""")

# ============================================================
# Cell 28: Parameter experiment
# ============================================================
code("""PARAM_GRID = [
    {'short': 5,  'long': 10},
    {'short': 5,  'long': 15},   # 默认
    {'short': 5,  'long': 20},
    {'short': 10, 'long': 20},
    {'short': 10, 'long': 30},
    {'short': 20, 'long': 60},
]

experiment_results = []

for stock_key in ['CATL', 'SMIC']:
    for params in PARAM_GRID:
        _, _, _, m = run_strategy(
            stock_key,
            short=params['short'],
            long=params['long'],
            time_window='full',
            verbose=False
        )
        experiment_results.append(m)

# 汇总为 DataFrame
exp_df = pd.DataFrame(experiment_results)
exp_df.insert(0, '股票', exp_df['stock'].map(lambda k: STOCKS[k]['name']))
exp_df = exp_df[['股票', 'short', 'long', 'n_days',
                 'total_return', 'annual_return', 'bm_return', 'excess_return',
                 'max_drawdown', 'bm_max_drawdown', 'sharpe', 'bm_sharpe',
                 'win_rate', 'n_trades', 'total_cost']]
exp_df.columns = ['股票', '短均线', '长均线', '交易日数',
                  '总收益率%', '年化收益率%', '基准收益率%', '超额收益%',
                  '最大回撤%', '基准回撤%', '夏普', '基准夏普',
                  '胜率%', '交易次数', '总成本(元)']

# 四舍五入
exp_display = exp_df.copy()
for col in ['总收益率%', '年化收益率%', '基准收益率%', '超额收益%',
            '最大回撤%', '基准回撤%', '夏普', '基准夏普', '胜率%', '总成本(元)']:
    exp_display[col] = exp_display[col].round(2)

exp_display""")

# ============================================================
# Cell 29: Experiment visualization
# ============================================================
code("""# 参数实验可视化: 各参数组合的总收益率对比
fig, axes = plt.subplots(1, 2, figsize=(16, 5))

for idx, stock_key in enumerate(['CATL', 'SMIC']):
    cfg = STOCKS[stock_key]
    sub = exp_df[exp_df['股票'] == cfg['name']].copy()
    sub['label'] = sub['短均线'].astype(str) + '/' + sub['长均线'].astype(str)
    
    x = range(len(sub))
    w = 0.35
    ax = axes[idx]
    bars1 = ax.bar([i - w/2 for i in x], sub['总收益率%'], w, 
                   color=COLOR_STRATEGY, label='双均线策略', alpha=0.8)
    bars2 = ax.bar([i + w/2 for i in x], sub['基准收益率%'], w,
                   color=COLOR_BENCHMARK, label='买入持有', alpha=0.8)
    
    ax.set_xticks(list(x))
    ax.set_xticklabels(sub['label'], fontsize=11)
    ax.set_title(f'{cfg["name"]} — 不同均线参数收益率对比', fontsize=13)
    ax.set_xlabel('短均线/长均线')
    ax.set_ylabel('收益率 (%)')
    ax.axhline(y=0, color='#333', linewidth=0.8)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.show()""")

# ============================================================
# Cell 30: Max drawdown comparison
# ============================================================
code("""# 最大回撤对比
fig, axes = plt.subplots(1, 2, figsize=(16, 5))

for idx, stock_key in enumerate(['CATL', 'SMIC']):
    cfg = STOCKS[stock_key]
    sub = exp_df[exp_df['股票'] == cfg['name']].copy()
    sub['label'] = sub['短均线'].astype(str) + '/' + sub['长均线'].astype(str)
    
    x = range(len(sub))
    w = 0.35
    ax = axes[idx]
    ax.bar([i - w/2 for i in x], sub['最大回撤%'], w,
           color='#FF6B6B', label='双均线回撤', alpha=0.8)
    ax.bar([i + w/2 for i in x], sub['基准回撤%'], w,
           color='#4ECDC4', label='买入持有回撤', alpha=0.8)
    
    ax.set_xticks(list(x))
    ax.set_xticklabels(sub['label'], fontsize=11)
    ax.set_title(f'{cfg["name"]} — 不同均线参数最大回撤对比', fontsize=13)
    ax.set_xlabel('短均线/长均线')
    ax.set_ylabel('最大回撤 (%)')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.show()""")

# ============================================================
# Cell 31: Section 9 - Time window
# ============================================================
md("""---
## 9. 时间窗口实验

固定股票和均线参数 (5/15)，变化回测时间窗口，观察策略在不同市场阶段的表现。

| 模式 | 说明 | CATL 区间 | SMIC 区间 |
|------|------|-----------|-----------|
| `full` | 全周期 | 242天 | 237天 |
| `recent_3m` | 近3个月 | ~63天 | ~63天 |
| `recent_6m` | 近6个月 | ~126天 | ~126天 |
| `recent_12m` | 近12个月 | ~252天 | ~252天 |""")

# ============================================================
# Cell 32: select_window
# ============================================================
code("""def select_window(df, time_window='full', long_period=LONG_PERIOD):
    \"\"\"
    按时间窗口截取回测数据 (含预热期)
    
    time_window: 'full' / 'recent_3m' / 'recent_6m' / 'recent_12m' / dict
    \"\"\"
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
        # 预热: 向前多取 long_period 天
        first_idx = mask.idxmax() if mask.any() else 0
        warmup_idx = max(0, first_idx - long_period)
        return df.iloc[warmup_idx:].reset_index(drop=True)
    else:
        return df.reset_index(drop=True)
    
    cutoff = max(0, cutoff - long_period)  # 预热期
    return df.iloc[cutoff:].reset_index(drop=True)

print("select_window() 定义完成 ✓")""")

# ============================================================
# Cell 33: Window experiments
# ============================================================
code("""WINDOWS = ['full', 'recent_3m', 'recent_6m', 'recent_12m']
WINDOW_NAMES = {'full': '全周期', 'recent_3m': '近3个月', 
                'recent_6m': '近6个月', 'recent_12m': '近12个月'}

window_results = []

for stock_key in ['CATL', 'SMIC']:
    for w in WINDOWS:
        _, _, _, m = run_strategy(
            stock_key,
            short=5, long=15,
            time_window=w,
            verbose=False
        )
        m['window_name'] = WINDOW_NAMES[w]
        window_results.append(m)

win_df = pd.DataFrame(window_results)
win_df.insert(0, '股票', win_df['stock'].map(lambda k: STOCKS[k]['name']))
win_df.insert(1, '时间窗口', win_df['window_name'])
win_df = win_df[['股票', '时间窗口', 'n_days',
                'total_return', 'annual_return', 'bm_return', 'excess_return',
                'max_drawdown', 'bm_max_drawdown', 'sharpe', 'bm_sharpe',
                'win_rate', 'n_trades']]
win_df.columns = ['股票', '时间窗口', '交易日数',
                  '总收益率%', '年化%', '基准%', '超额%',
                  '最大回撤%', '基准回撤%', '夏普', '基准夏普',
                  '胜率%', '交易次数']

win_display = win_df.copy()
for col in ['总收益率%', '年化%', '基准%', '超额%', '最大回撤%', '基准回撤%', '夏普', '基准夏普', '胜率%']:
    win_display[col] = win_display[col].round(2)

win_display""")

# ============================================================
# Cell 34: Window visualization
# ============================================================
code("""# 时间窗口实验可视化
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

for idx, stock_key in enumerate(['CATL', 'SMIC']):
    cfg = STOCKS[stock_key]
    sub = win_df[win_df['股票'] == cfg['name']]
    
    x = range(len(sub))
    w = 0.35
    
    # 收益率对比
    ax1 = axes[idx][0]
    ax1.bar([i - w/2 for i in x], sub['总收益率%'], w, color=COLOR_STRATEGY, label='双均线', alpha=0.8)
    ax1.bar([i + w/2 for i in x], sub['基准%'], w, color=COLOR_BENCHMARK, label='买入持有', alpha=0.8)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(sub['时间窗口'], fontsize=10)
    ax1.set_title(f'{cfg["name"]} — 不同时间窗口收益率', fontsize=13)
    ax1.set_ylabel('收益率 (%)')
    ax1.axhline(y=0, color='#333', linewidth=0.8)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # 超额收益
    ax2 = axes[idx][1]
    colors = [COLOR_UP if v >= 0 else COLOR_DOWN for v in sub['超额%']]
    ax2.bar(x, sub['超额%'], color=colors, alpha=0.8)
    ax2.set_xticks(list(x))
    ax2.set_xticklabels(sub['时间窗口'], fontsize=10)
    ax2.set_title(f'{cfg["name"]} — 超额收益 (策略 - 基准)', fontsize=13)
    ax2.set_ylabel('超额收益 (%)')
    ax2.axhline(y=0, color='#333', linewidth=0.8)
    ax2.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.show()""")

# ============================================================
# Cell 35: Custom window demo
# ============================================================
md("""### 9.1 自定义时间窗口

可以通过 `dict` 传入自定义区间，格式 `{"mode": "custom", "start_date": "YYYYMMDD", "end_date": "YYYYMMDD"}`。""")
code("""# 示例: 自定义 2026年1月~3月
custom_result, custom_bm, _, custom_m = run_strategy(
    'CATL',
    short=5, long=15,
    time_window={'mode': 'custom', 'start_date': '20260101', 'end_date': '20260331'},
    verbose=True
)

# 绘制自定义窗口的净值曲线
plot_net_value(custom_result, custom_bm, 'CATL')""")

# ============================================================
# Cell 36: Section 10 - Cross stock comparison
# ============================================================
md("""---
## 10. 跨股票对比

使用默认参数 (5/15)，全周期，对比宁德时代 vs 中芯国际。""")

code("""# 跨股票对比 (默认 5/15, full)
fig, axes = plt.subplots(1, 2, figsize=(16, 5))

for idx, stock_key in enumerate(['CATL', 'SMIC']):
    cfg = STOCKS[stock_key]
    sub = exp_df[(exp_df['股票'] == cfg['name']) & (exp_df['短均线'] == 5) & (exp_df['长均线'] == 15)]
    
    ax = axes[idx]
    categories = ['总收益率', '年化收益率', '最大回撤', '夏普比率']
    strategy_vals = [sub['总收益率%'].values[0], sub['年化收益率%'].values[0], 
                     sub['最大回撤%'].values[0], sub['夏普'].values[0]]
    bm_vals = [sub['基准收益率%'].values[0], sub['年化%'].values[0],
               sub['基准回撤%'].values[0], sub['基准夏普'].values[0]]
    
    x = range(len(categories))
    w = 0.35
    ax.bar([i - w/2 for i in x], strategy_vals, w, color=COLOR_STRATEGY, label='双均线策略', alpha=0.8)
    ax.bar([i + w/2 for i in x], bm_vals, w, color=COLOR_BENCHMARK, label='买入持有', alpha=0.8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories, fontsize=10)
    ax.set_title(f'{cfg["name"]} (5/15日)', fontsize=13)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=0, color='#333', linewidth=0.8)

plt.suptitle('宁德时代 vs 中芯国际 — 策略指标对比', fontsize=15, y=1.02)
plt.tight_layout()
plt.show()""")

# ============================================================
# Cell 37: Section 11 - Summary
# ============================================================
md("""---
## 11. 策略总结

### 11.1 双均线策略适用场景

- **趋势行情**（牛市/熊市）中表现优异，金叉/死叉能有效捕捉趋势反转
- **震荡行情**中频繁假信号，反复止损导致收益为负甚至跑输买入持有
- **长周期均线组合**（如20/60）信号少但更可靠，适合中长线投资者
- **短周期均线组合**（如5/10）信号多但噪声大，交易成本侵蚀明显

### 11.2 不同股票的表现差异

- **宁德时代（动力电池）**：波动较大，趋势性较强，双均线策略有机会跑赢或接近买入持有
- **中芯国际（半导体）**：需结合实际回测结果分析其趋势特征
- 行业属性影响：高波动成长股均线信号更频繁，蓝筹股趋势更稳定

### 11.3 参数选择心得

- 短均线周期过短 → 信号过于频繁，交易成本侵蚀收益
- 长均线周期过长 → 信号滞后，错过行情起点
- 均线周期选择应结合个股波动率和持仓周期偏好
- 建议：波动大的股票用较长周期，波动小的用较短周期

### 11.4 时间窗口表现差异

- **牛市阶段**：趋势明确，金叉信号有效，策略大概率跑赢或接近买入持有
- **熊市阶段**：死叉信号帮助规避下跌，策略可能大幅跑赢买入持有
- **震荡阶段**：频繁假信号，反复止损，策略可能跑输买入持有
- 时间窗口选择应覆盖不同市场环境，避免仅在单一行情下评估

### 11.5 策略局限与改进方向

- 单一指标策略局限性大，容易在震荡市亏损
- 可加入成交量、MACD、RSI 等辅助过滤信号
- 可加入止损/止盈机制控制风险
- 可尝试动态调仓而非满仓/空仓二选一
- 交易成本（手续费万三+滑点万一）对高频策略影响显著，需用超额收益覆盖
- 与买入持有对比：若策略无法跑赢买入持有，说明趋势判断未带来正增益

### 11.6 核心结论

> 双均线策略的核心价值在于**趋势识别**和**风险规避**。在单边行情中，它能有效捕捉趋势并在反转时及时退出；但在震荡市中，频繁的假信号和交易成本会侵蚀收益。因此，策略的有效性高度依赖市场环境和参数选择，**没有放之四海而皆准的最优参数**，需根据具体股票和市场阶段灵活调整。""")

# ============================================================
# Cell 38: Export
# ============================================================
md("""---
## 12. 导出结果

将实验结果保存为 CSV 文件，方便后续分析和报告撰写。""")
code("""# 保存参数实验结果
exp_df.to_csv('dual_ma_experiment_results.csv', index=False, encoding='utf-8-sig')
print(f"参数实验结果已保存: dual_ma_experiment_results.csv ({len(exp_df)} 行)")

# 保存时间窗口实验结果
win_df.to_csv('dual_ma_window_results.csv', index=False, encoding='utf-8-sig')
print(f"时间窗口实验结果已保存: dual_ma_window_results.csv ({len(win_df)} 行)")

print("\\n全部实验完成 ✓")""")

# ============================================================
# Build notebook
# ============================================================
notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "name": "python",
            "version": "3.12.0"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 5
}

output_path = r"C:\Users\86198\Desktop\quant-trials\dual_ma_strategy.ipynb"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)

print(f"Notebook generated: {output_path}")
print(f"Total cells: {len(cells)}")
