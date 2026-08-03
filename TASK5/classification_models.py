#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TASK5: 分类型机器学习算法实战
- 加载股票收益数据与乳腺癌数据集
- 构建逻辑回归、决策树、随机森林分类模型
- 评估模型（混淆矩阵、AUC、ROC曲线）
"""

import os
import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import rcParams

# 中文字体设置
rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']
rcParams['axes.unicode_minus'] = False

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    confusion_matrix, classification_report,
    roc_curve, roc_auc_score, accuracy_score,
    precision_score, recall_score, f1_score
)

# ============================================================
#  通用函数定义
# ============================================================

def plot_confusion_matrix(cm, classes, title, ax, cmap='Blues'):
    """绘制混淆矩阵热力图"""
    im = ax.imshow(cm, interpolation='nearest', cmap=cmap)
    ax.set_title(title, fontsize=13, fontweight='bold')
    tick_marks = np.arange(len(classes))
    ax.set_xticks(tick_marks)
    ax.set_xticklabels(classes, fontsize=11)
    ax.set_yticks(tick_marks)
    ax.set_yticklabels(classes, fontsize=11)
    # 在格子中标注数字
    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, format(cm[i, j], 'd'),
                    ha="center", va="center",
                    color="white" if cm[i, j] > thresh else "black",
                    fontsize=14, fontweight='bold')
    ax.set_ylabel('真实标签', fontsize=12)
    ax.set_xlabel('预测标签', fontsize=12)


def evaluate_model(model, X_test, y_test, model_name):
    """评估单个模型，返回指标字典"""
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    cm = confusion_matrix(y_test, y_pred)
    auc = roc_auc_score(y_test, y_prob)
    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    return {
        'model': model_name,
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1': f1,
        'auc': auc,
        'cm': cm,
        'y_prob': y_prob,
        'y_pred': y_pred
    }


def run_classification(data_name, X, y, feature_names, output_dir):
    """
    对给定数据集执行完整的分类流程：
    1. 数据划分
    2. 模型训练（逻辑回归、决策树、随机森林）
    3. 模型评估
    4. 绘制ROC曲线和混淆矩阵
    """
    print(f"\n{'='*60}")
    print(f"  数据集: {data_name}")
    print(f"  样本数: {X.shape[0]}, 特征数: {X.shape[1]}")
    print(f"  正样本占比: {y.mean():.2%}")
    print(f"{'='*60}")

    # ---- 1. 数据划分 ----
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    print(f"\n训练集: {X_train.shape[0]} 样本")
    print(f"测试集: {X_test.shape[0]} 样本")

    # ---- 2. 特征标准化（逻辑回归需要） ----
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # ---- 3. 构建并训练模型 ----
    models = {
        '逻辑回归': LogisticRegression(max_iter=1000, random_state=42),
        '决策树': DecisionTreeClassifier(max_depth=5, random_state=42),
        '随机森林': RandomForestClassifier(n_estimators=100, max_depth=8,
                                        random_state=42, n_jobs=-1),
    }

    results = {}
    for name, model in models.items():
        print(f"\n--- 训练 {name} ---")
        # 逻辑回归用标准化数据，树模型用原始数据
        if name == '逻辑回归':
            model.fit(X_train_scaled, y_train)
            result = evaluate_model(model, X_test_scaled, y_test, name)
        else:
            model.fit(X_train, y_train)
            result = evaluate_model(model, X_test, y_test, name)
        results[name] = result
        print(f"  准确率: {result['accuracy']:.4f}")
        print(f"  精确率: {result['precision']:.4f}")
        print(f"  召回率: {result['recall']:.4f}")
        print(f"  F1值:   {result['f1']:.4f}")
        print(f"  AUC:    {result['auc']:.4f}")

    # ---- 4. 汇总指标表 ----
    print(f"\n{'='*60}")
    print(f"  {data_name} - 模型评估汇总")
    print(f"{'='*60}")
    print(f"{'模型':<12} {'准确率':<10} {'精确率':<10} {'召回率':<10} {'F1值':<10} {'AUC':<10}")
    print("-" * 62)
    for name in results:
        r = results[name]
        print(f"{name:<12} {r['accuracy']:<10.4f} {r['precision']:<10.4f} "
              f"{r['recall']:<10.4f} {r['f1']:<10.4f} {r['auc']:<10.4f}")

    # ---- 5. 绘制 ROC 曲线 ----
    fig_roc, ax_roc = plt.subplots(figsize=(8, 6))
    colors = ['#e74c3c', '#2ecc71', '#3498db']
    for (name, r), color in zip(results.items(), colors):
        fpr, tpr, _ = roc_curve(y_test, r['y_prob'])
        ax_roc.plot(fpr, tpr, color=color, linewidth=2.5,
                    label=f'{name} (AUC = {r["auc"]:.4f})')
    ax_roc.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5, label='随机分类器')
    ax_roc.set_xlabel('假正率 (FPR)', fontsize=13)
    ax_roc.set_ylabel('真正率 (TPR)', fontsize=13)
    ax_roc.set_title(f'{data_name} - ROC 曲线对比', fontsize=15, fontweight='bold')
    ax_roc.legend(loc='lower right', fontsize=11)
    ax_roc.set_xlim([-0.01, 1.01])
    ax_roc.set_ylim([-0.01, 1.01])
    ax_roc.grid(True, alpha=0.3)
    fig_roc.tight_layout()
    roc_path = os.path.join(output_dir, f'roc_{data_name}.png')
    fig_roc.savefig(roc_path, dpi=150, bbox_inches='tight')
    plt.close(fig_roc)
    print(f"\nROC曲线已保存: {roc_path}")

    # ---- 6. 绘制混淆矩阵 ----
    fig_cm, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig_cm.suptitle(f'{data_name} - 混淆矩阵对比', fontsize=16, fontweight='bold', y=1.02)
    for ax, (name, r) in zip(axes, results.items()):
        plot_confusion_matrix(r['cm'], ['负类(0)', '正类(1)'],
                               f'{name}', ax)
    fig_cm.tight_layout()
    cm_path = os.path.join(output_dir, f'confusion_matrix_{data_name}.png')
    fig_cm.savefig(cm_path, dpi=150, bbox_inches='tight')
    plt.close(fig_cm)
    print(f"混淆矩阵已保存: {cm_path}")

    # ---- 7. 绘制指标对比柱状图 ----
    fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
    metrics_names = ['准确率', '精确率', '召回率', 'F1值', 'AUC']
    model_names = list(results.keys())
    x = np.arange(len(metrics_names))
    width = 0.25
    for i, name in enumerate(model_names):
        r = results[name]
        values = [r['accuracy'], r['precision'], r['recall'], r['f1'], r['auc']]
        bars = ax_bar.bar(x + i * width, values, width, label=name, color=colors[i])
        for bar, val in zip(bars, values):
            ax_bar.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                       f'{val:.3f}', ha='center', va='bottom', fontsize=8)
    ax_bar.set_xticks(x + width)
    ax_bar.set_xticklabels(metrics_names, fontsize=12)
    ax_bar.set_ylim([0, 1.08])
    ax_bar.set_ylabel('分数', fontsize=13)
    ax_bar.set_title(f'{data_name} - 模型评估指标对比', fontsize=15, fontweight='bold')
    ax_bar.legend(fontsize=11)
    ax_bar.grid(True, axis='y', alpha=0.3)
    fig_bar.tight_layout()
    bar_path = os.path.join(output_dir, f'metrics_{data_name}.png')
    fig_bar.savefig(bar_path, dpi=150, bbox_inches='tight')
    plt.close(fig_bar)
    print(f"指标对比图已保存: {bar_path}")

    return results


# ============================================================
#  主程序
# ============================================================
def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    # 设置matplotlib缓存目录避免权限问题
    os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib_cache'
    os.makedirs('/tmp/matplotlib_cache', exist_ok=True)

    # ============================================================
    #  数据集1: 乳腺癌数据
    # ============================================================
    print("\n" + "=" * 60)
    print("  加载乳腺癌数据集")
    print("=" * 60)
    cancer_path = os.path.join(output_dir, 'model_data_cancer.csv')
    df_cancer = pd.read_csv(cancer_path)
    print(f"数据形状: {df_cancer.shape}")
    print(f"列名: {list(df_cancer.columns)}")
    print(f"\n目标变量分布:\n{df_cancer['target'].value_counts()}")
    print(f"  (0=恶性, 1=良性)")

    feature_cols_cancer = [c for c in df_cancer.columns if c != 'target']
    X_cancer = df_cancer[feature_cols_cancer].values
    y_cancer = df_cancer['target'].values

    results_cancer = run_classification(
        '乳腺癌数据', X_cancer, y_cancer, feature_cols_cancer, output_dir
    )

    # ============================================================
    #  数据集2: 股票收益数据
    # ============================================================
    print("\n" + "=" * 60)
    print("  加载股票收益数据集")
    print("=" * 60)
    stock_path = os.path.join(output_dir, 'model_data_stock.csv')
    df_stock = pd.read_csv(stock_path)
    print(f"数据形状: {df_stock.shape}")
    print(f"列名: {list(df_stock.columns)}")

    # Y列为目标变量，True/False -> 1/0
    df_stock['Y'] = df_stock['Y'].astype(int)
    print(f"\n目标变量分布:\n{df_stock['Y'].value_counts()}")
    print(f"  (1=正收益, 0=负收益)")

    # 选取数值型特征列（排除Date, Code, Y）
    exclude_cols = ['Date', 'Code', 'Y']
    feature_cols_stock = [c for c in df_stock.columns if c not in exclude_cols]
    print(f"\n特征列({len(feature_cols_stock)}个): {feature_cols_stock}")

    # 处理缺失值和无穷值
    df_stock_clean = df_stock[feature_cols_stock + ['Y']].replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    print(f"\n清洗后样本数: {len(df_stock_clean)} (原始: {len(df_stock)})")

    X_stock = df_stock_clean[feature_cols_stock].values
    y_stock = df_stock_clean['Y'].values

    results_stock = run_classification(
        '股票收益数据', X_stock, y_stock, feature_cols_stock, output_dir
    )

    # ============================================================
    #  汇总输出
    # ============================================================
    print("\n" + "=" * 60)
    print("  全部完成！输出文件:")
    print("=" * 60)
    for f in sorted(os.listdir(output_dir)):
        if f.endswith('.png'):
            print(f"  - {f}")


if __name__ == '__main__':
    main()
