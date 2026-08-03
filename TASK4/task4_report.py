#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK4 PDF 报告生成脚本
====================
使用 reportlab 生成「夏阳+TASK4.pdf」，内容覆盖：
  一、海龟策略理论基础
  二、核心概念解析（高低点通道 / ATR / 止损条件）
  三、回测结果与可视化（宁德时代 N=20）
  四、参数优化与多周期对比
  五、多股票对比分析
  六、总结与心得
指标数值由 task4_turtle 实时计算，确保与图表一致。
"""

import os
import importlib.util

# 动态导入同目录下的 task4_turtle（仅取函数，不执行其 main）
_spec = importlib.util.spec_from_file_location(
    "task4_turtle", os.path.join(os.path.dirname(os.path.abspath(__file__)), "task4_turtle.py"))
_t = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_t)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                 Table, TableStyle, PageBreak)

# ===== 字体注册 =====
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("ArialUnicode", FONT_PATH))

# ===== 配色（与 TASK3 一致）=====
COLOR_UP = HexColor("#E74C3C")    # 红
COLOR_DOWN = HexColor("#27AE60")  # 绿
COLOR_TITLE = HexColor("#2C3E50")
COLOR_SUBTITLE = HexColor("#34495E")
COLOR_ACCENT = HexColor("#3498DB")
COLOR_BG = HexColor("#ECF0F1")
COLOR_PURPLE = HexColor("#8E44AD")

# ===== 路径 =====
BASE_DIR = "/Users/wangyanfen/Desktop/量化策略课程"
TASK4_DIR = os.path.join(BASE_DIR, "TASK4")
PDF_OUTPUT = os.path.join(TASK4_DIR, "夏阳+TASK4.pdf")

# ===== 样式 =====
styles = getSampleStyleSheet()

style_title = ParagraphStyle("CustomTitle", parent=styles["Title"],
    fontName="ArialUnicode", fontSize=22, leading=28,
    textColor=COLOR_TITLE, alignment=TA_CENTER, spaceAfter=20)
style_subtitle = ParagraphStyle("CustomSubtitle", parent=styles["Heading1"],
    fontName="ArialUnicode", fontSize=16, leading=22,
    textColor=COLOR_SUBTITLE, alignment=TA_LEFT, spaceBefore=16, spaceAfter=10)
style_heading2 = ParagraphStyle("CustomH2", parent=styles["Heading2"],
    fontName="ArialUnicode", fontSize=13, leading=18,
    textColor=COLOR_ACCENT, alignment=TA_LEFT, spaceBefore=10, spaceAfter=6)
style_body = ParagraphStyle("CustomBody", parent=styles["Normal"],
    fontName="ArialUnicode", fontSize=10.5, leading=16,
    textColor=black, alignment=TA_JUSTIFY, spaceBefore=4, spaceAfter=4)
style_bullet = ParagraphStyle("CustomBullet", parent=style_body,
    leftIndent=20, bulletIndent=10)
style_center = ParagraphStyle("CustomCenter", parent=style_body,
    alignment=TA_CENTER)
style_small = ParagraphStyle("CustomSmall", parent=style_body,
    fontSize=9, leading=13)


def add_image(story, img_path, width=16*cm, height=9*cm, caption=None):
    if os.path.exists(img_path):
        img = Image(img_path, width=width, height=height)
        story.append(img)
        if caption:
            story.append(Paragraph(caption, style_center))
        story.append(Spacer(1, 8))


def make_table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), "ArialUnicode"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#BDC3C7")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        style_cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
        ]
    t.setStyle(TableStyle(style_cmds))
    return t


def pct(x):
    return f"{x:.2%}"


# ========================================================================
# 实时计算指标（保证与图表一致）
# ========================================================================
def compute_all():
    N = _t.DEFAULT_N
    # 核心案例
    nd = _t.load_stock_data(_t.STOCK_FILES["宁德时代"]["path"])
    nd_sig = _t.calc_turtle_signals(nd, N, N // 2)
    nd_bt = _t.turtle_backtest(nd_sig)
    core = _t.calc_metrics(nd_bt)

    # 多参数
    params = []
    for n in _t.PARAM_N_LIST:
        m = n // 2
        s = _t.calc_turtle_signals(nd, n, m)
        b = _t.turtle_backtest(s)
        mm = _t.calc_metrics(b)
        params.append({"N": n, "M": m, **mm})

    # 多股票
    stocks = {}
    for sk in ["宁德时代", "平安银行", "贵州茅台", "五粮液"]:
        s = _t.calc_turtle_signals(_t.load_stock_data(_t.STOCK_FILES[sk]["path"]), N, N // 2)
        b = _t.turtle_backtest(s)
        stocks[sk] = _t.calc_metrics(b)

    return core, params, stocks


# ========================================================================
# 主流程：生成 PDF
# ========================================================================
def main():
    core, params, stocks = compute_all()

    doc = SimpleDocTemplate(PDF_OUTPUT, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
        title="夏阳+TASK4 - 海龟交易策略报告", author="夏阳")
    story = []
    avail = A4[0] - 4*cm

    # ===== 封面 =====
    story.append(Spacer(1, 60))
    story.append(Paragraph("量化策略课程", style_title))
    story.append(Spacer(1, 10))
    story.append(Paragraph("TASK4 - 海龟交易策略：通道突破、ATR 与纪律化风控", style_subtitle))
    story.append(Spacer(1, 20))
    story.append(Paragraph("作者：夏阳", style_center))
    story.append(Paragraph("日期：2026年7月9日", style_center))
    story.append(PageBreak())

    # ===== 第一章：理论基础 =====
    story.append(Paragraph("一、海龟策略理论基础", style_subtitle))
    story.append(Paragraph("1.1 策略起源", style_heading2))
    story.append(Paragraph(
        "海龟交易策略源自 1983 年 Richard Dennis 与 William Eckhardt 的一场著名实验："
        "两人为验证\"交易能否被传授\"，招募并培训了一批学员（\"海龟\"），"
        "传授一套完整、机械化的趋势跟随交易规则。结果证明，严格遵循规则的人普遍取得了优异回报，"
        "从而确立了\"交易系统可复制、可执行\"的理念。", style_body))

    story.append(Paragraph("1.2 核心思想", style_heading2))
    story.append(Paragraph(
        "海龟策略的本质是<b>趋势跟随（Trend Following）</b>，由三大支柱构成：<br/>"
        "① <b>唐奇安通道突破</b>——以 N 日高低点通道作为\"趋势开关\"，突破高点则顺势入场；<br/>"
        "② <b>ATR 波动率归一化仓位</b>——用平均真实波幅统一衡量波动，使每笔交易承担的风险相同；<br/>"
        "③ <b>2×ATR 严格机械止损</b>——截断亏损、让利润奔跑，把单笔最大亏损锁死在权益的 1%~2%。<br/>"
        "三者结合，形成\"突破买入—持有—止损/破低卖出\"的规则化闭环。", style_body))

    story.append(Paragraph("1.3 关键优势", style_heading2))
    story.append(Paragraph("• <b>规则机械化、可复制</b>：买卖信号完全由公式决定，杜绝主观判断与情绪干扰<br/>"
        "• <b>风控量化</b>：ATR 同时决定\"买多少\"与\"亏多少\"，单笔风险恒定，资金曲线平滑<br/>"
        "• <b>顺势而为</b>：在中长期强趋势中能完整捕获主升/主跌浪，赔率优势明显<br/>"
        "• <b>系统稳健</b>：可多品种、多周期分散，降低对单一行情的依赖<br/>"
        "• <b>易于扩展</b>：可叠加做空、金字塔加仓与双系统过滤，持续增强适应性", style_bullet))

    # ===== 第二章：核心概念 =====
    story.append(Paragraph("二、核心概念解析", style_subtitle))
    story.append(Paragraph("2.1 高低点通道（唐奇安通道 Donchian Channel）", style_heading2))
    story.append(Paragraph(
        "上轨 = 前 N 日最高价的最大值；下轨 = 前 M 日最低价的最小值（M 通常取 N 的一半）。"
        "通道是海龟的\"择时开关\"：<b>价格突破上轨</b>意味着短期动能强于过去 N 日，趋势可能启动，触发<b>买入</b>；"
        "<b>价格跌破下轨</b>意味着趋势可能终结，触发<b>卖出</b>。"
        "本任务取 N=20（对应系统1），M=10。通道越宽，信号越少但趋势越可靠。", style_body))

    story.append(Paragraph("2.2 平均真实波幅（ATR, Average True Range）", style_heading2))
    story.append(Paragraph(
        "真实波幅 TR = max(最高价−最低价, |最高价−昨收|, |最低价−昨收|)，"
        "它比普通振幅更能反映\"跳空\"带来的真实波动。ATR 为 TR 的平滑均值（本任务用 Wilder 指数平滑，周期与 N 一致）。"
        "ATR 在海龟中有<b>双重作用</b>：<br/>"
        "① <b>定仓位</b>：股数 = 1%权益 ÷ ATR，波动越大买得越少，使每笔风险一致；<br/>"
        "② <b>定止损</b>：止损距离 = 2×ATR，波动大则止损宽松、波动小则紧凑，贴合标的个性。", style_body))

    story.append(Paragraph("2.3 止损条件（2×ATR）", style_heading2))
    story.append(Paragraph(
        "持仓期间，若当日最低价 ≤ 买入价 − 2×ATR，立即以止损价离场，锁定单笔最大亏损。"
        "这是海龟\"截断亏损\"纪律的基石——不管基本面如何、不论亏损多少，规则触发即执行，"
        "避免在亏损头寸上犹豫而酿成巨亏。本任务采用<b>盘中触及即止损</b>建模，更贴近真实风控。", style_body))

    # ===== 第三章：回测结果 =====
    story.append(Paragraph("三、回测结果与可视化（宁德时代 N=20/M=10）", style_subtitle))
    story.append(Paragraph("3.1 核心指标", style_heading2))
    metrics_data = [
        ["指标", "数值", "说明"],
        ["累计回报", pct(core["cumulative_return"]), "策略总收益（A）"],
        ["年化收益率", pct(core["annual_return"]), "折算为年化"],
        ["最大回撤 MDD", pct(core["mdd"]), "最大亏损幅度"],
        ["夏普比率", f"{core['sharpe']:.2f}", "风险调整后收益"],
        ["买入 / 卖出次数", f"{core['buy_count']} / {core['sell_count']}",
         f"其中止损 {core['stop_count']} 次、破低 {core['channel_count']} 次"],
        ["基准回报（买入持有）", pct(core["benchmark_return"]), "同期 buy&hold 收益"],
        ["基准最大回撤", pct(core["benchmark_mdd"]), "买入持有的最大回撤"],
    ]
    story.append(make_table(metrics_data, col_widths=[4*cm, 4*cm, 8*cm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "本周期宁德时代虽整体上行（买入持有 +42.96%），但中途经历长段震荡，"
        "海龟以 20/10 通道进出，首笔成功捕获约 +5.6% 的升浪，"
        "后续在 350~470 区间反复假突破而被 2×ATR 止损与 10 日破低频繁洗出，最终微亏。"
        "但其<b>最大回撤仅 −10.17%</b>，远优于买入持有的 −18.46%，体现了风控价值。", style_body))
    story.append(Spacer(1, 6))

    story.append(Paragraph("3.2 可视化图表", style_heading2))
    add_image(story, os.path.join(TASK4_DIR, "图1_股价_唐奇安通道_信号.png"),
              width=avail, height=avail*0.5, caption="图1：宁德时代股价与唐奇安通道及买卖信号")
    add_image(story, os.path.join(TASK4_DIR, "图2_策略净值曲线.png"),
              width=avail, height=avail*0.45, caption="图2：策略净值与基准净值对比")
    story.append(PageBreak())
    add_image(story, os.path.join(TASK4_DIR, "图3_回撤曲线.png"),
              width=avail, height=avail*0.4, caption="图3：策略回撤曲线与最大回撤标注")
    add_image(story, os.path.join(TASK4_DIR, "图4_综合面板.png"),
              width=avail, height=avail*0.85, caption="图4：海龟策略综合面板（价格/通道/ATR/净值/回撤）")

    # ===== 第四章：参数优化 =====
    story.append(PageBreak())
    story.append(Paragraph("四、参数优化与多周期对比", style_subtitle))
    story.append(Paragraph(
        "通道周期 N 直接决定策略的灵敏度与交易频率。我们对比 N=10（灵敏）、N=20（标准）、N=55（长周期）三种设定：",
        style_body))
    pdata = [["通道参数", "累计回报", "年化收益", "最大回撤MDD", "夏普比率", "买卖次数", "止损/破低"]]
    for m in params:
        pdata.append([f"N{m['N']}/M{m['M']}", pct(m["cumulative_return"]), pct(m["annual_return"]),
                      pct(m["mdd"]), f"{m['sharpe']:.2f}",
                      f"{m['buy_count']}/{m['sell_count']}",
                      f"{m['stop_count']}/{m['channel_count']}"])
    story.append(make_table(pdata, col_widths=[3*cm, 2.4*cm, 2.4*cm, 2.6*cm, 2.2*cm, 2.4*cm, 2.4*cm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "• <b>N=10/M=5</b> 最灵敏，交易最多（8 买/8 卖），回撤最小（−6.06%），累计 +3.03%，为三者最优——"
        "说明本周期行情偏短波段，短通道更契合；<br/>"
        "• <b>N=20/M=10</b> 交易中等（5 买/5 卖），但因恰逢中段长震荡，被洗出而微亏；<br/>"
        "• <b>N=55/M=27</b> 信号极少（仅 2 次），在缺乏长趋势的本周期同样失效（−1.49%）。<br/>"
        "结论：<b>没有万能参数</b>，参数须匹配标的的波动特性与趋势长度；本周期趋势强度不足，长周期并无优势。",
        style_body))
    story.append(Spacer(1, 6))
    add_image(story, os.path.join(TASK4_DIR, "图5_多参数对比.png"),
              width=avail, height=avail*0.8, caption="图5：宁德时代多通道周期策略对比")

    # ===== 第五章：多股票对比 =====
    story.append(PageBreak())
    story.append(Paragraph("五、多股票对比分析", style_subtitle))
    story.append(Paragraph(
        "同一海龟参数（N=20/M=10）应用于四类代表性股票，并与其买入持有基准对照：", style_body))
    sdata = [["股票", "海龟累计回报", "海龟MDD", "海龟夏普", "基准回报", "基准MDD", "买卖次数"]]
    for sk in ["宁德时代", "平安银行", "贵州茅台", "五粮液"]:
        m = stocks[sk]
        sdata.append([sk, pct(m["cumulative_return"]), pct(m["mdd"]), f"{m['sharpe']:.2f}",
                      pct(m["benchmark_return"]), pct(m["benchmark_mdd"]),
                      f"{m['buy_count']}/{m['sell_count']}"])
    story.append(make_table(sdata, col_widths=[2.6*cm, 2.8*cm, 2.2*cm, 2.0*cm, 2.4*cm, 2.2*cm, 2.4*cm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "关键发现——海龟的核心价值在于<b>下行风控</b>：<br/>"
        "• 在<b>下跌/震荡的三只股票</b>（平安银行、贵州茅台、五粮液）上，海龟将买入持有的损失"
        "从 16%~39% 大幅压缩到 3%~6%，回撤远小于基准（如五粮液：海龟 −3.96% vs 基准 −39.19%）；<br/>"
        "• 在<b>单边上行且中途震荡的宁德时代</b>上，因 10 日退出通道偏紧、且本实现仅做多，"
        "策略反复止损/假突破，未能吃满 +42.96% 的主升浪，最终微亏；<br/>"
        "• 说明海龟是\"<b>风控优先的趋势跟随</b>\"策略：其优势常在\"少亏\"而非\"多赚\"，"
        "在趋势不明的震荡市中，空仓与严格止损反而是最优解。", style_body))
    story.append(Spacer(1, 6))
    add_image(story, os.path.join(TASK4_DIR, "图6_多股票对比.png"),
              width=avail, height=avail*0.8, caption="图6：海龟策略(N=20/M=10) 多股票净值对比")
    add_image(story, os.path.join(TASK4_DIR, "图7_多股票指标柱状图.png"),
              width=avail, height=avail*0.4, caption="图7：多股票指标对比柱状图")

    # ===== 第六章：总结 =====
    story.append(PageBreak())
    story.append(Paragraph("六、总结与心得", style_subtitle))
    story.append(Paragraph("6.1 海龟法则的适应场景", style_heading2))
    story.append(Paragraph(
        "1. <b>趋势清晰且持续的阶段</b>：当价格呈现持续上升或下降趋势时，通道突破能准确捕捉方向，"
        "策略收益显著（如本周期首笔 +5.6% 的升浪）；<br/>"
        "2. <b>高波动成长股</b>：波动率大、趋势性强的品种，通道信号更可靠，ATR 仓位管理也能充分发挥；<br/>"
        "3. <b>需要严控回撤的资金</b>：海龟以 1% 风险单位与 2×ATR 止损锁定下行，适合风险偏好较低的账户。",
        style_body))
    story.append(Paragraph("6.2 海龟法则的不适用场景", style_heading2))
    story.append(Paragraph(
        "1. <b>横盘震荡市</b>：价格在区间内来回，通道频繁假突破，反复止损导致磨损（本周期中段即如此）；<br/>"
        "2. <b>低波动价值股</b>：方向性趋势不显著，突破信号稀缺且易失败；<br/>"
        "3. <b>单边下行市（仅做多版本）</b>：本实现为多头策略，下跌市只能空仓避险，无法像做空那样获利，"
        "需扩展空头逻辑或接受低收益。", style_body))
    story.append(Paragraph("6.3 实践心得", style_heading2))
    story.append(Paragraph(
        "1. 海龟本质是<b>\"风控优先的趋势跟随\"</b>，其价值常在\"少亏\"而非\"多赚\"——评估时 MDD 与夏普比累计回报更重要；<br/>"
        "2. <b>ATR 是海龟的灵魂</b>：它同时管理人\"买多少\"（仓位）与\"亏多少\"（止损），是整套系统的波动标尺；<br/>"
        "3. 参数需匹配标的波动特性，<b>没有万能参数</b>；短周期灵敏但易洗，长周期稳健但信号少；<br/>"
        "4. 在应用前应先判断当前市场是否处于趋势阶段，避免在震荡市硬套突破策略；<br/>"
        "5. 可扩展方向：加入<b>做空</b>、<b>金字塔加仓</b>（0.5×ATR 递增、最多 4 单位）、"
        "<b>双系统 S1/S2 过滤</b>，以进一步提升对不同市况的适应力；<br/>"
        "6. 纪律胜过聪明——海龟实验的终极启示是：<b>严格、机械地执行规则</b>，比预测市场更能稳定盈利。",
        style_body))

    doc.build(story)
    print(f"PDF 报告已生成: {PDF_OUTPUT}")


if __name__ == "__main__":
    main()
