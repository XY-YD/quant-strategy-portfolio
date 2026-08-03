#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK3 PDF 报告生成脚本
====================
使用 reportlab 生成「夏阳+TASK3.pdf」
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                 Table, TableStyle, PageBreak)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ===== 字体注册 =====
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"
pdfmetrics.registerFont(TTFont("ArialUnicode", FONT_PATH))

# ===== 配色 =====
COLOR_UP = HexColor("#E74C3C")   # 红
COLOR_DOWN = HexColor("#27AE60")  # 绿
COLOR_TITLE = HexColor("#2C3E50")
COLOR_SUBTITLE = HexColor("#34495E")
COLOR_ACCENT = HexColor("#3498DB")
COLOR_BG = HexColor("#ECF0F1")

# ===== 路径 =====
BASE_DIR = "/Users/wangyanfen/Desktop/量化策略课程"
TASK3_DIR = os.path.join(BASE_DIR, "TASK3")
PDF_OUTPUT = os.path.join(TASK3_DIR, "夏阳+TASK3.pdf")

# ===== 样式 =====
styles = getSampleStyleSheet()

# 自定义样式
style_title = ParagraphStyle(
    "CustomTitle", parent=styles["Title"],
    fontName="ArialUnicode", fontSize=22, leading=28,
    textColor=COLOR_TITLE, alignment=TA_CENTER,
    spaceAfter=20,
)
style_subtitle = ParagraphStyle(
    "CustomSubtitle", parent=styles["Heading1"],
    fontName="ArialUnicode", fontSize=16, leading=22,
    textColor=COLOR_SUBTITLE, alignment=TA_LEFT,
    spaceBefore=16, spaceAfter=10,
)
style_heading2 = ParagraphStyle(
    "CustomH2", parent=styles["Heading2"],
    fontName="ArialUnicode", fontSize=13, leading=18,
    textColor=COLOR_ACCENT, alignment=TA_LEFT,
    spaceBefore=10, spaceAfter=6,
)
style_body = ParagraphStyle(
    "CustomBody", parent=styles["Normal"],
    fontName="ArialUnicode", fontSize=10.5, leading=16,
    textColor=black, alignment=TA_JUSTIFY,
    spaceBefore=4, spaceAfter=4,
)
style_bullet = ParagraphStyle(
    "CustomBullet", parent=style_body,
    leftIndent=20, bulletIndent=10,
)
style_center = ParagraphStyle(
    "CustomCenter", parent=style_body,
    alignment=TA_CENTER,
)
style_small = ParagraphStyle(
    "CustomSmall", parent=style_body,
    fontSize=9, leading=13,
)


def add_image(story, img_path, width=16*cm, caption=None):
    """添加图片到文档"""
    if os.path.exists(img_path):
        img = Image(img_path, width=width, height=width * 0.55)
        story.append(img)
        if caption:
            story.append(Paragraph(caption, style_center))
        story.append(Spacer(1, 8))


def make_table(data, col_widths=None, header=True):
    """创建格式化表格"""
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


def main():
    """生成完整 PDF 报告"""
    doc = SimpleDocTemplate(
        PDF_OUTPUT,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
        title="夏阳+TASK3 - 双均线策略报告",
        author="夏阳",
    )
    
    story = []
    avail_width = A4[0] - 4*cm  # 可用宽度
    
    # ===== 封面 =====
    story.append(Spacer(1, 60))
    story.append(Paragraph("量化策略课程", style_title))
    story.append(Spacer(1, 10))
    story.append(Paragraph("TASK3 - 策略首秀：双均线交叉捕捉市场趋势与波动", style_subtitle))
    story.append(Spacer(1, 20))
    story.append(Paragraph("作者：夏阳", style_center))
    story.append(Spacer(1, 10))
    story.append(Paragraph("日期：2026年7月8日", style_center))
    story.append(PageBreak())
    
    # ===== 第一章：理论基础 =====
    story.append(Paragraph("一、双均线策略理论基础", style_subtitle))
    
    story.append(Paragraph("1.1 移动平均线概述", style_heading2))
    story.append(Paragraph(
        "移动平均线（Moving Average, MA）是量化交易中最经典的技术指标之一。"
        "它通过对一定周期内的收盘价进行平滑平均，滤除短期噪音，揭示价格的中长期趋势方向。"
        "根据计算周期不同，均线可分为短周期均线（如MA5）和长周期均线（如MA15、MA30、MA60）。"
        "短均线对价格变化反应灵敏，长均线变化缓慢但趋势指向更稳定。",
        style_body))
    
    story.append(Paragraph("1.2 金叉与死叉", style_heading2))
    story.append(Paragraph(
        "双均线策略的核心信号来自两条均线的交叉点：",
        style_body))
    story.append(Paragraph(
        "• <b>金叉（买入信号）</b>：短周期均线从下方穿越长周期均线向上交叉。"
        "意味着短期趋势开始强于长期趋势，市场可能进入上升阶段，是买入时机。",
        style_bullet))
    story.append(Paragraph(
        "• <b>死叉（卖出信号）</b>：短周期均线从上方穿越长周期均线向下交叉。"
        "意味着短期趋势开始弱于长期趋势，市场可能进入下降阶段，是卖出时机。",
        style_bullet))
    
    story.append(Paragraph(
        "金叉和死叉的本质是<b>趋势反转的确认信号</b>。由于均线本身是滞后指标，"
        "交叉信号往往比实际拐点稍晚出现，这是均线策略的固有特征——用一定的滞后换取更高的可靠性。",
        style_body))
    
    story.append(Paragraph("1.3 双均线策略的优缺点", style_heading2))
    story.append(Paragraph("优势：", style_heading2))
    story.append(Paragraph(
        "• 逻辑简单、易于理解和实现<br/>"
        "• 能有效捕捉中长期趋势<br/>"
        "• 避免频繁交易，降低交易成本<br/>"
        "• 在趋势明显的市场中表现优异",
        style_bullet))
    story.append(Paragraph("局限：", style_heading2))
    story.append(Paragraph(
        "• 在震荡市中容易产生虚假信号（频繁交叉导致反复买卖）<br/>"
        "• 信号滞后，入场和出场时机偏晚<br/>"
        "• 无法预测趋势幅度，只能判断方向",
        style_bullet))
    
    # ===== 第二章：评估指标 =====
    story.append(Paragraph("二、策略评估指标", style_subtitle))
    
    story.append(Paragraph("2.1 最大回撤（MDD）", style_heading2))
    story.append(Paragraph(
        "最大回撤（Maximum Drawdown）衡量策略从净值峰值到后续最低点的最大跌幅，"
        "反映策略可能遭遇的最严重亏损。计算公式：<br/><br/>"
        "MDD = (净值峰值 - 谷底净值) / 净值峰值<br/><br/>"
        "MDD 越小越好，说明策略的风险控制能力越强。例如 MDD = -15% 表示策略在最坏情况下"
        "从高点回撤了15%。MDD 是衡量策略「最痛时刻」的关键指标。",
        style_body))
    
    story.append(Paragraph("2.2 夏普比率（Sharpe Ratio）", style_heading2))
    story.append(Paragraph(
        "夏普比率衡量每承担一单位风险所获得的超额回报。计算公式：<br/><br/>"
        "Sharpe = (策略年化收益率 - 无风险利率) / 策略收益率标准差 × √252<br/><br/>"
        "Sharpe > 1 通常被视为优秀策略，Sharpe > 0.5 为尚可，Sharpe < 0 说明策略"
        "风险调整后的收益不如无风险投资。本报告采用3%年化无风险利率。",
        style_body))
    
    story.append(Paragraph("2.3 累计回报（Cumulative Return）", style_heading2))
    story.append(Paragraph(
        "累计回报是策略从初始到期末的总收益率，不考虑时间维度。计算公式：<br/><br/>"
        "累计回报 = (期末净值 / 初始资金) - 1<br/><br/>"
        "例如累计回报 = 24.13% 表示初始10万元最终变为12.413万元。"
        "它是策略盈利能力的直观度量，但需结合 MDD 和 Sharpe 综合判断。",
        style_body))
    
    # ===== 第三章：回测结果 =====
    story.append(Paragraph("三、回测结果与可视化", style_subtitle))
    
    story.append(Paragraph("3.1 宁德时代双均线策略核心分析（MA5/MA15）", style_heading2))
    
    # 指标表
    metrics_data = [
        ["指标", "数值", "说明"],
        ["累计回报", "24.13%", "策略总收益"],
        ["年化收益率", "25.37%", "折算为年化"],
        ["最大回撤 MDD", "-14.20%", "最大亏损幅度"],
        ["夏普比率", "0.76", "风险调整后收益"],
        ["买入次数", "9", "金叉信号"],
        ["卖出次数", "9", "死叉信号"],
    ]
    story.append(make_table(metrics_data, col_widths=[4*cm, 4*cm, 8*cm]))
    story.append(Spacer(1, 10))
    
    # 图1
    add_image(story, os.path.join(TASK3_DIR, "图1_股价均线信号.png"), width=avail_width,
              caption="图1：宁德时代股价与均线信号（MA5/MA15）")
    
    # 图2
    add_image(story, os.path.join(TASK3_DIR, "图2_策略净值曲线.png"), width=avail_width,
              caption="图2：策略净值与基准净值对比")
    
    # 图3
    add_image(story, os.path.join(TASK3_DIR, "图3_策略回撤曲线.png"), width=avail_width,
              caption="图3：策略回撤曲线与最大回撤标注")
    
    story.append(PageBreak())
    
    # 图4 综合面板
    story.append(Paragraph("3.2 综合面板", style_heading2))
    add_image(story, os.path.join(TASK3_DIR, "图4_综合面板.png"), width=avail_width,
              caption="图4：宁德时代双均线策略综合面板")
    
    # ===== 第四章：参数优化 =====
    story.append(Paragraph("四、参数优化与多周期对比", style_subtitle))
    
    story.append(Paragraph(
        "均线周期的选择直接影响策略表现。短周期参数（如MA5/MA15）反应灵敏但交易频繁，"
        "长周期参数（如MA20/MA60）信号少但趋势捕捉更稳定。以下对比三种典型参数组合：",
        style_body))
    
    params_data = [
        ["均线参数", "累计回报", "年化收益率", "最大回撤MDD", "夏普比率", "交易次数"],
        ["MA5/MA15", "24.13%", "25.37%", "-14.20%", "0.76", "9买/9卖"],
        ["MA10/MA30", "23.46%", "24.65%", "-22.38%", "0.74", "5买/5卖"],
        ["MA20/MA60", "56.77%", "60.02%", "-12.66%", "1.53", "3买/3卖"],
    ]
    story.append(make_table(params_data, col_widths=[3*cm, 3*cm, 3*cm, 3*cm, 3*cm, 3*cm]))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "从对比中可以发现：<br/>"
        "• MA20/MA60 的累计回报（56.77%）远超其他参数组合，夏普比率（1.53）也最高，"
        "说明长周期均线在本期间更能捕捉宁德时代的大趋势<br/>"
        "• MA5/MA15 和 MA10/MA30 的表现相近，但后者回撤更深（-22.38%）<br/>"
        "• 长周期参数交易次数更少，有利于降低交易成本",
        style_body))
    
    add_image(story, os.path.join(TASK3_DIR, "图5_多参数对比.png"), width=avail_width,
              caption="图5：宁德时代多均线参数对比")
    
    story.append(PageBreak())
    
    # ===== 第五章：多股票对比 =====
    story.append(Paragraph("五、多股票对比分析", style_subtitle))
    
    story.append(Paragraph(
        "同一策略在不同股票上的表现差异显著。我们选取4只代表性股票进行对比："
        "宁德时代（新能源/高波动成长股）、平安银行（银行/低波动价值股）、"
        "贵州茅台（白酒/蓝筹消费股）、五粮液（白酒/成长消费股），"
        "均使用MA5/MA15参数。",
        style_body))
    
    stocks_data = [
        ["股票", "累计回报", "最大回撤MDD", "夏普比率", "买入次数"],
        ["宁德时代", "24.13%", "-14.20%", "0.76", "9"],
        ["平安银行", "-13.03%", "-13.03%", "-2.08", "12"],
        ["贵州茅台", "-4.82%", "-10.59%", "-0.66", "11"],
        ["五粮液", "-1.70%", "-7.83%", "-0.46", "8"],
    ]
    story.append(make_table(stocks_data, col_widths=[3*cm, 3*cm, 3.5*cm, 3.5*cm, 3*cm]))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(
        "对比发现：<br/>"
        "• <b>宁德时代</b>是唯一获得正收益的股票（24.13%），夏普比率0.76。"
        "新能源股波动大、趋势性强，适合均线策略捕捉方向性机会<br/>"
        "• <b>平安银行</b>表现最差（-13.03%），银行股走势偏震荡、缺乏方向性趋势，"
        "均线策略频繁触发虚假信号导致反复止损<br/>"
        "• <b>贵州茅台</b>和<b>五粮液</b>小幅亏损，白酒板块本期间震荡下行，"
        "均线策略难以在无明显趋势的行情中获利",
        style_body))
    
    add_image(story, os.path.join(TASK3_DIR, "图6_多股票对比.png"), width=avail_width,
              caption="图6：双均线策略(MA5/MA15) 多股票净值对比")
    
    add_image(story, os.path.join(TASK3_DIR, "图7_多股票指标柱状图.png"), width=avail_width,
              caption="图7：多股票指标对比柱状图")
    
    # ===== 第六章：结论 =====
    story.append(Paragraph("六、总结与心得", style_subtitle))
    
    story.append(Paragraph("6.1 双均线策略适用场景", style_heading2))
    story.append(Paragraph(
        "通过本次实验，我们对双均线策略的适用条件有了清晰的认知：<br/><br/>"
        "1. <b>趋势明显的市场</b>：当股价呈现持续上升或下降趋势时，均线交叉能准确捕捉方向转换，"
        "策略收益显著（如宁德时代在本期间的56.77%回报）<br/><br/>"
        "2. <b>高波动成长股</b>：波动率较大的股票趋势性更强，均线信号更可靠；"
        "低波动价值股走势偏横盘震荡，均线策略容易失灵<br/><br/>"
        "3. <b>长周期参数在强趋势中更优</b>：MA20/MA60虽然信号少，但在大趋势中能完整捕获方向，"
        "避免频繁进出的摩擦损失；MA5/MA15在震荡市中虚假信号过多",
        style_body))
    
    story.append(Paragraph("6.2 双均线策略不适用场景", style_heading2))
    story.append(Paragraph(
        "1. <b>横盘震荡市</b>：均线频繁交叉产生大量虚假信号，反复买卖导致亏损<br/><br/>"
        "2. <b>低波动性股票</b>：如银行股等价值型标的，方向性趋势不显著<br/><br/>"
        "3. <b>突发事件行情</b>：均线是滞后指标，无法应对突发的剧烈波动",
        style_body))
    
    story.append(Paragraph("6.3 实践心得", style_heading2))
    story.append(Paragraph(
        "1. 均线策略不是万能的——它本质上是<b>趋势跟随策略</b>，只在趋势市场中有效<br/>"
        "2. 参数选择需要根据标的特性和市场环境调整——没有「最优」的通用参数<br/>"
        "3. 策略评估不能只看收益——MDD和Sharpe比累计回报更重要<br/>"
        "4. 在应用双均线策略前，应先判断当前市场是否处于趋势阶段<br/>"
        "5. 可将双均线策略与其他指标（如RSI、MACD）结合，提高信号可靠性<br/>"
        "6. 长周期参数虽信号少，但胜率高、回撤小，适合风险偏好较低的投资者",
        style_body))
    
    # 构建 PDF
    doc.build(story)
    print(f"PDF 报告已生成: {PDF_OUTPUT}")


if __name__ == "__main__":
    main()
