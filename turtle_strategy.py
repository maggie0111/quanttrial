# -*- coding: utf-8 -*-
"""
海龟交易法则策略 (Turtle Trading Strategy)
==========================================
完整实现：数据加载 → 唐奇安通道 → ATR → 信号 → 回测 → 买入持有对比 → 参数实验 → HTML看板
作者: 郭美杰
日期: 2026-07-11
"""

import pandas as pd
import numpy as np
import json
import os

# ============================================================
# 1. 全局配置
# ============================================================
CONFIG = {
    "initial_capital": 100000,     # 初始资金 (元)
    "commission_rate": 0.0003,     # 手续费率 (万三, 双边)
    "slippage": 0.0001,            # 滑点率 (万一, 双边)
    "stamp_duty": 0,               # 印花税 (不考虑)
    "risk_free_rate": 0.02,        # 无风险利率 (年化2%)
    "trading_days_per_year": 252,  # 年交易日
}

# 默认策略参数
DEFAULT_PARAMS = {
    "entry_period": 20,   # 入场通道周期 (上轨=20日最高价)
    "exit_period": 10,    # 出场通道周期 (下轨=10日最低价)
    "atr_period": 20,     # ATR计算周期
}

# 参数实验网格
PARAM_GRID = [
    {"entry_period": 10, "exit_period": 5,  "atr_period": 10},
    {"entry_period": 15, "exit_period": 7,  "atr_period": 15},
    {"entry_period": 20, "exit_period": 10, "atr_period": 20},  # 默认
    {"entry_period": 25, "exit_period": 12, "atr_period": 25},
    {"entry_period": 30, "exit_period": 15, "atr_period": 30},
    {"entry_period": 55, "exit_period": 20, "atr_period": 55},  # 海龟长线
]

# 股票配置
STOCKS = {
    "CATL": {
        "name": "宁德时代",
        "code": "300750.SZ",
        "file": "CATL_300750_daily_qfq.csv",
    },
    "SMIC": {
        "name": "中芯国际",
        "code": "688981.SH",
        "file": "SMIC_688981_daily_qfq.csv",
    },
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ============================================================
# 2. 数据加载与预处理
# ============================================================
def load_stock(short_name):
    """加载股票前复权数据"""
    cfg = STOCKS[short_name]
    filepath = os.path.join(BASE_DIR, cfg["file"])
    df = pd.read_csv(filepath, dtype={"trade_date": str})
    df = df.dropna().reset_index(drop=True)

    # 数据校验
    assert (df["close"] > 0).all(), f"{short_name} 存在非正收盘价"
    assert (df["low"] <= df["high"]).all(), f"{short_name} low > high 异常"
    assert (df["low"] <= df["open"]).all() and (df["open"] <= df["high"]).all(), "open 超出高低范围"
    assert df["trade_date"].duplicated().sum() == 0, "日期重复"

    print(f"[{short_name}] 加载成功: {cfg['name']} ({cfg['code']}), "
          f"{len(df)} 个交易日, {df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}")
    return df


# ============================================================
# 3. 唐奇安通道计算
# ============================================================
def calc_donchian(df, entry_period=20, exit_period=10):
    """
    计算唐奇安通道:
    - 上轨 = 过去 N 日最高价 (不含当日, shift(1))
    - 下轨 = 过去 M 日最低价 (不含当日, shift(1))
    - 中轨 = (上轨 + 下轨) / 2
    """
    df = df.copy()
    df["upper_channel"] = df["high"].rolling(window=entry_period).max().shift(1)
    df["lower_channel"] = df["low"].rolling(window=exit_period).min().shift(1)
    df["mid_channel"] = (df["upper_channel"] + df["lower_channel"]) / 2
    return df


# ============================================================
# 4. ATR 计算
# ============================================================
def calc_atr(df, period=20):
    """
    计算真实波幅 (TR) 和平均真实波幅 (ATR):
    TR = max(high-low, |high-prev_close|, |low-prev_close|)
    ATR = TR 的 N 日简单移动平均
    """
    df = df.copy()
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    df["TR"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    # 第一个交易日无前收盘价, TR = high - low
    df.loc[df.index[0], "TR"] = df.loc[df.index[0], "high"] - df.loc[df.index[0], "low"]
    df["ATR"] = df["TR"].rolling(window=period).mean()
    return df


# ============================================================
# 5. 交易信号生成
# ============================================================
def gen_signals(df):
    """
    生成买卖信号:
    - 买入: close > upper_channel 且当前空仓
    - 卖出: close < lower_channel 且当前持仓
    """
    df = df.copy()
    df["signal"] = 0  # 1=买入, -1=卖出, 0=无操作
    df["position"] = 0  # 持仓状态: 1=持仓, 0=空仓

    pos = 0
    for i in range(len(df)):
        if pd.isna(df["upper_channel"].iloc[i]) or pd.isna(df["lower_channel"].iloc[i]):
            df.iloc[i, df.columns.get_loc("position")] = pos
            continue

        close = df["close"].iloc[i]
        upper = df["upper_channel"].iloc[i]
        lower = df["lower_channel"].iloc[i]

        if close > upper and pos == 0:
            df.iloc[i, df.columns.get_loc("signal")] = 1
            pos = 1
        elif close < lower and pos == 1:
            df.iloc[i, df.columns.get_loc("signal")] = -1
            pos = 0

        df.iloc[i, df.columns.get_loc("position")] = pos

    return df


# ============================================================
# 6. 回测引擎
# ============================================================
def backtest_turtle(df, initial_capital=100000, commission=0.0003, slippage=0.0001):
    """
    海龟策略回测:
    - 信号当日收盘价成交 (价格含滑点和手续费)
    - 满仓买入/卖出
    - 返回: 净值序列, 交易记录, 指标
    """
    capital = float(initial_capital)
    shares = 0.0
    pos = 0
    strategy_values = []
    trades = []
    buy_date = None
    buy_price = None
    buy_shares = None
    total_cost = 0.0

    for i in range(len(df)):
        close = df["close"].iloc[i]
        signal = df["signal"].iloc[i]
        trade_date = df["trade_date"].iloc[i]

        if signal == 1 and pos == 0:
            # 买入
            fill_price = close * (1 + slippage)
            cost_per_share = fill_price * (1 + commission)
            shares = capital / cost_per_share
            buy_cost = shares * cost_per_share
            commission_cost = shares * fill_price * commission
            slippage_cost = shares * close * slippage
            total_cost += commission_cost + slippage_cost
            capital = 0.0
            pos = 1
            buy_date = trade_date
            buy_price = cost_per_share
            buy_shares = shares
            trades.append({
                "date": trade_date,
                "action": "BUY",
                "signal_price": round(close, 2),
                "fill_price": round(fill_price, 2),
                "shares": round(shares, 2),
                "cost": round(buy_cost, 2),
                "upper_channel": round(df["upper_channel"].iloc[i], 2) if not pd.isna(df["upper_channel"].iloc[i]) else None,
                "atr": round(df["ATR"].iloc[i], 2) if not pd.isna(df["ATR"].iloc[i]) else None,
            })

        elif signal == -1 and pos == 1:
            # 卖出
            fill_price = close * (1 - slippage)
            revenue_per_share = fill_price * (1 - commission)
            sell_revenue = shares * revenue_per_share
            commission_cost = shares * fill_price * commission
            slippage_cost = shares * close * slippage
            total_cost += commission_cost + slippage_cost
            trade_return = (revenue_per_share / buy_price - 1) * 100
            holding_days = i - df.index[df["trade_date"] == buy_date][0]
            trades[-1].update({
                "sell_date": trade_date,
                "sell_price": round(close, 2),
                "sell_fill": round(fill_price, 2),
                "revenue": round(sell_revenue, 2),
                "return_pct": round(trade_return, 2),
                "holding_days": holding_days,
            })
            capital = sell_revenue
            shares = 0.0
            pos = 0

        # 当日净值
        daily_value = capital + shares * close
        strategy_values.append(daily_value)

    # 如果末尾仍持仓, 按末日收盘价估值
    if pos == 1:
        trade_return = (close / buy_price - 1) * 100
        holding_days = len(df) - 1 - df.index[df["trade_date"] == buy_date][0]
        trades[-1].update({
            "sell_date": df["trade_date"].iloc[-1] + "(未平仓)",
            "sell_price": round(close, 2),
            "sell_fill": round(close * (1 - slippage), 2),
            "revenue": round(shares * close * (1 - slippage) * (1 - commission), 2),
            "return_pct": round(trade_return, 2),
            "holding_days": holding_days,
        })

    return {
        "strategy_values": np.array(strategy_values),
        "trades": trades,
        "total_cost": total_cost,
        "final_value": strategy_values[-1] if strategy_values else initial_capital,
    }


def backtest_benchmark(df, initial_capital=100000, commission=0.0003, slippage=0.0001):
    """
    买入持有策略回测:
    - 首日全仓买入, 末日按收盘价估值
    """
    first_close = df["close"].iloc[0]
    fill_price = first_close * (1 + slippage)
    cost_per_share = fill_price * (1 + commission)
    shares = initial_capital / cost_per_share
    total_cost = shares * fill_price * commission + shares * first_close * slippage

    benchmark_values = []
    for i in range(len(df)):
        daily_value = shares * df["close"].iloc[i]
        benchmark_values.append(daily_value)

    return {
        "benchmark_values": np.array(benchmark_values),
        "total_cost": total_cost,
        "final_value": benchmark_values[-1],
        "shares": shares,
        "buy_price": cost_per_share,
    }


# ============================================================
# 7. 量化指标计算
# ============================================================
def calc_metrics(strategy_result, benchmark_result, initial_capital=100000,
                 risk_free_rate=0.02, trading_days=252):
    """计算海龟策略与买入持有的量化指标"""
    sv = strategy_result["strategy_values"]
    bv = benchmark_result["benchmark_values"]
    n_days = len(sv)

    # 日收益率
    daily_returns = np.diff(sv) / sv[:-1]
    bench_daily_returns = np.diff(bv) / bv[:-1]

    # 总收益率
    total_return = sv[-1] / initial_capital - 1
    bench_return = bv[-1] / initial_capital - 1

    # 年化收益率
    annual_return = (1 + total_return) ** (trading_days / n_days) - 1 if n_days > 0 else 0
    bench_annual = (1 + bench_return) ** (trading_days / n_days) - 1 if n_days > 0 else 0

    # 超额收益
    excess_return = total_return - bench_return

    # 最大回撤
    def max_drawdown(values):
        running_max = np.maximum.accumulate(values)
        drawdowns = 1 - values / running_max
        return np.max(drawdowns) * 100

    max_dd = max_drawdown(sv)
    bench_max_dd = max_drawdown(bv)

    # 夏普比率
    rf_daily = risk_free_rate / trading_days
    if len(daily_returns) > 1 and np.std(daily_returns) > 0:
        sharpe = (np.mean(daily_returns) - rf_daily) / np.std(daily_returns) * np.sqrt(trading_days)
    else:
        sharpe = 0.0

    if len(bench_daily_returns) > 1 and np.std(bench_daily_returns) > 0:
        bench_sharpe = (np.mean(bench_daily_returns) - rf_daily) / np.std(bench_daily_returns) * np.sqrt(trading_days)
    else:
        bench_sharpe = 0.0

    # 交易统计
    trades = strategy_result["trades"]
    complete_trades = [t for t in trades if "return_pct" in t]
    num_trades = len(complete_trades)

    winning = [t for t in complete_trades if t["return_pct"] > 0]
    losing = [t for t in complete_trades if t["return_pct"] <= 0]
    win_rate = len(winning) / num_trades * 100 if num_trades > 0 else 0

    avg_win = np.mean([t["return_pct"] for t in winning]) if winning else 0
    avg_loss = np.mean([abs(t["return_pct"]) for t in losing]) if losing else 0
    profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else float("inf")

    avg_holding = np.mean([t.get("holding_days", 0) for t in complete_trades]) if complete_trades else 0

    max_profit = max([t["return_pct"] for t in complete_trades]) if complete_trades else 0
    max_loss = min([t["return_pct"] for t in complete_trades]) if complete_trades else 0

    return {
        "total_return": round(total_return * 100, 2),
        "annual_return": round(annual_return * 100, 2),
        "bench_return": round(bench_return * 100, 2),
        "bench_annual": round(bench_annual * 100, 2),
        "excess_return": round(excess_return * 100, 2),
        "max_drawdown": round(max_dd, 2),
        "bench_max_drawdown": round(bench_max_dd, 2),
        "sharpe": round(sharpe, 3),
        "bench_sharpe": round(bench_sharpe, 3),
        "win_rate": round(win_rate, 1),
        "profit_loss_ratio": round(profit_loss_ratio, 2) if profit_loss_ratio != float("inf") else 999,
        "num_trades": num_trades,
        "avg_holding_days": round(avg_holding, 1),
        "max_single_profit": round(max_profit, 2),
        "max_single_loss": round(max_loss, 2),
        "total_cost": round(strategy_result["total_cost"], 2),
        "bench_cost": round(benchmark_result["total_cost"], 2),
        "final_value": round(sv[-1], 2),
        "bench_final_value": round(bv[-1], 2),
    }


# ============================================================
# 8. 完整策略执行
# ============================================================
def run_strategy(short_name, params=None, time_window="full"):
    """执行完整策略流程, 返回所有结果"""
    if params is None:
        params = DEFAULT_PARAMS

    df = load_stock(short_name)

    # 时间窗口截取
    warmup = max(params["entry_period"], params["exit_period"]) + 5
    if time_window == "recent_3m":
        cutoff = len(df) - 63
        df = df.iloc[max(0, cutoff - warmup):].reset_index(drop=True)
        bt_start = warmup if warmup < cutoff else 0
    elif time_window == "recent_6m":
        cutoff = len(df) - 126
        df = df.iloc[max(0, cutoff - warmup):].reset_index(drop=True)
        bt_start = warmup if warmup < cutoff else 0
    elif time_window == "recent_12m":
        cutoff = len(df) - 252
        df = df.iloc[max(0, cutoff - warmup):].reset_index(drop=True)
        bt_start = warmup if warmup < cutoff else 0
    else:
        bt_start = 0

    # 计算通道和ATR
    df = calc_donchian(df, params["entry_period"], params["exit_period"])
    df = calc_atr(df, params["atr_period"])

    # 从有效信号开始截取回测区间
    first_valid = df["upper_channel"].first_valid_index()
    if first_valid is not None and time_window != "full":
        df_bt = df.iloc[first_valid:].reset_index(drop=True)
    elif first_valid is not None:
        df_bt = df.iloc[first_valid:].reset_index(drop=True)
    else:
        df_bt = df.copy()

    # 生成信号
    df_bt = gen_signals(df_bt)

    # 回测
    bt_result = backtest_turtle(df_bt, CONFIG["initial_capital"],
                                CONFIG["commission_rate"], CONFIG["slippage"])
    bm_result = backtest_benchmark(df_bt, CONFIG["initial_capital"],
                                   CONFIG["commission_rate"], CONFIG["slippage"])

    # 指标
    metrics = calc_metrics(bt_result, bm_result, CONFIG["initial_capital"],
                          CONFIG["risk_free_rate"], CONFIG["trading_days_per_year"])

    return {
        "df": df_bt,
        "bt_result": bt_result,
        "bm_result": bm_result,
        "metrics": metrics,
        "params": params,
        "stock_name": STOCKS[short_name]["name"],
        "short_name": short_name,
        "time_window": time_window,
    }


# ============================================================
# 9. HTML 看板生成
# ============================================================
def generate_html(result, filename=None):
    """生成 ECharts 交互式 HTML 看板"""
    df = result["df"]
    bt = result["bt_result"]
    bm = result["bm_result"]
    m = result["metrics"]
    p = result["params"]
    stock_name = result["stock_name"]
    short_name = result["short_name"]
    tw = result["time_window"]

    if filename is None:
        filename = f"{short_name}_turtle_dashboard.html"

    # 准备数据
    dates = df["trade_date"].tolist()
    n = len(dates)

    # K线数据
    candle_data = []
    for _, row in df.iterrows():
        candle_data.append([row["open"], row["close"], row["low"], row["high"]])

    # 通道数据
    upper = [round(v, 2) if not pd.isna(v) else None for v in df["upper_channel"]]
    lower = [round(v, 2) if not pd.isna(v) else None for v in df["lower_channel"]]
    mid = [round(v, 2) if not pd.isna(v) else None for v in df["mid_channel"]]

    # 买卖标记
    buy_points = []
    sell_points = []
    for i in range(n):
        if df["signal"].iloc[i] == 1:
            buy_points.append({"coord": [dates[i], df["low"].iloc[i]], "value": "买入"})
        elif df["signal"].iloc[i] == -1:
            sell_points.append({"coord": [dates[i], df["high"].iloc[i]], "value": "卖出"})

    # 成交量
    vol_data = []
    for _, row in df.iterrows():
        color = "#FF4444" if row["close"] >= row["open"] else "#00AA00"
        vol_data.append({"value": row["volume"], "itemStyle": {"color": color}})

    # ATR
    tr_data = [round(v, 2) if not pd.isna(v) else None for v in df["TR"]]
    atr_data = [round(v, 2) if not pd.isna(v) else None for v in df["ATR"]]

    # 净值
    sv = bt["strategy_values"]
    bv = bm["benchmark_values"]
    sv_list = [round(float(v), 2) for v in sv]
    bv_list = [round(float(v), 2) for v in bv]

    # 持仓状态
    pos_data = df["position"].tolist()

    # 交易记录
    trades = bt["trades"]

    # 指标表
    metrics_rows = [
        ["总收益率", f"{m['total_return']}%", f"{m['bench_return']}%", f"{m['excess_return']:+}%"],
        ["年化收益率", f"{m['annual_return']}%", f"{m['bench_annual']}%", f"{m['annual_return']-m['bench_annual']:+.2f}%"],
        ["最大回撤", f"{m['max_drawdown']}%", f"{m['bench_max_drawdown']}%", f"{m['max_drawdown']-m['bench_max_drawdown']:+.2f}%"],
        ["夏普比率", f"{m['sharpe']}", f"{m['bench_sharpe']}", f"{m['sharpe']-m['bench_sharpe']:+.3f}"],
        ["胜率", f"{m['win_rate']}%", "—", "—"],
        ["盈亏比", f"{m['profit_loss_ratio']}", "—", "—"],
        ["交易次数", f"{m['num_trades']}", "1", "—"],
        ["平均持仓天数", f"{m['avg_holding_days']}", f"{n}", "—"],
        ["最大单笔盈利", f"{m['max_single_profit']}%", "—", "—"],
        ["最大单笔亏损", f"{m['max_single_loss']}%", "—", "—"],
        ["总交易成本", f"¥{m['total_cost']}", f"¥{m['bench_cost']}", f"¥{m['total_cost']-m['bench_cost']:+.2f}"],
        ["期末净值", f"¥{m['final_value']}", f"¥{m['bench_final_value']}", f"¥{m['final_value']-m['bench_final_value']:+.2f}"],
    ]

    # 交易明细
    trade_rows_html = ""
    for i, t in enumerate(trades):
        action_color = "#FF0000" if t["action"] == "BUY" else "#00AA00"
        sell_date = t.get("sell_date", "—")
        sell_price = t.get("sell_price", "—")
        ret = t.get("return_pct", "—")
        ret_str = f"{ret}%" if ret != "—" else "—"
        ret_color = "#FF0000" if (ret != "—" and ret > 0) else ("#00AA00" if (ret != "—" and ret <= 0) else "#999")
        hold = t.get("holding_days", "—")
        trade_rows_html += f"""
        <tr>
          <td>{i+1}</td>
          <td style="color:{action_color};font-weight:bold">{t['action']}</td>
          <td>{t['date']}</td>
          <td>{t['signal_price']}</td>
          <td>{t.get('fill_price', '—')}</td>
          <td>{sell_date}</td>
          <td>{sell_price}</td>
          <td style="color:{ret_color};font-weight:bold">{ret_str}</td>
          <td>{hold}</td>
          <td>{t.get('atr', '—')}</td>
        </tr>"""

    # 格式化日期为可读形式
    def fmt_date(d):
        return f"{d[:4]}-{d[4:6]}-{d[6:]}"

    x_axis_dates = [fmt_date(d) for d in dates]

    # === 预计算所有 JSON 数据 (避免 f-string 大括号转义冲突) ===
    json_dates = json.dumps(x_axis_dates)
    json_candle = json.dumps([[float(r[0]), float(r[1]), float(r[2]), float(r[3])] for r in candle_data])
    json_upper = json.dumps(upper)
    json_lower = json.dumps(lower)
    json_mid = json.dumps(mid)
    json_buy_scatter = json.dumps([[bp["coord"][0], bp["coord"][1]] for bp in buy_points])
    json_sell_scatter = json.dumps([[sp["coord"][0], sp["coord"][1]] for sp in sell_points])
    json_buy_mp = json.dumps([{"coord": bp["coord"], "value": "买入", "itemStyle": {"color": "#FF0000"}} for bp in buy_points])
    json_sell_mp = json.dumps([{"coord": sp["coord"], "value": "卖出", "itemStyle": {"color": "#00AA00"}} for sp in sell_points])
    json_vol = json.dumps([d["value"] for d in vol_data])
    json_oc_pairs = json.dumps([[float(df["open"].iloc[i]), float(df["close"].iloc[i])] for i in range(n)])
    json_tr = json.dumps(tr_data)
    json_atr = json.dumps(atr_data)
    json_sv = json.dumps(sv_list)
    json_bv = json.dumps(bv_list)
    json_capital = json.dumps([CONFIG["initial_capital"]] * n)
    json_pos = json.dumps([int(v) for v in pos_data])
    metrics_html = "".join(f"<tr><td>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td></tr>" for r in metrics_rows)

    # 颜色变量
    tr_color = "#FF0000" if m["total_return"] > 0 else "#00AA00"
    br_color = "#FF0000" if m["bench_return"] > 0 else "#00AA00"
    er_color = "#FF0000" if m["excess_return"] > 0 else "#00AA00"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{stock_name} 海龟交易法则策略看板</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: "Microsoft YaHei", "PingFang SC", sans-serif; background: #f0f2f5; color: #333; }}
  .header {{ background: linear-gradient(135deg, #1a237e 0%, #283593 100%); color: white; padding: 20px 30px; }}
  .header h1 {{ font-size: 24px; margin-bottom: 5px; }}
  .header p {{ font-size: 14px; opacity: 0.85; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 15px; }}
  .metrics-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 15px; }}
  .metrics-table th {{ background: #1a237e; color: white; padding: 10px 15px; text-align: left; font-size: 14px; }}
  .metrics-table td {{ padding: 8px 15px; border-bottom: 1px solid #eee; font-size: 13px; }}
  .metrics-table tr:hover {{ background: #f5f5f5; }}
  .chart-box {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 15px; padding: 15px; }}
  .chart-title {{ font-size: 16px; font-weight: bold; color: #1a237e; margin-bottom: 10px; padding-left: 10px; border-left: 4px solid #1a237e; }}
  .trade-table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  .trade-table th {{ background: #3949ab; color: white; padding: 8px 12px; text-align: left; font-size: 13px; }}
  .trade-table td {{ padding: 6px 12px; border-bottom: 1px solid #eee; font-size: 12px; }}
  .trade-table tr:hover {{ background: #e8eaf6; }}
  .summary-box {{ background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 15px; }}
  .summary-box h3 {{ color: #1a237e; margin-bottom: 10px; }}
  .summary-box p {{ font-size: 13px; line-height: 1.8; color: #555; }}
  .badge {{ display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; margin-right: 8px; }}
  .badge-blue {{ background: #e3f2fd; color: #1565c0; }}
  .badge-green {{ background: #e8f5e9; color: #2e7d32; }}
  .badge-red {{ background: #ffebee; color: #c62828; }}
</style>
</head>
<body>
<div class="header">
  <h1>{stock_name} 海龟交易法则策略看板</h1>
  <p>
    <span class="badge badge-blue">入场周期: {p['entry_period']}日</span>
    <span class="badge badge-blue">出场周期: {p['exit_period']}日</span>
    <span class="badge badge-blue">ATR周期: {p['atr_period']}日</span>
    <span class="badge badge-green">初始资金: ¥{CONFIG['initial_capital']:,}</span>
    <span class="badge badge-red">交易成本: 手续费万三+滑点万一</span>
    <span class="badge badge-blue">时间窗口: {tw}</span>
  </p>
</div>

<div class="container">

  <!-- 指标对比表 -->
  <table class="metrics-table">
    <thead>
      <tr><th>指标</th><th>海龟策略</th><th>买入持有(基准)</th><th>差值</th></tr>
    </thead>
    <tbody>
      {metrics_html}
    </tbody>
  </table>

  <!-- 主图: K线 + 通道 + 信号 -->
  <div class="chart-box">
    <div class="chart-title">股价K线 + 唐奇安通道 + 买卖信号</div>
    <div id="main_chart" style="height: 450px;"></div>
  </div>

  <!-- 成交量 -->
  <div class="chart-box">
    <div class="chart-title">成交量</div>
    <div id="vol_chart" style="height: 150px;"></div>
  </div>

  <!-- ATR -->
  <div class="chart-box">
    <div class="chart-title">ATR (平均真实波幅)</div>
    <div id="atr_chart" style="height: 180px;"></div>
  </div>

  <!-- 净值对比 -->
  <div class="chart-box">
    <div class="chart-title">策略净值 vs 买入持有</div>
    <div id="nav_chart" style="height: 300px;"></div>
  </div>

  <!-- 持仓状态 -->
  <div class="chart-box">
    <div class="chart-title">持仓状态</div>
    <div id="pos_chart" style="height: 120px;"></div>
  </div>

  <!-- 交易明细 -->
  <div class="chart-box">
    <div class="chart-title">交易明细</div>
    <table class="trade-table">
      <thead>
        <tr><th>#</th><th>方向</th><th>买入日期</th><th>信号价</th><th>成交价</th><th>卖出日期</th><th>卖出价</th><th>收益率</th><th>持仓天数</th><th>ATR</th></tr>
      </thead>
      <tbody>{trade_rows_html}
      </tbody>
    </table>
  </div>

  <!-- 策略总结 -->
  <div class="summary-box">
    <h3>策略分析摘要</h3>
    <p>
      <strong>策略表现:</strong> {stock_name}在{p['entry_period']}/{p['exit_period']}参数下，
      海龟策略总收益率为 <strong style="color:{tr_color}">{m['total_return']}%</strong>，
      买入持有基准收益率为 <strong style="color:{br_color}">{m['bench_return']}%</strong>，
      超额收益为 <strong style="color:{er_color}">{m['excess_return']:+}%</strong>。
    </p>
    <p>
      <strong>风险指标:</strong> 策略最大回撤 <strong>{m['max_drawdown']}%</strong>（基准 {m['bench_max_drawdown']}%），
      夏普比率 <strong>{m['sharpe']}</strong>（基准 {m['bench_sharpe']}）。
    </p>
    <p>
      <strong>交易统计:</strong> 共完成 <strong>{m['num_trades']}</strong> 笔交易，胜率 <strong>{m['win_rate']}%</strong>，
      盈亏比 <strong>{m['profit_loss_ratio']}</strong>，平均持仓 <strong>{m['avg_holding_days']}</strong> 天。
      最大单笔盈利 <strong style="color:#FF0000">{m['max_single_profit']}%</strong>，
      最大单笔亏损 <strong style="color:#00AA00">{m['max_single_loss']}%</strong>。
    </p>
    <p>
      <strong>成本分析:</strong> 策略总交易成本 ¥{m['total_cost']}，基准成本 ¥{m['bench_cost']}，
      成本差额 ¥{m['total_cost']-m['bench_cost']:+.2f}。单次完整交易成本率约0.08%（万八）。
    </p>
  </div>

</div>

<script>
// ===== 预计算数据 =====
var xDates = {json_dates};
var candleData = {json_candle};
var upperData = {json_upper};
var lowerData = {json_lower};
var midData = {json_mid};
var buyScatter = {json_buy_scatter};
var sellScatter = {json_sell_scatter};
var buyMP = {json_buy_mp};
var sellMP = {json_sell_mp};
var volData = {json_vol};
var ocPairs = {json_oc_pairs};
var trData = {json_tr};
var atrData = {json_atr};
var svData = {json_sv};
var bvData = {json_bv};
var capitalLine = {json_capital};
var posData = {json_pos};
var gridCommon = {{ left: 70, right: 40, top: 30, bottom: 30 }};

// ===== 1. 主图: K线 + 通道 + 信号 =====
var mainChart = echarts.init(document.getElementById('main_chart'));
mainChart.setOption({{
  tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }} }},
  legend: {{ data: ['K线', '上轨({p['entry_period']}日最高)', '下轨({p['exit_period']}日最低)', '中轨', '买入信号', '卖出信号'], top: 3 }},
  grid: gridCommon,
  dataZoom: [
    {{ type: 'inside', xAxisIndex: 0, start: 0, end: 100 }},
    {{ type: 'slider', xAxisIndex: 0, start: 0, end: 100, height: 20, bottom: 5 }}
  ],
  xAxis: {{ type: 'category', data: xDates, axisLabel: {{ fontSize: 10 }} }},
  yAxis: {{ type: 'value', scale: true }},
  series: [
    {{
      name: 'K线', type: 'candlestick',
      data: candleData,
      itemStyle: {{ color: '#FF4444', color0: '#00AA00', borderColor: '#FF4444', borderColor0: '#00AA00' }}
    }},
    {{
      name: '上轨({p['entry_period']}日最高)', type: 'line',
      data: upperData,
      lineStyle: {{ color: '#FF6B6B', width: 1.2, opacity: 0.8 }},
      symbol: 'none'
    }},
    {{
      name: '下轨({p['exit_period']}日最低)', type: 'line',
      data: lowerData,
      lineStyle: {{ color: '#4ECDC4', width: 1.2, opacity: 0.8 }},
      symbol: 'none'
    }},
    {{
      name: '中轨', type: 'line',
      data: midData,
      lineStyle: {{ color: '#999', width: 1, type: 'dashed', opacity: 0.6 }},
      symbol: 'none'
    }},
    {{
      name: '买入信号', type: 'scatter',
      data: buyScatter,
      symbol: 'triangle', symbolSize: 12,
      itemStyle: {{ color: '#FF0000' }},
      label: {{ show: true, formatter: '买', position: 'bottom', color: '#FF0000', fontSize: 10 }},
      markPoint: {{ symbol: 'pin', symbolSize: 45, data: buyMP }}
    }},
    {{
      name: '卖出信号', type: 'scatter',
      data: sellScatter,
      symbol: 'triangle', symbolSize: 12, symbolRotate: 180,
      itemStyle: {{ color: '#00AA00' }},
      label: {{ show: true, formatter: '卖', position: 'top', color: '#00AA00', fontSize: 10 }},
      markPoint: {{ symbol: 'pin', symbolSize: 45, symbolRotate: 180, data: sellMP }}
    }}
  ]
}});

// ===== 2. 成交量 =====
var volChart = echarts.init(document.getElementById('vol_chart'));
volChart.setOption({{
  tooltip: {{ trigger: 'axis' }},
  grid: gridCommon,
  dataZoom: [{{ type: 'inside', xAxisIndex: 0, start: 0, end: 100 }}],
  xAxis: {{ type: 'category', data: xDates, axisLabel: {{ show: false }} }},
  yAxis: {{ type: 'value', scale: true, axisLabel: {{ fontSize: 10 }} }},
  series: [{{
    name: '成交量', type: 'bar',
    data: volData,
    itemStyle: {{
      color: function(params) {{
        return ocPairs[params.dataIndex][1] >= ocPairs[params.dataIndex][0] ? '#FF4444' : '#00AA00';
      }}
    }}
  }}]
}});

// ===== 3. ATR =====
var atrChart = echarts.init(document.getElementById('atr_chart'));
atrChart.setOption({{
  tooltip: {{ trigger: 'axis' }},
  legend: {{ data: ['TR', 'ATR'], top: 3 }},
  grid: gridCommon,
  dataZoom: [{{ type: 'inside', xAxisIndex: 0, start: 0, end: 100 }}],
  xAxis: {{ type: 'category', data: xDates, axisLabel: {{ show: false }} }},
  yAxis: {{ type: 'value', scale: true, axisLabel: {{ fontSize: 10 }} }},
  series: [
    {{ name: 'TR', type: 'bar', data: trData, itemStyle: {{ color: '#ccc' }} }},
    {{ name: 'ATR', type: 'line', data: atrData, lineStyle: {{ color: '#EE6666', width: 1.5 }}, symbol: 'none' }}
  ]
}});

// ===== 4. 净值对比 =====
var navChart = echarts.init(document.getElementById('nav_chart'));
navChart.setOption({{
  tooltip: {{ trigger: 'axis' }},
  legend: {{ data: ['海龟策略', '买入持有', '初始资金'], top: 3 }},
  grid: gridCommon,
  dataZoom: [{{ type: 'inside', xAxisIndex: 0, start: 0, end: 100 }}],
  xAxis: {{ type: 'category', data: xDates, axisLabel: {{ fontSize: 10 }} }},
  yAxis: {{ type: 'value', scale: true }},
  series: [
    {{ name: '海龟策略', type: 'line', data: svData,
       lineStyle: {{ color: '#5470C6', width: 2 }}, symbol: 'none',
       areaStyle: {{ color: 'rgba(84,112,198,0.1)' }} }},
    {{ name: '买入持有', type: 'line', data: bvData,
       lineStyle: {{ color: '#91CC75', width: 2, type: 'dashed' }}, symbol: 'none' }},
    {{ name: '初始资金', type: 'line', data: capitalLine,
       lineStyle: {{ color: '#999', width: 1, type: 'dotted', opacity: 0.5 }}, symbol: 'none' }}
  ],
  markLine: {{
    silent: true,
    data: [
      {{ yAxis: {m['final_value']}, lineStyle: {{ color: '#5470C6' }}, label: {{ formatter: '策略终值' }} }},
      {{ yAxis: {m['bench_final_value']}, lineStyle: {{ color: '#91CC75' }}, label: {{ formatter: '基准终值' }} }}
    ]
  }}
}});

// ===== 5. 持仓状态 =====
var posChart = echarts.init(document.getElementById('pos_chart'));
posChart.setOption({{
  tooltip: {{ trigger: 'axis' }},
  grid: gridCommon,
  dataZoom: [{{ type: 'inside', xAxisIndex: 0, start: 0, end: 100 }}],
  xAxis: {{ type: 'category', data: xDates, axisLabel: {{ fontSize: 10 }} }},
  yAxis: {{ type: 'value', min: -0.1, max: 1.1, axisLabel: {{ formatter: function(v) {{ return v === 1 ? '持仓' : '空仓'; }} }} }},
  series: [{{
    name: '持仓', type: 'line', step: 'end',
    data: posData,
    lineStyle: {{ color: '#5470C6', width: 1.5 }},
    areaStyle: {{ color: 'rgba(84,112,198,0.2)' }},
    symbol: 'none'
  }}]
}});

// 联动
echarts.connect([mainChart, volChart, atrChart, navChart, posChart]);

// 响应式
window.addEventListener('resize', function() {{
  mainChart.resize(); volChart.resize(); atrChart.resize(); navChart.resize(); posChart.resize();
}});
</script>
</body>
</html>"""

    filepath = os.path.join(BASE_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  → HTML看板已生成: {filepath}")
    return filepath


# ============================================================
# 10. 参数实验
# ============================================================
def run_experiments():
    """运行参数实验, 生成对比表"""
    results = []
    for short_name in ["CATL", "SMIC"]:
        for params in PARAM_GRID:
            for window in ["full", "recent_3m", "recent_6m"]:
                result = run_strategy(short_name, params, window)
                m = result["metrics"]
                row = {
                    "股票": STOCKS[short_name]["name"],
                    "代码": STOCKS[short_name]["code"],
                    "入场周期": params["entry_period"],
                    "出场周期": params["exit_period"],
                    "ATR周期": params["atr_period"],
                    "时间窗口": window,
                    "交易日数": len(result["df"]),
                    "总收益率%": m["total_return"],
                    "年化收益率%": m["annual_return"],
                    "基准收益率%": m["bench_return"],
                    "超额收益%": m["excess_return"],
                    "最大回撤%": m["max_drawdown"],
                    "基准最大回撤%": m["bench_max_drawdown"],
                    "夏普比率": m["sharpe"],
                    "基准夏普": m["bench_sharpe"],
                    "胜率%": m["win_rate"],
                    "盈亏比": m["profit_loss_ratio"],
                    "交易次数": m["num_trades"],
                    "平均持仓天数": m["avg_holding_days"],
                    "最大单笔盈利%": m["max_single_profit"],
                    "最大单笔亏损%": m["max_single_loss"],
                    "总交易成本": m["total_cost"],
                }
                results.append(row)
                print(f"  [{short_name}] {params['entry_period']}/{params['exit_period']} "
                      f"window={window}: 收益={m['total_return']}% 基准={m['bench_return']}% "
                      f"超额={m['excess_return']:+}% 胜率={m['win_rate']}%")

    df_results = pd.DataFrame(results)
    csv_path = os.path.join(BASE_DIR, "turtle_experiment_results.csv")
    df_results.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n参数实验结果已保存: {csv_path}")
    print(f"共 {len(df_results)} 组实验")
    return df_results


# ============================================================
# 11. 主函数
# ============================================================
if __name__ == "__main__":
    print("=" * 70)
    print("[海龟交易法则策略] 完整回测")
    print("=" * 70)

    # === 1. CATL 默认参数回测 ===
    print("\n[1] 宁德时代 (CATL) 默认参数回测 (入场20/出场10/ATR20)")
    catl_result = run_strategy("CATL", DEFAULT_PARAMS, "full")
    m = catl_result["metrics"]
    print(f"  策略收益: {m['total_return']}% | 基准收益: {m['bench_return']}% | 超额: {m['excess_return']:+}%")
    print(f"  最大回撤: {m['max_drawdown']}% (基准 {m['bench_max_drawdown']}%) | 夏普: {m['sharpe']} (基准 {m['bench_sharpe']})")
    print(f"  胜率: {m['win_rate']}% | 盈亏比: {m['profit_loss_ratio']} | 交易次数: {m['num_trades']} | 平均持仓: {m['avg_holding_days']}天")
    generate_html(catl_result, "CATL_turtle_dashboard.html")

    # === 2. SMIC 默认参数回测 ===
    print("\n[2] 中芯国际 (SMIC) 默认参数回测 (入场20/出场10/ATR20)")
    smic_result = run_strategy("SMIC", DEFAULT_PARAMS, "full")
    m = smic_result["metrics"]
    print(f"  策略收益: {m['total_return']}% | 基准收益: {m['bench_return']}% | 超额: {m['excess_return']:+}%")
    print(f"  最大回撤: {m['max_drawdown']}% (基准 {m['bench_max_drawdown']}%) | 夏普: {m['sharpe']} (基准 {m['bench_sharpe']})")
    print(f"  胜率: {m['win_rate']}% | 盈亏比: {m['profit_loss_ratio']} | 交易次数: {m['num_trades']} | 平均持仓: {m['avg_holding_days']}天")
    generate_html(smic_result, "SMIC_turtle_dashboard.html")

    # === 3. 参数实验 ===
    print("\n[3] 参数实验 (6组参数 x 2支股票 x 3个时间窗口 = 36组)")
    exp_results = run_experiments()

    print("\n" + "=" * 70)
    print("[完成] 全部输出文件:")
    print("  - CATL_turtle_dashboard.html (宁德时代海龟策略看板)")
    print("  - SMIC_turtle_dashboard.html (中芯国际海龟策略看板)")
    print("  - turtle_experiment_results.csv (参数实验汇总)")
    print("=" * 70)
