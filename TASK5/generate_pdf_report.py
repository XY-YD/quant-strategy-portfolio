#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TASK5: 生成PDF格式报告
格式要求：宋体、五号字(10.5pt)、1.5倍行距、0段间距、文字两端对齐
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
from reportlab.lib.pagesizes import A4

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
FS = 10.5          # 五号字
LEADING = FS * 1.5 # 1.5倍行距 = 15.75pt
SPACE_BEFORE = 0   # 0段间距
SPACE_AFTER = 0

style_title = ParagraphStyle(
    name='ReportTitle',
    fontName='SimSunBold',
    fontSize=22,
    leading=22 * 1.5,
    alignment=TA_CENTER,
    spaceBefore=0,
    spaceAfter=0,
)

style_h1 = ParagraphStyle(
    name='H1',
    fontName='SimSunBold',
    fontSize=16,
    leading=16 * 1.5,
    alignment=TA_LEFT,
    spaceBefore=0,
    spaceAfter=0,
)

style_h2 = ParagraphStyle(
    name='H2',
    fontName='SimSunBold',
    fontSize=14,
    leading=14 * 1.5,
    alignment=TA_LEFT,
    spaceBefore=0,
    spaceAfter=0,
)

style_h3 = ParagraphStyle(
    name='H3',
    fontName='SimSunBold',
    fontSize=FS,
    leading=LEADING,
    alignment=TA_LEFT,
    spaceBefore=0,
    spaceAfter=0,
)

style_body = ParagraphStyle(
    name='Body',
    fontName='SimSun',
    fontSize=FS,
    leading=LEADING,
    alignment=TA_JUSTIFY,   # 两端对齐
    spaceBefore=SPACE_BEFORE,
    spaceAfter=SPACE_AFTER,
    firstLineIndent=FS * 2, # 首行缩进2字符
)

style_body_noindent = ParagraphStyle(
    name='BodyNoIndent',
    fontName='SimSun',
    fontSize=FS,
    leading=LEADING,
    alignment=TA_JUSTIFY,
    spaceBefore=0,
    spaceAfter=0,
)

style_caption = ParagraphStyle(
    name='Caption',
    fontName='SimSunBold',
    fontSize=FS,
    leading=LEADING,
    alignment=TA_CENTER,
    spaceBefore=0,
    spaceAfter=0,
)

style_code = ParagraphStyle(
    name='Code',
    fontName='SimSun',
    fontSize=9,
    leading=9 * 1.5,
    alignment=TA_LEFT,
    spaceBefore=0,
    spaceAfter=0,
    leftIndent=20,
)

style_table_cell = ParagraphStyle(
    name='TableCell',
    fontName='SimSun',
    fontSize=9,
    leading=9 * 1.5,
    alignment=TA_CENTER,
    spaceBefore=0,
    spaceAfter=0,
)

style_table_header = ParagraphStyle(
    name='TableHeader',
    fontName='SimSunBold',
    fontSize=9,
    leading=9 * 1.5,
    alignment=TA_CENTER,
    spaceBefore=0,
    spaceAfter=0,
    textColor=colors.white,
)

# ============================================================
#  辅助函数
# ============================================================
def P(text, style=None):
    """快捷创建段落"""
    if style is None:
        style = style_body
    return Paragraph(text, style)

def make_table(data, col_widths=None, header=True):
    """创建格式化表格"""
    # 将所有单元格转为Paragraph
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
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
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
    # 图标题
    story.append(P(f'图 {fig_num}  {title}', style_caption))
    story.append(Spacer(1, 4))
    # 图片
    if os.path.exists(img_path):
        img = Image(img_path, width=width, height=width * 0.62)
        story.append(img)
    story.append(Spacer(1, 4))
    # 解读
    story.append(P(interpretation, style_body))
    story.append(Spacer(1, 8))

# ============================================================
#  生成PDF
# ============================================================
def build_pdf():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(output_dir, 'TASK5_分类算法报告.pdf')

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title='分类型机器学习算法实战报告',
    )

    story = []

    # ====== 封面标题 ======
    story.append(Spacer(1, 3 * cm))
    story.append(P('分类型机器学习算法实战报告', style_title))
    story.append(Spacer(1, 1 * cm))
    story.append(P('—— 逻辑回归、决策树、随机森林与模型评价 ——', style_h3))
    story.append(Spacer(1, 0.5 * cm))
    story.append(P('TASK5  量化策略课程', style_caption))
    story.append(Spacer(1, 2 * cm))

    # 摘要
    story.append(P('摘  要', style_h2))
    story.append(P(
        '本报告系统介绍了分类型机器学习的三种经典算法——逻辑回归、决策树和随机森林，'
        '以及混淆矩阵、AUC、ROC曲线等模型评价指标的原理与含义。在此基础上，使用Python编程语言，'
        '分别对乳腺癌数据集（569个样本、27个特征）和股票收益数据集（20772个样本、17个特征）'
        '进行了完整的分类建模实验，包括数据加载、训练集与测试集划分、模型训练、AUC计算和ROC曲线绘制。'
        '实验结果表明，乳腺癌数据集上逻辑回归表现最佳（AUC=0.9977），而股票收益数据集上随机森林表现相对最好（AUC=0.6331），'
        '但整体预测效果有限，符合金融市场难以预测的客观规律。',
        style_body
    ))
    story.append(PageBreak())

    # ====== 目录 ======
    story.append(P('目  录', style_h1))
    story.append(Spacer(1, 6))
    toc_items = [
        '第一部分  分类型机器学习算法',
        '    1.1  逻辑回归',
        '    1.2  决策树',
        '    1.3  随机森林',
        '第二部分  模型评价指标',
        '    2.1  混淆矩阵',
        '    2.2  ROC曲线',
        '    2.3  AUC',
        '第三部分  Python编程实战',
        '    3.1  数据准备',
        '    3.2  完整代码',
        '    3.3  代码解读',
        '第四部分  结果展示与分析',
        '    4.1  乳腺癌数据集结果',
        '    4.2  股票收益数据集结果',
        '第五部分  总结',
    ]
    for item in toc_items:
        story.append(P(item, style_body_noindent))
    story.append(PageBreak())

    # ====== 第一部分：算法讲解 ======
    story.append(P('第一部分  分类型机器学习算法', style_h1))
    story.append(Spacer(1, 8))
    story.append(P(
        '分类（Classification）是监督学习的核心任务之一：给定带标签的训练数据，'
        '学习一个从特征X到离散标签Y的映射关系。常用的分类算法包括逻辑回归、决策树、随机森林等，'
        '它们各有特点和适用场景。', style_body
    ))

    # 1.1 逻辑回归
    story.append(Spacer(1, 8))
    story.append(P('1.1  逻辑回归（Logistic Regression）', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '虽然名字里有"回归"，但逻辑回归是经典的分类算法，尤其适合二分类任务。'
        '其核心思想是通过Sigmoid函数将线性回归的输出映射到(0,1)区间，表示样本属于正类的概率。'
        'Sigmoid函数的数学表达式为：', style_body
    ))
    story.append(P('σ(z) = 1 / (1 + e^(-z))，其中 z = w·x + b', style_body_noindent))
    story.append(P(
        '当P(Y=1|X) ≥ 0.5时，预测为正类（1），否则预测为负类（0）。'
        '逻辑回归使用对数损失（交叉熵损失）作为损失函数：', style_body
    ))
    story.append(P('L(w) = -(1/m) · Σ [y·log(ŷ) + (1-y)·log(1-ŷ)]', style_body_noindent))
    story.append(P(
        '逻辑回归的优点在于训练速度快、可解释性强、输出概率值便于调整阈值；'
        '缺点是只能学习线性决策边界，对非线性关系表现欠佳，且对特征尺度敏感（需要进行标准化处理）。',
        style_body
    ))

    # 1.2 决策树
    story.append(Spacer(1, 8))
    story.append(P('1.2  决策树（Decision Tree）', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '决策树是一种树形结构的分类器，通过对特征空间进行递归划分来预测样本标签。'
        '从根节点开始，选择信息增益最大或基尼系数最小的特征进行切分，递归构建子树，直到满足停止条件。'
        '常用的划分准则包括：', style_body
    ))
    story.append(P('信息增益：IG(D, A) = H(D) - H(D|A)（ID3/C4.5算法）', style_body_noindent))
    story.append(P('基尼系数：Gini(D) = 1 - Σpk²（CART算法）', style_body_noindent))
    story.append(P(
        '决策树的优点是模型直观可解释、可视化方便、无需特征标准化、能学习非线性关系；'
        '缺点是容易过拟合（需要剪枝）、对训练数据的小变化敏感、可能陷入局部最优。',
        style_body
    ))

    # 1.3 随机森林
    story.append(Spacer(1, 8))
    story.append(P('1.3  随机森林（Random Forest）', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '随机森林是集成学习（Ensemble Learning）的代表性算法，通过组合多棵决策树来提升整体性能。'
        '其采用自助采样（Bootstrap Sampling）从训练集中有放回地抽取多个子集，分别训练决策树，'
        '预测时采用多数投票（分类）或平均（回归）的方式整合结果。', style_body
    ))
    story.append(P('随机森林的随机性来源于两个方面：', style_body))
    story.append(P('（1）样本随机：每棵树用不同的bootstrap样本训练；', style_body_noindent))
    story.append(P('（2）特征随机：每棵树分裂时只考虑特征的随机子集。', style_body_noindent))
    story.append(P(
        '随机森林的优点是精度通常比单棵决策树高、抗过拟合能力强、可输出特征重要性、支持并行训练；'
        '缺点是模型可解释性差（黑盒）、占用内存大、对高维稀疏数据效果一般。',
        style_body
    ))

    story.append(PageBreak())

    # ====== 第二部分：评价指标 ======
    story.append(P('第二部分  模型评价指标', style_h1))
    story.append(Spacer(1, 8))

    # 2.1 混淆矩阵
    story.append(P('2.1  混淆矩阵（Confusion Matrix）', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '混淆矩阵是评估分类模型性能的基础工具，将预测结果按真实类别与预测类别的组合进行统计。'
        '对于二分类问题，混淆矩阵包含四个基本元素：', style_body
    ))

    cm_table_data = [
        ['', '预测为负类(0)', '预测为正类(1)'],
        ['真实负类(0)', 'TN（真负）', 'FP（假正）'],
        ['真实正类(1)', 'FN（假负）', 'TP（真正）'],
    ]
    story.append(make_table(cm_table_data, col_widths=[4*cm, 4*cm, 4*cm]))
    story.append(Spacer(1, 8))

    story.append(P('由混淆矩阵可衍生出以下常用评价指标：', style_body))
    story.append(P('准确率（Accuracy）= (TP + TN) / (TP + FP + FN + TN)', style_body_noindent))
    story.append(P('精确率（Precision）= TP / (TP + FP)，即预测为正的样本中实际为正的比例', style_body_noindent))
    story.append(P('召回率（Recall）= TP / (TP + FN)，即实际为正的样本中被正确识别的比例', style_body_noindent))
    story.append(P('F1分数（F1-Score）= 2·(P·R) / (P + R)，即精确率与召回率的调和平均', style_body_noindent))
    story.append(Spacer(1, 4))
    story.append(P(
        '在实际应用中，关注"宁可错杀不可放过"的场景（如疾病筛查）应重点考察召回率；'
        '关注"推荐必须精准"的场景（如垃圾邮件识别）应重点考察精确率；'
        '需要综合平衡两者时则使用F1值。', style_body
    ))

    # 2.2 ROC曲线
    story.append(Spacer(1, 8))
    story.append(P('2.2  ROC曲线（Receiver Operating Characteristic）', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        'ROC曲线以假正率（FPR）为横轴、真正率（TPR，即召回率）为纵轴，'
        '展示了模型在不同分类阈值下的表现。其计算公式为：', style_body
    ))
    story.append(P('FPR = FP / (FP + TN)，TPR = TP / (TP + FN)', style_body_noindent))
    story.append(P(
        '绘制方法为：遍历所有可能的分类阈值，每个阈值对应一对(FPR, TPR)值，连成曲线。'
        'ROC曲线越靠近左上角，模型性能越好；对角线（y=x）代表随机分类器，'
        '曲线越偏离对角线，说明模型的分类能力越强。', style_body
    ))

    # 2.3 AUC
    story.append(Spacer(1, 8))
    story.append(P('2.3  AUC（Area Under Curve）', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        'AUC即ROC曲线下方的面积，取值范围为[0, 1]。从概率角度理解，'
        'AUC表示随机抽取一对正负样本时，模型将正样本排在负样本前面的概率。'
        '例如AUC=0.85意味着：随机一对正负样本，模型有85%的概率给正样本打出更高的预测分数。', style_body
    ))

    auc_table = [
        ['AUC范围', '模型能力'],
        ['0.50', '等同于随机猜测'],
        ['0.50 ~ 0.70', '效果较差'],
        ['0.70 ~ 0.85', '效果一般'],
        ['0.85 ~ 0.95', '效果很好'],
        ['0.95 ~ 1.00', '效果优秀'],
    ]
    story.append(Spacer(1, 4))
    story.append(make_table(auc_table, col_widths=[5*cm, 5*cm]))

    story.append(PageBreak())

    # ====== 第三部分：Python编程实战 ======
    story.append(P('第三部分  Python编程实战', style_h1))
    story.append(Spacer(1, 8))

    # 3.1 数据准备
    story.append(P('3.1  数据准备', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '本案例同时使用两个数据集进行对比实验。乳腺癌数据集来自scikit-learn内置数据集的导出版本，'
        '包含569个样本、27个特征（细胞核形态指标），目标变量为0（恶性）或1（良性），'
        '其中良性357个、恶性212个。股票收益数据集包含20772个样本、17个特征（估值指标和增长率指标），'
        '目标变量Y为True（正收益）或False（负收益），其中正收益8389个、负收益12383个。', style_body
    ))

    # 3.2 完整代码
    story.append(Spacer(1, 8))
    story.append(P('3.2  完整代码', style_h2))
    story.append(Spacer(1, 4))

    code_lines = [
        'import numpy as np',
        'import pandas as pd',
        'import matplotlib.pyplot as plt',
        'from sklearn.model_selection import train_test_split',
        'from sklearn.preprocessing import StandardScaler',
        'from sklearn.linear_model import LogisticRegression',
        'from sklearn.tree import DecisionTreeClassifier',
        'from sklearn.ensemble import RandomForestClassifier',
        'from sklearn.metrics import (confusion_matrix, roc_curve,',
        '    roc_auc_score, accuracy_score, precision_score,',
        '    recall_score, f1_score)',
        '',
        '# 1. 加载数据',
        "df = pd.read_csv('model_data_cancer.csv')",
        "feature_cols = [c for c in df.columns if c != 'target']",
        'X = df[feature_cols].values',
        "y = df['target'].values",
        '',
        '# 2. 划分训练集/测试集 (7:3)',
        'X_train, X_test, y_train, y_test = train_test_split(',
        '    X, y, test_size=0.3, random_state=42, stratify=y)',
        '',
        '# 3. 特征标准化 (逻辑回归需要)',
        'scaler = StandardScaler()',
        'X_train_s = scaler.fit_transform(X_train)',
        'X_test_s = scaler.transform(X_test)',
        '',
        '# 4. 构建并训练模型',
        'models = {',
        "    '逻辑回归': LogisticRegression(max_iter=1000),",
        "    '决策树': DecisionTreeClassifier(max_depth=5),",
        "    '随机森林': RandomForestClassifier(n_estimators=100, max_depth=8)",
        '}',
        '',
        '# 5. 模型评估 + 6. 绘制ROC曲线',
        "fig, ax = plt.subplots(figsize=(8, 6))",
        "colors = ['#e74c3c', '#2ecc71', '#3498db']",
        '',
        'for (name, model), color in zip(models.items(), colors):',
        "    if name == '逻辑回归':",
        '        model.fit(X_train_s, y_train)',
        '        y_prob = model.predict_proba(X_test_s)[:, 1]',
        '    else:',
        '        model.fit(X_train, y_train)',
        '        y_prob = model.predict_proba(X_test)[:, 1]',
        '',
        '    auc = roc_auc_score(y_test, y_prob)',
        '    fpr, tpr, _ = roc_curve(y_test, y_prob)',
        '    ax.plot(fpr, tpr, color=color, linewidth=2.5,',
        "        label=f'{name} (AUC = {auc:.4f})')",
        '',
        "ax.plot([0,1], [0,1], 'k--', label='随机分类器')",
        "ax.set_xlabel('假正率 (FPR)')",
        "ax.set_ylabel('真正率 (TPR)')",
        "ax.set_title('ROC 曲线对比')",
        'ax.legend(); ax.grid(True, alpha=0.3)',
        'plt.tight_layout()',
        "plt.savefig('roc_curve.png', dpi=150)",
    ]

    for line in code_lines:
        # 转义XML特殊字符
        safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        story.append(Paragraph(safe_line, style_code))

    # 3.3 代码解读
    story.append(Spacer(1, 8))
    story.append(P('3.3  代码解读', style_h2))
    story.append(Spacer(1, 4))

    explain_table = [
        ['步骤', '关键代码', '作用'],
        ['①数据加载', 'pd.read_csv()', '读取CSV数据为DataFrame'],
        ['②数据划分', 'train_test_split(stratify=y)', '按7:3划分训练/测试集，保持类别比例'],
        ['③特征标准化', 'StandardScaler()', '缩放为均值0方差1，对逻辑回归尤为重要'],
        ['④模型训练', 'model.fit(X_train, y_train)', '用训练集拟合模型参数'],
        ['⑤预测概率', 'predict_proba()[:,1]', '取正类预测概率用于绘制ROC'],
        ['⑥计算AUC', 'roc_auc_score(y_test, y_prob)', '计算ROC曲线下面积'],
        ['⑦绘制ROC', 'roc_curve(y_test, y_prob)', '计算(FPR,TPR)序列并绘制曲线'],
    ]
    story.append(make_table(explain_table, col_widths=[2.5*cm, 5*cm, 6.5*cm]))

    story.append(PageBreak())

    # ====== 第四部分：结果展示与分析 ======
    story.append(P('第四部分  结果展示与分析', style_h1))
    story.append(Spacer(1, 8))

    # 4.1 乳腺癌数据集
    story.append(P('4.1  乳腺癌数据集结果', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '乳腺癌数据集共569个样本，按7:3比例划分后训练集398个、测试集171个。'
        '三种模型在测试集上的评估结果如下表所示：', style_body
    ))
    story.append(Spacer(1, 4))

    cancer_table = [
        ['模型', '准确率', '精确率', '召回率', 'F1值', 'AUC'],
        ['逻辑回归', '0.9883', '0.9907', '0.9907', '0.9907', '0.9977'],
        ['决策树', '0.9357', '0.9444', '0.9533', '0.9488', '0.9268'],
        ['随机森林', '0.9415', '0.9619', '0.9439', '0.9528', '0.9907'],
    ]
    story.append(make_table(cancer_table, col_widths=[2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm]))
    story.append(Spacer(1, 8))

    # 图1: ROC曲线
    add_figure(
        story,
        os.path.join(output_dir, 'roc_乳腺癌数据.png'),
        1,
        '乳腺癌数据集ROC曲线对比',
        '如图1所示，三条ROC曲线均显著偏离对角线，其中逻辑回归的曲线最靠近左上角，'
        'AUC达到0.9977，接近完美分类。随机森林的AUC为0.9907，同样表现优异。'
        '决策树的AUC为0.9268，虽然略低于前两者，但仍然属于"效果优秀"的范畴。'
        '这表明乳腺癌数据集的特征与目标之间具有较强的可分性，三种模型均能有效识别良恶性肿瘤。'
    )

    # 图2: 混淆矩阵
    add_figure(
        story,
        os.path.join(output_dir, 'confusion_matrix_乳腺癌数据.png'),
        2,
        '乳腺癌数据集混淆矩阵对比',
        '如图2所示，逻辑回归在测试集上仅有2个样本被误判（1个假正、1个假负），'
        '准确率高达98.83%。决策树和随机森林分别有11个和10个误判样本。'
        '在医学诊断场景中，假负（将恶性误判为良性）的代价远高于假正，'
        '因此召回率尤为重要。逻辑回归的召回率达到99.07%，仅漏诊1例，表现最为可靠。'
    )

    # 图3: 指标对比
    add_figure(
        story,
        os.path.join(output_dir, 'metrics_乳腺癌数据.png'),
        3,
        '乳腺癌数据集评估指标对比',
        '如图3所示，从五项指标的横向对比来看，逻辑回归在准确率、召回率、F1值和AUC四项上均最优，'
        '仅在精确率上略低于随机森林。决策树在各项指标上均处于末位，'
        '说明单棵决策树容易受到数据波动的影响。随机森林通过集成多棵树，'
        '有效提升了稳定性，各项指标均优于决策树。'
    )

    story.append(Spacer(1, 8))
    story.append(P(
        '综合分析：乳腺癌数据集三类模型均表现优异，AUC都在0.92以上。'
        '逻辑回归表现最好（AUC=0.9977），说明经过特征标准化后，特征与目标之间近似线性可分。'
        '随机森林紧随其后（AUC=0.9907），体现出集成学习的优势。',
        style_body
    ))

    story.append(PageBreak())

    # 4.2 股票收益数据集
    story.append(P('4.2  股票收益数据集结果', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '股票收益数据集共20772个样本，按7:3比例划分后训练集14540个、测试集6232个。'
        '三种模型在测试集上的评估结果如下表所示：', style_body
    ))
    story.append(Spacer(1, 4))

    stock_table = [
        ['模型', '准确率', '精确率', '召回率', 'F1值', 'AUC'],
        ['逻辑回归', '0.5956', '0.4615', '0.0072', '0.0141', '0.5561'],
        ['决策树', '0.6114', '0.5396', '0.2571', '0.3482', '0.6078'],
        ['随机森林', '0.6248', '0.5727', '0.2801', '0.3762', '0.6331'],
    ]
    story.append(make_table(stock_table, col_widths=[2.5*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2*cm]))
    story.append(Spacer(1, 8))

    # 图4: ROC曲线
    add_figure(
        story,
        os.path.join(output_dir, 'roc_股票收益数据.png'),
        4,
        '股票收益数据集ROC曲线对比',
        '如图4所示，三条ROC曲线均较为接近对角线，AUC值在0.55至0.63之间，'
        '说明模型的分类能力仅略优于随机猜测。随机森林的曲线最优（AUC=0.6331），'
        '决策树次之（AUC=0.6078），逻辑回归最弱（AUC=0.5561）。'
        '这表明股票收益受多重复杂因素影响，仅凭历史财务指标难以稳定预测未来涨跌方向。'
    )

    # 图5: 混淆矩阵
    add_figure(
        story,
        os.path.join(output_dir, 'confusion_matrix_股票收益数据.png'),
        5,
        '股票收益数据集混淆矩阵对比',
        '如图5所示，逻辑回归的召回率极低（仅0.72%），几乎将所有样本预测为负类，'
        '说明线性模型在处理股票数据的复杂非线性关系时力不从心。'
        '决策树和随机森林的召回率分别为25.71%和28.01%，虽然有所改善但仍不理想。'
        '随机森林在保持较高准确率（62.48%）的同时，召回率和F1值均为三者最高，'
        '体现出其非线性拟合能力的一定优势。'
    )

    # 图6: 指标对比
    add_figure(
        story,
        os.path.join(output_dir, 'metrics_股票收益数据.png'),
        6,
        '股票收益数据集评估指标对比',
        '如图6所示，随机森林在准确率、精确率、召回率、F1值和AUC五项指标上均优于其他两种模型。'
        '逻辑回归的F1值仅为0.0141，说明其在正类预测上几乎失效。'
        '整体来看，股票数据的各项指标均远低于乳腺癌数据集，'
        '反映了金融时间序列预测的高难度特征。'
    )

    story.append(Spacer(1, 8))
    story.append(P(
        '综合分析：股票数据集所有模型的AUC都在0.55至0.65之间，预测效果有限。'
        '这并非模型本身的问题，而是股票市场受宏观经济、政策、情绪、突发事件等多重因素影响，'
        '仅凭历史财务指标难以稳定预测未来收益——这也印证了"股票市场不可预测"这一业界共识。'
        '其中随机森林表现相对最好（AUC=0.6331），说明其非线性拟合能力有一定优势。',
        style_body
    ))

    story.append(PageBreak())

    # ====== 第五部分：总结 ======
    story.append(P('第五部分  总结', style_h1))
    story.append(Spacer(1, 8))

    story.append(P('5.1  算法对比总结', style_h2))
    story.append(Spacer(1, 4))

    summary_table = [
        ['维度', '逻辑回归', '决策树', '随机森林'],
        ['模型类型', '线性分类器', '非线性树模型', '集成树模型'],
        ['可解释性', '高', '较高', '一般'],
        ['训练速度', '快', '较快', '中等'],
        ['抗过拟合', '强', '弱', '较强'],
        ['预测精度', '中', '中', '高'],
        ['特征要求', '需标准化', '无需标准化', '无需标准化'],
        ['适用场景', '线性可分问题', '需要解释的简单任务', '追求精度的复杂任务'],
    ]
    story.append(make_table(summary_table, col_widths=[2.5*cm, 3.5*cm, 3.5*cm, 3.5*cm]))
    story.append(Spacer(1, 8))

    story.append(P('5.2  评价指标选择建议', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '当类别分布平衡时，使用准确率和AUC即可较好地评估模型性能，如本任务的乳腺癌数据集。'
        '当类别分布不平衡时，准确率可能产生误导（如全预测为多数类即可获得高准确率），'
        '此时应重点关注F1值和AUC-PR曲线，关注少数类的识别效果。'
        '当模型需要输出概率而非硬标签时（如信用评分），AUC和对数损失更为合适，'
        '因为它们可以评估模型对不同样本的排序能力。', style_body
    ))

    story.append(Spacer(1, 8))
    story.append(P('5.3  关键收获', style_h2))
    story.append(Spacer(1, 4))
    story.append(P(
        '第一，三种分类算法各有适用场景，随机森林在大多数情况下表现最稳健，'
        '是实际项目中的首选基线模型。', style_body
    ))
    story.append(P(
        '第二，ROC曲线与AUC是评估分类模型最常用、且不受分类阈值影响的指标，'
        '能够全面反映模型在不同决策阈值下的整体表现。', style_body
    ))
    story.append(P(
        '第三，金融数据预测本质上是非常困难的任务，AUC略高于0.5已说明模型捕捉到了微弱信号，'
        '不应期望通过简单的财务指标建模获得高精度的收益预测。', style_body
    ))
    story.append(P(
        '第四，特征工程和数据质量往往比模型选择更影响最终效果，'
        '在投入复杂模型之前，应充分做好数据清洗、特征筛选和特征构造工作。', style_body
    ))

    # 构建PDF
    doc.build(story)
    print(f'PDF报告已生成: {pdf_path}')
    print(f'文件大小: {os.path.getsize(pdf_path) / 1024:.1f} KB')


if __name__ == '__main__':
    build_pdf()
