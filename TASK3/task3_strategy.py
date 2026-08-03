#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK3 - 双均线策略：用均线交叉捕捉市场趋势与波动
=====================================================

本脚本实现完整的双均线策略分析流程：
1. 加载股价数据
2. 计算短/长均线
3. 生成买入卖出信号（金叉/死叉）
4. 绘制可视化图形（7张图表）
5. 模拟交易回测
6. 计算量化评估指标（MDD、Sharpe、累计回报）
7. 多参数对比
8. 多股票对比

作者：夏阳
课程：量化策略课程 - TASK3
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # 无界面后端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec

# ===== 环境配置 =====
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"

# 中文字体配置
plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# 中国股市颜色惯例：涨=红，跌=绿
COLOR_UP = "#E74C3C"   # 红色
COLOR_DOWN = "#27AE60"  # 绿色

# ===== 路径配置 =====
BASE_DIR = "/Users/wangyanfen/Desktop/量化策略课程"
TASK1_DIR = os.path.join(BASE_DIR, "TASK1")
TASK3_DIR = os.path.join(BASE_DIR, "TASK3")
DATA_DIR = os.path.join(TASK3_DIR, "data")
OUTPUT_DIR = TASK3_DIR  # 图表和CSV输出到TASK3目录

# 股票配置：(数据文件路径, 代码, 名称)
STOCK_FILES = {
    "宁德时代": {
        "path": os.path.join(TASK1_DIR, "宁德时代_300750_日线数据.csv"),
        "code": "300750.SZ",
        "name": "宁德时代",
    },
    "平安银行": {
        "path": os.path.join(DATA_DIR, "平安银行_000001.SZ_日线数据.csv"),
        "code": "000001.SZ",
        "name": "平安银行",
    },
    "贵州茅台": {
        "path": os.path.join(DATA_DIR, "贵州茅台_600519.SH_日线数据.csv"),
        "code": "600519.SH",
        "name": "贵州茅台",
    },
    "五粮液": {
        "path": os.path.join(DATA_DIR, "五粮液_000858.SZ_日线数据.csv"),
        "code": "000858.SZ",
        "name": "五粮液",
    },
}

# 默认均线参数
DEFAULT_SHORT = 5
DEFAULT_LONG = 15

# 多参数对比配置
PARAM_COMBOS = [
    (5, 15),
    (10, 30),
    (20, 60),
]


# ========================================================================
# 第一部分：数据加载
# ========================================================================

def load_stock_data(filepath: str) -> pd.DataFrame:
    """
    加载标准格式股价 CSV 数据
    列：股票代码,交易日期,开盘价,最高价,最低价,收盘价,前收盘价,涨跌额,涨跌幅(%),成交量(手),成交额(千元)
    """
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期").reset_index(drop=True)
    return df


# ========================================================================
# 第二部分：均线计算与信号生成
# ========================================================================

def calc_ma_signals(df: pd.DataFrame, short_window: int, long_window: int) -> pd.DataFrame:
    """
    计算均线并生成交易信号
    
    参数：
        df: 含 '收盘价' 列的 DataFrame
        short_window: 短均线周期
        long_window: 长均线周期
    
    返回：
        添加了 MA_short, MA_long, signal, position 列的 DataFrame
        
    信号定义：
        signal = 1 → 买入信号（金叉：短均线从下方穿越长均线）
        signal = -1 → 卖出信号（死叉：短均线从上方穿越长均线）
        signal = 0 → 无信号
        position = 1 → 持仓
        position = 0 → 空仓
    """
    df = df.copy()
    df["MA_short"] = df["收盘价"].rolling(window=short_window, min_periods=1).mean()
    df["MA_long"] = df["收盘价"].rolling(window=long_window, min_periods=1).mean()
    
    # 金叉/死叉判断
    # 信号 = 短均线与长均线的关系变化
    # 前一日短 < 长 & 当日短 > 长 → 金叉(买入)
    # 前一日短 > 长 & 当日短 < 长 → 止叉(卖出)
    df["ma_diff"] = df["MA_short"] - df["MA_long"]
    df["ma_diff_prev"] = df["ma_diff"].shift(1)
    
    df["signal"] = 0
    # 金叉：短均线从下方穿越长均线
    df.loc[(df["ma_diff_prev"] <= 0) & (df["ma_diff"] > 0), "signal"] = 1
    # 死叉：短均线从上方穿越长均线
    df.loc[(df["ma_diff_prev"] >= 0) & (df["ma_diff"] < 0), "signal"] = -1
    
    # 持仓状态：根据信号累积
    df["position"] = 0
    pos = 0
    for i in range(len(df)):
        if df.loc[i, "signal"] == 1:
            pos = 1  # 买入持仓
        elif df.loc[i, "signal"] == -1:
            pos = 0  # 卖出空仓
        df.loc[i, "position"] = pos
    
    return df


# ========================================================================
# 第三部分：回测引擎
# ========================================================================

def backtest(df: pd.DataFrame, initial_capital: float = 100000.0) -> pd.DataFrame:
    """
    模拟交易回测
    
    假设：
    - 每次买入/卖出全仓操作
    - 以收盘价成交
    - 不考虑手续费和滑点
    - 信号当日收盘执行
    
    参数：
        df: 含 signal, position, 收盘价 列的 DataFrame
        initial_capital: 初始资金
    
    返回：
        添加了 strategy_return, cumulative_return, portfolio_value, drawdown 列的 DataFrame
    """
    df = df.copy()
    
    # 日收益率（基于收盘价）
    df["daily_return"] = df["收盘价"].pct_change()
    
    # 策略收益率：持仓时获得日收益，空仓时收益为0
    df["strategy_return"] = df["position"] * df["daily_return"]
    
    # 策略累计收益率
    df["cumulative_return"] = (1 + df["strategy_return"]).cumprod() - 1
    
    # 策略净值曲线
    df["portfolio_value"] = initial_capital * (1 + df["strategy_return"]).cumprod()
    
    # 基准净值曲线（持有不动）
    df["benchmark_value"] = initial_capital * (1 + df["daily_return"]).cumprod()
    
    # 最大回撤
    df["peak"] = df["portfolio_value"].cummax()
    df["drawdown"] = (df["portfolio_value"] - df["peak"]) / df["peak"]
    
    return df


# ========================================================================
# 第四部分：量化指标计算
# ========================================================================

def calc_metrics(df: pd.DataFrame, risk_free_rate: float = 0.03) -> dict:
    """
    计算策略评估指标
    
    参数：
        df: 含 strategy_return, drawdown, cumulative_return 列的 DataFrame
        risk_free_rate: 无风险利率（年化，默认3%）
    
    返回：
        包含各指标的字典
    """
    # 累计回报
    cumulative_return = df["cumulative_return"].iloc[-1]
    
    # 年化收益率
    n_days = len(df) - 1
    annual_return = (1 + cumulative_return) ** (252 / n_days) - 1
    
    # 最大回撤 (MDD)
    mdd = df["drawdown"].min()
    
    # 夏普比率 (Sharpe Ratio)
    # 使用超额收益的均值 / 标准差
    daily_rf = risk_free_rate / 252  # 日无风险利率
    excess_returns = df["strategy_return"] - daily_rf
    # 去掉 NaN
    excess_returns = excess_returns.dropna()
    if len(excess_returns) > 0 and excess_returns.std() > 0:
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    else:
        sharpe = 0.0
    
    # 交易次数
    buy_count = (df["signal"] == 1).sum()
    sell_count = (df["signal"] == -1).sum()
    
    # 基准累计回报
    benchmark_return = df["benchmark_value"].iloc[-1] / df["benchmark_value"].iloc[0] - 1
    
    # 基准 MDD
    benchmark_peak = df["benchmark_value"].cummax()
    benchmark_dd = (df["benchmark_value"] - benchmark_peak) / benchmark_peak
    benchmark_mdd = benchmark_dd.min()
    
    return {
        "cumulative_return": cumulative_return,
        "annual_return": annual_return,
        "mdd": mdd,
        "sharpe": sharpe,
        "buy_count": int(buy_count),
        "sell_count": int(sell_count),
        "benchmark_return": benchmark_return,
        "benchmark_mdd": benchmark_mdd,
        "n_days": n_days,
    }


# ========================================================================
# 第五部分：可视化
# ========================================================================

def plot_price_ma_signals(df: pd.DataFrame, stock_name: str,
                          short_w: int, long_w: int, save_path: str) -> None:
    """
    图1：股价 + 长短均线 + 买入卖出信号标记
    """
    fig, ax = plt.subplots(figsize=(14, 7))
    
    # 股价
    ax.plot(df["交易日期"], df["收盘价"], color="#34495E", linewidth=1.2, label="收盘价", alpha=0.8)
    # 均线
    ax.plot(df["交易日期"], df["MA_short"], color=COLOR_UP, linewidth=1.5,
            label=f"MA{short_w}(短均线)", alpha=0.9)
    ax.plot(df["交易日期"], df["MA_long"], color="#3498DB", linewidth=1.5,
            label=f"MA{long_w}(长均线)", alpha=0.9)
    
    # 买入信号标记
    buy_signals = df[df["signal"] == 1]
    ax.scatter(buy_signals["交易日期"], buy_signals["收盘价"],
               marker="^", color=COLOR_UP, s=100, zorder=5,
               label="买入信号(金叉)")
    
    # 卖出信号标记
    sell_signals = df[df["signal"] == -1]
    ax.scatter(sell_signals["交易日期"], sell_signals["收盘价"],
               marker="v", color=COLOR_DOWN, s=100, zorder=5,
               label="卖出信号(死叉)")
    
    ax.set_title(f"{stock_name} 双均线策略信号图 (MA{short_w}/MA{long_w})",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("价格 (元)", fontsize=12)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")


def plot_portfolio_curve(df: pd.DataFrame, stock_name: str,
                         short_w: int, long_w: int, save_path: str) -> None:
    """
    图2：策略净值曲线 vs 基准净值曲线
    """
    fig, ax = plt.subplots(figsize=(14, 6))
    
    ax.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP,
            linewidth=1.5, label="策略净值")
    ax.plot(df["交易日期"], df["benchmark_value"], color="#3498DB",
            linewidth=1.2, label="基准净值(持有不动)", alpha=0.7)
    
    # 标注初始资金
    ax.axhline(y=100000, color="#95A5A6", linestyle="--", alpha=0.5, label="初始资金")
    
    ax.set_title(f"{stock_name} 策略净值曲线 (MA{short_w}/MA{long_w})",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("净值 (元)", fontsize=12)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")


def plot_drawdown(df: pd.DataFrame, stock_name: str,
                  short_w: int, long_w: int, save_path: str) -> None:
    """
    图3：策略回撤曲线
    """
    fig, ax = plt.subplots(figsize=(14, 5))
    
    ax.fill_between(df["交易日期"], df["drawdown"], 0,
                    color=COLOR_DOWN, alpha=0.4, label="回撤区域")
    ax.plot(df["交易日期"], df["drawdown"], color=COLOR_DOWN, linewidth=1.2)
    
    # 标注最大回撤点
    mdd_idx = df["drawdown"].idxmin()
    mdd_val = df["drawdown"].iloc[mdd_idx]
    mdd_date = df["交易日期"].iloc[mdd_idx]
    ax.annotate(f"MDD: {mdd_val:.2%}\n({mdd_date.strftime('%Y-%m-%d')})",
                xy=(mdd_date, mdd_val),
                xytext=(mdd_date, mdd_val * 0.7),
                fontsize=11, color=COLOR_DOWN, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=COLOR_DOWN))
    
    ax.set_title(f"{stock_name} 策略回撤曲线 (MA{short_w}/MA{long_w})",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("回撤幅度", fontsize=12)
    ax.legend(loc="lower left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")


def plot_comprehensive_panel(df: pd.DataFrame, metrics: dict,
                             stock_name: str, short_w: int, long_w: int,
                             save_path: str) -> None:
    """
    图4：综合面板（3个子图：信号+净值+回撤）
    """
    fig = plt.figure(figsize=(16, 12))
    gs = GridSpec(3, 1, height_ratios=[2, 1.5, 1], hspace=0.3)
    
    # 子图1：股价 + 均线 + 信号
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df["交易日期"], df["收盘价"], color="#34495E", linewidth=1, alpha=0.8)
    ax1.plot(df["交易日期"], df["MA_short"], color=COLOR_UP, linewidth=1.2, label=f"MA{short_w}")
    ax1.plot(df["交易日期"], df["MA_long"], color="#3498DB", linewidth=1.2, label=f"MA{long_w}")
    buys = df[df["signal"] == 1]
    sells = df[df["signal"] == -1]
    ax1.scatter(buys["交易日期"], buys["收盘价"], marker="^", color=COLOR_UP, s=80, label="买入")
    ax1.scatter(sells["交易日期"], sells["收盘价"], marker="v", color=COLOR_DOWN, s=80, label="卖出")
    ax1.set_title(f"{stock_name} 双均线策略综合面板 (MA{short_w}/MA{long_w})", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    
    # 子图2：净值曲线
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP, linewidth=1.2, label="策略净值")
    ax2.plot(df["交易日期"], df["benchmark_value"], color="#3498DB", linewidth=1, alpha=0.7, label="基准净值")
    ax2.axhline(y=100000, color="#95A5A6", linestyle="--", alpha=0.4)
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylabel("净值 (元)", fontsize=10)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    
    # 子图3：回撤
    ax3 = fig.add_subplot(gs[2])
    ax3.fill_between(df["交易日期"], df["drawdown"], 0, color=COLOR_DOWN, alpha=0.4)
    ax3.plot(df["交易日期"], df["drawdown"], color=COLOR_DOWN, linewidth=1)
    ax3.set_ylabel("回撤幅度", fontsize=10)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax3.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    
    # 指标信息框
    info_text = (
        f"累计回报: {metrics['cumulative_return']:.2%}  |  "
        f"年化收益: {metrics['annual_return']:.2%}  |  "
        f"最大回撤: {metrics['mdd']:.2%}  |  "
        f"夏普比率: {metrics['sharpe']:.2f}  |  "
        f"买入次数: {metrics['buy_count']}  |  "
        f"卖出次数: {metrics['sell_count']}"
    )
    fig.text(0.5, 0.01, info_text, ha="center", fontsize=11, fontweight="bold",
             color="#2C3E50", bbox=dict(boxstyle="round,pad=0.5", facecolor="#ECF0F1", alpha=0.8))
    
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")


def plot_multi_params(stock_name: str, stock_key: str, save_path: str) -> None:
    """
    图5：多参数对比（不同均线周期的策略表现）
    """
    filepath = STOCK_FILES[stock_key]["path"]
    df_raw = load_stock_data(filepath)
    
    fig, axes = plt.subplots(3, 2, figsize=(16, 12))
    
    all_metrics = []
    for i, (sw, lw) in enumerate(PARAM_COMBOS):
        df_sig = calc_ma_signals(df_raw, sw, lw)
        df_bt = backtest(df_sig)
        m = calc_metrics(df_bt)
        all_metrics.append({"short": sw, "long": lw, **m})
        
        # 左列：净值曲线
        ax_val = axes[i][0]
        ax_val.plot(df_bt["交易日期"], df_bt["portfolio_value"],
                    color=COLOR_UP, linewidth=1.2, label=f"策略MA{sw}/MA{lw}")
        ax_val.plot(df_bt["交易日期"], df_bt["benchmark_value"],
                    color="#3498DB", linewidth=0.8, alpha=0.6, label="基准")
        ax_val.set_title(f"MA{sw}/MA{lw} 净值曲线", fontsize=11)
        ax_val.legend(fontsize=8)
        ax_val.grid(True, alpha=0.3)
        ax_val.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
        
        # 右列：回撤曲线
        ax_dd = axes[i][1]
        ax_dd.fill_between(df_bt["交易日期"], df_bt["drawdown"], 0,
                           color=COLOR_DOWN, alpha=0.4)
        ax_dd.plot(df_bt["交易日期"], df_bt["drawdown"], color=COLOR_DOWN, linewidth=1)
        ax_dd.set_title(f"MA{sw}/MA{lw} 回撤 (MDD={m['mdd']:.2%})", fontsize=11)
        ax_dd.grid(True, alpha=0.3)
        ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    
    # 指标汇总
    summary = "参数对比汇总:\n"
    for m in all_metrics:
        summary += f"  MA{m['short']}/MA{m['long']}: 累计回报={m['cumulative_return']:.2%}, 夏普={m['sharpe']:.2f}, MDD={m['mdd']:.2%}\n"
    fig.text(0.5, 0.01, summary, ha="center", fontsize=10,
             color="#2C3E50", fontweight="bold",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#ECF0F1", alpha=0.8))
    
    fig.suptitle(f"{stock_name} 多均线参数对比", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0.06, 1, 0.96])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")
    
    return all_metrics


def plot_multi_stocks(short_w: int, long_w: int, save_path: str) -> None:
    """
    图6：多股票对比（同一策略在不同股票上的表现）
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    all_metrics = {}
    stocks_list = ["宁德时代", "平安银行", "贵州茅台", "五粮液"]
    
    for i, sk in enumerate(stocks_list):
        filepath = STOCK_FILES[sk]["path"]
        df_raw = load_stock_data(filepath)
        df_sig = calc_ma_signals(df_raw, short_w, long_w)
        df_bt = backtest(df_sig)
        m = calc_metrics(df_bt)
        all_metrics[sk] = m
        
        ax = axes[i // 2][i % 2]
        ax.plot(df_bt["交易日期"], df_bt["portfolio_value"],
                color=COLOR_UP, linewidth=1.2, label=f"策略净值")
        ax.plot(df_bt["交易日期"], df_bt["benchmark_value"],
                color="#3498DB", linewidth=0.8, alpha=0.6, label="基准净值")
        ax.set_title(f"{sk} MA{short_w}/MA{long_w} (回报={m['cumulative_return']:.2%}, 夏普={m['sharpe']:.2f})",
                     fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    
    fig.suptitle(f"双均线策略(MA{short_w}/MA{long_w}) 多股票对比", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")
    
    return all_metrics


def plot_metrics_bar(all_stocks_metrics: dict, short_w: int, long_w: int, save_path: str) -> None:
    """
    图7：多股票指标对比柱状图
    """
    stocks = list(all_stocks_metrics.keys())
    
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    
    # 累计回报
    cr_vals = [all_stocks_metrics[s]["cumulative_return"] * 100 for s in stocks]
    colors = [COLOR_UP if v > 0 else COLOR_DOWN for v in cr_vals]
    axes[0].bar(stocks, cr_vals, color=colors, alpha=0.8)
    axes[0].set_title("累计回报 (%)", fontsize=12, fontweight="bold")
    axes[0].axhline(y=0, color="#95A5A6", linewidth=0.5)
    
    # 最大回撤
    mdd_vals = [all_stocks_metrics[s]["mdd"] * 100 for s in stocks]
    axes[1].bar(stocks, mdd_vals, color=COLOR_DOWN, alpha=0.8)
    axes[1].set_title("最大回撤 MDD (%)", fontsize=12, fontweight="bold")
    
    # 夏普比率
    sharpe_vals = [all_stocks_metrics[s]["sharpe"] for s in stocks]
    colors = [COLOR_UP if v > 0 else COLOR_DOWN for v in sharpe_vals]
    axes[2].bar(stocks, sharpe_vals, color=colors, alpha=0.8)
    axes[2].set_title("夏普比率", fontsize=12, fontweight="bold")
    axes[2].axhline(y=0, color="#95A5A6", linewidth=0.5)
    
    fig.suptitle(f"双均线策略(MA{short_w}/MA{long_w}) 多股票指标对比", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")


# ========================================================================
# 第六部分：CSV 数据导出
# ========================================================================

def export_signal_csv(df: pd.DataFrame, stock_name: str,
                      short_w: int, long_w: int) -> str:
    """
    导出信号+回测数据 CSV
    """
    out_cols = ["交易日期", "收盘价", "MA_short", "MA_long", "signal", "position",
                "strategy_return", "cumulative_return", "portfolio_value", "drawdown"]
    df_out = df[out_cols].copy()
    df_out.columns = ["交易日期", "收盘价", f"MA{short_w}", f"MA{long_w}",
                      "信号(1买/-1卖/0无)", "持仓状态", "策略日收益率",
                      "累计收益率", "策略净值", "回撤幅度"]
    
    path = os.path.join(OUTPUT_DIR, f"{stock_name}_双均线策略_MA{short_w}_MA{long_w}_回测数据.csv")
    df_out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {path}")
    return path


def export_metrics_csv(metrics_dict: dict, filename: str) -> str:
    """
    导出指标汇总 CSV
    """
    rows = []
    for stock_name, m in metrics_dict.items():
        rows.append({
            "股票": stock_name,
            "累计回报": f"{m['cumulative_return']:.4%}",
            "年化收益率": f"{m['annual_return']:.4%}",
            "最大回撤MDD": f"{m['mdd']:.4%}",
            "夏普比率": f"{m['sharpe']:.4f}",
            "买入次数": m['buy_count'],
            "卖出次数": m['sell_count'],
            "基准回报": f"{m['benchmark_return']:.4%}",
            "基准MDD": f"{m['benchmark_mdd']:.4%}",
        })
    
    df_m = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, filename)
    df_m.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {path}")
    return path


def export_params_csv(all_params_metrics: list, stock_name: str) -> str:
    """
    导出多参数对比指标 CSV
    """
    rows = []
    for m in all_params_metrics:
        rows.append({
            "均线参数": f"MA{m['short']}/MA{m['long']}",
            "短均线": m['short'],
            "长均线": m['long'],
            "累计回报": f"{m['cumulative_return']:.4%}",
            "年化收益率": f"{m['annual_return']:.4%}",
            "最大回撤MDD": f"{m['mdd']:.4%}",
            "夏普比率": f"{m['sharpe']:.4f}",
            "买入次数": m['buy_count'],
            "卖出次数": m['sell_count'],
        })
    
    df_p = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, f"{stock_name}_多参数对比指标.csv")
    df_p.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {path}")
    return path


# ========================================================================
# 第七部分：主流程
# ========================================================================

def main():
    """运行完整分析流程"""
    print("=" * 60)
    print("TASK3 - 双均线策略分析")
    print("=" * 60)
    
    # ===== 核心股票分析：宁德时代 MA5/MA15 =====
    print("\n>>> 第一部分：宁德时代核心分析 (MA5/MA15)")
    nd_filepath = STOCK_FILES["宁德时代"]["path"]
    nd_raw = load_stock_data(nd_filepath)
    print(f"  加载宁德时代数据: {len(nd_raw)} 行, {nd_raw['交易日期'].iloc[0].strftime('%Y-%m-%d')} ~ {nd_raw['交易日期'].iloc[-1].strftime('%Y-%m-%d')}")
    
    # 计算信号
    nd_sig = calc_ma_signals(nd_raw, DEFAULT_SHORT, DEFAULT_LONG)
    # 回测
    nd_bt = backtest(nd_sig)
    # 指标
    nd_metrics = calc_metrics(nd_bt)
    
    print(f"  累计回报: {nd_metrics['cumulative_return']:.2%}")
    print(f"  年化收益: {nd_metrics['annual_return']:.2%}")
    print(f"  最大回撤: {nd_metrics['mdd']:.2%}")
    print(f"  夏普比率: {nd_metrics['sharpe']:.2f}")
    print(f"  买入次数: {nd_metrics['buy_count']}, 卖出次数: {nd_metrics['sell_count']}")
    
    # 绘图
    print("\n>>> 第二部分：绘制可视化图形")
    plot_price_ma_signals(nd_sig, "宁德时代", DEFAULT_SHORT, DEFAULT_LONG,
                         os.path.join(OUTPUT_DIR, "图1_股价均线信号.png"))
    plot_portfolio_curve(nd_bt, "宁德时代", DEFAULT_SHORT, DEFAULT_LONG,
                        os.path.join(OUTPUT_DIR, "图2_策略净值曲线.png"))
    plot_drawdown(nd_bt, "宁德时代", DEFAULT_SHORT, DEFAULT_LONG,
                  os.path.join(OUTPUT_DIR, "图3_策略回撤曲线.png"))
    plot_comprehensive_panel(nd_bt, nd_metrics, "宁德时代", DEFAULT_SHORT, DEFAULT_LONG,
                            os.path.join(OUTPUT_DIR, "图4_综合面板.png"))
    
    # 导出 CSV
    print("\n>>> 第三部分：导出数据")
    export_signal_csv(nd_bt, "宁德时代", DEFAULT_SHORT, DEFAULT_LONG)
    
    # ===== 多参数对比 =====
    print("\n>>> 第四部分：多参数对比 (MA5/MA15, MA10/MA30, MA20/MA60)")
    params_metrics = plot_multi_params("宁德时代", "宁德时代",
                                        os.path.join(OUTPUT_DIR, "图5_多参数对比.png"))
    export_params_csv(params_metrics, "宁德时代")
    
    # ===== 多股票对比 =====
    print("\n>>> 第五部分：多股票对比 (MA5/MA15)")
    stocks_metrics = plot_multi_stocks(DEFAULT_SHORT, DEFAULT_LONG,
                                        os.path.join(OUTPUT_DIR, "图6_多股票对比.png"))
    plot_metrics_bar(stocks_metrics, DEFAULT_SHORT, DEFAULT_LONG,
                     os.path.join(OUTPUT_DIR, "图7_多股票指标柱状图.png"))
    export_metrics_csv(stocks_metrics, "多股票策略指标对比.csv")
    
    print("\n" + "=" * 60)
    print("TASK3 分析全部完成！")
    print("=" * 60)
    
    # 返回指标供后续使用
    return nd_metrics, params_metrics, stocks_metrics


if __name__ == "__main__":
    main()
