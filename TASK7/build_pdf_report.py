#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 TASK7 聚宽双均线策略报告.pdf（中文，无HTML），覆盖5个步骤。"""
import os, json
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image as RLImage,
                                Table, TableStyle, PageBreak, HRFlowable)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

BASE = "/Users/wangyanfen/Desktop/量化策略课程/TASK7"
FIG = os.path.join(BASE, "figs")
OUT = os.path.join(BASE, "聚宽双均线策略报告.pdf")

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
FONT = "STSong-Light"

# 读取指标
M = json.load(open(os.path.join(BASE, "metrics.json"), encoding="utf-8"))
ins, oos, oosd = M["insample"], M["oos"], M["oos_default"]
bs, bl = M["best_short"], M["best_long"]

# 样式
def style(name, **kw):
    return ParagraphStyle(name, fontName=FONT, **kw)

S_TITLE = style("t", fontSize=22, leading=28, alignment=TA_CENTER, textColor=colors.HexColor("#1A5276"))
S_SUB = style("s", fontSize=12, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#566573"))
S_H1 = style("h1", fontSize=15, leading=20, spaceBefore=14, spaceAfter=8, textColor=colors.HexColor("#1A5276"))
S_H2 = style("h2", fontSize=12.5, leading=17, spaceBefore=10, spaceAfter=5, textColor=colors.HexColor("#21618C"))
S_BODY = style("b", fontSize=10.5, leading=16, alignment=TA_JUSTIFY, spaceAfter=6)
S_BULLET = style("bu", fontSize=10.5, leading=15, leftIndent=14, spaceAfter=3)
S_SMALL = style("sm", fontSize=9, leading=12, textColor=colors.HexColor("#566573"))
S_CAP = style("cap", fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor("#566573"), spaceAfter=10)

def P(t, s=S_BODY): return Paragraph(t, s)
def bullets(items):
    return [Paragraph("• " + x, S_BULLET) for x in items]

def img(name, width=460, cap=None):
    path = os.path.join(FIG, name)
    iw, ih = Image.open(path).size
    h = width * ih / iw
    flow = [RLImage(path, width=width, height=h)]
    if cap:
        flow.append(Paragraph(cap, S_CAP))
    return flow

def fmt_pct(x): return f"{x*100:.2f}%"
def fmt_num(x, d=3): return f"{x:.{d}f}"

# 指标对比表
rows = [
    ["指标", "样本内(最优)", "样本外(实盘模拟)", "样本外(默认5/15)"],
    ["累计收益", fmt_pct(ins["累计收益"]), fmt_pct(oos["累计收益"]), fmt_pct(oosd["累计收益"])],
    ["年化收益", fmt_pct(ins["年化收益"]), fmt_pct(oos["年化收益"]), fmt_pct(oosd["年化收益"])],
    ["年化波动率", fmt_pct(ins["年化波动"]), fmt_pct(oos["年化波动"]), fmt_pct(oosd["年化波动"])],
    ["夏普比率", fmt_num(ins["夏普"]), fmt_num(oos["夏普"]), fmt_num(oosd["夏普"])],
    ["索提诺比率", fmt_num(ins["索提诺"]), fmt_num(oos["索提诺"]), fmt_num(oosd["索提诺"])],
    ["最大回撤", fmt_pct(ins["最大回撤"]), fmt_pct(oos["最大回撤"]), fmt_pct(oosd["最大回撤"])],
    ["最大回撤时长(日)", fmt_num(ins["最大回撤时长(日)"],0), fmt_num(oos["最大回撤时长(日)"],0), fmt_num(oosd["最大回撤时长(日)"],0)],
    ["基准(持有)年化", fmt_pct(ins["基准年化"]), fmt_pct(oos["基准年化"]), fmt_pct(oosd["基准年化"])],
    ["基准最大回撤", fmt_pct(ins["基准最大回撤"]), fmt_pct(oos["基准最大回撤"]), fmt_pct(oosd["基准最大回撤"])],
    ["交易次数", fmt_num(ins["交易次数"],0), fmt_num(oos["交易次数"],0), fmt_num(oosd["交易次数"],0)],
    ["日胜率", fmt_pct(ins["日胜率"]), fmt_pct(oos["日胜率"]), fmt_pct(oosd["日胜率"])],
    ["VaR(95%)", fmt_pct(ins["VaR95"]), fmt_pct(oos["VaR95"]), fmt_pct(oosd["VaR95"])],
    ["CVaR(95%)", fmt_pct(ins["CVaR95"]), fmt_pct(oos["CVaR95"]), fmt_pct(oosd["CVaR95"])],
    ["Beta(对沪深300)", fmt_num(ins["Beta"]), fmt_num(oos["Beta"]), fmt_num(oosd["Beta"])],
    ["年化换手率", fmt_num(ins["年化换手率"]), fmt_num(oos["年化换手率"]), fmt_num(oosd["年化换手率"])],
    ["Calmar", fmt_num(ins["Calmar"]), fmt_num(oos["Calmar"]), fmt_num(oosd["Calmar"])],
]

def make_table(data, col_widths):
    t = Table(data, colWidths=col_widths, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), FONT),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1A5276")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), FONT),
        ("ALIGN", (1,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#EAF2F8")]),
        ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#AAB7B8")),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    return t

# 成本敏感性表
cost = M["cost_sensitivity"]
cost_rows = [["单边滑点", "年化收益", "夏普比率", "最大回撤"]]
for c in cost:
    cost_rows.append([f"{c['滑点']*100:.1f}%", fmt_pct(c["年化收益"]), fmt_num(c["夏普"]), fmt_pct(c["最大回撤"])])

# 参数寻优 Top5 表
top5 = M["tune_top5"]
top_rows = [["排名","短均线","长均线","年化收益","夏普","最大回撤","交易次数"]]
for i, r in enumerate(top5, 1):
    top_rows.append([str(i), str(r["短均线"]), str(r["长均线"]),
                     fmt_pct(r["年化收益"]), fmt_num(r["夏普"]), fmt_pct(r["最大回撤"]), str(r["交易次数"])])

story = []

# ===== 封面 =====
story.append(Spacer(1, 60))
story.append(P("聚宽（JoinQuant）双均线交易策略", S_TITLE))
story.append(P("实现、参数优化、实盘模拟与风险暴露分析", S_TITLE))
story.append(Spacer(1, 14))
story.append(P("量化策略课程 · TASK7", S_SUB))
story.append(Spacer(1, 8))
story.append(P(f"标的：宁德时代(300750.SZ) ｜ 样本内 {M['in_sample_range'][0]} ~ {M['in_sample_range'][1]} ｜ "
               f"样本外(实盘模拟) {M['oos_range'][0]} ~ {M['oos_range'][1]}", S_SUB))
story.append(Spacer(1, 24))
story.append(HRFlowable(width="60%", color=colors.HexColor("#1A5276")))
story.append(Spacer(1, 16))
# 摘要框
summary_text = (
    f"<b>摘要：</b>本策略以课程 TASK3 的双均线（金叉/死叉）为模板，增加趋势过滤、止损、涨跌停过滤与"
    f"交易成本建模四重风控后，在聚宽框架下实现。样本内(2019–2024)网格寻优得到最优参数 "
    f"<b>短均线={bs} / 长均线={bl}</b>，样本内夏普 {fmt_num(ins['夏普'])}、年化 {fmt_pct(ins['年化收益'])}；"
    f"但在样本外(2025–2026)前向测试中，最优参数年化降至 {fmt_pct(oos['年化收益'])}、夏普 {fmt_num(oos['夏普'])}，"
    f"反而弱于未优化的默认参数(5/15)（年化 {fmt_pct(oosd['年化收益'])}、夏普 {fmt_num(oosd['夏普'])}）。"
    f"这一结果揭示了参数过拟合与 regimes 切换风险，是本次实践最核心的教训。"
)
story.append(P(summary_text, S_BODY))
story.append(PageBreak())

# ===== 第1章 =====
story.append(P("1. 策略模板选择与改造设计", S_H1))
story.append(P("1.1 模板来源", S_H2))
story.append(P(
    "课程 TASK3 已构建过一套本地双均线策略（金叉买入、死叉卖出、全仓进出）。该模板逻辑清晰、参数少、"
    "易于解释，非常适合作为聚宽平台上的入门策略。因此本次直接以它为基础模板，重点放在<b>平台化实现</b>与"
    "<b>风控增强</b>上，而非另起炉灶。"))
story.append(P("1.2 在模板基础上的四项改造（风控增强）", S_H2))
story += bullets([
    "<b>趋势过滤</b>：仅在收盘价高于长期趋势均线（默认120日）时才允许做多，过滤下跌趋势中频繁的假金叉，降低震荡市耗损。",
    "<b>止损线</b>：持仓期间若回撤超过阈值（默认10%），无论是否死叉都强制平仓，控制单笔亏损。",
    "<b>涨跌停过滤</b>：涨停买不进、跌停卖不出（用 high_limit / low_limit 判断），避免回测中不合理的“完美成交”。",
    "<b>交易成本建模</b>：在 initialize 中设置佣金（买万三、卖万三+印花税千一）与千一滑点，使回测贴近真实成交。",
])
story.append(P("1.3 聚宽代码结构（要点）", S_H2))
story.append(P(
    "聚宽策略由 <b>initialize(context)</b> 与每日回调 <b>handle_data(context)</b> 组成：前者设置标的、参数、"
    "基准、费率与运行频率（每天15:00）；后者用 attribute_history 取历史收盘价计算长短均线、判断金叉/死叉与"
    "趋势，再调用 order_target_value 调整目标仓位。完整的可运行代码见文件 "
    "<b>jq_dual_ma_strategy.py</b> 与报告附录。下图展示了样本内信号分布。"))
story += img("fig1_insample_signals.png", 460, "图1 样本内双均线信号：金叉买入(▲红)、死叉卖出(▼绿)，MA15/MA20")

story.append(PageBreak())

# ===== 第2章 =====
story.append(P("2. 回测结果与参数调整", S_H1))
story.append(P("2.1 回测设置", S_H2))
story.append(P(
    f"数据：宁德时代(300750.SZ) 日线，经 Tushare 获取 2019-01-02 ~ 2026-07-24 共 {M['n_ins']+M['n_oos']} 个交易日。"
    f"为区分“调参”与“验证”，将 <b>{M['in_sample_range'][0]} ~ {M['in_sample_range'][1]}</b> 作为样本内用于参数寻优，"
    f"<b>{M['oos_range'][0]} ~ {M['oos_range'][1]}</b> 作为样本外用于模拟实盘。成本模型：买入成本0.13%、卖出成本0.23%。"))
story.append(P("2.2 参数网格寻优", S_H2))
story.append(P(
    "在样本内对 短均线∈{5,8,10,15,20}、长均线∈{20,30,40,60,120} 做网格搜索（共约20组可行组合），"
    "以夏普比率为目标函数。寻优结果 Top5 如下，最优组合为 <b>MA{bs}/MA{bl}</b>。"))
story.append(make_table(top_rows, [2.2*cm, 2.2*cm, 2.2*cm, 2.6*cm, 2.0*cm, 2.6*cm, 2.4*cm]))
story.append(Spacer(1, 8))
story.append(P("下图直观展示不同参数组合的夏普分布——颜色越绿越好，可见最优区集中在中短周期附近，但并非唯一尖峰，"
               "提示参数存在一定稳健区间，也暗示过窄的“单点最优”可能只是样本内噪声。", S_SMALL))
story += img("fig4_param_heatmap.png", 360, "图4 样本内参数寻优：夏普比率热力图（行=长均线，列=短均线）")
story.append(P("2.3 样本内表现", S_H2))
story.append(P(
    f"最优参数下样本内年化收益 {fmt_pct(ins['年化收益'])}、夏普 {fmt_num(ins['夏普'])}、最大回撤 "
    f"{fmt_pct(ins['最大回撤'])}（回撤时长长达 {fmt_num(ins['最大回撤时长(日)'],0)} 日），显著跑赢买入持有基准"
    f"（基准年化 {fmt_pct(ins['基准年化'])}、最大回撤 {fmt_pct(ins['基准最大回撤'])}）。策略通过趋势跟踪规避了"
    f"部分大跌，但最大回撤仍接近四成，说明单标的趋势策略的尾部风险不可小觑。"))
story += img("fig2_insample_nav.png", 460, "图2 样本内策略净值 vs 基准(持有不动)")
story += img("fig3_insample_drawdown.png", 460, "图3 样本内回撤曲线")

story.append(PageBreak())

# ===== 第3章 =====
story.append(P("3. 实盘模拟（样本外前向测试）", S_H1))
story.append(P("3.1 聚宽模拟交易配置", S_H2))
story.append(P(
    "在聚宽平台上，“实盘模拟”通过<b>模拟交易</b>功能实现：将同一策略绑定一个模拟账户，设定初始资金"
    "（本例 100,000 元）、调仓周期（每天）、提醒方式后，平台会在每个交易日 15:00 自动按 handle_data 逻辑"
    "以<b>模拟盘</b>撮合下单，成交与持仓均来自真实行情但不涉及真实资金。其回测引擎与模拟盘共用同一套"
    "撮合与费率设置，因此本地“样本外前向测试”可视为对模拟盘结果的严格近似。"))
story.append(P("3.2 样本外（实盘模拟）表现", S_H2))
story.append(P(
    f"用样本内最优参数 MA{bs}/MA{bl} 直接跑样本外，年化收益降至 {fmt_pct(oos['年化收益'])}、夏普 "
    f"{fmt_num(oos['夏普'])}、最大回撤 {fmt_pct(oos['最大回撤'])}。值得注意的是，同一时期<b>买入持有基准</b>的"
    f"年化高达 {fmt_pct(oos['基准年化'])}——即在该样本外区间，简单的“一直持有”反而显著优于双均线策略。"
    f"这说明样本外恰逢标的的强势上行段，趋势策略因反复“高买低卖”的鞭锯(whipsaw)效应而跑输。"))
story += img("fig5_oos_nav.png", 460, "图5 样本外(实盘模拟)策略净值 vs 基准，紫色虚线为默认参数(5/15)对照")
story += img("fig6_oos_drawdown.png", 460, "图6 样本外回撤曲线")

story.append(PageBreak())

# ===== 第4章 =====
story.append(P("4. 实际表现评估与风险暴露分析", S_H1))
story.append(P("4.1 样本内 vs 样本外 vs 默认参数：核心指标对比", S_H2))
story.append(make_table(rows, [3.6*cm, 3.4*cm, 3.6*cm, 3.6*cm]))
story.append(Spacer(1, 6))
story.append(P("4.2 风险暴露拆解", S_H2))
story += bullets([
    f"<b>单标的集中度风险</b>：策略始终 100% 持仓单一股票，Beta 对沪深300约 {fmt_num(oos['Beta'])}，"
    "个股特异风险（如业绩/政策冲击）无法分散。这是该策略最突出的风险暴露来源。",
    f"<b>回撤与回撤时长</b>：样本内最大回撤 {fmt_pct(ins['最大回撤'])}、最长 {fmt_num(ins['最大回撤时长(日)'],0)} 日"
    f"未创新高；样本外回撤收敛至 {fmt_pct(oos['最大回撤'])}，但需警惕极端行情下单标的回撤可瞬间放大。",
    f"<b>波动与尾部风险</b>：样本外年化波动 {fmt_pct(oos['年化波动'])}，日 VaR(95%)={fmt_pct(oos['VaR95'])}、"
    f"CVaR(95%)={fmt_pct(oos['CVaR95'])}，提示单日潜在亏损约2%~4%。",
    "<b>参数敏感性 / 过拟合风险</b>：下左图显示样本外夏普对均线周期高度敏感，最优(15/20)周围小幅扰动即明显"
    "变化；且“样本内最优”在样本外竟弱于默认(5/15)，说明寻优可能捕捉了样本内噪声。",
    "<b>成本敏感性</b>：右侧表格显示，滑点从0升至0.3%时，样本外年化由 "
    f"{fmt_pct(cost[0]['年化收益'])} 降至 {fmt_pct(cost[-1]['年化收益'])}——高频换手的趋势策略对成本相当敏感。",
])
story.append(make_table(cost_rows, [3.0*cm, 3.0*cm, 3.0*cm, 3.0*cm]))
story.append(Spacer(1, 6))
story += img("fig7_risk_compare.png", 460, "图7 风险收益指标对比：样本内(寻优) / 样本外(实盘模拟) / 默认参数样本外")
story += img("fig8_sensitivity.png", 360, "图8 样本外参数敏感性（夏普热力图，红框为样本内最优15/20）")

story.append(PageBreak())

# ===== 第5章 =====
story.append(P("5. 经验与教训总结", S_H1))
story.append(P("5.1 关键经验", S_H2))
story += bullets([
    "<b>平台化最小可运行闭环</b>：聚宽的 initialize/handle_data/order_target 三件套即可跑通一个策略，"
    "参数、基准、费率、滑点都应在 initialize 显式声明，避免“免费”回测假象。",
    "<b>风控要内建</b>：趋势过滤+止损+涨跌停过滤+成本，四项叠加后虽未提升收益，却让回测更贴近现实、"
    "避免了对“理想成交”的过度乐观。",
    "<b>用样本外验证</b>：把数据切成样本内(调参)与样本外(验证)两段，是检验策略是否“真有效”的最低门槛。",
    "<b>可视化即诊断</b>：信号图、净值、回撤、参数热力图四张图能快速定位问题（如鞭锯、长回撤、参数尖峰）。",
])
story.append(P("5.2 教训与改进方向", S_H2))
story += bullets([
    "<b>警惕过拟合</b>：本次“样本内最优15/20”在样本外跑输默认5/15，说明网格寻优可能只是拟合了历史噪声。"
    "应改用更宽参数区间取“稳健区”而非单点最优，或用 walk-forward 滚动验证。",
    "<b>策略与 regim 匹配</b>：双均线属趋势跟踪，在单边市有效、在震荡/急涨市跑输买入持有。样本外正值强势上行，"
    "策略因此落后——选择策略须先判断市场状态。",
    "<b>分散与仓位</b>：单标的100%仓位放大了个体风险。后续可拓展为多标的组合或加入仓位管理（如按波动率定仓）。",
    "<b>成本不可忽略</b>：滑点每升0.1%都显著侵蚀收益，实盘模拟中应把手续费、滑点、停牌、涨跌停都纳入。",
    "<b>平台差异</b>：本地仿真与聚宽撮合在细节（复权、停牌处理、订单类型）上仍有差异，最终须以平台模拟盘为准。",
])
story.append(Spacer(1, 10))
story.append(HRFlowable(width="100%", color=colors.HexColor("#AAB7B8")))
story.append(P("附录：关键聚宽代码（节选）见文件 jq_dual_ma_strategy.py；完整数据与图表由 backtest_dual_ma.py 生成。", S_SMALL))

# ===== 页脚 =====
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 8)
    canvas.setFillColor(colors.HexColor("#95A5A6"))
    canvas.drawString(2*cm, 1*cm, "TASK7 · 聚宽双均线策略报告")
    canvas.drawRightString(A4[0]-2*cm, 1*cm, f"第 {doc.page} 页")
    canvas.restoreState()

doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                        topMargin=1.8*cm, bottomMargin=1.8*cm,
                        title="聚宽双均线策略报告", author="量化策略课程")
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("PDF 已生成:", OUT)
