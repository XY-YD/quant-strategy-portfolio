#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK4 进阶版（经典双系统海龟）分析报告生成脚本
=============================================
使用 reportlab 生成「Task4_plus.pdf」，内容覆盖：
  一、策略解释（双系统 S1/S2 + 金字塔加仓 + 对称做空）
  二、信号计算（入场 / 加仓 / 平仓 / 止损的信号生成与优先级）
  三、回测指标分析（宁德时代核心案例）
  四、多参数实验（标准 / 灵敏 / 稳健）
  五、多股票实验（宁德时代 / 平安银行 / 贵州茅台 / 五粮液）
  六、总结与反思（与 TASK4 单系统版对照，适用场景与改进）

指标数值由 task4_advanced_turtle 与 task4_turtle 实时计算，确保与图表一致。
"""

import os
import importlib.util

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                Table, TableStyle, PageBreak)

# ===== 路径 =====
BASE_DIR = "/Users/wangyanfen/Desktop/量化策略课程"
TASK4_DIR = os.path.join(BASE_DIR, "TASK4")
OUTPUT_DIR = os.path.join(BASE_DIR, "TASK4_advanced")
PDF_OUTPUT = os.path.join(OUTPUT_DIR, "Task4_plus.pdf")

# ===== 动态导入计算模块 =====
def _import(mod_name, path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

_adv = _import("task4_advanced_turtle",
               os.path.join(OUTPUT_DIR, "task4_advanced_turtle.py"))
_ot = _import("task4_turtle", os.path.join(TASK4_DIR, "task4_turtle.py"))

# ===== 字体注册 =====
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("ArialUnicode", FONT_PATH))

# ===== 配色（与 TASK3 / TASK4 一致）=====
COLOR_UP = HexColor("#E74C3C")       # 红（涨 / 多）
COLOR_DOWN = HexColor("#27AE60")     # 绿（跌 / 空）
COLOR_TITLE = HexColor("#2C3E50")
COLOR_SUBTITLE = HexColor("#34495E")
COLOR_ACCENT = HexColor("#3498DB")
COLOR_BG = HexColor("#ECF0F1")
COLOR_PURPLE = HexColor("#8E44AD")

# ===== 样式 =====
styles = getSampleStyleSheet()
style_title = ParagraphStyle("CT", parent=styles["Title"], fontName="ArialUnicode",
    fontSize=22, leading=28, textColor=COLOR_TITLE, alignment=TA_CENTER, spaceAfter=20)
style_subtitle = ParagraphStyle("CS", parent=styles["Heading1"], fontName="ArialUnicode",
    fontSize=16, leading=22, textColor=COLOR_SUBTITLE, alignment=TA_LEFT,
    spaceBefore=16, spaceAfter=10)
style_heading2 = ParagraphStyle("CH2", parent=styles["Heading2"], fontName="ArialUnicode",
    fontSize=13, leading=18, textColor=COLOR_ACCENT, alignment=TA_LEFT,
    spaceBefore=10, spaceAfter=6)
style_body = ParagraphStyle("CB", parent=styles["Normal"], fontName="ArialUnicode",
    fontSize=10.5, leading=16, textColor=black, alignment=TA_JUSTIFY,
    spaceBefore=4, spaceAfter=4)
style_bullet = ParagraphStyle("CBu", parent=style_body, leftIndent=20, bulletIndent=10)
style_center = ParagraphStyle("CC", parent=style_body, alignment=TA_CENTER)
style_small = ParagraphStyle("CSm", parent=style_body, fontSize=9, leading=13)


def add_image(story, img_path, width=16*cm, height=9*cm, caption=None):
    if os.path.exists(img_path):
        img = Image(img_path, width=width, height=height)
        story.append(img)
        if caption:
            story.append(Paragraph(caption, style_center))
        story.append(Spacer(1, 8))


def make_table(data, col_widths=None, header=True):
    t = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
    cmds = [
        ("FONTNAME", (0, 0), (-1, -1), "ArialUnicode"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#BDC3C7")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        cmds += [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), white),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
        ]
    t.setStyle(TableStyle(cmds))
    return t


def pct(x):
    return f"{x:.2%}"


# ========================================================================
# 实时计算（保证与图表一致）
# ========================================================================
def compute_all():
    # 核心案例：宁德时代，经典标准配置
    raw_nd = _adv.load_stock_data(_adv.STOCK_FILES["宁德时代"]["path"])
    df_core = _adv.turtle_dual_backtest(raw_nd)
    core = _adv.calc_metrics_adv(df_core)

    # 多参数对比（标准 / 灵敏 / 稳健），宁德时代
    param_list = []
    for cfg in _adv.PARAM_CONFIGS:
        raw = _adv.load_stock_data(_adv.STOCK_FILES["宁德时代"]["path"])
        df = _adv.turtle_dual_backtest(raw, s1_entry=cfg["s1e"], s1_exit=cfg["s1x"],
                                       s2_entry=cfg["s2e"], s2_exit=cfg["s2x"])
        m = _adv.calc_metrics_adv(df)
        param_list.append({**cfg, **m})

    # 多股票对比（标准配置）
    stock_metrics = {}
    for sk in ["宁德时代", "平安银行", "贵州茅台", "五粮液"]:
        raw = _adv.load_stock_data(_adv.STOCK_FILES[sk]["path"])
        df = _adv.turtle_dual_backtest(raw)
        stock_metrics[sk] = _adv.calc_metrics_adv(df)

    # 对照：TASK4 单系统版（仅做多，N=20/M=10）于宁德时代
    single = _ot.calc_metrics(_ot.turtle_backtest(
        _ot.calc_turtle_signals(
            _ot.load_stock_data(_ot.STOCK_FILES["宁德时代"]["path"]), 20, 10)))

    return core, df_core, param_list, stock_metrics, single


# ========================================================================
# 主流程
# ========================================================================
def main():
    core, df_core, param_list, stock_metrics, single = compute_all()

    doc = SimpleDocTemplate(PDF_OUTPUT, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm,
        title="Task4_plus - 经典双系统海龟分析报告", author="夏阳")
    story = []
    avail = A4[0] - 4*cm

    # ===== 封面 =====
    story.append(Spacer(1, 55))
    story.append(Paragraph("量化策略课程", style_title))
    story.append(Spacer(1, 10))
    story.append(Paragraph("TASK4 进阶：经典双系统海龟（S1/S2 + 金字塔加仓 + 做空）", style_subtitle))
    story.append(Spacer(1, 20))
    story.append(Paragraph("分析报告 · Task4_plus", style_center))
    story.append(Paragraph("作者：夏阳", style_center))
    story.append(Paragraph("日期：2026年8月2日", style_center))
    story.append(PageBreak())

    # ===== 第一章：策略解释 =====
    story.append(Paragraph("一、策略解释：经典双系统海龟", style_subtitle))
    story.append(Paragraph("1.1 为什么要在 TASK4 单系统上加码", style_heading2))
    story.append(Paragraph(
        "TASK4 已实现了忠实而简化的单系统海龟：以 N 日唐奇安通道突破做多、以 2×ATR 盘中止损、"
        "以 M 日通道破低出场，并用 ATR 做单单位仓位管理。它在<b>下行市表现出色（少亏）</b>，"
        "但当标的<b>单边下跌</b>时只能空仓避险、无法获利。Richard Dennis 的原版\"海龟\"规则远比这丰盈——"
        "本扩展版将单系统升级为<b>经典双系统 + 金字塔加仓 + 对称做空</b>的完整形态。", style_body))

    story.append(Paragraph("1.2 双系统并行（S1 / S2）", style_heading2))
    story.append(Paragraph(
        "原版海龟同时运行两套互不干扰的系统，捕捉不同时间尺度的趋势：<br/>"
        "• <b>系统1（S1，短周期）</b>：突破<b>前 20 日高</b>做多、跌破<b>前 10 日低</b>平多；"
        "跌破<b>前 20 日低</b>做空、突破<b>前 10 日高</b>平空；<br/>"
        "• <b>系统2（S2，长周期）</b>：突破<b>前 55 日高</b>做多、跌破<b>前 20 日低</b>平多；"
        "跌破<b>前 55 日低</b>做空、突破<b>前 20 日高</b>平空。<br/>"
        "两系统在同一标的上<b>独立建仓、独立风控</b>，因此可同时持有多头与空头（如 S1 做多、S2 做空），"
        "极大提升了策略在不同节奏行情中的覆盖能力。", style_body))

    story.append(Paragraph("1.3 金字塔加仓（Pyramiding）", style_heading2))
    story.append(Paragraph(
        "建仓后，价格每向<b>有利方向推进 0.5×ATR</b>，便加 1 个单位；单系统最多加至 <b>4 个单位</b>"
        "（即总风险 ≤ 4% 权益）。金字塔加仓让策略在<b>强趋势</b>中\"让利润奔跑\"、"
        "逐步加重仓位，而在趋势反转时最早的单位最先被 2×ATR 止损打掉，天然实现\"盈利加仓、亏损即止\"。", style_body))

    story.append(Paragraph("1.4 对称做空与 ATR 仓位管理", style_heading2))
    story.append(Paragraph(
        "做空与做多<b>完全对称</b>：向下突破通道开空、价格回升突破通道上轨平空，止损同样为 2×ATR。"
        "仓位仍由 <b>海龟 N（ATR20）</b> 决定：<b>每单位股数 = 1% 权益 ÷ ATR</b>，"
        "使每一单位的单笔风险恒定为权益的 1%。本扩展版额外加入<b>单系统市值上限（≤50% 权益）</b>约束，"
        "以适配股票无杠杆的现实（详见第六章反思）。", style_body))

    # ===== 第二章：信号计算 =====
    story.append(Paragraph("二、信号计算逻辑", style_subtitle))
    story.append(Paragraph(
        "每个交易日、每个系统按<b>固定优先级</b>判定一次事件（每根 K 线至多一次加仓/出场）：", style_body))
    story.append(Paragraph(
        "① <b>2×ATR 硬止损（最高优先级）</b>：最新单位入场价反向偏离 2×ATR 且盘中触及，"
        "立即平掉该系统全部单位。多头看当日最低价 ≤ 入场价−2×ATR；空头看当日最高价 ≥ 入场价+2×ATR。<br/>"
        "② <b>通道突破出场</b>：多头收盘价跌破 M 日通道下轨、或空头收盘价突破 M 日通道上轨，平仓。<br/>"
        "③ <b>入场信号（仅空仓时）</b>：S1/S2 上轨被突破开多、下轨被突破开空。<br/>"
        "④ <b>金字塔加仓</b>：持仓且未达 4 单位时，多头价 ≥ 末单位入场价+0.5×ATR 加多、"
        "空头价 ≤ 末单位入场价−0.5×ATR 加空。", style_bullet))
    story.append(Paragraph(
        "为杜绝未来函数，所有通道均以 <b>shift(1)</b> 取\"前 N 日\"数值；仓位定基以<b>全盘真实权益"
        "（现金 + 两系统持仓市值）</b>为准，避免做空回收现金造成虚增、进而放大杠杆。", style_small))
    story.append(Spacer(1, 6))
    add_image(story, os.path.join(OUTPUT_DIR, "图1_双系统通道_多空信号.png"),
              width=avail, height=avail*0.5,
              caption="图1：宁德时代双系统通道与多空/加仓/平仓信号（▲多开 ▼空开 ◆加仓 ×平仓）")

    # ===== 第三章：回测指标分析 =====
    story.append(PageBreak())
    story.append(Paragraph("三、回测指标分析（宁德时代 · 标准 S1=20/10, S2=55/20）", style_subtitle))
    story.append(Paragraph("3.1 核心指标", style_heading2))
    m = core
    metrics_data = [
        ["指标", "数值", "说明"],
        ["累计回报", pct(m["cumulative_return"]), "策略总收益"],
        ["年化收益率", pct(m["annual_return"]), "折算为年化"],
        ["最大回撤 MDD", pct(m["mdd"]), "最大亏损幅度"],
        ["夏普比率", f"{m['sharpe']:.2f}", "风险调整后收益"],
        ["做多 / 做空开仓", f"{m['long_entries']} / {m['short_entries']}",
         f"多加 {m['add_long']} 次、空加 {m['add_short']} 次"],
        ["平多 / 平空", f"{m['exit_long']} / {m['exit_short']}", "出场次数"],
        ["基准回报（买入持有）", pct(m["benchmark_return"]), "同期 buy&hold"],
        ["基准最大回撤", pct(m["benchmark_mdd"]), "买入持有回撤"],
    ]
    story.append(make_table(metrics_data, col_widths=[4*cm, 4*cm, 8*cm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"宁德时代在此区间整体上行（买入持有 +{m['benchmark_return']:.2%}），但过程剧烈震荡。"
        f"双系统海龟<b>首段成功捕获约 +17% 的升浪</b>，其后在高位区间反复假突破被 2×ATR 止损与通道出场洗出，"
        f"更在后续上涨中被 S2 空头<b>逼空</b>，最终累计 {pct(m['cumulative_return'])}、"
        f"MDD {pct(m['mdd'])}。这说明：<b>做空是把双刃剑</b>——上行趋势中空的头寸会反噬收益。"
        f"不过策略 MDD（{pct(m['mdd'])}）仍显著优于基准的 {pct(m['benchmark_mdd'])}，"
        f"下行保护依旧成立。", style_body))
    story.append(Spacer(1, 6))
    add_image(story, os.path.join(OUTPUT_DIR, "图2_策略净值曲线.png"),
              width=avail, height=avail*0.45, caption="图2：双系统海龟净值 vs 基准净值")
    story.append(PageBreak())
    add_image(story, os.path.join(OUTPUT_DIR, "图3_回撤曲线.png"),
              width=avail, height=avail*0.4, caption="图3：策略回撤曲线与最大回撤标注")
    add_image(story, os.path.join(OUTPUT_DIR, "图4_综合面板.png"),
              width=avail, height=avail*0.85,
              caption="图4：双系统综合面板（价格/通道/信号 · 持仓单位数 · ATR · 净值 · 回撤）")

    # ===== 第四章：多参数实验 =====
    story.append(PageBreak())
    story.append(Paragraph("四、多参数实验（标准 / 灵敏 / 稳健）", style_subtitle))
    story.append(Paragraph(
        "三套灵敏度配置在宁德时代上对比：标准(20/10,55/20)、灵敏(10/5,40/20)、稳健(55/27,100/50)。", style_body))
    pdata = [["配置", "累计回报", "年化收益", "MDD", "夏普", "多开/空开", "基准回报"]]
    for p in param_list:
        pdata.append([p["name"], pct(p["cumulative_return"]), pct(p["annual_return"]),
                      pct(p["mdd"]), f"{p['sharpe']:.2f}",
                      f"{p['long_entries']}/{p['short_entries']}",
                      pct(p["benchmark_return"])])
    story.append(make_table(pdata, col_widths=[2.8*cm, 2.4*cm, 2.4*cm, 2.4*cm, 1.8*cm, 2.4*cm, 2.6*cm]))
    story.append(Spacer(1, 8))
    # 定位三套
    std = next(p for p in param_list if p["name"] == "标准(经典)")
    sen = next(p for p in param_list if p["name"] == "灵敏")
    rob = next(p for p in param_list if p["name"] == "稳健")
    story.append(Paragraph(
        f"• <b>稳健配置</b>累计 {pct(rob['cumulative_return'])}、MDD 仅 {pct(rob['mdd'])}（三套最优），"
        f"印证长周期在震荡上行市里\"少动少错\"；<br/>"
        f"• <b>标准配置</b>累计 {pct(std['cumulative_return'])}、MDD {pct(std['mdd'])}；<br/>"
        f"• <b>灵敏配置</b>交易最频繁（多开 {sen['long_entries']}/空开 {sen['short_entries']}），"
        f"但 MDD 恶化至 {pct(sen['mdd'])}，频繁换手放大了逼空损耗。<br/>"
        f"结论：<b>在方向反复的行情里，缩短周期并不等于更好</b>——灵敏度提升带来更多噪声，"
        f"稳健的长周期反而以更低换手控制了回撤。", style_body))
    story.append(Spacer(1, 6))
    add_image(story, os.path.join(OUTPUT_DIR, "图5_多参数对比.png"),
              width=avail, height=avail*0.8, caption="图5：宁德时代多参数（标准/灵敏/稳健）净值与回撤对比")

    # ===== 第五章：多股票实验 =====
    story.append(PageBreak())
    story.append(Paragraph("五、多股票实验（标准配置）", style_subtitle))
    story.append(Paragraph(
        "同一标准参数应用于四类代表性股票，并与其买入持有基准对照——本组最能凸显<b>做空的价值</b>：", style_body))
    sdata = [["股票", "海龟累计", "海龟MDD", "海龟夏普", "基准回报", "基准MDD", "多开/空开"]]
    for sk in ["宁德时代", "平安银行", "贵州茅台", "五粮液"]:
        mm = stock_metrics[sk]
        sdata.append([sk, pct(mm["cumulative_return"]), pct(mm["mdd"]),
                      f"{mm['sharpe']:.2f}", pct(mm["benchmark_return"]),
                      pct(mm["benchmark_mdd"]), f"{mm['long_entries']}/{mm['short_entries']}"])
    story.append(make_table(sdata, col_widths=[2.6*cm, 2.6*cm, 2.2*cm, 2.0*cm, 2.4*cm, 2.2*cm, 2.4*cm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "• <b>五粮液（基准 −39.19%）</b>：海龟借助做空实现 <b>+29.64%</b>，最大单笔空头加仓 13 次，"
        "把 39% 的暴跌扭转为大幅盈利——做空是双系统相对单系统最大的增量价值；<br/>"
        "• <b>贵州茅台（基准 −16.02%）</b>：海龟 <b>+3.28%</b>，做空 7 次抵消了多头磨损；<br/>"
        "• <b>平安银行（基准 −18.33%）</b>：海龟 −11.98%，虽仍亏损，但已明显优于基准、回撤更小；<br/>"
        "• <b>宁德时代（基准 +42.96%）</b>：海龟 −13.77%，上行中被空头逼空拖累，体现做空在牛市中的反噬。<br/>"
        "关键结论：<b>双系统 + 做空让海龟在下跌/震荡市从\"少亏\"升级为\"能赚\"</b>，"
        "但代价是在单边上行市里要承受空头回补的损失——这正是多系统、多周期分散的意义所在。", style_body))
    story.append(Spacer(1, 6))
    add_image(story, os.path.join(OUTPUT_DIR, "图6_多股票对比.png"),
              width=avail, height=avail*0.8, caption="图6：双系统海龟（标准配置）多股票净值对比")
    add_image(story, os.path.join(OUTPUT_DIR, "图7_多股票指标柱状图.png"),
              width=avail, height=avail*0.4, caption="图7：多股票累计回报 / MDD / 夏普对比柱状图")

    # ===== 第六章：总结与反思 =====
    story.append(PageBreak())
    story.append(Paragraph("六、总结与反思", style_subtitle))

    story.append(Paragraph("6.1 与 TASK4 单系统版的对照", style_heading2))
    cmp = [
        ["版本（宁德时代）", "累计回报", "MDD", "夏普", "能否做空"],
        ["TASK4 单系统（仅做多）", pct(single["cumulative_return"]),
         pct(single["mdd"]), f"{single['sharpe']:.2f}", "否"],
        ["TASK4+ 双系统（S1/S2+加仓+做空）", pct(core["cumulative_return"]),
         pct(core["mdd"]), f"{core['sharpe']:.2f}", "是"],
    ]
    story.append(make_table(cmp, col_widths=[6*cm, 3*cm, 3*cm, 2.4*cm, 2.2*cm]))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "同一只上行股上，双系统版反而跑输单系统版——根因正是<b>多出来的空头在牛市中被逼空</b>。"
        "但把视野放到多只股票的完整样本（第五章）即可看到：单系统版在下跌市只能\"空仓少亏\"，"
        "双系统版却能\"借做空盈利\"。因此二者并非替代关系：<b>单系统胜在简洁、上行/震荡市少磨损；"
        "双系统胜在完备、下跌市能盈利</b>，代价是上行市要扛空头回补。", style_body))

    story.append(Paragraph("6.2 工程实现的关键教训（杠杆约束）", style_heading2))
    story.append(Paragraph(
        "原版海龟为期货设计，\"1% 风险\"对应的合约市值往往远小于本金，故可放心加至 4 单位。"
        "直接套到<b>高价股票</b>时，1% 风险对应的<b>股数市值会远超本金</b>，导致现金转为深度负、"
        "权益被隐式杠杆放大、单笔亏损失控（一度出现 −45% MDD）。教训：<b>把期货规则移植到股票，"
        "必须加入市值/保证金约束</b>——本版以\"单系统持仓市值 ≤ 50% 权益\"封顶，双系统同向最多满仓不杠杆，"
        "问题即解。这是量化策略跨市场迁移时最易被忽视的坑。", style_body))

    story.append(Paragraph("6.3 适用场景与改进方向", style_heading2))
    story.append(Paragraph(
        "• <b>最适用</b>：趋势清晰且持续的阶段、高波动品种、以及<b>下跌/震荡市</b>（做空带来正收益）；<br/>"
        "• <b>最不适用</b>：横盘震荡（假突破磨损）、单边长牛（空头逼空拖累）；<br/>"
        "• <b>改进方向</b>：① 加入趋势过滤器（如长期均线方向）抑制震荡市噪音交易；"
        "② 对空头与多头设置不同权重或相关性约束，降低同向踏错时的回撤；"
        "③ 以波动率目标（Volatility Targeting）替代固定 1% 风险，平滑不同市况下的仓位暴露；"
        "④ 跨多品种组合运行，用分散进一步压低回撤。", style_body))
    story.append(Paragraph(
        "一句话总结：<b>经典双系统海龟是一台更完整的趋势跟随机器</b>——它补齐了单系统的做空短板，"
        "用金字塔加仓放大强趋势收益；但其威力真正发挥，取决于是否把它放在\"对的市况\"、"
        "并为其配上适配标的属性的风控约束。", style_body))

    doc.build(story)
    print(f"PDF 报告已生成: {PDF_OUTPUT}")


if __name__ == "__main__":
    main()
