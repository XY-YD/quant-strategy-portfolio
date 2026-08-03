#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK8 PDF 报告生成脚本
=====================
生成完整的学习报告 PDF，包含封面、目录、摘要、五章正文和附录。
格式：宋体五号字1.5倍行距，图表统一编号，文字两端对齐。
"""
import os, json
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.lib.colors import HexColor, black, white
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame,
                                 Paragraph, Spacer, Image, Table, TableStyle,
                                 PageBreak, NextPageTemplate, KeepTogether)
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# ===== 字体注册（宋体） =====
pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
FONT = "STSong-Light"
FONT_BOLD = "STSong-Light"  # CID字体无独立粗体，用加粗样式

# ===== 路径 =====
BASE = "/Users/wangyanfen/Desktop/量化策略课程"
TASK8 = os.path.join(BASE, "TASK8")
FIGS = os.path.join(TASK8, "figs")
OUT = os.path.join(TASK8, "夏阳+TASK8_量化交易学习报告.pdf")

# 读取TASK7指标
with open(os.path.join(BASE, "TASK7", "metrics.json"), "r", encoding="utf-8") as f:
    M = json.load(f)
INS = M["insample"]
OOS = M["oos"]
OOSD = M["oos_default"]

# ===== 配色 =====
C_TITLE = HexColor("#1A5276")
C_H1 = HexColor("#1A5276")
C_H2 = HexColor("#21618C")
C_H3 = HexColor("#2874A6")
C_BODY = black
C_ACCENT = HexColor("#3498DB")
C_BG = HexColor("#EAF2F8")
C_GREY = HexColor("#95A5A6")

# ===== 页面参数 =====
PAGE_W, PAGE_H = A4
MARGIN_L = 2.5 * cm
MARGIN_R = 2.5 * cm
MARGIN_T = 2.5 * cm
MARGIN_B = 2.5 * cm
AVAIL_W = PAGE_W - MARGIN_L - MARGIN_R  # 可用宽度约16cm

# ===== 样式定义 =====
# 五号字=10.5pt, 1.5倍行距=15.75pt
S_COVER_TITLE = ParagraphStyle("CoverTitle", fontName=FONT, fontSize=22,
                                leading=30, alignment=TA_CENTER, textColor=C_TITLE)
S_COVER_SUB = ParagraphStyle("CoverSub", fontName=FONT, fontSize=14,
                              leading=20, alignment=TA_CENTER, textColor=HexColor("#566573"))
S_COVER_INFO = ParagraphStyle("CoverInfo", fontName=FONT, fontSize=12,
                                leading=18, alignment=TA_CENTER, textColor=HexColor("#566573"))

S_H1 = ParagraphStyle("H1", fontName=FONT, fontSize=15, leading=22,
                       alignment=TA_LEFT, textColor=C_H1,
                       spaceBefore=16, spaceAfter=10, keepWithNext=1)
S_H2 = ParagraphStyle("H2", fontName=FONT, fontSize=13, leading=19,
                       alignment=TA_LEFT, textColor=C_H2,
                       spaceBefore=12, spaceAfter=8, keepWithNext=1)
S_H3 = ParagraphStyle("H3", fontName=FONT, fontSize=11.5, leading=17,
                       alignment=TA_LEFT, textColor=C_H3,
                       spaceBefore=8, spaceAfter=6, keepWithNext=1)

S_BODY = ParagraphStyle("Body", fontName=FONT, fontSize=10.5, leading=15.75,
                         alignment=TA_JUSTIFY, textColor=C_BODY,
                         spaceBefore=0, spaceAfter=0)
S_BULLET = ParagraphStyle("Bullet", fontName=FONT, fontSize=10.5, leading=15.75,
                           alignment=TA_JUSTIFY, textColor=C_BODY,
                           leftIndent=20, bulletIndent=10,
                           spaceBefore=0, spaceAfter=0)
S_CAP = ParagraphStyle("Caption", fontName=FONT, fontSize=9, leading=13.5,
                         alignment=TA_CENTER, textColor=HexColor("#566573"),
                         spaceBefore=4, spaceAfter=10)
S_TOC_TITLE = ParagraphStyle("TocTitle", fontName=FONT, fontSize=16, leading=24,
                              alignment=TA_CENTER, textColor=C_TITLE,
                              spaceAfter=20)

# TOC样式
S_TOC1 = ParagraphStyle("TOC1", fontName=FONT, fontSize=11, leading=16,
                         leftIndent=0, spaceBefore=4, spaceAfter=2)
S_TOC2 = ParagraphStyle("TOC2", fontName=FONT, fontSize=10, leading=14,
                         leftIndent=20, spaceBefore=2, spaceAfter=1)


# ===== 工具函数 =====
def add_image(img_path, width=None, caption=None):
    """添加图片，自动按比例缩放"""
    flow = []
    if width is None:
        width = AVAIL_W
    if os.path.exists(img_path):
        iw, ih = PILImage.open(img_path).size
        h = width * ih / iw
        if h > 12 * cm:  # 超高则限制高度
            h = 12 * cm
            width = h * iw / ih
        flow.append(Image(img_path, width=width, height=h))
        if caption:
            flow.append(Paragraph(caption, S_CAP))
        flow.append(Spacer(1, 6))
    else:
        print(f"  [警告] 图片不存在: {img_path}")
    return flow


def make_table(data, col_widths=None, font_size=9):
    """创建格式化表格（不跨页，重复表头）"""
    if col_widths is None:
        n = len(data[0])
        col_widths = [AVAIL_W / n] * n
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), FONT),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#BDC3C7")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, 0), C_H1),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("FONTNAME", (0, 0), (-1, 0), FONT),
        ("FONTSIZE", (0, 0), (-1, 0), font_size),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [white, C_BG]),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


def P(text, style=None):
    """快捷段落"""
    if style is None:
        style = S_BODY
    return Paragraph(text, style)


def bullets(items):
    """生成项目符号列表"""
    return [Paragraph(f"\u2022 {item}", S_BULLET) for item in items]


def fmt_pct(x):
    return f"{x*100:.2f}%"


def fmt_num(x, d=2):
    return f"{x:.{d}f}"


# ========================================================================
# 自定义文档模板（支持TOC和页码）
# ========================================================================
class ReportDocTemplate(BaseDocTemplate):
    def __init__(self, filename, **kw):
        BaseDocTemplate.__init__(self, filename, **kw)
        # 正文页模板
        frame_normal = Frame(MARGIN_L, MARGIN_B, AVAIL_W,
                             PAGE_H - MARGIN_T - MARGIN_B, id="normal")
        # 封面页模板（无页码）
        frame_cover = Frame(MARGIN_L, MARGIN_B, AVAIL_W,
                            PAGE_H - MARGIN_T - MARGIN_B, id="cover")
        self.addPageTemplates([
            PageTemplate(id="Cover", frames=[frame_cover],
                         onPage=self._cover_page),
            PageTemplate(id="Normal", frames=[frame_normal],
                         onPage=self._normal_page),
        ])

    def _cover_page(self, canvas, doc):
        pass  # 封面无页码

    def _normal_page(self, canvas, doc):
        canvas.saveState()
        canvas.setFont(FONT, 8)
        canvas.setFillColor(C_GREY)
        canvas.drawCentredString(PAGE_W / 2, 1.2 * cm, f"— {doc.page} —")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        """捕获标题，添加到TOC"""
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            text = flowable.getPlainText()
            if style_name == "H1":
                self.notify("TOCEntry", (0, text, self.page))
            elif style_name == "H2":
                self.notify("TOCEntry", (1, text, self.page))


# ========================================================================
# 构建报告内容
# ========================================================================
def build_story():
    story = []

    # ====================================================================
    # 封面
    # ====================================================================
    story.append(Spacer(1, 5 * cm))
    story.append(P("量化交易策略开发与机器学习应用", S_COVER_TITLE))
    story.append(Spacer(1, 8))
    story.append(P("——学习实践报告", S_COVER_TITLE))
    story.append(Spacer(1, 20))
    story.append(P("量化策略课程  TASK8  成果展示", S_COVER_SUB))
    story.append(Spacer(1, 40))

    # 装饰线
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(width="50%", color=C_TITLE, thickness=1.5))
    story.append(Spacer(1, 30))

    story.append(P("作者：夏阳", S_COVER_INFO))
    story.append(Spacer(1, 10))
    story.append(P("日期：2026年7月25日", S_COVER_INFO))
    story.append(Spacer(1, 10))
    story.append(P("指导课程：量化策略课程", S_COVER_INFO))

    story.append(NextPageTemplate("Normal"))
    story.append(PageBreak())

    # ====================================================================
    # 目录
    # ====================================================================
    story.append(P("目  录", S_TOC_TITLE))
    toc = TableOfContents()
    toc.levelStyles = [S_TOC1, S_TOC2]
    story.append(toc)
    story.append(PageBreak())

    # ====================================================================
    # 摘要
    # ====================================================================
    story.append(P("摘  要", S_H1))
    story.append(P(
        "本报告系统总结了量化策略课程七个任务的学习与实践成果。"
        "在策略开发方面，实现了双均线策略和海龟交易策略，通过回测验证了趋势跟随策略"
        "在方向性行情中的有效性，同时揭示了震荡市中虚假信号的风险。"
        "在机器学习应用方面，完成了从数据预处理、特征工程到模型训练、评估和策略回测的"
        "完整流程，对比了逻辑回归、决策树、随机森林和梯度提升四类模型在选股策略中的表现，"
        "发现集成模型（随机森林和梯度提升）在风险调整后收益上显著优于单一模型。"
        "在策略优化方面，通过样本内网格寻优和样本外前向测试，验证了参数寻优的局限性——"
        "样本内最优参数在样本外反而跑输默认参数，揭示了过拟合风险和策略与市场状态匹配的重要性。"
        "报告最后从策略逻辑、风控体系、模型方法和实盘模拟四个维度提出了八条具体改进建议，"
        "为后续量化交易研究指明了方向。"))
    story.append(Spacer(1, 10))
    story.append(PageBreak())

    # ====================================================================
    # 第一章：量化交易核心概念
    # ====================================================================
    story.append(P("第一章  量化交易核心概念", S_H1))

    story.append(P("1.1  量化交易的定义与核心价值", S_H2))
    story.append(P(
        "量化交易是指利用数学模型和计算机程序，基于历史数据和市场信息，"
        "按照预先设定的规则自动进行交易决策和执行的一种交易方式。"
        "与传统的 discretionary trading（主观交易）不同，量化交易将投资逻辑"
        "转化为可量化、可回测、可执行的系统化策略，旨在消除人为情绪干扰、"
        "提高决策效率和一致性。"))
    story.append(Spacer(1, 4))
    story.append(P(
        "量化交易的核心价值体现在以下四个方面：<b>纪律性</b>——策略规则一旦设定，"
        "计算机严格执行，克服了人性行为中的贪婪与恐惧；<b>系统性</b>——"
        "可同时考虑估值、成长、动量、波动等多维度因子，实现综合性决策；"
        "<b>可回测</b>——策略在投入实盘前可用历史数据验证其有效性，"
        "量化评估收益与风险；<b>速度</b>——程序化执行可在毫秒级别完成"
        "信号检测和订单提交，远超人工操作速度。"))

    story.append(P("1.2  量化交易的流程框架", S_H2))
    story.append(P(
        "完整的量化交易流程涵盖从数据到实盘的六个环节。"
        "首先是数据获取，包括行情数据（量价）和基本面数据（财务指标），"
        "是策略开发的原料。其次是因子分析，从原始数据中提炼具有预测能力的"
        "特征变量。第三是策略设计，将因子转化为具体的买卖信号规则。"
        "第四是回测验证，用历史数据模拟策略表现，计算收益和风险指标。"
        "第五是风险管理，包括止损、仓位控制和成本管理，是策略长期存活的保障。"
        "最后是实盘执行，将经过验证的策略部署到交易系统中。"
        "图1展示了本课程七个任务在这一流程中的对应关系。"))
    story.extend(add_image(os.path.join(FIGS, "fig_summary_strategies.png"),
                            caption="图1  量化交易策略体系总览"))

    story.append(P("1.3  关键评估指标解析", S_H2))
    story.append(P(
        "策略评估需要从收益和风险两个维度综合考量。"
        "本课程中使用的核心指标及其定义如表1所示。"))
    story.append(Spacer(1, 4))

    table1_data = [
        ["指标", "定义", "评判标准"],
        ["累计收益率", "策略从初始到期末的总收益率", "越高越好"],
        ["年化收益率", "将累计收益折算为年度的复合收益率", "越高越好"],
        ["最大回撤", "净值从峰值到后续谷底的最大跌幅", "越小越好（绝对值）"],
        ["夏普比率", "超额收益与总风险的比值，衡量风险调整后收益", "大于1为优秀"],
        ["索提诺比率", "仅考虑下行风险的收益风险比", "越大越好"],
        ["Calmar比率", "年化收益与最大回撤的比值", "越大越好"],
        ["胜率", "盈利交易占总交易的比例", "越高越好"],
        ["VaR", "给定置信水平下的最大可能亏损", "绝对值越小越好"],
    ]
    story.append(make_table(table1_data, col_widths=[3*cm, 8*cm, 5*cm]))
    story.append(P("表1  核心评估指标定义与评判标准", S_CAP))

    story.append(P(
        "需要强调的是，<b>单一指标无法全面评价策略优劣</b>。"
        "一个年化收益30%但最大回撤50%的策略，可能不如年化15%但回撤仅10%的策略。"
        "夏普比率综合考虑了收益和波动，是业内最常用的风险调整后收益指标。"
        "在后续各任务的策略评估中，我们将始终以多指标组合作为评判依据。"))

    story.append(PageBreak())

    # ====================================================================
    # 第二章：量化交易策略综合分析
    # ====================================================================
    story.append(P("第二章  量化交易策略综合分析", S_H1))
    story.append(P(
        "本章对课程中实现的两类核心策略——双均线策略（TASK3）和海龟交易策略（TASK4）"
        "进行综合分析，比较其设计逻辑、风控机制和回测表现，并探讨多策略系统的构建思路。"))

    # 2.1 双均线策略
    story.append(P("2.1  双均线策略（TASK3）", S_H2))
    story.append(P("2.1.1  策略原理", S_H3))
    story.append(P(
        "双均线策略是最经典的趋势跟随策略之一。其核心逻辑是："
        "当短期均线从下方上穿长期均线时（金叉），视为上升趋势的开始，买入建仓；"
        "当短期均线从上方下穿长期均线时（死叉），视为下降趋势的开始，卖出平仓。"
        "均线本身是收盘价的移动平均，起到平滑噪音、揭示趋势方向的作用。"
        "短周期均线（如MA5）对价格反应灵敏，长周期均线（如MA15）变化缓慢但趋势指向更稳定。"))
    story.append(P(
        "在TASK3中，以宁德时代（300750.SZ）为核心标的，采用MA5/MA15参数组合，"
        "全仓操作、以收盘价成交、暂不考虑手续费。回测区间为2025年7月至2026年7月，"
        "共242个交易日。"))

    story.append(P("2.1.2  回测结果", S_H3))
    story.append(P(
        "图2和图3分别展示了双均线策略的信号分布和净值曲线。"
        "从信号图可见，金叉和死叉交替出现，策略在趋势段捕捉了主要方向，"
        "但在震荡段也产生了若干虚假信号。"))
    story.extend(add_image(os.path.join(BASE, "TASK3", "图1_股价均线信号.png"),
                            caption="图2  宁德时代双均线策略信号图（MA5/MA15）"))
    story.extend(add_image(os.path.join(BASE, "TASK3", "图2_策略净值曲线.png"),
                            caption="图3  双均线策略净值曲线与基准对比"))

    story.append(P("2.1.3  多参数对比", S_H3))
    story.append(P(
        "均线周期的选择直接影响策略表现。表2对比了三种典型参数组合在宁德时代上的回测结果。"))
    story.append(Spacer(1, 4))

    table2_data = [
        ["均线参数", "累计回报", "年化收益率", "最大回撤", "夏普比率", "交易次数"],
        ["MA5/MA15", "24.13%", "25.37%", "-14.20%", "0.76", "9买/9卖"],
        ["MA10/MA30", "23.46%", "24.65%", "-22.38%", "0.74", "5买/5卖"],
        ["MA20/MA60", "56.77%", "60.02%", "-12.66%", "1.53", "3买/3卖"],
    ]
    story.append(make_table(table2_data, col_widths=[2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.5*cm, 2.3*cm]))
    story.append(P("表2  双均线策略多参数对比（宁德时代）", S_CAP))

    story.append(P(
        "对比发现，长周期参数MA20/MA60在本期间表现最优，累计回报56.77%、夏普1.53，"
        "且交易次数仅3次，降低了摩擦成本。这说明在趋势明显的标的上，"
        "<b>长周期均线更能完整捕获大趋势，避免频繁进出的信号噪音</b>。"
        "然而，长周期参数信号少也意味着在趋势转换时反应滞后，这一局限需在不同市场环境中权衡。"))

    story.append(PageBreak())

    # 2.2 海龟交易策略
    story.append(P("2.2  海龟交易策略（TASK4）", S_H2))
    story.append(P("2.2.1  策略原理", S_H3))
    story.append(P(
        "海龟交易策略是著名的趋势突破策略，由理查德·丹尼斯在1980年代设计。"
        "其核心要素包括：唐奇安高低点通道作为信号触发——突破前N日最高价买入，"
        "跌破前M日最低价卖出；ATR（平均真实波幅）作为波动率度量——"
        "用于止损和仓位管理；2倍ATR硬止损——单笔最大风险锁定在2倍ATR水平；"
        "以及1%风险仓位管理——每笔交易风险占总权益的1%，使仓位随波动率自动调整。"))
    story.append(P(
        "在TASK4中，以宁德时代为核心标的，采用N=20日买入通道、M=10日卖出通道、"
        "ATR周期20日、止损2倍ATR、风险比例1%的参数配置。"))

    story.append(P("2.2.2  回测结果", S_H3))
    story.extend(add_image(os.path.join(BASE, "TASK4", "图1_股价_唐奇安通道_信号.png"),
                            caption="图4  海龟策略：股价与唐奇安通道及信号"))
    story.extend(add_image(os.path.join(BASE, "TASK4", "图4_综合面板.png"),
                            caption="图5  海龟策略综合面板（含ATR、净值、回撤）"))

    story.append(P("2.2.3  多参数对比", S_H3))
    story.append(P(
        "表3对比了不同通道周期参数下的海龟策略表现。"))
    story.append(Spacer(1, 4))

    table3_data = [
        ["通道参数", "累计回报", "年化收益率", "最大回撤", "夏普", "止损/破低"],
        ["N10/M5", "3.03%", "3.17%", "-6.06%", "0.06", "0/8"],
        ["N20/M10", "-0.02%", "-0.02%", "-10.17%", "-0.32", "2/3"],
        ["N55/M27", "-1.49%", "-1.56%", "-4.59%", "-0.63", "1/1"],
    ]
    story.append(make_table(table3_data, col_widths=[2.8*cm, 2.8*cm, 2.8*cm, 2.8*cm, 2.3*cm, 2.5*cm]))
    story.append(P("表3  海龟策略多参数对比（宁德时代）", S_CAP))

    story.append(P(
        "海龟策略在宁德时代本期间的整体表现不如双均线策略，"
        "主要原因在于该期间趋势以中短期波段为主，而海龟策略更适合捕捉长周期大趋势。"
        "不过，海龟策略的风险控制更为严格——止损机制使每笔亏损有上限，"
        "ATR仓位管理使高波动时段自动减仓，这些设计在极端行情中更具安全性。"))

    story.append(PageBreak())

    # 2.3 策略对比
    story.append(P("2.3  策略对比与关联性分析", S_H2))
    story.append(P(
        "双均线策略和海龟策略虽同属趋势跟随体系，但在信号生成、风控机制和仓位管理上存在显著差异。"
        "表4从六个维度对比了两类策略的特征。"))
    story.append(Spacer(1, 4))

    table4_data = [
        ["对比维度", "双均线策略", "海龟交易策略"],
        ["信号生成", "均线交叉（金叉/死叉）", "通道突破（新高/新低）"],
        ["信号灵敏度", "较高，反应较快", "较低，确认更严格"],
        ["止损机制", "无独立止损", "2倍ATR硬止损+通道退出"],
        ["仓位管理", "全仓操作", "1%风险，ATR归一化"],
        ["适用场景", "中短期趋势，高波动品种", "强趋势大行情，高波动品种"],
        ["主要风险", "震荡市虚假信号频繁", "信号滞后，假突破损失"],
    ]
    story.append(make_table(table4_data, col_widths=[3.5*cm, 6.25*cm, 6.25*cm]))
    story.append(P("表4  双均线策略与海龟策略特征对比", S_CAP))

    story.append(P(
        "两类策略具有明显的互补性。双均线策略信号灵敏，能较快捕捉趋势转换，"
        "但缺少风控机制导致单笔亏损可能较大；海龟策略风控完善、仓位管理科学，"
        "但信号滞后在快速反转行情中可能错失最佳时机。"
        "图6直观对比了两种策略及TASK7寻优策略的核心指标。"))
    story.extend(add_image(os.path.join(FIGS, "fig_strategy_comparison.png"),
                            caption="图6  各策略核心指标对比（宁德时代）"))

    story.append(P(
        "从对比可见，TASK7的样本内寻优策略（MA15/MA20）年化收益和夏普比率最高，"
        "但最大回撤也最大（-39.17%），体现了高收益伴随高风险的特征。"
        "双均线策略（MA5/MA15）在收益和回撤之间取得了较好平衡。"
        "海龟策略在本期间表现一般，但其风控设计理念值得借鉴。"))

    # 2.4 多策略系统
    story.append(P("2.4  多策略量化交易系统构建思路", S_H2))
    story.append(P(
        "单一策略在任何市场状态下都存在失效风险，构建多策略系统是提升稳健性的关键路径。"
        "基于本课程实践，多策略系统可从三个层面构建：<b>分散化</b>——"
        "将双均线、海龟、机器学习选股等不同逻辑的策略并行运行，"
        "利用策略间低相关性降低组合波动；<b>动态权重</b>——"
        "根据市场状态识别（如用ADX指标判断趋势/震荡），"
        "动态调整各策略的资金分配权重，趋势市加大趋势策略权重，震荡市切换至均值回归策略；"
        "<b>组合层面风控</b>——在单策略止损的基础上，增加组合层面的"
        "整体回撤限制和相关性监控，防止单一策略极端亏损拖累全局。"))

    story.append(PageBreak())

    # ====================================================================
    # 第三章：机器学习在量化交易中的应用
    # ====================================================================
    story.append(P("第三章  机器学习在量化交易中的应用总结", S_H1))
    story.append(P(
        "本章总结TASK5和TASK6中机器学习算法在量化交易中的应用实践，"
        "覆盖数据预处理、特征工程、模型训练、评估优化和策略回测全流程。"))

    # 3.1 数据预处理与特征工程
    story.append(P("3.1  数据预处理与特征工程", S_H2))
    story.append(P(
        "数据预处理是机器学习的第一步，直接影响模型质量。"
        "在TASK5中，对乳腺癌数据集（569样本、27特征）和股票收益数据"
        "（20772行、17特征）进行了缺失值和无穷值清洗，并对逻辑回归模型使用"
        "StandardScaler进行特征标准化。在TASK6中，进一步将无穷值替换为NaN后删除，"
        "确保输入数据无异常值干扰。"))
    story.append(P(
        "特征工程是量化ML策略的核心环节。TASK6在20个原始因子"
        "（9个估值因子：企业倍数、市净率、市盈率等；10个成长因子：净利润、"
        "净资产等同比增长率；1个规模因子：市值）的基础上，"
        "设计了7个衍生因子以增强信息量：<b>估值综合排名</b>——"
        "取PE、PB、PS三个估值因子的截面排名均值；<b>成长综合排名</b>——"
        "8个成长因子的截面排名均值；<b>质量因子</b>——"
        "净利润增长率减去总资产增长率，衡量盈利增速与扩张速度的匹配度；"
        "<b>规模因子</b>——市值取对数；<b>估值偏离度</b>——PE与PB之差；"
        "<b>成长稳定性</b>——多个成长因子变异系数的倒数；"
        "<b>现金流质量</b>——经营现金流增长率减去净利润增长率。"))
    story.append(P(
        "应变量设计采用截面中位数法：若下期收益高于同期截面中位数则标记为1（正类），"
        "否则为0（负类）。这一设计将预测问题转化为"
        "「能否跑赢市场中位数」的二分类问题，避免了对收益绝对值的预测。"))
    story.extend(add_image(os.path.join(FIGS, "fig_ml_pipeline.png"),
                            caption="图7  机器学习量化交易流程"))

    story.append(PageBreak())

    # 3.2 模型选择与训练
    story.append(P("3.2  模型选择与训练", S_H2))
    story.append(P(
        "TASK5构建了三类分类模型：逻辑回归（需标准化输入）、决策树（max_depth=5控制复杂度）、"
        "随机森林（100棵树、max_depth=8）。TASK6在此基础上增加了梯度提升模型"
        "（150棵树、max_depth=5、学习率0.1），并将随机森林扩展至200棵树。"
        "此外，TASK6的附加题还构建了5个回归模型（线性回归、岭回归、决策树回归、"
        "随机森林回归、梯度提升回归），直接预测下期收益率。"))
    story.append(P(
        "在数据划分上，TASK5采用随机划分（70%训练/30%测试），"
        "TASK6采用时间分割——2021年第三季度之前为训练集，之后为测试集。"
        "<b>时间分割是量化领域的正确做法</b>，因为它避免了未来信息泄漏"
        "（前视偏差），更贴近实盘中用历史训练、用未来验证的真实场景。"))
    story.append(Spacer(1, 4))

    table5_data = [
        ["模型", "类型", "关键参数", "是否标准化"],
        ["逻辑回归", "分类", "max_iter=2000, C=1.0", "是"],
        ["决策树", "分类", "max_depth=6, min_samples_leaf=50", "否"],
        ["随机森林", "分类", "n_estimators=200, max_depth=10", "否"],
        ["梯度提升", "分类", "n_estimators=150, max_depth=5, lr=0.1", "否"],
    ]
    story.append(make_table(table5_data, col_widths=[3*cm, 3*cm, 7*cm, 3*cm]))
    story.append(P("表5  TASK6各分类模型参数配置", S_CAP))

    # 3.3 模型评估与优化
    story.append(P("3.3  模型评估与优化", S_H2))
    story.append(P(
        "模型评估从分类性能和策略回测两个层面展开。"
        "分类性能方面，使用准确率、精确率、召回率、F1值和AUC五个指标，"
        "并通过ROC曲线和混淆矩阵可视化模型判别能力。"
        "图8展示了TASK5中三类模型在乳腺癌数据集上的ROC曲线对比。"))
    story.extend(add_image(os.path.join(BASE, "TASK5", "roc_乳腺癌数据.png"),
                            width=10*cm, caption="图8  分类模型ROC曲线对比（乳腺癌数据集）"))

    story.append(P(
        "在策略回测层面，TASK6采用「每季度选预测概率最高的50只股票等权持有」的策略，"
        "以全市场等权组合为基准，计算累计收益、年化收益、夏普比率、最大回撤和胜率。"
        "表6汇总了四个分类模型的回测核心指标。"))
    story.append(Spacer(1, 4))

    table6_data = [
        ["模型", "累计收益", "年化收益", "夏普比率", "最大回撤", "胜率"],
        ["逻辑回归", "14.37%", "14.37%", "1.15", "-5.83%", "75.00%"],
        ["决策树", "-5.28%", "-5.28%", "-0.18", "-14.90%", "50.00%"],
        ["随机森林", "24.19%", "24.19%", "2.91", "-0.86%", "75.00%"],
        ["梯度提升", "25.97%", "25.97%", "3.41", "0.00%", "75.00%"],
    ]
    story.append(make_table(table6_data, col_widths=[2.8*cm, 2.8*cm, 2.8*cm, 2.5*cm, 2.8*cm, 2.3*cm]))
    story.append(P("表6  机器学习模型策略回测指标对比（TASK6）", S_CAP))

    story.append(P(
        "结果显示，<b>集成模型显著优于单一模型</b>。梯度提升和随机森林的夏普比率"
        "分别达到3.41和2.91，远超逻辑回归（1.15）和决策树（-0.18）。"
        "梯度提升模型的累计收益最高（25.97%），且最大回撤为零，表现最为优异。"
        "决策树作为单一弱学习器，在多因子选股场景下能力不足，出现负收益。"
        "图9直观对比了四个模型在累计收益、夏普、胜率和回撤四个维度上的表现。"))
    story.extend(add_image(os.path.join(FIGS, "fig_ml_model_comparison.png"),
                            caption="图9  机器学习模型交易策略效果对比"))

    story.append(P(
        "在特征重要性方面，图10展示了随机森林模型中贡献最大的15个因子。"
        "衍生因子（如估值综合排名、成长综合排名）在重要性排名中位居前列，"
        "验证了特征工程的价值——通过信息综合和排名变换，"
        "衍生因子比单一原始因子具有更强的预测能力。"))
    story.extend(add_image(os.path.join(BASE, "TASK6", "feature_importance.png"),
                            width=12*cm, caption="图10  随机森林模型特征重要性排名（前15）"))

    story.append(PageBreak())

    # 3.4 优势与局限
    story.append(P("3.4  机器学习算法的优势与局限性", S_H2))
    story.append(P("3.4.1  优势", S_H3))
    story.append(P(
        "机器学习在量化交易中的优势体现在三个方面。"
        "<b>多维度信息整合</b>——模型可同时处理数十个因子，捕捉因子间的交互效应，"
        "这是人工分析难以企及的。"
        "<b>非线性关系发现</b>——决策树和集成模型能自动发现因子与收益间的"
        "非线性结构，如阈值效应和条件依赖。"
        "<b>自动化预测</b>——训练后的模型可快速对新数据生成预测，"
        "实现批量选股和动态调仓。"))

    story.append(P("3.4.2  局限性", S_H3))
    story.append(P(
        "机器学习同样存在不可忽视的局限。"
        "<b>过拟合风险</b>——模型可能在训练集上表现优异，但对未见数据泛化能力弱。"
        "TASK6中决策树的负收益即是过拟合的典型表现。"
        "<b>因子衰减</b>——市场是动态博弈系统，曾经有效的因子可能因套利行为而逐渐失效，"
        "模型需要持续监控和迭代。"
        "<b>市场状态切换</b>——模型在一种市场状态（如牛市）下训练，"
        "可能在另一种状态（如熊市）下完全失效。"
        "<b>数据窥探</b>——在回测中不自觉地使用了未来信息，"
        "如用全样本归一化、多次试参数等，导致回测结果虚高。"))

    story.append(P("3.5  未来发展趋势", S_H2))
    story.append(P(
        "机器学习在量化交易领域的发展趋势包括：<b>深度学习时序模型</b>——"
        "利用LSTM和Transformer等序列模型捕捉价格的时间依赖结构；"
        "<b>强化学习</b>——将交易建模为马尔可夫决策过程，"
        "让智能体通过试错学习最优交易策略；"
        "<b>替代数据</b>——利用自然语言处理技术从新闻、社交媒体、"
        "研报中提取情绪因子，补充传统量价和基本面信息；"
        "<b>自动化机器学习</b>——实现特征工程、模型选择和超参数优化的全自动化，"
        "降低量化策略开发的门槛。"))

    story.append(PageBreak())

    # ====================================================================
    # 第四章：策略寻优与实盘模拟
    # ====================================================================
    story.append(P("第四章  策略寻优与实盘模拟", S_H1))
    story.append(P(
        "本章基于TASK7的实践，分析双均线策略在长周期数据上的参数寻优与样本外实盘模拟结果，"
        "揭示过拟合风险和成本敏感性的实际影响。"))

    # 4.1 样本内参数寻优
    story.append(P("4.1  样本内参数寻优", S_H2))
    story.append(P(
        "TASK7使用宁德时代2019年1月至2024年12月（1456个交易日）的长周期数据，"
        "对双均线策略进行网格参数寻优。搜索范围为短均线{5, 8, 10, 15, 20}和"
        "长均线{20, 30, 40, 60, 120}的所有有效组合，以夏普比率为目标函数。"
        "图11展示了各参数组合的夏普分布热力图。"))
    story.extend(add_image(os.path.join(BASE, "TASK7", "figs", "fig4_param_heatmap.png"),
                            width=11*cm, caption="图11  样本内参数寻优夏普比率热力图"))

    story.append(P(
        f"寻优结果显示，最优参数为MA{M['best_short']}/MA{M['best_long']}，"
        f"样本内夏普{fmt_num(INS['夏普'])}，年化收益{fmt_pct(INS['年化收益'])}，"
        f"累计收益{fmt_pct(INS['累计收益'])}。"
        f"然而，从热力图可见，最优区域并非单一尖峰，而是一个较宽的「稳健区间」，"
        f"提示单点最优可能只是样本内噪声的产物。"))
    story.append(Spacer(1, 4))

    # 4.2 样本外实盘模拟
    story.append(P("4.2  样本外实盘模拟", S_H2))
    story.append(P(
        f"将样本内最优参数MA{M['best_short']}/MA{M['best_long']}直接应用于"
        f"样本外区间（2025年1月至2026年7月，{M['n_oos']}个交易日），进行前向测试。"
        f"同时以TASK3默认参数MA5/MA15作为对照。"))
    story.extend(add_image(os.path.join(BASE, "TASK7", "figs", "fig5_oos_nav.png"),
                            caption="图12  样本外策略净值曲线（最优参数 vs 默认参数）"))

    story.append(P(
        f"样本外表现出现了显著衰减：年化收益从{fmt_pct(INS['年化收益'])}降至"
        f"{fmt_pct(OOS['年化收益'])}（衰减{fmt_pct((INS['年化收益']-OOS['年化收益'])/INS['年化收益'])}），"
        f"夏普从{fmt_num(INS['夏普'])}降至{fmt_num(OOS['夏普'])}。"
        f"更值得深思的是，<b>样本内最优参数在样本外反而跑输默认参数</b>——"
        f"默认MA5/MA15的样本外夏普为{fmt_num(OOSD['夏普'])}，"
        f"年化为{fmt_pct(OOSD['年化收益'])}，均优于寻优参数。"
        f"这一结果深刻揭示了参数过拟合风险：网格寻优可能拟合了样本内的特定噪声，"
        f"而非捕捉了真正的市场规律。"))
    story.extend(add_image(os.path.join(FIGS, "fig_insample_oos.png"),
                            caption="图13  样本内 vs 样本外 vs 默认参数核心指标对比"))

    story.append(P(
        "图13直观展示了三组指标的对比：样本内（红柱）各项指标均领先，"
        "样本外寻优参数（蓝柱）全面衰减，而默认参数样本外（灰柱）在某些维度上"
        "反而优于寻优参数。这一发现呼应了附录建议1和5的核心观点。"))

    story.append(PageBreak())

    # 4.3 风险暴露分析
    story.append(P("4.3  风险暴露分析", S_H2))
    story.append(P(
        "TASK7对策略进行了全面的风险暴露分析，表7汇总了三组配置的核心风险指标。"))
    story.append(Spacer(1, 4))

    table7_data = [
        ["风险指标", "样本内（寻优）", "样本外（寻优）", "样本外（默认）"],
        ["年化波动率", fmt_pct(INS["年化波动"]), fmt_pct(OOS["年化波动"]), fmt_pct(OOSD["年化波动"])],
        ["最大回撤", fmt_pct(INS["最大回撤"]), fmt_pct(OOS["最大回撤"]), fmt_pct(OOSD["最大回撤"])],
        ["最大回撤时长(日)", fmt_num(INS["最大回撤时长(日)"], 0), fmt_num(OOS["最大回撤时长(日)"], 0), fmt_num(OOSD["最大回撤时长(日)"], 0)],
        ["日VaR(95%)", fmt_pct(INS["VaR95"]), fmt_pct(OOS["VaR95"]), fmt_pct(OOSD["VaR95"])],
        ["日CVaR(95%)", fmt_pct(INS["CVaR95"]), fmt_pct(OOS["CVaR95"]), fmt_pct(OOSD["CVaR95"])],
        ["Beta(对沪深300)", fmt_num(INS["Beta"]), fmt_num(OOS["Beta"]), fmt_num(OOSD["Beta"])],
        ["年化换手率", fmt_num(INS["年化换手率"]), fmt_num(OOS["年化换手率"]), fmt_num(OOSD["年化换手率"])],
        ["Calmar比率", fmt_num(INS["Calmar"]), fmt_num(OOS["Calmar"]), fmt_num(OOSD["Calmar"])],
    ]
    story.append(make_table(table7_data, col_widths=[4*cm, 4*cm, 4*cm, 4*cm]))
    story.append(P("表7  风险暴露指标对比", S_CAP))

    story.append(P(
        "风险分析揭示了几个重要发现。"
        f"<b>波动率控制</b>：策略的年化波动率（{fmt_pct(OOS['年化波动'])}）"
        f"显著低于基准持有不动（{fmt_pct(OOS['基准波动'])}），"
        "说明策略通过择时规避了部分高波动时段。"
        f"<b>尾部风险</b>：日VaR(95%)为{fmt_pct(OOS['VaR95'])}，"
        f"意味着在95%的交易日中，单日最大亏损不超过{fmt_pct(abs(OOS['VaR95']))}；"
        f"CVaR(95%)为{fmt_pct(OOS['CVaR95'])}，衡量了极端亏损日的平均损失。"
        f"<b>Beta暴露</b>：策略对沪深300的Beta约{fmt_num(OOS['Beta'])}，"
        "远低于1，说明策略具有低市场相关性，但也意味着在市场大涨时可能跑输基准。"))

    story.append(P(
        "成本敏感性是实盘中的关键考量。表8展示了不同滑点水平下策略样本外的表现。"))
    story.append(Spacer(1, 4))

    cost = M["cost_sensitivity"]
    table8_data = [["单边滑点", "年化收益", "夏普比率", "最大回撤"]]
    for c in cost:
        table8_data.append([
            f"{c['滑点']*100:.1f}%",
            fmt_pct(c["年化收益"]),
            fmt_num(c["夏普"]),
            fmt_pct(c["最大回撤"]),
        ])
    story.append(make_table(table8_data, col_widths=[4*cm, 4*cm, 4*cm, 4*cm]))
    story.append(P("表8  交易成本敏感性分析", S_CAP))

    story.append(P(
        f"滑点从0升至0.3%，年化收益从{fmt_pct(cost[0]['年化收益'])}降至"
        f"{fmt_pct(cost[-1]['年化收益'])}，降幅达"
        f"{fmt_pct((cost[0]['年化收益']-cost[-1]['年化收益'])/cost[0]['年化收益'])}。"
        "这一结果说明高频交易的趋势策略对成本高度敏感，"
        "在实盘部署中必须将佣金、滑点和印花税纳入回测。"))

    story.extend(add_image(os.path.join(FIGS, "fig_risk_dashboard.png"),
                            width=12*cm, caption="图14  风险调整后指标雷达图（归一化）"))
    story.extend(add_image(os.path.join(BASE, "TASK7", "figs", "fig8_sensitivity.png"),
                            width=11*cm, caption="图15  样本外参数敏感性热力图"))

    story.append(PageBreak())

    # ====================================================================
    # 第五章：结论与展望
    # ====================================================================
    story.append(P("第五章  结论与展望", S_H1))

    story.append(P("5.1  主要收获", S_H2))
    story.append(P(
        "通过七个任务的系统学习与实践，在理论、技术和实践三个层面均有显著收获。"
        "<b>理论层面</b>，系统理解了量化交易从数据到实盘的完整流程，"
        "掌握了趋势跟随和突破策略的设计逻辑，理解了机器学习在选股中的应用框架。"
        "<b>技术层面</b>，独立搭建了Python回测框架，实现了信号生成、回测引擎、"
        "指标计算和可视化的完整工具链；掌握了scikit-learn的分类和回归模型训练流程，"
        "完成了从特征工程到策略回测的端到端ML pipeline。"
        "<b>实践层面</b>，深刻认知了样本内外差异——回测好看不等于实盘能赚；"
        "理解了参数寻优的局限性——单点最优可能只是噪声拟合；"
        "认识到风险管理的重要性——止损和仓位管理比信号优化更具决定性。"))

    story.append(P("5.2  核心体会", S_H2))
    story.append(P(
        "在七个任务的实践中，形成了三条核心体会。"))
    story.append(P(
        "<b>第一，策略无圣杯。</b>"
        "任何参数在样本外都会衰减，TASK7中样本内夏普1.24在样本外降至0.45。"
        "更值得关注的是策略逻辑的合理性而非参数的过度拟合——"
        "一个逻辑清晰、风控完善的策略，即使参数不是「最优」，"
        "也比一个过拟合的「最优参数」策略更具长期生命力。"))
    story.append(P(
        "<b>第二，风控为王。</b>"
        "TASK4海龟策略的ATR止损和1%风险仓位管理，"
        "TASK7的趋势过滤和止损机制，都验证了风控的重要性。"
        "在趋势策略中，单笔亏损的控制比信号优化更能决定长期业绩——"
        "一次未止损的大跌可能抹掉数十次正确交易的积累。"))
    story.append(P(
        "<b>第三，样本外为王。</b>"
        "TASK7最深刻的教训是：样本内最优参数在样本外跑输默认参数。"
        "前向测试是检验策略是否「真有效」的最低门槛。"
        "任何策略在投入实盘前，都应预留充足的样本外数据进行验证，"
        "并持续监控实盘与回测的偏差。"))

    story.append(P("5.3  未来方向", S_H2))
    story.append(P(
        "基于当前学习成果，未来计划从以下方向深入探索。"
        "<b>多策略组合</b>——将双均线、海龟和ML选股策略组合运行，"
        "利用低相关性降低组合波动，实现更稳健的风险收益比。"
        "<b>滚动重训练</b>——对ML模型采用walk-forward方式，每季度滚动重训练，"
        "适应市场状态变化，缓解因子衰减问题。"
        "<b>深度学习时序建模</b>——探索LSTM和Transformer模型在价格预测中的应用，"
        "捕捉传统因子难以描述的时间序列结构。"
        "<b>替代数据挖掘</b>——利用自然语言处理技术从新闻和社交媒体中提取情绪因子，"
        "补充传统量价和基本面信息，增强模型的预测维度。"))

    story.append(PageBreak())

    # ====================================================================
    # 附录：改进建议
    # ====================================================================
    story.append(P("附录  改进建议", S_H1))
    story.append(P(
        "基于正文中各任务的分析结果，提出以下八条改进建议，"
        "正文中已按编号引用（如「附录建议1」「附录建议5」等）。"))

    suggestions = [
        ("建议1  双均线策略增加趋势过滤模块",
         "TASK3双均线策略在震荡市频繁产生虚假信号（参见2.1节）。"
         "参照TASK7的做法，增加120日均线趋势过滤——仅在收盘价高于趋势线时允许买入，"
         "可有效过滤下跌趋势中的假金叉信号。"
         "TASK7的实践表明，趋势过滤虽未提升样本内收益，但使回测更贴近现实。"),
        ("建议2  海龟策略增加成交量确认",
         "TASK4海龟策略的唐奇安通道突破存在假突破问题（参见2.2节）。"
         "建议在突破信号触发时增加成交量确认条件——"
         "突破日成交量需大于20日平均成交量的1.5倍方确认有效，"
         "可过滤低量假突破，提高信号可靠性。"),
        ("建议3  机器学习模型增加交叉验证与正则化",
         "TASK5和TASK6的模型可能在测试集上表现良好但泛化能力不足（参见3.3节）。"
         "建议增加时间序列交叉验证（TimeSeriesSplit），"
         "并对逻辑回归引入L1/L2正则化（调节C参数），"
         "对树模型增加min_samples_leaf和max_depth约束，"
         "防止模型过度拟合训练数据。"),
        ("建议4  采用滚动窗口重训练机制",
         "TASK6采用固定时间分割点（2021Q3），导致模型随时间推移逐渐老化（参见3.2节）。"
         "建议每季度滚动重训练模型——每次用最近N个季度的数据训练，"
         "预测下一季度，逐步向前推进。"
         "这种walk-forward方式能更好地适应市场状态变化，缓解因子衰减问题。"),
        ("建议5  优化交易成本与换手率",
         "TASK7的成本敏感性分析显示，滑点从0升至0.3%即侵蚀约27%的年化收益（参见4.3节）。"
         "建议降低交易频率——增加信号确认条件（如连续两日突破方执行），"
         "减少不必要的换手；同时在回测中严格纳入佣金、滑点和印花税成本，"
         "避免「免费回测」的虚假乐观。"),
        ("建议6  构建多标的组合分散集中风险",
         "TASK3、TASK4和TASK7均以宁德时代单一标的为操作对象（参见2.1、2.2、4.1节），"
         "个股集中风险极高——一次业绩冲击或政策变化即可造成重大损失。"
         "建议扩展为多股票组合，如选取5至10只不同行业的趋势性标的等权运行策略，"
         "利用标的间低相关性降低组合波动和尾部风险。"),
        ("建议7  深化特征工程维度",
         "TASK6的特征以基本面因子为主（估值+成长），缺少技术面和市场情绪因子（参见3.1节）。"
         "建议增加技术面因子（如MACD动量、RSI超买超卖、布林带位置），"
         "以及市场情绪因子（如北向资金持仓变化、融资融券余额变动、换手率异动），"
         "丰富模型的信息维度，提升预测的全面性。"),
        ("建议8  建立动态仓位管理机制",
         "当前策略仓位为全仓（TASK3双均线）或固定1%风险（TASK4海龟），"
         "缺乏根据市场状态动态调整的机制（参见2.4节、4.3节）。"
         "建议引入波动率目标仓位——当市场波动率（如VIX或ATR）放大时自动减仓，"
         "波动率收敛时恢复正常仓位。"
         "同时可基于市场状态识别（趋势/震荡）动态调整策略间的资金分配权重。"),
    ]

    for title, content in suggestions:
        story.append(P(title, S_H3))
        story.append(P(content, S_BODY))
        story.append(Spacer(1, 6))

    return story


# ========================================================================
# 主函数
# ========================================================================
def main():
    print("=" * 60)
    print("TASK8 PDF 报告生成")
    print("=" * 60)

    story = build_story()

    doc = ReportDocTemplate(
        OUT,
        pagesize=A4,
        leftMargin=MARGIN_L, rightMargin=MARGIN_R,
        topMargin=MARGIN_T, bottomMargin=MARGIN_B,
        title="量化交易策略开发与机器学习应用——学习实践报告",
        author="夏阳",
    )

    # 两遍构建：第一遍收集TOC，第二遍生成最终PDF
    doc.multiBuild(story)
    print(f"\nPDF 报告已生成: {OUT}")
    print(f"文件大小: {os.path.getsize(OUT) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
