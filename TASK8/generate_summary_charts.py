#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK8 汇总图表生成脚本
======================
生成6张统一风格的汇总图表，用于量化交易学习报告。
风格：红涨绿跌、PingFang SC字体、白底、网格alpha=0.3
"""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"
plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

BASE = "/Users/wangyanfen/Desktop/量化策略课程"
FIG_DIR = os.path.join(BASE, "TASK8", "figs")
os.makedirs(FIG_DIR, exist_ok=True)

# 配色
C_UP = "#E74C3C"       # 红（涨/优）
C_DOWN = "#27AE60"      # 绿（跌/劣）
C_BLUE = "#3498DB"
C_GREY = "#95A5A6"
C_DARK = "#2C3E50"
C_ORANGE = "#F39C12"
C_PURPLE = "#9B59B6"


# ========================================================================
# 图1：策略体系总览（流程图式）
# ========================================================================
def fig1_summary():
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 7)
    ax.axis("off")

    # 颜色定义
    colors = {
        "data": "#3498DB",
        "strategy": "#E74C3C",
        "risk": "#F39C12",
        "eval": "#27AE60",
        "live": "#9B59B6",
    }

    boxes = [
        # (x, y, w, h, text, color)
        (0.3, 5.2, 2.2, 1.0, "数据获取\n行情/基本面", colors["data"]),
        (2.8, 5.2, 2.2, 1.0, "因子分析\n估值/成长/技术", colors["data"]),
        (5.3, 5.2, 2.2, 1.0, "策略设计\n双均线/海龟/ML", colors["strategy"]),
        (7.8, 5.2, 2.2, 1.0, "回测验证\n样本内寻优", colors["strategy"]),
        (10.3, 5.2, 2.2, 1.0, "风险管理\n止损/仓位/成本", colors["risk"]),
        (0.3, 3.0, 2.2, 1.0, " TASK1-2\n基础数据探索", colors["data"]),
        (2.8, 3.0, 2.2, 1.0, " TASK3\n双均线策略", colors["strategy"]),
        (5.3, 3.0, 2.2, 1.0, " TASK4\n海龟策略", colors["strategy"]),
        (7.8, 3.0, 2.2, 1.0, " TASK5-6\n机器学习", colors["strategy"]),
        (10.3, 3.0, 2.2, 1.0, " TASK7\n寻优与实盘", colors["risk"]),
        (2.8, 0.8, 3.2, 1.0, "前向测试（样本外）", colors["live"]),
        (6.5, 0.8, 3.2, 1.0, "风险暴露分析", colors["eval"]),
        (10.3, 0.8, 3.0, 1.0, "策略迭代优化", colors["eval"]),
    ]

    for x, y, w, h, text, color in boxes:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                             facecolor=color, alpha=0.15, edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=9, fontweight="bold", color=color)

    # 箭头：上层流程
    arrows_top = [(2.5, 5.7, 2.8, 5.7), (5.0, 5.7, 5.3, 5.7),
                  (7.5, 5.7, 7.8, 5.7), (10.0, 5.7, 10.3, 5.7)]
    for x1, y1, x2, y2 in arrows_top:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=C_DARK, lw=1.5))

    # 箭头：上层到下层
    for x_center in [1.4, 3.9, 6.4, 8.9, 11.4]:
        ax.annotate("", xy=(x_center, 4.0), xytext=(x_center, 5.2),
                    arrowprops=dict(arrowstyle="->", color=C_GREY, lw=1.2, ls="--"))

    # 箭头：下层到底层
    bottom_arrows = [(3.9, 3.0, 3.9, 1.8), (6.4, 3.0, 6.4, 1.8), (8.9, 3.0, 8.9, 1.8), (11.4, 3.0, 11.4, 1.8)]
    for x1, y1, x2, y2 in bottom_arrows:
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=C_GREY, lw=1.2, ls="--"))

    # 底层箭头
    ax.annotate("", xy=(6.5, 1.3), xytext=(6.0, 1.3),
                arrowprops=dict(arrowstyle="->", color=C_DARK, lw=1.5))
    ax.annotate("", xy=(10.3, 1.3), xytext=(9.7, 1.3),
                arrowprops=dict(arrowstyle="->", color=C_DARK, lw=1.5))

    # 标题
    ax.text(7, 6.6, "量化交易策略体系总览", ha="center", fontsize=15, fontweight="bold", color=C_DARK)

    # 图例
    legend_items = [
        mpatches.Patch(color=colors["data"], alpha=0.3, label="数据层"),
        mpatches.Patch(color=colors["strategy"], alpha=0.3, label="策略层"),
        mpatches.Patch(color=colors["risk"], alpha=0.3, label="风控层"),
        mpatches.Patch(color=colors["eval"], alpha=0.3, label="评估层"),
        mpatches.Patch(color=colors["live"], alpha=0.3, label="实盘层"),
    ]
    ax.legend(handles=legend_items, loc="lower left", fontsize=9, ncol=5,
              framealpha=0.8, bbox_to_anchor=(0.02, -0.02))

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig_summary_strategies.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {path}")


# ========================================================================
# 图2：各策略核心指标对比柱状图
# ========================================================================
def fig2_strategy_comparison():
    strategies = ["双均线(MA5/15)\nTASK3", "海龟(N20/M10)\nTASK4",
                  "寻优样本内\n(15/20) TASK7", "寻优样本外\n(15/20) TASK7"]
    ann_returns = [25.37, -0.02, 40.33, 11.78]
    sharpes = [0.76, -0.32, 1.24, 0.45]
    mdds = [-14.20, -10.17, -39.17, -19.72]

    x = np.arange(len(strategies))
    width = 0.25

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))

    # 年化收益
    vals = ann_returns
    colors = [C_UP if v > 0 else C_DOWN for v in vals]
    bars = axes[0].bar(x, vals, width*2.5, color=colors, alpha=0.85)
    axes[0].set_title("年化收益率（%）", fontsize=13, fontweight="bold")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(strategies, fontsize=9)
    axes[0].grid(True, axis="y", alpha=0.3)
    axes[0].axhline(y=0, color=C_GREY, linewidth=0.5)
    for bar, val in zip(bars, vals):
        axes[0].text(bar.get_x() + bar.get_width()/2, val + (1 if val > 0 else -2),
                     f"{val:.2f}", ha="center", fontsize=9, fontweight="bold")

    # 夏普比率
    vals = sharpes
    colors = [C_UP if v > 0 else C_DOWN for v in vals]
    bars = axes[1].bar(x, vals, width*2.5, color=colors, alpha=0.85)
    axes[1].set_title("夏普比率", fontsize=13, fontweight="bold")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(strategies, fontsize=9)
    axes[1].grid(True, axis="y", alpha=0.3)
    axes[1].axhline(y=0, color=C_GREY, linewidth=0.5)
    for bar, val in zip(bars, vals):
        axes[1].text(bar.get_x() + bar.get_width()/2, val + (0.03 if val > 0 else -0.08),
                     f"{val:.2f}", ha="center", fontsize=9, fontweight="bold")

    # 最大回撤
    vals = mdds
    bars = axes[2].bar(x, vals, width*2.5, color=C_DOWN, alpha=0.85)
    axes[2].set_title("最大回撤（%）", fontsize=13, fontweight="bold")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(strategies, fontsize=9)
    axes[2].grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars, vals):
        axes[2].text(bar.get_x() + bar.get_width()/2, val - 1.5,
                     f"{val:.2f}", ha="center", fontsize=9, fontweight="bold")

    fig.suptitle("各策略核心指标对比（宁德时代）", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    path = os.path.join(FIG_DIR, "fig_strategy_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {path}")


# ========================================================================
# 图3：机器学习流程图
# ========================================================================
def fig3_ml_pipeline():
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6)
    ax.axis("off")

    colors_pipe = ["#3498DB", "#E74C3C", "#9B59B6", "#F39C12", "#27AE60", "#1ABC9C"]
    steps = [
        (0.3, 2.5, 2.0, 1.2, "数据获取\n行情+基本面", colors_pipe[0]),
        (2.6, 2.5, 2.0, 1.2, "特征工程\n20原始+7衍生", colors_pipe[1]),
        (4.9, 2.5, 2.0, 1.2, "模型训练\n分类+回归", colors_pipe[2]),
        (7.2, 2.5, 2.0, 1.2, "模型预测\n概率排序", colors_pipe[3]),
        (9.5, 2.5, 2.0, 1.2, "组合构建\n选前50只", colors_pipe[4]),
        (11.8, 2.5, 1.9, 1.2, "回测评估\n收益/风险", colors_pipe[5]),
    ]

    for x, y, w, h, text, color in steps:
        box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.1",
                             facecolor=color, alpha=0.15, edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x + w/2, y + h/2, text, ha="center", va="center",
                fontsize=10, fontweight="bold", color=color)

    # 箭头
    for i in range(len(steps) - 1):
        x1 = steps[i][0] + steps[i][2]
        x2 = steps[i+1][0]
        ax.annotate("", xy=(x2, 3.1), xytext=(x1, 3.1),
                    arrowprops=dict(arrowstyle="->", color=C_DARK, lw=2))

    # 上层：关键要点
    notes = [
        (1.3, 4.5, "缺失值/无穷值清洗\n标准化处理"),
        (3.6, 4.5, "估值/成长/质量\n规模/稳定/现金流"),
        (5.9, 4.5, "逻辑回归/决策树\n随机森林/梯度提升"),
        (8.2, 4.5, "下期收益>中位数→1\n或直接预测收益率"),
        (10.5, 4.5, "等权持有\n季度调仓"),
        (12.75, 4.5, "累计/年化/夏普\n胜率/最大回撤"),
    ]
    for x, y, text in notes:
        ax.text(x, y, text, ha="center", fontsize=8, color=C_GREY, style="italic")
        ax.annotate("", xy=(x, 3.7), xytext=(x, 4.0),
                    arrowprops=dict(arrowstyle="->", color=C_GREY, lw=0.8, ls=":"))

    # 下层：评估指标
    eval_notes = [
        (3.6, 1.0, "准确率/精确率/召回率/F1/AUC"),
        (5.9, 1.0, "均方误差/R²/信息系数"),
        (8.2, 1.0, "累计收益/年化收益/夏普/胜率/MDD"),
    ]
    for x, y, text in eval_notes:
        ax.text(x, y, text, ha="center", fontsize=8, color=C_DOWN,
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#EAF7F0", alpha=0.7))

    ax.text(7, 5.5, "机器学习量化交易流程", ha="center", fontsize=15, fontweight="bold", color=C_DARK)

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig_ml_pipeline.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {path}")


# ========================================================================
# 图4：机器学习模型效果对比
# ========================================================================
def fig4_ml_model_comparison():
    # TASK6 回测指标数据
    models = ["逻辑回归", "决策树", "随机森林", "梯度提升"]
    cum_rets = [14.37, -5.28, 24.19, 25.97]
    sharpes = [1.15, -0.18, 2.91, 3.41]
    win_rates = [75.0, 50.0, 75.0, 75.0]
    mdds = [-5.83, -14.90, -0.86, 0.00]

    colors_ml = [C_UP, C_DOWN, C_BLUE, C_ORANGE]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("机器学习模型交易策略效果对比（TASK6）", fontsize=15, fontweight="bold", y=0.98)

    x = np.arange(len(models))
    width = 0.5

    # 累计收益
    vals = cum_rets
    colors = [C_UP if v > 0 else C_DOWN for v in vals]
    bars = axes[0][0].bar(x, vals, width, color=colors, alpha=0.85)
    axes[0][0].set_title("累计收益率（%）", fontsize=12, fontweight="bold")
    axes[0][0].set_xticks(x)
    axes[0][0].set_xticklabels(models, fontsize=10)
    axes[0][0].grid(True, axis="y", alpha=0.3)
    axes[0][0].axhline(y=0, color=C_GREY, linewidth=0.5)
    for bar, val in zip(bars, vals):
        axes[0][0].text(bar.get_x() + bar.get_width()/2, val + (0.5 if val > 0 else -1.5),
                        f"{val:.2f}", ha="center", fontsize=9, fontweight="bold")

    # 夏普比率
    vals = sharpes
    colors = [C_UP if v > 0 else C_DOWN for v in vals]
    bars = axes[0][1].bar(x, vals, width, color=colors, alpha=0.85)
    axes[0][1].set_title("夏普比率", fontsize=12, fontweight="bold")
    axes[0][1].set_xticks(x)
    axes[0][1].set_xticklabels(models, fontsize=10)
    axes[0][1].grid(True, axis="y", alpha=0.3)
    axes[0][1].axhline(y=0, color=C_GREY, linewidth=0.5)
    for bar, val in zip(bars, vals):
        axes[0][1].text(bar.get_x() + bar.get_width()/2, val + (0.05 if val > 0 else -0.15),
                        f"{val:.2f}", ha="center", fontsize=9, fontweight="bold")

    # 胜率
    vals = win_rates
    bars = axes[1][0].bar(x, vals, width, color=colors_ml, alpha=0.85)
    axes[1][0].set_title("胜率（%）", fontsize=12, fontweight="bold")
    axes[1][0].set_xticks(x)
    axes[1][0].set_xticklabels(models, fontsize=10)
    axes[1][0].grid(True, axis="y", alpha=0.3)
    axes[1][0].set_ylim(0, 100)
    for bar, val in zip(bars, vals):
        axes[1][0].text(bar.get_x() + bar.get_width()/2, val + 1,
                        f"{val:.0f}", ha="center", fontsize=9, fontweight="bold")

    # 最大回撤
    vals = mdds
    bars = axes[1][1].bar(x, vals, width, color=C_DOWN, alpha=0.85)
    axes[1][1].set_title("最大回撤（%）", fontsize=12, fontweight="bold")
    axes[1][1].set_xticks(x)
    axes[1][1].set_xticklabels(models, fontsize=10)
    axes[1][1].grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars, vals):
        axes[1][1].text(bar.get_x() + bar.get_width()/2, val - 0.5,
                        f"{val:.2f}", ha="center", fontsize=9, fontweight="bold")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    path = os.path.join(FIG_DIR, "fig_ml_model_comparison.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {path}")


# ========================================================================
# 图5：TASK7样本内外关键指标对比
# ========================================================================
def fig5_insample_oos():
    with open(os.path.join(BASE, "TASK7", "metrics.json"), "r", encoding="utf-8") as f:
        M = json.load(f)

    ins = M["insample"]
    oos = M["oos"]
    oosd = M["oos_default"]

    categories = ["年化收益", "夏普比率", "最大回撤", "Calmar比率", "年化波动"]
    ins_vals = [ins["年化收益"]*100, ins["夏普"], ins["最大回撤"]*100,
                ins["Calmar"], ins["年化波动"]*100]
    oos_vals = [oos["年化收益"]*100, oos["夏普"], oos["最大回撤"]*100,
                oos["Calmar"], oos["年化波动"]*100]
    def_vals = [oosd["年化收益"]*100, oosd["夏普"], oosd["最大回撤"]*100,
                oosd["Calmar"], oosd["年化波动"]*100]

    x = np.arange(len(categories))
    width = 0.25

    fig, ax = plt.subplots(figsize=(14, 6))
    bars1 = ax.bar(x - width, ins_vals, width, label="样本内（寻优MA15/20）", color=C_UP, alpha=0.85)
    bars2 = ax.bar(x, oos_vals, width, label="样本外（寻优MA15/20）", color=C_BLUE, alpha=0.85)
    bars3 = ax.bar(x + width, def_vals, width, label="样本外（默认MA5/15）", color=C_GREY, alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=11)
    ax.legend(fontsize=10, loc="upper right")
    ax.grid(True, axis="y", alpha=0.3)
    ax.axhline(y=0, color="#2C3E50", linewidth=0.5)
    ax.set_title("样本内 vs 样本外 vs 默认参数：核心指标对比", fontsize=14, fontweight="bold")

    # 标注数值
    for bars in [bars1, bars2, bars3]:
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, h + (1 if h > 0 else -3),
                    f"{h:.2f}", ha="center", fontsize=7.5, fontweight="bold")

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig_insample_oos.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {path}")


# ========================================================================
# 图6：风险指标雷达图
# ========================================================================
def fig6_risk_dashboard():
    with open(os.path.join(BASE, "TASK7", "metrics.json"), "r", encoding="utf-8") as f:
        M = json.load(f)

    ins = M["insample"]
    oos = M["oos"]
    oosd = M["oos_default"]

    # 归一化指标（0-1区间，1=最优）
    # 夏普/索提诺/Calmar/日胜率 → 越大越好，直接归一化
    # 最大回撤/VaR/波动 → 越小（绝对值）越好，取倒数归一化
    metrics_names = ["夏普比率", "索提诺比率", "Calmar比率", "日胜率", "回撤控制", "波动控制"]

    def normalize(val, vmin, vmax, higher_better=True):
        if higher_better:
            return (val - vmin) / (vmax - vmin) if vmax > vmin else 0.5
        else:
            return (vmax - val) / (vmax - vmin) if vmax > vmin else 0.5

    # 收集原始值
    sharpes = [ins["夏普"], oos["夏普"], oosd["夏普"]]
    sortinos = [ins["索提诺"], oos["索提诺"], oosd["索提诺"]]
    calmars = [ins["Calmar"], oos["Calmar"], oosd["Calmar"]]
    winrates = [ins["日胜率"], oos["日胜率"], oosd["日胜率"]]
    mdds = [abs(ins["最大回撤"]), abs(oos["最大回撤"]), abs(oosd["最大回撤"])]
    vols = [ins["年化波动"], oos["年化波动"], oosd["年化波动"]]

    # 归一化
    ins_norm = [
        normalize(sharpes[0], min(sharpes), max(sharpes)),
        normalize(sortinos[0], min(sortinos), max(sortinos)),
        normalize(calmars[0], min(calmars), max(calmars)),
        normalize(winrates[0], min(winrates), max(winrates)),
        normalize(mdds[0], min(mdds), max(mdds), higher_better=False),
        normalize(vols[0], min(vols), max(vols), higher_better=False),
    ]
    oos_norm = [
        normalize(sharpes[1], min(sharpes), max(sharpes)),
        normalize(sortinos[1], min(sortinos), max(sortinos)),
        normalize(calmars[1], min(calmars), max(calmars)),
        normalize(winrates[1], min(winrates), max(winrates)),
        normalize(mdds[1], min(mdds), max(mdds), higher_better=False),
        normalize(vols[1], min(vols), max(vols), higher_better=False),
    ]
    def_norm = [
        normalize(sharpes[2], min(sharpes), max(sharpes)),
        normalize(sortinos[2], min(sortinos), max(sortinos)),
        normalize(calmars[2], min(calmars), max(calmars)),
        normalize(winrates[2], min(winrates), max(winrates)),
        normalize(mdds[2], min(mdds), max(mdds), higher_better=False),
        normalize(vols[2], min(vols), max(vols), higher_better=False),
    ]

    # 雷达图
    angles = np.linspace(0, 2 * np.pi, len(metrics_names), endpoint=False).tolist()
    angles += angles[:1]

    ins_norm += ins_norm[:1]
    oos_norm += oos_norm[:1]
    def_norm += def_norm[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    ax.plot(angles, ins_norm, "o-", linewidth=2.5, color=C_UP, label="样本内（寻优）")
    ax.fill(angles, ins_norm, alpha=0.15, color=C_UP)
    ax.plot(angles, oos_norm, "s-", linewidth=2.5, color=C_BLUE, label="样本外（寻优）")
    ax.fill(angles, oos_norm, alpha=0.15, color=C_BLUE)
    ax.plot(angles, def_norm, "^-", linewidth=2.5, color=C_GREY, label="样本外（默认）")
    ax.fill(angles, def_norm, alpha=0.15, color=C_GREY)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(metrics_names, fontsize=11)
    ax.set_ylim(0, 1.1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=8)
    ax.set_title("风险调整后指标雷达图（归一化）", fontsize=14, fontweight="bold", pad=20)
    ax.legend(fontsize=10, loc="upper right", bbox_to_anchor=(1.3, 1.1))

    plt.tight_layout()
    path = os.path.join(FIG_DIR, "fig_risk_dashboard.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {path}")


# ========================================================================
# 主函数
# ========================================================================
def main():
    print("=" * 60)
    print("TASK8 汇总图表生成")
    print("=" * 60)

    print("\n>>> 生成图1：策略体系总览")
    fig1_summary()

    print("\n>>> 生成图2：各策略核心指标对比")
    fig2_strategy_comparison()

    print("\n>>> 生成图3：机器学习流程图")
    fig3_ml_pipeline()

    print("\n>>> 生成图4：机器学习模型效果对比")
    fig4_ml_model_comparison()

    print("\n>>> 生成图5：样本内外指标对比")
    fig5_insample_oos()

    print("\n>>> 生成图6：风险指标雷达图")
    fig6_risk_dashboard()

    print("\n" + "=" * 60)
    print("全部6张汇总图表生成完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
