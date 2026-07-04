# -*- coding: utf-8 -*-
"""
生成"郭美杰+TASK1.pdf"
基于宁德时代A/H股对比看板数据，包含K线、基本面、技术面概念解释
格式要求：宋体，五号字(10.5pt)，1.5倍行距，0段间距，两端对齐
"""

import csv
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.dates import DateFormatter
import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable

# ============ 1. 注册宋体字体 ============
SIMSUN_PATH = r"C:\Windows\Fonts\simsun.ttc"
SIMHEI_PATH = r"C:\Windows\Fonts\simhei.ttf"

pdfmetrics.registerFont(TTFont('SimSun', SIMSUN_PATH))
pdfmetrics.registerFont(TTFont('SimHei', SIMHEI_PATH))

# matplotlib 中文设置
plt.rcParams['font.sans-serif'] = ['SimHei', 'SimSun', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

# ============ 2. 定义段落样式 ============
# 五号字 = 10.5pt, 1.5倍行距 => leading = 10.5 * 1.5 = 15.75pt

FONT_NAME = 'SimSun'
FONT_SIZE = 10.5  # 五号字
LEADING = 15.75   # 1.5倍行距
SPACE_BEFORE = 0   # 0段间距
SPACE_AFTER = 0

style_title = ParagraphStyle(
    'TitleStyle',
    fontName='SimHei',
    fontSize=18,
    leading=27,
    alignment=TA_CENTER,
    spaceBefore=0,
    spaceAfter=0,
    textColor=HexColor('#1a1a2e'),
)

style_h1 = ParagraphStyle(
    'H1Style',
    fontName='SimHei',
    fontSize=14,
    leading=21,
    alignment=TA_LEFT,
    spaceBefore=12,
    spaceAfter=0,
    textColor=HexColor('#16213e'),
)

style_h2 = ParagraphStyle(
    'H2Style',
    fontName='SimHei',
    fontSize=12,
    leading=18,
    alignment=TA_LEFT,
    spaceBefore=10,
    spaceAfter=0,
    textColor=HexColor('#0f3460'),
)

style_body = ParagraphStyle(
    'BodyStyle',
    fontName=FONT_NAME,
    fontSize=FONT_SIZE,
    leading=LEADING,
    alignment=TA_JUSTIFY,
    spaceBefore=SPACE_BEFORE,
    spaceAfter=SPACE_AFTER,
    firstLineIndent=21,  # 首行缩进2字符
)

style_body_noindent = ParagraphStyle(
    'BodyNoIndent',
    fontName=FONT_NAME,
    fontSize=FONT_SIZE,
    leading=LEADING,
    alignment=TA_JUSTIFY,
    spaceBefore=SPACE_BEFORE,
    spaceAfter=SPACE_AFTER,
)

style_caption = ParagraphStyle(
    'CaptionStyle',
    fontName='SimHei',
    fontSize=9,
    leading=13.5,
    alignment=TA_CENTER,
    spaceBefore=3,
    spaceAfter=6,
    textColor=HexColor('#555555'),
)

style_table_header = ParagraphStyle(
    'TableHeader',
    fontName='SimHei',
    fontSize=9,
    leading=13.5,
    alignment=TA_CENTER,
    textColor=white,
)

style_table_cell = ParagraphStyle(
    'TableCell',
    fontName=FONT_NAME,
    fontSize=9,
    leading=13.5,
    alignment=TA_CENTER,
)

style_table_cell_left = ParagraphStyle(
    'TableCellLeft',
    fontName=FONT_NAME,
    fontSize=9,
    leading=13.5,
    alignment=TA_LEFT,
)


# ============ 3. 读取数据 ============
def read_csv(filepath):
    """读取CSV文件"""
    records = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append({
                'trade_date': row['trade_date'],
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'pre_close': float(row['pre_close']),
                'change': float(row['change']),
                'pct_chg': float(row['pct_chg']),
                'vol': float(row['vol']),
                'amount': float(row['amount']),
            })
    return records


def fmt_date(date_str):
    """20250704 -> 2025-07-04"""
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"


a_records = read_csv(r'C:\Users\86198\Desktop\quant-trials\CATL_300750_daily.csv')
h_records = read_csv(r'C:\Users\86198\Desktop\quant-trials\CATL_3750HK_daily.csv')

print(f"A股数据: {len(a_records)} 条, {a_records[0]['trade_date']} ~ {a_records[-1]['trade_date']}")
print(f"港股数据: {len(h_records)} 条, {h_records[0]['trade_date']} ~ {h_records[-1]['trade_date']}")

# 汇率
HKD_TO_CNY = 0.86784

# ============ 4. 生成统计图表 ============
CHART_DIR = r'C:\Users\86198\Desktop\quant-trials\charts_temp'
os.makedirs(CHART_DIR, exist_ok=True)

# 颜色定义
COLOR_UP = '#e74c3c'   # 红涨
COLOR_DOWN = '#2ecc71' # 绿跌
COLOR_A = '#e74c3c'
COLOR_H = '#3498db'

# --- 图1: A股K线图 ---
def draw_kline(records, title, color_up, color_down, filename, fig_num):
    fig, ax = plt.subplots(figsize=(12, 5))
    dates = [fmt_date(r['trade_date']) for r in records]
    x = range(len(records))

    for i, r in enumerate(records):
        is_up = r['close'] >= r['open']
        c = color_up if is_up else color_down
        # 影线
        ax.vlines(i, r['low'], r['high'], color=c, linewidth=0.8)
        # 实体
        bottom = min(r['open'], r['close'])
        height = abs(r['close'] - r['open'])
        if height < 0.01:
            height = 0.5
        ax.bar(i, height, bottom=bottom, width=0.6, color=c, edgecolor=c, linewidth=0.5)

    # x轴标签 - 每30天显示一次
    step = max(1, len(records) // 15)
    ax.set_xticks(range(0, len(records), step))
    ax.set_xticklabels([dates[i] for i in range(0, len(records), step)], rotation=45, fontsize=8, ha='right')

    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.set_ylabel('价格 (元)', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_xlim(-1, len(records))
    plt.tight_layout()
    filepath = os.path.join(CHART_DIR, filename)
    plt.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close()
    return filepath

chart1_path = draw_kline(a_records, '宁德时代 A股(300750.SZ) 近一年日K线图', COLOR_UP, COLOR_DOWN, 'chart1_kline_a.png', 1)
chart2_path = draw_kline(h_records, '宁德时代 港股(03750.HK) 近一年日K线图', COLOR_UP, COLOR_DOWN, 'chart2_kline_h.png', 2)

# --- 图3: 收盘价走势对比 ---
fig, ax = plt.subplots(figsize=(12, 5))
a_dates = [fmt_date(r['trade_date']) for r in a_records]
h_dates = [fmt_date(r['trade_date']) for r in h_records]
a_close = [r['close'] for r in a_records]
h_close_cny = [r['close'] * HKD_TO_CNY for r in h_records]

ax.plot(range(len(a_records)), a_close, color=COLOR_A, linewidth=1.5, label='A股收盘价(CNY)')
ax.plot(range(len(h_records)), h_close_cny, color=COLOR_H, linewidth=1.5, label='港股收盘价(换算CNY)')

step = max(1, len(a_records) // 15)
ax.set_xticks(range(0, len(a_records), step))
ax.set_xticklabels([a_dates[i] for i in range(0, len(a_records), step)], rotation=45, fontsize=8, ha='right')
ax.set_title('图3 宁德时代 A股与港股收盘价走势对比（统一换算为人民币）', fontsize=13, fontweight='bold')
ax.set_ylabel('价格 (元)', fontsize=11)
ax.legend(fontsize=10, loc='upper left')
ax.grid(True, alpha=0.3, linestyle='--')
plt.tight_layout()
chart3_path = os.path.join(CHART_DIR, 'chart3_price_compare.png')
plt.savefig(chart3_path, dpi=150, bbox_inches='tight')
plt.close()

# --- 图4: A/H溢价率走势 ---
# 找共同交易日
a_date_map = {r['trade_date']: r for r in a_records}
h_date_map = {r['trade_date']: r for r in h_records}
common_dates = sorted(set(a_date_map.keys()) & set(h_date_map.keys()))

premiums = []
premium_dates = []
for d in common_dates:
    a_c = a_date_map[d]['close']
    h_c = h_date_map[d]['close'] * HKD_TO_CNY
    premium = (a_c / h_c - 1) * 100
    premiums.append(premium)
    premium_dates.append(fmt_date(d))

fig, ax = plt.subplots(figsize=(12, 4.5))
ax.fill_between(range(len(premiums)), premiums, 0, where=[p < 0 for p in premiums],
                color=(46/255, 204/255, 113/255, 0.3), interpolate=True)
ax.fill_between(range(len(premiums)), premiums, 0, where=[p >= 0 for p in premiums],
                color=(231/255, 76/255, 60/255, 0.3), interpolate=True)
ax.plot(range(len(premiums)), premiums, color='#9b59b6', linewidth=1.5)
ax.axhline(y=0, color='#999', linestyle='--', linewidth=1)

step = max(1, len(premium_dates) // 15)
ax.set_xticks(range(0, len(premium_dates), step))
ax.set_xticklabels([premium_dates[i] for i in range(0, len(premium_dates), step)], rotation=45, fontsize=8, ha='right')
ax.set_title('图4 宁德时代 A/H股溢价率走势', fontsize=13, fontweight='bold')
ax.set_ylabel('溢价率 (%)', fontsize=11)
ax.grid(True, alpha=0.3, linestyle='--')
# 标注均值
avg_premium = sum(premiums) / len(premiums)
ax.axhline(y=avg_premium, color='#e67e22', linestyle=':', linewidth=1.5, label=f'均值: {avg_premium:.2f}%')
ax.legend(fontsize=10)
plt.tight_layout()
chart4_path = os.path.join(CHART_DIR, 'chart4_premium.png')
plt.savefig(chart4_path, dpi=150, bbox_inches='tight')
plt.close()

# --- 图5: 成交量对比 ---
fig, ax = plt.subplots(figsize=(12, 5))
a_vols = [r['vol'] / 10000 for r in a_records]  # 转万手
h_vols = [r['vol'] / 10000 for r in h_records]

# 按涨跌着色
a_colors = [COLOR_UP if r['close'] >= r['open'] else COLOR_DOWN for r in a_records]
h_colors = [COLOR_UP if r['close'] >= r['open'] else COLOR_DOWN for r in h_records]

width = 0.35
ax.bar([i - width/2 for i in range(len(a_vols))], a_vols, width, color=a_colors, alpha=0.8, label='A股成交量')
ax.bar([i + width/2 for i in range(len(h_vols))], h_vols, width, color=h_colors, alpha=0.6, label='港股成交量')

step = max(1, len(a_records) // 15)
ax.set_xticks(range(0, len(a_records), step))
ax.set_xticklabels([a_dates[i] for i in range(0, len(a_records), step)], rotation=45, fontsize=8, ha='right')
ax.set_title('图5 宁德时代 A股与港股成交量对比', fontsize=13, fontweight='bold')
ax.set_ylabel('成交量 (万手)', fontsize=11)
ax.legend(fontsize=10, loc='upper left')
ax.grid(True, alpha=0.3, linestyle='--', axis='y')
plt.tight_layout()
chart5_path = os.path.join(CHART_DIR, 'chart5_volume.png')
plt.savefig(chart5_path, dpi=150, bbox_inches='tight')
plt.close()

# --- 图6: 日涨跌幅散点图 ---
fig, ax = plt.subplots(figsize=(8, 7))
scatter_data = []
for d in common_dates:
    a_pct = a_date_map[d]['pct_chg']
    h_pct = h_date_map[d]['pct_chg']
    scatter_data.append((a_pct, h_pct, fmt_date(d)))

x_vals = [s[0] for s in scatter_data]
y_vals = [s[1] for s in scatter_data]
ax.scatter(x_vals, y_vals, s=20, color='#9b59b6', alpha=0.6, edgecolors='#8e44ad', linewidths=0.5)
ax.axhline(y=0, color='#ccc', linewidth=1)
ax.axvline(x=0, color='#ccc', linewidth=1)

# 趋势线
import numpy as np
if len(x_vals) > 2:
    z = np.polyfit(x_vals, y_vals, 1)
    p = np.poly1d(z)
    x_fit = np.linspace(min(x_vals), max(x_vals), 100)
    ax.plot(x_fit, p(x_fit), 'r--', linewidth=1.5, label=f'趋势线: y={z[0]:.2f}x+{z[1]:.2f}')

ax.set_xlabel('A股日涨跌幅 (%)', fontsize=12)
ax.set_ylabel('港股日涨跌幅 (%)', fontsize=12)
ax.set_title('图6 宁德时代 A股与港股日涨跌幅散点对比', fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, linestyle='--')
plt.tight_layout()
chart6_path = os.path.join(CHART_DIR, 'chart6_scatter.png')
plt.savefig(chart6_path, dpi=150, bbox_inches='tight')
plt.close()

# --- 图7: 历年财务表现 ---
years = ['2019', '2020', '2021', '2022', '2023', '2024', '2025', '2026F']
net_profits = [45.6, 55.83, 159.31, 307.29, 441.21, 507.45, 722.01, 950.82]
eps_vals = [2.09, 2.49, 6.88, 7.18, 10.06, 11.58, 16.14, 20.77]
revenues = [None, None, None, 4009.17, 3620.13, None, 4237.02, 5876.0]

fig, ax1 = plt.subplots(figsize=(10, 5.5))
bar_width = 0.35
x_pos = np.arange(len(years))

# 净利润柱
bars1 = ax1.bar(x_pos - bar_width/2, net_profits, bar_width, label='净利润(亿)', color='#e74c3c', alpha=0.7)
# 营收柱
rev_data = [r if r is not None else 0 for r in revenues]
bars2 = ax1.bar(x_pos + bar_width/2, rev_data, bar_width, label='营业收入(亿)', color='#3498db', alpha=0.5)

ax1.set_xlabel('年度', fontsize=12)
ax1.set_ylabel('金额 (亿元)', fontsize=12)
ax1.set_xticks(x_pos)
ax1.set_xticklabels(years, fontsize=11)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3, linestyle='--', axis='y')

ax2 = ax1.twinx()
ax2.plot(x_pos, eps_vals, 'o-', color='#9b59b6', linewidth=2, markersize=6, label='每股收益(元)')
ax2.set_ylabel('每股收益 (元)', fontsize=12)
ax2.legend(loc='upper right', fontsize=10)

ax1.set_title('图7 宁德时代历年财务表现（2019-2026F）', fontsize=13, fontweight='bold')
plt.tight_layout()
chart7_path = os.path.join(CHART_DIR, 'chart7_financial.png')
plt.savefig(chart7_path, dpi=150, bbox_inches='tight')
plt.close()

# --- 图8: 均线系统图 (技术面) ---
fig, ax = plt.subplots(figsize=(12, 5.5))

closes = [r['close'] for r in a_records]
dates_str = [fmt_date(r['trade_date']) for r in a_records]

# 计算5日、10日、20日、60日均线
def calc_ma(data, period):
    ma = []
    for i in range(len(data)):
        if i < period - 1:
            ma.append(None)
        else:
            ma.append(sum(data[i-period+1:i+1]) / period)
    return ma

ma5 = calc_ma(closes, 5)
ma10 = calc_ma(closes, 10)
ma20 = calc_ma(closes, 20)
ma60 = calc_ma(closes, 60)

ax.plot(range(len(closes)), closes, color='#333', linewidth=1, label='收盘价', alpha=0.8)
ax.plot(range(len(ma5)), ma5, color='#e74c3c', linewidth=1, label='MA5', alpha=0.8)
ax.plot(range(len(ma10)), ma10, color='#3498db', linewidth=1, label='MA10', alpha=0.8)
ax.plot(range(len(ma20)), ma20, color='#9b59b6', linewidth=1.2, label='MA20', alpha=0.8)
ax.plot(range(len(ma60)), ma60, color='#2ecc71', linewidth=1.5, label='MA60', alpha=0.8)

step = max(1, len(a_records) // 15)
ax.set_xticks(range(0, len(a_records), step))
ax.set_xticklabels([dates_str[i] for i in range(0, len(a_records), step)], rotation=45, fontsize=8, ha='right')
ax.set_title('图8 宁德时代A股均线系统图（MA5/MA10/MA20/MA60）', fontsize=13, fontweight='bold')
ax.set_ylabel('价格 (元)', fontsize=11)
ax.legend(fontsize=9, loc='upper left')
ax.grid(True, alpha=0.3, linestyle='--')
plt.tight_layout()
chart8_path = os.path.join(CHART_DIR, 'chart8_ma.png')
plt.savefig(chart8_path, dpi=150, bbox_inches='tight')
plt.close()

print("所有图表生成完毕!")

# ============ 5. 构建PDF文档 ============
output_path = r'C:\Users\86198\Desktop\quant-trials\郭美杰+TASK1.pdf'

doc = SimpleDocTemplate(
    output_path,
    pagesize=A4,
    leftMargin=2.5 * cm,
    rightMargin=2.5 * cm,
    topMargin=2.5 * cm,
    bottomMargin=2.5 * cm,
    title='郭美杰+TASK1',
    author='郭美杰'
)

story = []

# === 标题页 ===
story.append(Spacer(1, 100))
story.append(Paragraph('宁德时代A股与港股对比分析报告', style_title))
story.append(Spacer(1, 15))
story.append(Paragraph('——基于K线图、基本面与技术面的综合分析', ParagraphStyle(
    'Subtitle', fontName='SimHei', fontSize=12, leading=18, alignment=TA_CENTER, textColor=HexColor('#555')
)))
story.append(Spacer(1, 30))
story.append(Paragraph('姓名：郭美杰', style_body_noindent))
story.append(Paragraph('日期：2026年7月4日', style_body_noindent))
story.append(Paragraph('数据区间：2025年7月4日 至 2026年7月3日', style_body_noindent))
story.append(PageBreak())

# === 摘要 ===
story.append(Paragraph('摘要', style_h1))
story.append(Spacer(1, 6))
story.append(Paragraph(
    '本报告以宁德时代（300750.SZ / 03750.HK）近一年（2025年7月至2026年7月）的日线行情数据为基础，'
    '分别从K线图形态、基本面财务数据和技术面指标三个维度，对宁德时代A股与港股的表现进行系统性对比分析。'
    '报告首先对K线图、基本面分析、技术面分析的基本概念进行阐释，随后结合实际数据与统计图表展开深入分析。'
    '研究发现，报告期内港股涨幅（+92.11%）显著高于A股（+42.96%），A股持续处于折价状态，'
    'A/H溢价率均值约为-20.35%，反映国际投资者对宁德时代港股的偏好更为强烈。',
    style_body
))
story.append(Spacer(1, 12))

# === 第一章：基本概念 ===
story.append(Paragraph('一、基本概念解释', style_h1))
story.append(Spacer(1, 6))

story.append(Paragraph('（一）K线图', style_h2))
story.append(Paragraph(
    'K线图（Candlestick Chart），又称蜡烛图或日本线，是金融市场中最常用的价格走势可视化工具之一。'
    '它由日本米市商人本间宗久于18世纪发明，后被引入股票、期货等金融市场，广泛应用于技术分析领域。'
    'K线图通过四个关键价格数据来绘制每一根K线：开盘价（Open）、最高价（High）、最低价（Low）和收盘价（Close），'
    '简称"开高低收"（OHLC）。',
    style_body
))
story.append(Paragraph(
    '一根标准的K线由"实体"和"影线"两部分组成。实体表示开盘价与收盘价之间的价格区间，'
    '当收盘价高于开盘价时，称为"阳线"（在中国A股市场以红色表示，表示上涨）；'
    '当收盘价低于开盘价时，称为"阴线"（以绿色表示，表示下跌）。'
    '实体上方的细线称为"上影线"，其顶端代表当日最高价；实体下方的细线称为"下影线"，'
    '其底端代表当日最低价。影线的长短反映了价格波动的幅度和方向。',
    style_body
))
story.append(Paragraph(
    'K线图的核心价值在于直观地展示了多空双方的力量对比。'
    '长阳线表示买方力量强劲，长阴线表示卖方力量占优。'
    '上影线长说明上方抛压较重，下影线长说明下方支撑较强。'
    '通过连续观察多根K线的排列组合，投资者可以判断市场趋势、识别反转信号并做出交易决策。'
    '常见的K线组合形态包括十字星、锤头线、吞没形态、早晨之星、黄昏之星等，'
    '每种形态都传递着特定的市场信号。',
    style_body
))
story.append(Paragraph(
    '在本次分析中，我们采用日线K线图来展示宁德时代A股和港股近一年的价格走势，'
    '并遵循中国A股市场的红涨绿跌惯例进行着色，以便于投资者直观理解。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（二）基本面分析', style_h2))
story.append(Paragraph(
    '基本面分析（Fundamental Analysis）是一种通过分析影响证券内在价值的经济、财务和行业因素来评估投资价值的方法。'
    '与侧重于价格走势图形的技术分析不同，基本面分析关注的是企业的"真实价值"，'
    '试图通过深入研究企业的经营状况、财务数据、行业地位、宏观环境等因素，'
    '判断当前市场价格是高估还是低估。',
    style_body
))
story.append(Paragraph(
    '基本面分析的核心要素包括以下几个维度：'
    '第一，财务指标分析，主要包括营业收入、净利润、毛利率、净利率、净资产收益率（ROE）、'
    '每股收益（EPS）、市盈率（PE）、市净率（PB）等。'
    '第二，行业地位与竞争格局，考察企业在行业中的市场份额、竞争壁垒和成长空间。'
    '第三，宏观环境与政策影响，包括经济周期、货币政策、产业政策等对企业经营的外部影响。'
    '第四，管理层与公司治理，评估管理团队的战略眼光、执行能力和诚信水平。',
    style_body
))
story.append(Paragraph(
    '对于宁德时代而言，作为全球动力电池行业的龙头企业，其基本面分析需要特别关注以下方面：'
    '全球及中国动力电池市场规模与增速、宁德时代在全球及国内的市场占有率、'
    '储能业务的增长潜力、海外市场拓展进展、技术创新能力（如固态电池、钠离子电池研发）、'
    '以及与主要客户（特斯拉、宝马等）的合作关系等。'
    '这些因素共同决定了宁德时代的长期投资价值。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（三）技术面分析', style_h2))
story.append(Paragraph(
    '技术面分析（Technical Analysis）是通过研究证券价格和成交量的历史数据来预测未来价格走势的分析方法。'
    '技术分析的理论基础是道氏理论（Dow Theory），其核心假设包括：'
    '市场行为包容消化一切（所有影响价格的因素都已反映在价格中）、'
    '价格以趋势方式演变（趋势一旦形成将持续，直至出现明确的反转信号）、'
    '历史会重演（相同的市场心理会反复出现，形成可识别的价格形态）。',
    style_body
))
story.append(Paragraph(
    '技术面分析的主要工具包括：'
    '（1）趋势线与通道：通过连接价格的高点或低点来判断市场趋势方向。'
    '（2）移动平均线（MA）：将一定周期内的收盘价取平均值连成线，'
    '常用周期包括5日、10日、20日（短期）、60日、120日（中长期）。'
    '当短期均线上穿长期均线时形成"金叉"，为买入信号；反之形成"死叉"，为卖出信号。'
    '（3）成交量分析：成交量是价格的确认指标，价升量增表示上涨趋势健康，'
    '价升量缩则可能预示上涨乏力。'
    '（4）技术指标：包括MACD（指数平滑异同移动平均线）、RSI（相对强弱指数）、'
    'KDJ（随机指标）、布林带（Bollinger Bands）等。',
    style_body
))
story.append(Paragraph(
    '在本报告中，技术面分析部分将以宁德时代A股的均线系统（MA5/MA10/MA20/MA60）为核心，'
    '结合成交量变化，分析其短期和中长期的技术走势特征。',
    style_body
))

story.append(PageBreak())

# === 第二章：K线图分析 ===
story.append(Paragraph('二、K线图分析', style_h1))
story.append(Spacer(1, 6))

story.append(Paragraph('（一）A股K线图', style_h2))
story.append(Paragraph(
    '图1展示了宁德时代A股（300750.SZ）近一年的日线K线走势。'
    '从整体趋势来看，A股价格从2025年7月初的约266元起步，经历了2025年8月的低点约258元后，'
    '开启了长达数月的上升通道，于2026年5月初达到年内最高价460元，'
    '随后在6月出现一定回调，7月初收于380元附近。'
    '区间涨幅约42.96%，呈现出先低后高、高位回调的技术形态。',
    style_body
))

# 插入A股K线图
img_w = 16 * cm
img_h = 6.7 * cm
story.append(RLImage(chart1_path, width=img_w, height=img_h))
story.append(Paragraph('图1 宁德时代A股（300750.SZ）近一年日K线图', style_caption))
story.append(Spacer(1, 8))

story.append(Paragraph(
    '从K线形态分析：2025年8月中旬出现明显的底部锤头线形态，随后连续阳线上攻，'
    '形成了可靠的底部反转信号。2026年2月至3月期间，股价从约345元快速拉升至413元附近，'
    '出现多根长阳线，表明多头力量强劲。但5月之后，K线实体逐渐缩小，'
    '上影线增多，提示上方抛压加重，上涨动力减弱。6月下旬出现的连续阴线吞没形态，'
    '预示短期调整仍未结束。',
    style_body
))

story.append(Spacer(1, 8))
story.append(Paragraph('（二）港股K线图', style_h2))
story.append(Paragraph(
    '图2展示了宁德时代港股（03750.HK）近一年的K线走势。'
    '港股价格从2025年7月初的约352港元起步，经历了8月的震荡筑底后，'
    '于9月开启了一轮强劲的上升趋势。'
    '2026年3月至5月期间，港股加速上涨，最高触及779.50港元，'
    '区间涨幅高达92.11%，远超A股同期表现。7月初收于675.50港元附近。',
    style_body
))

story.append(RLImage(chart2_path, width=img_w, height=img_h))
story.append(Paragraph('图2 宁德时代港股（03750.HK）近一年日K线图', style_caption))
story.append(Spacer(1, 8))

story.append(Paragraph(
    '对比图1和图2可以观察到：港股K线的阳线数量明显多于A股，'
    '且长阳线更为集中，反映出港股市场对宁德时代的看多情绪更为一致。'
    '此外，港股在2026年3-5月的加速上涨阶段形成了清晰的上升通道，'
    '技术形态更为标准。相比之下，A股在该阶段的上涨更为曲折，'
    '回调幅度更大，波动性更高。',
    style_body
))

story.append(PageBreak())

# === 收盘价走势对比 ===
story.append(Paragraph('（三）收盘价走势对比', style_h2))
story.append(Paragraph(
    '图3将A股和港股的收盘价统一换算为人民币（按央行中间价1 HKD = 0.86784 CNY）后进行对比。'
    '可以清晰地看到，两条价格曲线整体走势方向一致，均呈上升趋势，但港股的上升斜率明显更陡。'
    '在2025年11月之前，两地价格走势高度同步；'
    '此后港股开始加速上行，与A股的价差逐渐拉大。'
    '到2026年年中，港股换算后价格已显著高于A股，'
    '说明国际资本市场对宁德时代的估值定价更为积极。',
    style_body
))

story.append(RLImage(chart3_path, width=img_w, height=img_h))
story.append(Paragraph('图3 宁德时代A股与港股收盘价走势对比（统一换算为人民币）', style_caption))
story.append(Spacer(1, 8))

# === A/H溢价率 ===
story.append(Paragraph('（四）A/H溢价率分析', style_h2))
story.append(Paragraph(
    '图4展示了A/H溢价率的走势。A/H溢价率是衡量同一家公司A股价格相对于港股价格偏离程度的重要指标，'
    '其计算公式为：A/H溢价率 =（A股收盘价 / 港股收盘价换算人民币 - 1）× 100%。'
    '当溢价率为正时，表示A股价格高于港股（A股溢价）；'
    '当溢价率为负时，表示A股价格低于港股（A股折价）。',
    style_body
))

story.append(RLImage(chart4_path, width=img_w, height=5 * cm))
story.append(Paragraph('图4 宁德时代A/H股溢价率走势', style_caption))
story.append(Spacer(1, 8))

story.append(Paragraph(
    '从图4可以看出，在整个报告期内，A/H溢价率始终为负值，'
    '即宁德时代A股持续处于折价状态。溢价率区间为-36.86%至-6.89%，均值为-20.35%。'
    '溢价率在2025年11月曾一度收窄至约-7%附近，这是两地价格最接近的时期；'
    '但此后随着港股加速上涨，折价幅度重新扩大，到2026年6-7月维持在-35%左右的高位折价水平。'
    '这一现象表明，国际投资者对宁德时代港股给予了更高的估值溢价，'
    '可能与国际资金对新能源龙头企业的偏好、港股流动性改善以及南向资金的持续流入有关。',
    style_body
))

story.append(PageBreak())

# === 第三章：基本面分析 ===
story.append(Paragraph('三、基本面分析', style_h1))
story.append(Spacer(1, 6))

story.append(Paragraph('（一）核心财务指标', style_h2))
story.append(Paragraph(
    '宁德时代2026年一季报显示，公司实现营业收入1291.31亿元，同比增长52.45%；'
    '归属于母公司股东的净利润207.38亿元，同比增长48.52%；扣非净利润180.93亿元，同比增长52.95%。'
    '毛利率为24.8%，净利率为17.6%，每股收益（EPS）4.58元。'
    '经营性现金流净额336.81亿元，现金储备超过4100亿元，展现出强劲的盈利能力和充裕的现金流。',
    style_body
))

# 财务指标表格
fin_data = [
    ['财务指标', '2026Q1数值', '同比变化', '说明'],
    ['营业收入', '1,291.31亿元', '+52.45%', '增速大幅提升'],
    ['归母净利润', '207.38亿元', '+48.52%', '盈利能力强劲'],
    ['扣非净利润', '180.93亿元', '+52.95%', '主业增长突出'],
    ['毛利率', '24.8%', '-', '维持较高水平'],
    ['净利率', '17.6%', '-', '盈利质量优秀'],
    ['每股收益(EPS)', '4.58元', '-', '每股盈利能力'],
    ['ROE', '5.98%', '-', '单季度净资产收益率'],
    ['研发费用', '53.14亿元', '-', '持续高研发投入'],
    ['经营现金流', '336.81亿元', '-', '现金流充裕'],
    ['现金储备', '4,100+亿元', '-', '资金实力雄厚'],
]

fin_table_data = []
for i, row in enumerate(fin_data):
    if i == 0:
        fin_table_data.append([Paragraph(cell, style_table_header) for cell in row])
    else:
        fin_table_data.append([Paragraph(cell, style_table_cell) for cell in row])

fin_table = Table(fin_table_data, colWidths=[3.5*cm, 3.5*cm, 3*cm, 5*cm])
fin_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#ddd')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f8f9fa')]),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(fin_table)
story.append(Paragraph('表1 宁德时代2026年一季度核心财务指标', style_caption))
story.append(Spacer(1, 10))

story.append(Paragraph(
    '从表1可以看出，宁德时代2026年一季度业绩表现亮眼，营收和利润均实现近50%的高速增长。'
    '毛利率24.8%处于行业领先水平，净利率17.6%表明公司在规模效应和成本控制方面表现出色。'
    '超过4100亿元的现金储备为公司的产能扩张、技术研发和海外布局提供了坚实的资金保障。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（二）估值与市值', style_h2))
story.append(Paragraph(
    '截至2026年7月3日，宁德时代A股总市值约17,581亿元，市盈率（PE）24.35倍，PE(TTM) 22.26倍，'
    '市净率（PB）4.92倍，市销率（PS）4.15倍，股息率1.778%。'
    '对比行业平均估值水平，宁德时代当前PE处于合理偏低区间，'
    '考虑到公司高达50%以上的业绩增速，PEG指标小于0.5，'
    '表明当前估值具有较强的投资吸引力。',
    style_body
))

story.append(Spacer(1, 8))
story.append(Paragraph('（三）全球市场地位', style_h2))
story.append(Paragraph(
    '宁德时代在全球动力电池市场占据绝对领先地位。'
    '截至2026年一季度，公司全球动力电池市占率达42.1%，同比提升3.4个百分点；'
    '国内市占率47.7%，同样提升3.4个百分点，创五年新高。'
    '储能业务方面，一季度储能出货约50GWh，同比增长108%，占比达25%，成为新的增长引擎。'
    '海外收入占比突破30.6%，海外毛利率较国内高出8个百分点，国际化战略成效显著。'
    '公司累计专利超过54,000项，研发人员超过21,000人，'
    '在神行III、麒麟III、凝聚态电池、钠离子电池等领域保持技术领先。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（四）历年财务表现', style_h2))
story.append(Paragraph(
    '图7展示了宁德时代2019年至2026年（预测）的历年财务表现。'
    '从净利润来看，公司从2019年的45.6亿元增长至2025年的722.01亿元，'
    '七年增长近15倍，年均复合增长率超过58%。2026年机构一致预期净利润约950.82亿元，'
    '继续保持高速增长态势。每股收益从2019年的2.09元增长至2025年的16.14元，'
    '预计2026年达到20.77元。ROE长期维持在24%以上的高水平，'
    '体现了公司卓越的资本回报能力。'
    '营业总收入方面，2022年突破4000亿元大关，2025年达4237亿元，'
    '2026年机构预期将达5876亿元，规模效应持续释放。',
    style_body
))

story.append(RLImage(chart7_path, width=15 * cm, height=8.25 * cm))
story.append(Paragraph('图7 宁德时代历年财务表现（2019-2026F）', style_caption))
story.append(Spacer(1, 8))

story.append(Paragraph(
    '从图7可以观察到，宁德时代的净利润和营收呈现出持续高速增长的态势，'
    '尽管2023年营收较2022年有所下降（从4009亿降至3620亿），'
    '但净利润仍保持了显著增长（从307亿增长至441亿），'
    '说明公司在行业调整期通过降本增效维持了盈利能力的提升。'
    '2025-2026年的加速增长则得益于动力电池和储能双轮驱动，'
    '以及海外市场的快速拓展。',
    style_body
))

story.append(PageBreak())

# === 第四章：技术面分析 ===
story.append(Paragraph('四、技术面分析', style_h1))
story.append(Spacer(1, 6))

story.append(Paragraph('（一）均线系统分析', style_h2))
story.append(Paragraph(
    '移动平均线（Moving Average，简称MA）是技术分析中最基础也最重要的趋势跟踪指标之一。'
    '它通过计算一定周期内收盘价的算术平均值，并将这些平均值连成线，'
    '来平滑价格波动、识别趋势方向。常用的均线周期包括：'
    'MA5和MA10为短期均线，反映近期价格走势；'
    'MA20为中期均线，常被视为短期趋势的分水岭；'
    'MA60和MA120为中长期均线，是判断中长期趋势的重要参考。',
    style_body
))

story.append(Paragraph(
    '图8展示了宁德时代A股的均线系统。'
    'MA5（红色）与MA10（蓝色）的交叉关系能够提供短期交易信号：'
    '当MA5上穿MA10时形成"金叉"，为短期买入信号；反之形成"死叉"，为短期卖出信号。'
    'MA20（紫色）是中期趋势线，股价站上MA20通常意味着中期趋势转强。'
    'MA60（绿色）作为中长期趋势线，是判断牛市与熊市的重要分界——'
    '股价在MA60之上运行通常被视为多头市场，反之则为空头市场。',
    style_body
))

story.append(RLImage(chart8_path, width=img_w, height=img_h * 1.1))
story.append(Paragraph('图8 宁德时代A股均线系统图（MA5/MA10/MA20/MA60）', style_caption))
story.append(Spacer(1, 8))

story.append(Paragraph(
    '从图8的均线走势分析：在2025年8-9月，MA5和MA10多次在MA20附近纠缠，'
    '随后MA5和MA10同时上穿MA20，形成了典型的"多头排列"格局——'
    '即MA5 > MA10 > MA20 > MA60，表明短期、中期、长期趋势一致向上。'
    '这一多头排列从2025年9月一直持续到2026年5月，期间股价从约330元上涨至460元，'
    '涨幅约39%，均线系统发出了持续而可靠的做多信号。'
    '进入2026年6月后，MA5开始下穿MA10形成"死叉"，股价也跌破MA20，'
    '提示短期调整压力加大。但MA60仍在缓慢上行，中长期趋势尚未破坏。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（二）成交量分析', style_h2))
story.append(Paragraph(
    '成交量是技术分析中仅次于价格的第二重要指标。'
    '成交量代表了市场交易的活跃程度和资金的参与力度，'
    '经典的技术分析理论认为"成交量是价格的先行指标"——'
    '即在价格发生重大转折之前，成交量往往会率先发出信号。',
    style_body
))

story.append(Paragraph(
    '成交量分析的核心原则包括：'
    '（1）价升量增：价格上涨伴随成交量放大，表示上涨趋势健康，买盘积极；'
    '（2）价升量缩：价格上涨但成交量萎缩，可能预示上涨动力不足，存在回调风险；'
    '（3）价跌量增：价格下跌伴随成交量放大，表示抛压沉重，下跌趋势可能加速；'
    '（4）价跌量缩：价格下跌但成交量萎缩，可能预示卖盘枯竭，调整接近尾声。',
    style_body
))

story.append(RLImage(chart5_path, width=img_w, height=img_h))
story.append(Paragraph('图5 宁德时代A股与港股成交量对比', style_caption))
story.append(Spacer(1, 8))

story.append(Paragraph(
    '从图5的成交量对比可以观察到以下特征：'
    '第一，A股成交量整体远大于港股（A股日均约32.6万手，港股日均约3.1万手），'
    '反映了A股市场流动性更为充裕。'
    '第二，在关键转折点，成交量均出现显著放大。'
    '例如2025年8月底A股放量上涨（成交量达78万手），对应底部反转；'
    '2026年5月初A股成交量达47万手，对应阶段性顶部。'
    '第三，港股成交量在2026年3-5月加速上涨期间明显放大，'
    '多次突破4万手甚至6万手，量价配合良好，验证了上涨趋势的有效性。',
    style_body
))

story.append(PageBreak())

# === 第五章：综合对比分析 ===
story.append(Paragraph('五、综合对比分析', style_h1))
story.append(Spacer(1, 6))

story.append(Paragraph('（一）涨跌幅联动性分析', style_h2))
story.append(Paragraph(
    '图6以散点图的形式展示了A股和港股日涨跌幅的联动关系。'
    '横轴为A股日涨跌幅，纵轴为港股日涨跌幅，每个散点代表一个交易日。'
    '图中虚线为趋势线，其斜率反映了港股对A股涨跌的敏感程度。'
    '趋势线斜率大于1表示港股涨跌幅度大于A股，反之则小于A股。',
    style_body
))

story.append(RLImage(chart6_path, width=12 * cm, height=10.5 * cm))
story.append(Paragraph('图6 宁德时代A股与港股日涨跌幅散点对比', style_caption))
story.append(Spacer(1, 8))

story.append(Paragraph(
    '从图6可以观察到：散点整体分布在第一象限和第三象限，'
    '说明两地市场涨跌方向基本一致，存在正相关性。'
    '趋势线斜率约为1.2，表明港股的日涨跌幅波动幅度略大于A股，'
    '港股对利好或利淡消息的反应更为敏感。'
    '部分散点偏离趋势线较远，如2025年8月29日A股大涨10.37%而港股仅涨4.17%，'
    '以及2026年3月10日港股大涨9.34%而A股涨5.26%，'
    '这些异常点通常对应重大事件或市场情绪分化，'
    '提示投资者关注两地市场的结构性差异。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（二）关键数据对比', style_h2))

# 对比统计表
compare_data = [
    ['对比指标', 'A股 (300750.SZ)', '港股 (03750.HK)', '差异/说明'],
    ['报告期', '2025/07/04~2026/07/03', '2025/07/03~2026/07/03', '港股多1个交易日'],
    ['交易日数', '242天', '246天', '-'],
    ['最新收盘价', '¥380.00', 'HK$675.50', '港股面值更高'],
    ['区间涨幅', '+42.96%', '+92.11%', '港股涨幅超A股一倍'],
    ['年内最高价', '¥460.00', 'HK$779.50', '-'],
    ['年内最低价', '¥258.89', 'HK$348.67', '-'],
    ['日均成交量', '约32.6万手', '约3.1万手', 'A股流动性远超港股'],
    ['A/H溢价率(当前)', '-35.18%', '-', 'A股深度折价'],
    ['A/H溢价率(均值)', '-20.35%', '-', '持续折价状态'],
    ['A/H溢价率(区间)', '-36.86%~ -6.89%', '-', '折价幅度波动较大'],
]

comp_table_data = []
for i, row in enumerate(compare_data):
    if i == 0:
        comp_table_data.append([Paragraph(cell, style_table_header) for cell in row])
    else:
        comp_table_data.append([Paragraph(cell, style_table_cell) for cell in row])

comp_table = Table(comp_table_data, colWidths=[3.5*cm, 4*cm, 4*cm, 3.5*cm])
comp_table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), HexColor('#1a1a2e')),
    ('TEXTCOLOR', (0, 0), (-1, 0), white),
    ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#ddd')),
    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [HexColor('#ffffff'), HexColor('#f8f9fa')]),
    ('TOPPADDING', (0, 0), (-1, -1), 5),
    ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
]))
story.append(comp_table)
story.append(Paragraph('表2 宁德时代A股与港股关键数据对比', style_caption))
story.append(Spacer(1, 10))

story.append(Paragraph(
    '从表2的对比数据可以看出，宁德时代港股在报告期内的涨幅（+92.11%）显著高于A股（+42.96%），'
    '差距接近一倍。这一差异主要体现在2026年3月至5月港股加速上涨阶段。'
    'A股日均成交量约32.6万手，是港股（3.1万手）的十倍以上，'
    '体现了A股市场在流动性方面的绝对优势。'
    'A/H溢价率方面，A股相对于港股持续处于折价状态，'
    '当前折价幅度约35%，历史均值约20%，'
    '说明A股投资者对宁德时代的估值定价相对保守，'
    '而国际市场给予了更高的估值溢价。',
    style_body
))

story.append(PageBreak())

# === 第六章：结论与展望 ===
story.append(Paragraph('六、结论与展望', style_h1))
story.append(Spacer(1, 6))

story.append(Paragraph('（一）主要结论', style_h2))
story.append(Paragraph(
    '通过对宁德时代A股与港股近一年数据的系统分析，本报告得出以下主要结论：'
    '第一，从K线图形态来看，两地市场整体趋势一致向上，'
    '但港股走势更为流畅，K线阳线更为集中，A股波动性更大。'
    '第二，从基本面来看，宁德时代2026年一季度业绩超预期，'
    '营收和净利润均实现近50%的增长，全球市占率持续提升至42.1%，'
    '基本面支撑强劲，估值处于合理偏低区间。'
    '第三，从技术面来看，A股均线系统在2025年9月至2026年5月期间维持多头排列，'
    '发出了持续可靠的做多信号；但6月后短期技术指标转弱，存在调整压力。',
    style_body
))
story.append(Paragraph(
    '第四，A/H溢价率方面，A股持续深度折价（均值-20.35%），'
    '且折价幅度在报告期末段有扩大趋势，'
    '反映了国际投资者对宁德时代港股的偏好更为强烈。'
    '第五，两地市场日涨跌幅存在显著正相关性，'
    '但港股的波动幅度更大，对市场消息的反应更为敏感。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（二）投资建议', style_h2))
story.append(Paragraph(
    '综合基本面、技术面和K线形态的分析，宁德时代作为全球动力电池龙头企业，'
    '具备强劲的盈利能力、领先的市场地位和充裕的现金流，'
    '长期投资价值突出。短期来看，A股在6月后进入技术性调整阶段，'
    '建议关注MA20和MA60的支撑力度，若能在中长期均线附近企稳，'
    '仍具备较好的中长期配置价值。对于A/H两地市场的选择，'
    '当前A股折价幅度较大，从估值角度具有一定的安全边际；'
    '而港股虽然涨幅更大，但流动性较低且波动性更高，'
    '投资者应根据自身风险偏好和投资期限做出选择。',
    style_body
))

story.append(Spacer(1, 10))
story.append(Paragraph('（三）风险提示', style_h2))
story.append(Paragraph(
    '本报告基于历史数据分析，不构成投资建议。'
    '投资者应注意以下风险：'
    '（1）新能源行业政策变化风险，包括补贴退坡、碳排放法规调整等；'
    '（2）原材料价格波动风险，锂、钴、镍等关键原材料价格波动可能影响毛利率；'
    '（3）国际地缘政治风险，海外市场拓展可能面临贸易壁垒和政策不确定性；'
    '（4）技术替代风险，固态电池等新技术路线的突破可能改变行业竞争格局；'
    '（5）汇率波动风险，A/H溢价率受人民币与港币汇率变动影响。',
    style_body
))

story.append(Spacer(1, 20))
story.append(HRFlowable(width='100%', thickness=0.5, color=HexColor('#999')))
story.append(Spacer(1, 8))
story.append(Paragraph(
    '<font size="8" color="#888888">'
    '数据来源：A股数据来自Tushare金融数据接口；港股数据来自Yahoo Finance（yfinance）；'
    '汇率采用中国人民银行2026年7月1日中间价1 HKD = 0.86784 CNY；'
    '财务数据来自同花顺F10、券商研报及公司公告。<br/>'
    '本报告仅供学术研究参考，不构成任何投资建议。'
    '</font>',
    style_body_noindent
))

# ============ 6. 生成PDF ============
print("开始构建PDF...")
doc.build(story)
print(f"PDF已生成: {output_path}")

# 清理临时图表文件
import shutil
shutil.rmtree(CHART_DIR, ignore_errors=True)
print("临时文件已清理。")
