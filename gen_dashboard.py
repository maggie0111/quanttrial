"""
Generate CATL A/H-share technical indicators dashboard (ECharts)
Charts: Price+BB, RSI, MACD, ATR for both A and H shares
"""
import json
import os

BASE_DIR = r"C:\Users\86198\Desktop\quant-trials"

with open(os.path.join(BASE_DIR, "catl_indicators_data.json"), "r", encoding="utf-8") as f:
    data = json.load(f)

# Format dates for display
def fmt_date(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}"

for market in ["a_share", "h_share"]:
    data[market]["dates_fmt"] = [fmt_date(d) for d in data[market]["dates"]]

html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>宁德时代 A/H股 技术指标看板</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/echarts/5.4.3/echarts.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif; background: #f5f5f5; color: #333; }}
  .header {{ background: #1a1a2e; color: #fff; padding: 20px 30px; }}
  .header h1 {{ font-size: 22px; font-weight: 600; }}
  .header p {{ font-size: 13px; color: #aaa; margin-top: 4px; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
  .row {{ display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }}
  .card {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); flex: 1; min-width: 600px; }}
  .card-title {{ font-size: 15px; font-weight: 600; margin-bottom: 8px; color: #1a1a2e; display: flex; align-items: center; gap: 8px; }}
  .tag {{ font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 500; }}
  .tag-a {{ background: #fce8e8; color: #c0392b; }}
  .tag-h {{ background: #e8f0fc; color: #1a5276; }}
  .chart {{ width: 100%; height: 320px; }}
  .chart-sm {{ width: 100%; height: 280px; }}
  .summary {{ background: #fff; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
  .summary h2 {{ font-size: 16px; margin-bottom: 12px; color: #1a1a2e; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
  .metric {{ background: #f8f9fa; border-radius: 6px; padding: 12px; }}
  .metric-label {{ font-size: 12px; color: #888; margin-bottom: 4px; }}
  .metric-value {{ font-size: 18px; font-weight: 600; color: #1a1a2e; }}
  .metric-signal {{ font-size: 11px; margin-top: 2px; }}
  .signal-bullish {{ color: #c0392b; }}
  .signal-bearish {{ color: #27ae60; }}
  .signal-neutral {{ color: #888; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 12px; }}
  th {{ background: #f0f0f0; padding: 8px; text-align: left; font-weight: 600; color: #555; border-bottom: 2px solid #ddd; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #eee; text-align: right; }}
  td:first-child, th:first-child {{ text-align: left; }}
  .up {{ color: #c0392b; font-weight: 600; }}
  .down {{ color: #27ae60; font-weight: 600; }}
</style>
</head>
<body>
<div class="header">
  <h1>宁德时代 技术指标看板 — A股 vs H股</h1>
  <p>300750.SZ (A股) / 3750.HK (H股) · 前复权数据 · RSI(14) / MACD(12,26,9) / BB(20,2) / ATR(14)</p>
</div>

<div class="container">
  <!-- Latest Summary -->
  <div class="summary">
    <h2>最新指标速览 (2026-07-03)</h2>
    <div class="summary-grid">
      <div class="metric">
        <div class="metric-label">A股 收盘价</div>
        <div class="metric-value">¥380.00</div>
      </div>
      <div class="metric">
        <div class="metric-label">A股 RSI(14)</div>
        <div class="metric-value">41.12</div>
        <div class="metric-signal signal-bearish">偏弱 (30-50)</div>
      </div>
      <div class="metric">
        <div class="metric-label">A股 MACD</div>
        <div class="metric-value">-7.42</div>
        <div class="metric-signal signal-bearish">死叉/空头</div>
      </div>
      <div class="metric">
        <div class="metric-label">A股 BB %B</div>
        <div class="metric-value">10.14%</div>
        <div class="metric-signal signal-bearish">接近下轨</div>
      </div>
      <div class="metric">
        <div class="metric-label">A股 ATR(14)</div>
        <div class="metric-value">15.73</div>
        <div class="metric-signal signal-neutral">占收盘价 4.14%</div>
      </div>
      <div class="metric">
        <div class="metric-label">H股 收盘价</div>
        <div class="metric-value">HK$675.50</div>
      </div>
      <div class="metric">
        <div class="metric-label">H股 RSI(14)</div>
        <div class="metric-value">45.44</div>
        <div class="metric-signal signal-bearish">偏弱 (30-50)</div>
      </div>
      <div class="metric">
        <div class="metric-label">H股 MACD</div>
        <div class="metric-value">-0.25</div>
        <div class="metric-signal signal-bearish">死叉/空头</div>
      </div>
      <div class="metric">
        <div class="metric-label">H股 BB %B</div>
        <div class="metric-value">25.34%</div>
        <div class="metric-signal signal-neutral">中性区间</div>
      </div>
      <div class="metric">
        <div class="metric-label">H股 ATR(14)</div>
        <div class="metric-value">33.70</div>
        <div class="metric-signal signal-neutral">占收盘价 4.99%</div>
      </div>
    </div>
  </div>

  <!-- A-share charts -->
  <div class="row">
    <div class="card">
      <div class="card-title">A股 收盘价 + 布林带 <span class="tag tag-a">300750.SZ</span></div>
      <div id="chart_a_bb" class="chart"></div>
    </div>
  </div>
  <div class="row">
    <div class="card">
      <div class="card-title">A股 RSI(14) <span class="tag tag-a">300750.SZ</span></div>
      <div id="chart_a_rsi" class="chart-sm"></div>
    </div>
    <div class="card">
      <div class="card-title">A股 MACD <span class="tag tag-a">300750.SZ</span></div>
      <div id="chart_a_macd" class="chart-sm"></div>
    </div>
  </div>
  <div class="row">
    <div class="card">
      <div class="card-title">A股 ATR(14) <span class="tag tag-a">300750.SZ</span></div>
      <div id="chart_a_atr" class="chart-sm"></div>
    </div>
  </div>

  <!-- H-share charts -->
  <div class="row">
    <div class="card">
      <div class="card-title">H股 收盘价 + 布林带 <span class="tag tag-h">3750.HK</span></div>
      <div id="chart_h_bb" class="chart"></div>
    </div>
  </div>
  <div class="row">
    <div class="card">
      <div class="card-title">H股 RSI(14) <span class="tag tag-h">3750.HK</span></div>
      <div id="chart_h_rsi" class="chart-sm"></div>
    </div>
    <div class="card">
      <div class="card-title">H股 MACD <span class="tag tag-h">3750.HK</span></div>
      <div id="chart_h_macd" class="chart-sm"></div>
    </div>
  </div>
  <div class="row">
    <div class="card">
      <div class="card-title">H股 ATR(14) <span class="tag tag-h">3750.HK</span></div>
      <div id="chart_h_atr" class="chart-sm"></div>
    </div>
  </div>

  <!-- A vs H comparison -->
  <div class="row">
    <div class="card">
      <div class="card-title">A vs H RSI(14) 对比</div>
      <div id="chart_compare_rsi" class="chart-sm"></div>
    </div>
    <div class="card">
      <div class="card-title">A vs H ATR(14) 对比 (归一化%)</div>
      <div id="chart_compare_atr" class="chart-sm"></div>
    </div>
  </div>

  <!-- Data Table -->
  <div class="card" style="overflow-x: auto;">
    <div class="card-title">指标明细表 — A股 最近10日</div>
    <table id="table_a">
      <thead><tr><th>日期</th><th>收盘</th><th>RSI</th><th>MACD DIF</th><th>MACD DEA</th><th>MACD HIST</th><th>BB上轨</th><th>BB中轨</th><th>BB下轨</th><th>BB%B</th><th>ATR</th></tr></thead>
      <tbody id="tbody_a"></tbody>
    </table>
  </div>
  <div class="card" style="overflow-x: auto; margin-top: 20px;">
    <div class="card-title">指标明细表 — H股 最近10日</div>
    <table id="table_h">
      <thead><tr><th>日期</th><th>收盘</th><th>RSI</th><th>MACD DIF</th><th>MACD DEA</th><th>MACD HIST</th><th>BB上轨</th><th>BB中轨</th><th>BB下轨</th><th>BB%B</th><th>ATR</th></tr></thead>
      <tbody id="tbody_h"></tbody>
    </table>
  </div>
</div>

<script>
const rawData = {json.dumps(data)};

const aDates = rawData.a_share.dates_fmt;
const hDates = rawData.h_share.dates_fmt;

// ===== Helper: shared tooltip =====
const tooltipCommon = {{
  trigger: 'axis',
  axisPointer: {{ type: 'cross' }},
  backgroundColor: 'rgba(255,255,255,0.95)',
  borderColor: '#ddd',
  textStyle: {{ fontSize: 12 }}
}};

const gridCommon = {{ left: 60, right: 30, top: 30, bottom: 60 }};

const dataZoomCommon = [
  {{ type: 'inside', start: 0, end: 100 }},
  {{ type: 'slider', start: 0, end: 100, height: 18, bottom: 8 }}
];

// ===== Chart: A-share Price + BB =====
function makeBBChart(elemId, dates, market, label) {{
  const d = rawData[market];
  const chart = echarts.init(document.getElementById(elemId));
  chart.setOption({{
    tooltip: tooltipCommon,
    legend: {{ data: ['收盘价', 'BB上轨', 'BB中轨', 'BB下轨'], top: 2, textStyle: {{ fontSize: 11 }} }},
    grid: gridCommon,
    xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10, rotate: 30 }} }},
    yAxis: {{ type: 'value', scale: true, name: label, nameTextStyle: {{ fontSize: 11 }} }},
    dataZoom: dataZoomCommon,
    series: [
      {{ name: '收盘价', type: 'line', data: d.close, lineStyle: {{ width: 2, color: '#2c3e50' }}, symbol: 'none' }},
      {{ name: 'BB上轨', type: 'line', data: d.BB_UP, lineStyle: {{ width: 1, color: '#e74c3c', type: 'dashed' }}, symbol: 'none' }},
      {{ name: 'BB中轨', type: 'line', data: d.BB_MID, lineStyle: {{ width: 1, color: '#8e44ad' }}, symbol: 'none' }},
      {{ name: 'BB下轨', type: 'line', data: d.BB_LOW, lineStyle: {{ width: 1, color: '#27ae60', type: 'dashed' }}, symbol: 'none',
        areaStyle: {{ color: 'rgba(142,68,173,0.05)', origin: 'start' }} }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}}

// ===== Chart: RSI =====
function makeRSIChart(elemId, dates, market, label) {{
  const d = rawData[market];
  const chart = echarts.init(document.getElementById(elemId));
  chart.setOption({{
    tooltip: tooltipCommon,
    grid: gridCommon,
    xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10, rotate: 30 }} }},
    yAxis: {{ type: 'value', min: 0, max: 100, name: 'RSI', nameTextStyle: {{ fontSize: 11 }} }},
    dataZoom: dataZoomCommon,
    series: [
      {{ name: 'RSI(14)', type: 'line', data: d.RSI_14, lineStyle: {{ width: 2, color: '#534AB7' }}, symbol: 'none',
        markLine: {{
          silent: true,
          data: [
            {{ yAxis: 70, lineStyle: {{ color: '#e74c3c', type: 'dashed', width: 1 }}, label: {{ formatter: '超买 70', fontSize: 10, color: '#e74c3c' }} }},
            {{ yAxis: 50, lineStyle: {{ color: '#aaa', type: 'dotted', width: 0.5 }}, label: {{ formatter: '50', fontSize: 10 }} }},
            {{ yAxis: 30, lineStyle: {{ color: '#27ae60', type: 'dashed', width: 1 }}, label: {{ formatter: '超卖 30', fontSize: 10, color: '#27ae60' }} }}
          ]
        }},
        areaStyle: {{
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {{ offset: 0, color: 'rgba(83,74,183,0.15)' }},
            {{ offset: 1, color: 'rgba(83,74,183,0.02)' }}
          ])
        }}
      }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}}

// ===== Chart: MACD =====
function makeMACDChart(elemId, dates, market, label) {{
  const d = rawData[market];
  const chart = echarts.init(document.getElementById(elemId));
  // Color histogram bars: red for positive, green for negative (Chinese convention)
  const histColors = d.MACD_HIST.map(v => {{
    if (v === null) return '#ccc';
    return v >= 0 ? '#e74c3c' : '#27ae60';
  }});
  chart.setOption({{
    tooltip: tooltipCommon,
    legend: {{ data: ['DIF', 'DEA', 'MACD柱'], top: 2, textStyle: {{ fontSize: 11 }} }},
    grid: gridCommon,
    xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10, rotate: 30 }} }},
    yAxis: {{ type: 'value', scale: true, name: label, nameTextStyle: {{ fontSize: 11 }} }},
    dataZoom: dataZoomCommon,
    series: [
      {{ name: 'DIF', type: 'line', data: d.MACD_DIF, lineStyle: {{ width: 1.5, color: '#534AB7' }}, symbol: 'none' }},
      {{ name: 'DEA', type: 'line', data: d.MACD_DEA, lineStyle: {{ width: 1.5, color: '#e67e22' }}, symbol: 'none' }},
      {{ name: 'MACD柱', type: 'bar', data: d.MACD_HIST.map((v, i) => ({{ value: v, itemStyle: {{ color: histColors[i] }} }})),
        barWidth: '60%' }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}}

// ===== Chart: ATR =====
function makeATRChart(elemId, dates, market, label) {{
  const d = rawData[market];
  const chart = echarts.init(document.getElementById(elemId));
  chart.setOption({{
    tooltip: tooltipCommon,
    grid: gridCommon,
    xAxis: {{ type: 'category', data: dates, axisLabel: {{ fontSize: 10, rotate: 30 }} }},
    yAxis: {{ type: 'value', scale: true, name: label, nameTextStyle: {{ fontSize: 11 }} }},
    dataZoom: dataZoomCommon,
    series: [
      {{ name: 'ATR(14)', type: 'line', data: d.ATR_14, lineStyle: {{ width: 2, color: '#d35400' }}, symbol: 'none',
        areaStyle: {{
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            {{ offset: 0, color: 'rgba(211,84,0,0.2)' }},
            {{ offset: 1, color: 'rgba(211,84,0,0.02)' }}
          ])
        }}
      }},
      {{ name: 'TR', type: 'bar', data: d.TR, itemStyle: {{ color: 'rgba(211,84,0,0.15)' }}, barWidth: '40%' }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}}

// ===== Comparison Charts =====
function makeCompareRSI() {{
  const chart = echarts.init(document.getElementById('chart_compare_rsi'));
  chart.setOption({{
    tooltip: tooltipCommon,
    legend: {{ data: ['A股 RSI', 'H股 RSI'], top: 2, textStyle: {{ fontSize: 11 }} }},
    grid: gridCommon,
    xAxis: {{ type: 'category', data: aDates, axisLabel: {{ fontSize: 10, rotate: 30 }} }},
    yAxis: {{ type: 'value', min: 0, max: 100 }},
    dataZoom: dataZoomCommon,
    series: [
      {{ name: 'A股 RSI', type: 'line', data: rawData.a_share.RSI_14, lineStyle: {{ width: 2, color: '#c0392b' }}, symbol: 'none' }},
      {{ name: 'H股 RSI', type: 'line', data: rawData.h_share.RSI_14, lineStyle: {{ width: 2, color: '#1a5276' }}, symbol: 'none' }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}}

function makeCompareATR() {{
  // Normalize ATR as % of close
  const atrPctA = rawData.a_share.ATR_14.map((v, i) => v !== null ? +(v / rawData.a_share.close[i] * 100).toFixed(2) : null);
  const atrPctH = rawData.h_share.ATR_14.map((v, i) => v !== null ? +(v / rawData.h_share.close[i] * 100).toFixed(2) : null);
  const chart = echarts.init(document.getElementById('chart_compare_atr'));
  chart.setOption({{
    tooltip: tooltipCommon,
    legend: {{ data: ['A股 ATR%', 'H股 ATR%'], top: 2, textStyle: {{ fontSize: 11 }} }},
    grid: gridCommon,
    xAxis: {{ type: 'category', data: aDates, axisLabel: {{ fontSize: 10, rotate: 30 }} }},
    yAxis: {{ type: 'value', scale: true, name: 'ATR/Close %', nameTextStyle: {{ fontSize: 11 }} }},
    dataZoom: dataZoomCommon,
    series: [
      {{ name: 'A股 ATR%', type: 'line', data: atrPctA, lineStyle: {{ width: 2, color: '#c0392b' }}, symbol: 'none' }},
      {{ name: 'H股 ATR%', type: 'line', data: atrPctH, lineStyle: {{ width: 2, color: '#1a5276' }}, symbol: 'none' }}
    ]
  }});
  window.addEventListener('resize', () => chart.resize());
}}

// ===== Render All Charts =====
makeBBChart('chart_a_bb', aDates, 'a_share', '¥');
makeRSIChart('chart_a_rsi', aDates, 'a_share', 'RSI');
makeMACDChart('chart_a_macd', aDates, 'a_share', 'DIF/DEA');
makeATRChart('chart_a_atr', aDates, 'a_share', 'ATR');

makeBBChart('chart_h_bb', hDates, 'h_share', 'HK$');
makeRSIChart('chart_h_rsi', hDates, 'h_share', 'RSI');
makeMACDChart('chart_h_macd', hDates, 'h_share', 'DIF/DEA');
makeATRChart('chart_h_atr', hDates, 'h_share', 'ATR');

makeCompareRSI();
makeCompareATR();

// ===== Fill Tables (last 10 rows, reversed) =====
function fillTable(elemId, market) {{
  const d = rawData[market];
  const dates = market === 'a_share' ? aDates : hDates;
  const tbody = document.getElementById(elemId);
  const n = dates.length;
  const start = Math.max(0, n - 10);
  let html = '';
  for (let i = n - 1; i >= start; i--) {{
    const cls = v => v === null ? '' : (v >= 0 ? 'up' : 'down');
    const fmt = v => v === null ? '—' : (typeof v === 'number' ? v.toFixed(2) : v);
    html += '<tr>' +
      '<td>' + dates[i] + '</td>' +
      '<td>' + fmt(d.close[i]) + '</td>' +
      '<td class="' + cls(d.RSI_14[i]) + '">' + fmt(d.RSI_14[i]) + '</td>' +
      '<td class="' + cls(d.MACD_DIF[i]) + '">' + fmt(d.MACD_DIF[i]) + '</td>' +
      '<td class="' + cls(d.MACD_DEA[i]) + '">' + fmt(d.MACD_DEA[i]) + '</td>' +
      '<td class="' + cls(d.MACD_HIST[i]) + '">' + fmt(d.MACD_HIST[i]) + '</td>' +
      '<td>' + fmt(d.BB_UP[i]) + '</td>' +
      '<td>' + fmt(d.BB_MID[i]) + '</td>' +
      '<td>' + fmt(d.BB_LOW[i]) + '</td>' +
      '<td>' + fmt(d.BB_PCTB[i]) + '</td>' +
      '<td>' + fmt(d.ATR_14[i]) + '</td>' +
      '</tr>';
  }}
  tbody.innerHTML = html;
}}

fillTable('tbody_a', 'a_share');
fillTable('tbody_h', 'h_share');
</script>
</body>
</html>
"""

out_path = os.path.join(BASE_DIR, "CATL_indicators_dashboard.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Dashboard saved: {out_path}")
