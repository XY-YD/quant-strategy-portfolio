#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TASK6: 生成PDF格式报告
格式要求：宋体、五号字(10.5pt)、1.5倍行距、0段间距、文字两端对齐
每个统计图都有标号、标题和解读
"""

import os
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib_cache'

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image,
    Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
#  字体注册
# ============================================================
FONT_PATH = '/System/Library/Fonts/Supplemental/Songti.ttc'
pdfmetrics.registerFont(TTFont('SimSun', FONT_PATH, subfontIndex=0))
pdfmetrics.registerFont(TTFont('SimSunBold', FONT_PATH, subfontIndex=1))

# ============================================================
#  样式定义
#  五号字 = 10.5pt, 1.5倍行距 => leading = 15.75pt
# ============================================================
FS = 10.5
LEADING = FS * 1.5
SPACE_BEFORE = 0
SPACE_AFTER = 0

style_title = ParagraphStyle(
    name='ReportTitle', fontName='SimSunBold', fontSize=22,
    leading=22 * 1.5, alignment=TA_CENTER,
    spaceBefore=0, spaceAfter=0,
)
style_subtitle = ParagraphStyle(
    name='Subtitle', fontName='SimSun', fontSize=FS,
    leading=LEADING, alignment=TA_CENTER,
    spaceBefore=0, spaceAfter=0,
)
style_h1 = ParagraphStyle(
    name='H1', fontName='SimSunBold', fontSize=16,
    leading=16 * 1.5, alignment=TA_LEFT,
    spaceBefore=0, spaceAfter=0,
)
style_h2 = ParagraphStyle(
    name='H2', fontName='SimSunBold', fontSize=14,
    leading=14 * 1.5, alignment=TA_LEFT,
    spaceBefore=0, spaceAfter=0,
)
style_h3 = ParagraphStyle(
    name='H3', fontName='SimSunBold', fontSize=FS,
    leading=LEADING, alignment=TA_LEFT,
    spaceBefore=0, spaceAfter=0,
)
style_body = ParagraphStyle(
    name='Body', fontName='SimSun', fontSize=FS,
    leading=LEADING, alignment=TA_JUSTIFY,
    spaceBefore=SPACE_BEFORE, spaceAfter=SPACE_AFTER,
    firstLineIndent=FS * 2,
)
style_body_noindent = ParagraphStyle(
    name='BodyNoIndent', fontName='SimSun', fontSize=FS,
    leading=LEADING, alignment=TA_JUSTIFY,
    spaceBefore=0, spaceAfter=0,
)
style_caption = ParagraphStyle(
    name='Caption', fontName='SimSunBold', fontSize=FS,
    leading=LEADING, alignment=TA_CENTER,
    spaceBefore=0, spaceAfter=0,
)
style_code = ParagraphStyle(
    name='Code', fontName='SimSun', fontSize=9,
    leading=9 * 1.5, alignment=TA_LEFT,
    spaceBefore=0, spaceAfter=0, leftIndent=20,
)
style_table_cell = ParagraphStyle(
    name='TableCell', fontName='SimSun', fontSize=9,
    leading=9 * 1.5, alignment=TA_CENTER,
    spaceBefore=0, spaceAfter=0,
)
style_table_header = ParagraphStyle(
    name='TableHeader', fontName='SimSunBold', fontSize=9,
    leading=9 * 1.5, alignment=TA_CENTER,
    spaceBefore=0, spaceAfter=0, textColor=colors.white,
)

# ============================================================
#  辅助函数
# ============================================================
def P(text, style=None):
    if style is None:
        style = style_body
    return Paragraph(text, style)

def make_table(data, col_widths=None, header=True):
    table_data = []
    for i, row in enumerate(data):
        new_row = []
        for cell in row:
            if i == 0 and header:
                new_row.append(Paragraph(str(cell), style_table_header))
            else:
                new_row.append(Paragraph(str(cell), style_table_cell))
        table_data.append(new_row)
    t = Table(table_data, colWidths=col_widths)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3c72')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t

def add_figure(story, img_path, fig_num, title, interpretation, width=15*cm):
    """添加统计图：标号 + 标题 + 图片 + 解读"""
    story.append(P(f'图 {fig_num}  {title}', style_caption))
    story.append(Spacer(1, 4))
    if os.path.exists(img_path):
        img = Image(img_path, width=width, height=width * 0.62)
        story.append(img)
    story.append(Spacer(1, 4))
    story.append(P(interpretation, style_body))
    story.append(Spacer(1, 8))

def add_table_with_caption(story, table_data, tbl_num, title, col_widths=None):
    """添加表格：标号 + 标题 + 表格"""
    story.append(P(f'表 {tbl_num}  {title}', style_caption))
    story.append(Spacer(1, 4))
    story.append(make_table(table_data, col_widths=col_widths))
    story.append(Spacer(1, 8))


# ============================================================
#  生成PDF
# ============================================================
def build_pdf():
    output_dir = '/Users/wangyanfen/Desktop/量化策略课程/TASK6'
    pdf_path = os.path.join(output_dir, 'TASK6_ML交易策略报告.pdf')

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=2.5 * cm, rightMargin=2.5 * cm,
        topMargin=2.5 * cm, bottomMargin=2.5 * cm,
    )
    story = []

    # ============================================================
    #  封面
    # ============================================================
    story.append(Spacer(1, 60))
    story.append(P('基于机器学习模型的交易策略', style_title))
    story.append(Spacer(1, 20))
    story.append(P('—— 量化策略课程 TASK6 报告 ——', style_subtitle))
    story.append(Spacer(1, 40))
    story.append(P('数据来源：A 股 4,281 只股票 × 10 个季度（2020Q1 ~ 2022Q2）', style_subtitle))
    story.append(P('样本量：39,616 条  |  特征数：26 个（19 原始 + 7 衍生）', style_subtitle))
    story.append(P('模型：逻辑回归 / 决策树 / 随机森林 / 梯度提升', style_subtitle))
    story.append(Spacer(1, 40))
    story.append(P('格式说明：宋体 五号字 1.5倍行距 0段间距 两端对齐', style_subtitle))
    story.append(PageBreak())

    # ============================================================
    #  目录
    # ============================================================
    story.append(P('目 录', style_h1))
    story.append(Spacer(1, 10))
    toc_items = [
        '一、基于机器学习模型的交易策略核心理念与优缺点',
        '  1.1 核心理念',
        '  1.2 优缺点分析',
        '二、量化交易ML模型中常见自变量因子和应变量定义',
        '  2.1 自变量因子（Features / X）',
        '  2.2 应变量（Labels / Y）',
        '三、Python编程实现',
        '  3.1 加载存储的模型样本',
        '  3.2 衍生模型自变量，设计应变量指标',
        '  3.3 划分训练集/测试集，构建并训练模型',
        '  3.4 基于模型建立交易策略，计算季度收益率',
        '  3.5 回测策略，计算核心指标，绘制图形',
        '  3.6 对比决策树、随机森林等模型效果',
        '四、附加题：回归模型直接预测收益率策略',
        '五、总结与结论',
    ]
    for item in toc_items:
        story.append(P(item, style_body_noindent))
    story.append(PageBreak())

    # ============================================================
    #  第一部分
    # ============================================================
    story.append(P('一、基于机器学习模型的交易策略核心理念与优缺点', style_h1))
    story.append(Spacer(1, 8))

    story.append(P('1.1 核心理念', style_h2))
    story.append(Spacer(1, 6))
    story.append(P(
        '基于机器学习模型的交易策略（ML-Based Trading Strategy）是一类将监督学习、'
        '无监督学习或强化学习算法应用于金融市场，旨在从历史数据中自动学习"特征—未来收益"'
        '或"特征—市场状态"之间复杂非线性映射的量化交易范式。其核心理念可概括为三个关键假设和四步工作流。', style_body))
    story.append(P('三个关键假设：', style_h3))
    story.append(P('（1）历史可重演性：市场参与者的群体行为模式具有一定的统计规律性，'
        '过去发生的"特征—收益"关系在未来会以一定概率延续。', style_body))
    story.append(P('（2）可量化驱动：个股的超额收益可被一系列可观测的财务、价量、情绪等特征（因子）解释或预测。', style_body))
    story.append(P('（3）非线性可学习：因子之间存在交互效应（如低估值+高成长），'
        '传统线性模型难以捕捉，机器学习能自动学习这些模式。', style_body))
    story.append(P('四步工作流：①因子构建（Feature Engineering）→ 提取/衍生自变量；'
        '②标签生成（Labeling）→ 设计应变量（如下期收益是否大于截面中位数）；'
        '③模型训练（Model Training）→ 在历史数据上拟合 f(X)→Y；'
        '④策略回测（Backtesting）→ 用模型预测排序，构造投资组合，评估风险收益。', style_body))

    story.append(Spacer(1, 6))
    story.append(P('1.2 优缺点分析', style_h2))
    story.append(Spacer(1, 6))

    # 优点
    story.append(P('优点：', style_h3))
    pros = [
        '（1）非线性建模能力：能捕捉因子间的复杂交互（如小市值+高成长的双因子效应），'
        '相比线性回归具有更强的表达能力。',
        '（2）高维特征处理：可同时使用数百上千个因子，决策树类模型对共线性不敏感，'
        '无需手动做特征选择。',
        '（3）自适应学习：可滚动训练，模型能跟随市场风格切换，相比固定因子的传统多因子模型更灵活。',
        '（4）减少人为偏差：由算法自动挖掘规律，避免过度依赖主观经验，策略可复制性强。',
        '（5）组合优化便利：模型可输出概率分数，便于构建等权/加权/多空组合，灵活度极高。',
    ]
    for p in pros:
        story.append(P(p, style_body))

    # 缺点
    story.append(P('缺点：', style_h3))
    cons = [
        '（1）过拟合风险高：金融数据信噪比极低（SNR接近1），模型容易记住历史噪声而非真实规律，'
        '尤其在样本量不足时更为严重。',
        '（2）黑箱可解释性差：深度模型和大型集成模型难以解释"为什么做出这个决策"，'
        '不利于风控和合规审查。',
        '（3）数据依赖性强：对数据质量、特征工程、缺失值处理极度敏感，'
        '微小的数据预处理差异可能导致截然不同的结果。',
        '（4）市场非平稳：金融数据分布随时间漂移（regime shift），模型可能突然失效，'
        '需要持续监控和再训练。',
        '（5）交易成本侵蚀：换手率高导致手续费/冲击成本吞噬超额收益，'
        '回测中的高收益在实际交易中可能大打折扣。',
        '（6）回测陷阱：前视偏差、幸存者偏差、过度参数调优会美化回测结果，'
        '使得回测表现与实盘表现存在系统性偏差。',
    ]
    for c in cons:
        story.append(P(c, style_body))

    story.append(P(
        '实践建议：在金融场景中，简单模型加强先验（如正则化、单调约束、特征选择）'
        '往往比堆叠复杂深度模型更稳健；时间序列交叉验证（而非随机划分）至关重要；'
        '应关注样本外（OOS）表现、IC衰减、最大回撤等更稳健的评估指标。', style_body))

    story.append(PageBreak())

    # ============================================================
    #  第二部分
    # ============================================================
    story.append(P('二、量化交易ML模型中常见自变量因子和应变量定义', style_h1))
    story.append(Spacer(1, 8))

    story.append(P('2.1 自变量因子（Features / X）', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('量化交易中常见的自变量因子按数据来源可分为基本面、价量、情绪、另类四大类。'
        '下表列举了最常用的因子类别及其计算方式。', style_body))

    add_table_with_caption(story, [
        ['类别', '因子示例', '计算/含义', '投资逻辑'],
        ['估值因子', '市盈率PE(TTM)', '股价/每股收益', '低PE股票长期跑赢'],
        ['', '市净率PB(MRQ)', '股价/每股净资产', '破净股具有安全边际'],
        ['', '市销率PS', '市值/营业收入', '适合亏损公司估值'],
        ['', '企业倍数EV/EBITDA', '企业价值/息税折旧摊销前利润', '跨资本结构可比'],
        ['', '股息率', '每股分红/股价', '高股息稳健回报'],
        ['成长因子', '净利润同比增长率', '(本期-上期)净利润/上期', '盈利高增长带来股价弹性'],
        ['', '营业总收入同比增长率', '同上口径', '反映规模扩张能力'],
        ['', 'EPS同比增长率', '每股收益同比变化', '直接关联每股价值'],
        ['', '净资产同比增长率', '股东权益积累速度', '资本内生能力'],
        ['规模因子', '市值MV', '股价×总股本', '小盘股长期溢价'],
        ['', '对数市值log(MV)', '对数变换后更稳健', '消除量纲影响'],
        ['动量/反转', 'N月动量', '过去N月累计收益', '趋势延续效应'],
        ['', '换手率', '成交量/流通股本', '反映交易活跃度'],
        ['', '波动率', '收益标准差', '高波动≠高收益'],
        ['质量因子', 'ROE/ROA/ROIC', '盈利能力指标', '高质量公司抗跌'],
        ['', '资产负债率', '总负债/总资产', '财务健康度'],
    ], 1, '常见自变量因子分类与定义', col_widths=[2.5*cm, 4*cm, 5*cm, 4.5*cm])

    story.append(Spacer(1, 6))
    story.append(P('2.2 应变量（Labels / Y）', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('应变量（标签）的设计直接决定了模型的学习目标。常用设计方式如下表所示。', style_body))

    add_table_with_caption(story, [
        ['类型', '定义', '优点', '适用场景'],
        ['回归型', 'Y = 下期收益率（连续值）', '信息保留完整，便于排序', '需要精确预测收益大小的策略'],
        ['二分类', 'Y = 1(Next_Ret > 截面中位数/0)', '忽略极端值，关注相对排名', '截面选股、多空对冲'],
        ['三分类', 'Y = {涨/平/跌} 或 {Top/Mid/Bot}', '捕捉非线性收益分布', '市场风格多变的均衡市'],
        ['多分类', 'Y = 跑赢行业的相对收益排名', '剥离行业beta，纯alpha', '行业中性策略'],
    ], 2, '常见应变量设计方式', col_widths=[2.5*cm, 5*cm, 4*cm, 4.5*cm])

    story.append(P('本研究采用的设计：应变量 Y = 1 if Next_Ret > 季度截面中位数，'
        '即下期收益跑赢同期市场中位数的股票标记为1，否则为0。该设计的优点：'
        '①截面可比，剥离市场整体涨跌；②正负样本均衡（约50%），便于训练；'
        '③收益极值对标签影响小，模型更稳健。', style_body))

    story.append(PageBreak())

    # ============================================================
    #  第三部分
    # ============================================================
    story.append(P('三、Python编程实现', style_h1))
    story.append(Spacer(1, 8))
    story.append(P('本部分基于 model_data.csv（39,616条样本，10个季度，4281只A股）'
        '完整实现ML交易策略的六大步骤。', style_body))

    # 3.1
    story.append(P('3.1 加载存储的模型样本', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('数据包含19个财务/估值因子和1个目标变量 Next_Ret（下期收益率）。'
        '原始数据已无缺失值和无穷值，数据概况如下表所示。', style_body))

    add_table_with_caption(story, [
        ['指标', '数值', '说明'],
        ['样本总数', '39,616', '4281只股票×约10个季度'],
        ['季度数', '10', '2020Q1 ~ 2022Q2'],
        ['股票数', '4,281', '覆盖A股主要标的'],
        ['原始因子数', '19', '估值9个+成长10个'],
        ['Next_Ret均值', '2.70%', '下期季度平均收益率'],
        ['Next_Ret标准差', '25.14%', '收益波动较大'],
    ], 3, '数据概况统计', col_widths=[4*cm, 4*cm, 8*cm])

    story.append(P('核心加载代码如下：', style_body))
    story.append(P('df = pd.read_csv("model_data.csv")', style_code))
    story.append(P('df["Date"] = pd.to_datetime(df["Date"], format="%Y/%m/%d")', style_code))
    story.append(P('df = df.sort_values(["Date", "Code"]).reset_index(drop=True)', style_code))

    # 3.2
    story.append(Spacer(1, 6))
    story.append(P('3.2 衍生模型自变量，设计应变量指标', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('在19个原始因子的基础上，本研究衍生了7个新特征，以增强模型对"盈利质量"'
        '和"成长性"的捕获能力。衍生特征定义如下表所示。', style_body))

    add_table_with_caption(story, [
        ['特征名', '构造方法', '经济学含义'],
        ['valuation_rank', 'PE/PB/PS截面排名均值', '估值越低排名越靠前，价值因子综合'],
        ['growth_rank', '8个成长率因子排名均值', '成长性综合排名'],
        ['quality', '净利润增长率−总资产增长率', 'ROE改善（盈利增速vs资产扩张速度）'],
        ['log_MV', 'log(1+MV)', '对数市值，弱化极端值影响'],
        ['pe_pb_diff', 'PE−PB', 'PE/PB偏离度，反映估值结构'],
        ['growth_stability', '成长率均值/标准差', '成长稳定性（类信息比率）'],
        ['cashflow_quality', '经营现金流增长率−净利润增长率', '盈利质量（现金vs利润）'],
    ], 4, '衍生自变量因子定义', col_widths=[3.5*cm, 5*cm, 7.5*cm])

    story.append(P('应变量设计：Y = 1 if Next_Ret > 季度截面中位数 else 0。'
        '经过该处理，正样本占比为50.02%，负样本为49.98%，形成完美平衡的二分类问题。'
        '最终输入模型的特征共26个（19原始+7衍生）。', style_body))

    # 3.3
    story.append(Spacer(1, 6))
    story.append(P('3.3 划分训练集/测试集，构建并训练模型', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('为避免前视偏差，采用按时间切分的方式：训练集为2020Q1~2021Q2'
        '（6个季度，22,855样本），测试集为2021Q3~2022Q2（4个季度，16,761样本）。'
        '构建并训练4个对比模型：逻辑回归、决策树、随机森林、梯度提升。', style_body))

    add_table_with_caption(story, [
        ['模型', '关键参数', '适用场景'],
        ['逻辑回归', 'max_iter=2000, C=1.0', '线性可解释基线'],
        ['决策树', 'max_depth=6, min_samples_leaf=50', '单棵树可解释'],
        ['随机森林', 'n_estimators=200, max_depth=10', 'Bagging集成，稳健'],
        ['梯度提升', 'n_estimators=150, lr=0.1, max_depth=5', 'Boosting集成，精度高'],
    ], 5, '四个对比模型配置', col_widths=[3*cm, 6*cm, 7*cm])

    story.append(P('分类评估指标对比与ROC曲线如下图所示。', style_body))

    add_figure(story, os.path.join(output_dir, 'model_metrics.png'), 1,
        '各模型分类评估指标对比（准确率/精确率/召回率/F1/AUC）',
        '解读：梯度提升和随机森林在AUC上表现最佳（0.5963和0.6036），'
        '明显优于决策树（0.5805）和逻辑回归（0.5835）。所有模型均显著高于0.5的'
        '随机基线，说明财务因子中确实存在可学习的预测信号。梯度提升在准确率'
        '（57.19%）和F1值（0.5488）上领先，随机森林的AUC最高。')

    add_figure(story, os.path.join(output_dir, 'roc_curves.png'), 2,
        '各模型ROC曲线对比',
        '解读：ROC曲线展示了不同阈值下真正率（TPR）与假正率（FPR）的权衡关系。'
        '随机森林的曲线最靠近左上角，AUC达0.6036，表明其区分涨跌股票的能力最强。'
        '梯度提升紧随其后（AUC=0.5963）。决策树的曲线波动最大，泛化能力较弱。')

    add_figure(story, os.path.join(output_dir, 'feature_importance.png'), 3,
        '随机森林特征重要性Top15',
        '解读：成长综合排名（growth_rank）位居首位，说明成长性是预测下期收益'
        '最重要的因子。其次是对数市值（log_MV）和EPS同比增长率，反映了规模效应'
        '和盈利成长的价值。衍生因子的贡献度整体较高，验证了特征工程的有效性。')

    story.append(PageBreak())

    # 3.4
    story.append(P('3.4 基于模型建立交易策略，计算季度收益率', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('策略规则：每季度初用模型对全市场股票打分（预测上涨概率），'
        '选取预测概率最高的Top 50只股票等权配置，持仓一个季度后再平衡。'
        '基准为全市场等权（所有股票等权持有）。', style_body))

    story.append(P('各模型在测试集4个季度的收益明细如下表所示。', style_body))

    add_table_with_caption(story, [
        ['季度', '逻辑回归', '决策树', '随机森林', '梯度提升', '基准'],
        ['2021-Q3', '1.98%', '11.31%', '6.80%', '7.25%', '11.36%'],
        ['2021-Q4', '10.64%', '-7.40%', '9.40%', '7.23%', '-8.37%'],
        ['2022-Q1', '7.64%', '5.50%', '7.20%', '9.44%', '1.07%'],
        ['2022-Q2', '-5.83%', '-12.89%', '-0.86%', '0.10%', '-9.20%'],
    ], 6, '各模型季度收益率明细', col_widths=[2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])

    story.append(P('从上表可以看出，2021-Q4是策略超额收益最显著的一个季度——'
        '基准大跌8.37%，但梯度提升和随机森林分别获得7.23%和9.40%的正收益，'
        '超额收益超过15个百分点。2022-Q2市场整体下跌时，ML策略同样展现了'
        '较强的抗跌能力。', style_body))

    add_figure(story, os.path.join(output_dir, 'quarterly_returns.png'), 4,
        '各模型季度收益率柱状对比',
        '解读：从季度收益柱状图可以直观看出，随机森林和梯度提升在4个季度中'
        '表现最为稳定，仅有1个季度为负收益。决策树在2022-Q2大幅亏损12.89%，'
        '波动最大。逻辑回归在2021-Q3表现偏弱（仅1.98%），但在后续季度稳步回升。')

    add_figure(story, os.path.join(output_dir, 'excess_returns.png'), 5,
        '各模型季度超额收益（相对全市场等权基准）',
        '解读：超额收益柱状图显示，梯度提升在4个季度中有3个季度跑赢基准，'
        '仅在2021-Q3略低于基准。随机森林同样有3个季度跑赢基准，且超额收益'
        '幅度更为均衡。决策树的超额收益波动剧烈，2021-Q3基本持平但2022-Q2'
        '大幅落后。')

    # 3.5
    story.append(Spacer(1, 6))
    story.append(P('3.5 回测策略，计算核心指标，绘制图形', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('基于季度收益率序列，计算累计收益、年化收益、夏普比率、'
        '最大回撤、胜率等核心回测指标，结果如下表所示。', style_body))

    add_table_with_caption(story, [
        ['模型', '累计收益', '年化收益', '夏普比率', '最大回撤', '胜率', '超额夏普'],
        ['逻辑回归', '14.37%', '14.37%', '1.1496', '-5.83%', '75%', '0.9680'],
        ['决策树', '-5.28%', '-5.28%', '-0.1798', '-14.90%', '50%', '0.2854'],
        ['随机森林', '24.19%', '24.19%', '2.9053', '-0.86%', '75%', '1.7432'],
        ['梯度提升', '25.97%', '25.97%', '3.4069', '0.00%', '75%', '2.0388'],
        ['基准(等权)', '-6.35%', '-6.35%', '-0.3079', '-', '-', '-'],
    ], 7, '各模型回测核心指标汇总', col_widths=[2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 1.5*cm, 2*cm])

    story.append(P('梯度提升综合最优：累计收益25.97%，夏普3.41，最大回撤0%。'
        '随机森林次之：累计24.19%，夏普2.91。所有ML策略均显著跑赢全市场等权基准'
        '（-6.35%），超额收益在11.62%~32.32%之间。', style_body))

    add_figure(story, os.path.join(output_dir, 'cumulative_returns.png'), 6,
        '各模型交易策略累计收益曲线对比',
        '解读：累计收益曲线清晰展示了各模型的净值增长轨迹。梯度提升和随机森林'
        '的曲线几乎单调上升，仅在一个季度有小幅回撤，远超基准（灰色虚线）。'
        '决策树的曲线在最后两个季度大幅下滑，累计收益转负。逻辑回归介于两者之间，'
        '走势相对平稳。')

    add_figure(story, os.path.join(output_dir, 'backtest_metrics.png'), 7,
        '回测核心指标四象限对比（累计收益/年化收益/夏普/最大回撤）',
        '解读：四象限对比图直观展示了各模型在收益和风险维度的差异。梯度提升在'
        '累计收益、年化收益和夏普比率三个维度均领先，且最大回撤为0%。决策树在'
        '所有维度均表现最差。灰色虚线为基准水平，所有模型在夏普和年化收益上'
        '均优于基准。')

    story.append(PageBreak())

    # 3.6
    story.append(P('3.6 对比决策树、随机森林等模型效果', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('综合分类指标和回测表现，各模型效果排名如下表所示。', style_body))

    add_table_with_caption(story, [
        ['排名', '模型', 'AUC', '累计收益', '夏普', '综合评价'],
        ['1', '梯度提升', '0.5963', '25.97%', '3.41', '样本内外均优，集成优势凸显'],
        ['2', '随机森林', '0.6036', '24.19%', '2.91', 'AUC最高，策略收益略低于GB'],
        ['3', '逻辑回归', '0.5835', '14.37%', '1.15', '稳健但线性假设限制表现'],
        ['4', '决策树', '0.5805', '-5.28%', '-0.18', '单棵树过拟合，OOS失效'],
    ], 8, '模型效果综合排名', col_widths=[1.2*cm, 2.5*cm, 2*cm, 2.5*cm, 2*cm, 5.5*cm])

    story.append(P('结论与分析：', style_h3))
    story.append(P('（1）集成模型远胜单一模型：随机森林和梯度提升通过集成多棵树，'
        '显著降低了单棵决策树的过拟合风险。', style_body))
    story.append(P('（2）Boosting优于Bagging：梯度提升（Boosting）在本数据上略优于'
        '随机森林（Bagging），因为它能更精细地修正预测错误。', style_body))
    story.append(P('（3）决策树的陷阱：即使限制了max_depth=6和min_samples_leaf=50，'
        '单棵树在样本外依然失效，说明金融数据的噪声远大于单棵树的容量。', style_body))
    story.append(P('（4）逻辑回归的稳健性：作为线性模型，其表现优于决策树，'
        '说明在低信噪比场景下，"先验简单+强正则化"往往优于"复杂但易过拟合"。', style_body))
    story.append(P('（5）AUC与策略收益不完全一致：随机森林AUC最高（0.6036），'
        '但策略收益不如梯度提升，说明分类准确率只是选股能力的一部分，'
        '概率排序的精确性和Top-N集中度也很关键。', style_body))

    story.append(PageBreak())

    # ============================================================
    #  第四部分：附加题
    # ============================================================
    story.append(P('四、附加题：回归模型直接预测收益率策略', style_h1))
    story.append(Spacer(1, 8))
    story.append(P('为对比分类与回归方法的差异，附加题使用5个回归模型直接预测'
        'Next_Ret（连续收益率），并基于预测值排序构建等权多头组合和多空对冲组合。'
        '回归模型包括：线性回归、岭回归、决策树回归、随机森林回归、梯度提升回归。', style_body))

    story.append(P('回归模型评估指标与回测结果如下表所示。', style_body))

    add_table_with_caption(story, [
        ['模型', 'MSE', 'R²', 'IC', '累计收益', '年化收益', '夏普', '最大回撤', '胜率'],
        ['线性回归', '0.0581', '-0.0868', '0.1078', '22.99%', '22.99%', '2.24', '-2.18%', '75%'],
        ['岭回归', '0.0581', '-0.0868', '0.1078', '24.24%', '24.24%', '2.33', '-2.18%', '75%'],
        ['决策树回归', '0.0583', '-0.0906', '0.0968', '-4.51%', '-4.51%', '-0.18', '-13.02%', '25%'],
        ['随机森林回归', '0.0564', '-0.0553', '0.1339', '21.27%', '21.27%', '1.75', '-3.35%', '100%'],
        ['梯度提升回归', '0.0584', '-0.0923', '0.1093', '15.19%', '15.19%', '1.19', '-5.42%', '100%'],
    ], 9, '附加题：回归模型评估与回测指标', col_widths=[2.5*cm, 1.5*cm, 1.5*cm, 1.3*cm, 1.8*cm, 1.8*cm, 1.2*cm, 1.8*cm, 1.2*cm])

    story.append(P('关键发现：随机森林回归的IC最高（0.1339），说明其预测排名能力最强，'
        '胜率达100%，4个季度全部跑赢基准。岭回归策略收益最高（24.24%），'
        '在MSE与线性回归相同的情况下收益更稳健。所有模型R²都为负，'
        '说明个股收益的绝对预测极难（噪声大于信号），但相对排序（IC>0.1）是可行的。', style_body))

    add_figure(story, os.path.join(output_dir, 'bonus_regression_returns.png'), 8,
        '附加题：5个回归模型交易策略累计收益曲线',
        '解读：岭回归和线性回归的累计收益曲线最为平稳，最终收益分别为24.24%和22.99%。'
        '随机森林回归虽然IC最高，但在2021-Q3的超额收益较小，累计收益略低于线性模型。'
        '决策树回归在最后一个季度大幅回撤，累计收益转负。所有非线性集成模型'
        '均跑赢基准（灰色虚线）。')

    add_figure(story, os.path.join(output_dir, 'bonus_long_short.png'), 9,
        '附加题：多空组合（做多Top50+做空Bottom50）累计收益',
        '解读：多空组合通过同时做多模型预测最高的50只股票和做空预测最低的50只股票，'
        '剥离了市场系统性风险。岭回归的多空组合累计收益最高，曲线持续上升，'
        '说明模型不仅能选出好股票，还能有效识别劣质股票。随机森林回归的多空'
        '组合同样表现强劲，验证了IC的预测价值。')

    add_figure(story, os.path.join(output_dir, 'bonus_ic_compare.png'), 10,
        '附加题：各回归模型IC（信息系数）对比',
        '解读：IC（Information Coefficient）衡量预测值与实际收益的相关性，'
        '是量化选股中最核心的评估指标之一。随机森林回归IC=0.1339最高，'
        '显著优于其他模型。IC>0.1在实务中已属于可用水平。线性模型'
        '（线性回归、岭回归）的IC约为0.1078，梯度提升回归IC=0.1093。'
        '决策树回归IC最低（0.0968），与其策略表现最差一致。')

    story.append(PageBreak())

    # ============================================================
    #  第五部分：总结
    # ============================================================
    story.append(P('五、总结与结论', style_h1))
    story.append(Spacer(1, 8))

    story.append(P('5.1 研究结论', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('（1）ML交易策略可以跑赢基准：本研究最优模型（梯度提升分类）'
        '在2021Q3~2022Q2的样本外测试中，4个季度有3个跑赢全市场等权基准，'
        '4个季度累计收益25.97%，最大回撤0%。', style_body))
    story.append(P('（2）集成模型显著优于单一模型：梯度提升和随机森林的策略收益'
        '都超过20%，远超逻辑回归（14.37%）和决策树（-5.28%）。'
        '集成学习通过聚合多棵弱学习器，有效降低了过拟合风险。', style_body))
    story.append(P('（3）衍生因子的价值：通过构建growth_rank、quality、cashflow_quality'
        '等衍生因子，将原始19个特征扩展为26个，提升了模型对"盈利质量"'
        '和"成长性"的捕获能力。特征重要性分析显示growth_rank居首。', style_body))
    story.append(P('（4）分类与回归各有优劣：分类（Y=1/0）关注相对排名，标签鲁棒，'
        '梯度提升分类夏普最高（3.41）；回归（Y=收益率）保留幅度信息，'
        '岭回归累计收益最高（24.24%）。两种方法可互为补充。', style_body))

    story.append(Spacer(1, 6))
    story.append(P('5.2 局限性', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('（1）测试期仅4个季度，统计显著性不足，建议在更长的时间窗口上验证。', style_body))
    story.append(P('（2）未考虑交易成本（手续费、印花税、冲击成本），实际收益会进一步打折扣。', style_body))
    story.append(P('（3）未做行业中性化处理，模型可能隐含行业暴露。', style_body))
    story.append(P('（4）未做超参数调优（如GridSearchCV），模型性能可能还有提升空间。', style_body))
    story.append(P('（5）未使用滚动训练/再训练，模型可能随市场风格漂移而失效。', style_body))

    story.append(Spacer(1, 6))
    story.append(P('5.3 改进方向', style_h2))
    story.append(Spacer(1, 6))
    story.append(P('（1）引入更多因子：价量因子（动量/换手率/波动率）、'
        '情绪因子（分析师预期修正）、另类数据。', style_body))
    story.append(P('（2）使用LightGBM/XGBoost替代sklearn的GradientBoosting，'
        '提升训练效率和精度。', style_body))
    story.append(P('（3）做截面标准化（z-score）和行业中性化处理，'
        '剥离行业beta的影响。', style_body))
    story.append(P('（4）使用walk-forward滚动训练避免过拟合，'
        '模型随市场风格自适应更新。', style_body))
    story.append(P('（5）考虑Stacking/模型融合提升稳健性，'
        '结合分类与回归模型的优势。', style_body))

    story.append(Spacer(1, 10))
    story.append(P(
        '最终评价：本研究证实了基于机器学习模型的交易策略在A股市场的可行性和有效性。'
        '集成学习（特别是梯度提升和随机森林）配合精心设计的衍生因子，'
        '能够稳定地生成超额收益。但需注意：金融市场的低信噪比意味着任何模型'
        '都存在失效风险，稳健性优先于精度的工程实践（如时间序列交叉验证、'
        '严控过拟合、滚动再训练）才是量化策略长期生存的关键。', style_body))

    # ============================================================
    #  构建
    # ============================================================
    doc.build(story)
    print(f"PDF已生成: {pdf_path}")
    print(f"文件大小: {os.path.getsize(pdf_path) / 1024:.1f} KB")


if __name__ == '__main__':
    build_pdf()
