#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK4 - 海龟交易策略（Turtle Trading Strategy）
================================================

本脚本实现完整的海龟交易策略分析流程（简化但忠于原版的单系统）：
1. 加载已存储的股价数据
2. 计算唐奇安高低点通道（Donchian Channel）
3. 计算平均真实波幅（ATR）
4. 生成买入/卖出交易信号（突破 N 日高点买入；跌破 N/2 日低点 或 触及 2×ATR 止损 卖出）
5. 模拟交易回测（ATR 单单位仓位管理，每笔风险 1% 权益；2×ATR 盘中触及即止损）
6. 计算量化评估指标（MDD、夏普比率、累计回报等）
7. 绘制可视化图形（股价+通道+信号、净值、回撤、综合面板、多参数、多股票）
8. 参数扫描（通道周期 10/20/55）与多股票对比，并导出 CSV

可复用 TASK3 的约定：红涨绿跌、PingFang 中文字体、Agg 后端、utf-8-sig 加载。

作者：夏阳
课程：量化策略课程 - TASK4
"""

import os
import math
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
COLOR_UP = "#E74C3C"    # 红色（买入/上涨）
COLOR_DOWN = "#27AE60"  # 绿色（卖出/下跌）
COLOR_BLUE = "#3498DB"
COLOR_DARK = "#34495E"
COLOR_GRAY = "#95A5A6"

# ===== 路径配置 =====
BASE_DIR = "/Users/wangyanfen/Desktop/量化策略课程"
TASK1_DIR = os.path.join(BASE_DIR, "TASK1")
TASK3_DIR = os.path.join(BASE_DIR, "TASK3")
DATA_DIR = os.path.join(TASK3_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "TASK4")  # 图表和 CSV 输出到 TASK4 目录

# 股票配置：(数据文件路径, 代码, 名称) —— 直接复用已存储的数据
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

# ===== 策略默认参数 =====
DEFAULT_N = 20          # 唐奇安买入通道周期（系统1默认20日）
INITIAL_CAPITAL = 100000.0   # 初始资金
RISK_FRACTION = 0.01   # 每笔交易风险占权益比例（1%）
STOP_MULT = 2.0        # 止损倍数：2 × ATR

# 多参数对比的通道周期组合
PARAM_N_LIST = [10, 20, 55]


# ========================================================================
# 第一部分：数据加载
# ========================================================================

def load_stock_data(filepath: str) -> pd.DataFrame:
    """
    加载标准格式股价 CSV 数据（复用 TASK3 约定）
    列：股票代码,交易日期,开盘价,最高价,最低价,收盘价,前收盘价,涨跌额,涨跌幅(%),成交量(手),成交额(千元)
    """
    df = pd.read_csv(filepath, encoding="utf-8-sig")
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期").reset_index(drop=True)
    return df


# ========================================================================
# 第二部分：唐奇安通道 与 ATR
# ========================================================================

def calc_donchian(df: pd.DataFrame, N: int, M: int) -> pd.DataFrame:
    """
    计算唐奇安高低点通道（Donchian Channel）
    上轨 = 前 N 日最高价的最大值（买入触发线）
    下轨 = 前 M 日最低价的最小值（卖出触发线）
    使用 shift(1) 避免未来函数。
    """
    df = df.copy()
    df["upper"] = df["最高价"].rolling(window=N, min_periods=N).max().shift(1)
    df["lower"] = df["最低价"].rolling(window=M, min_periods=M).min().shift(1)
    return df


def calc_atr(df: pd.DataFrame, ATR_N: int) -> pd.DataFrame:
    """
    计算平均真实波幅（ATR, Average True Range）
    TR = max(最高价-最低价, |最高价-昨收|, |最低价-昨收|)
    ATR = TR 的 Wilder 平滑（EMA, alpha = 1/ATR_N）
    """
    df = df.copy()
    prev_close = df["收盘价"].shift(1)
    tr = pd.concat([
        df["最高价"] - df["最低价"],
        (df["最高价"] - prev_close).abs(),
        (df["最低价"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    df["TR"] = tr
    df["ATR"] = tr.ewm(alpha=1.0 / ATR_N, adjust=False).mean()
    return df


# ========================================================================
# 第三部分：海龟交易信号
# ========================================================================

def calc_turtle_signals(df: pd.DataFrame, N: int, M: int,
                        stop_mult: float = STOP_MULT) -> pd.DataFrame:
    """
    生成海龟交易信号（单系统）
    买入：空仓 且 收盘价 > 上轨（前 N 日高点突破）
    卖出：持仓 且（当日最低价 ≤ 买入价 - 2×ATR（止损） 或 收盘价 < 下轨（通道退出））
    止损优先级高于通道退出。

    新增列：signal(1买/-1卖/0无), position(1持仓/0空仓),
            exit_reason(stop_loss/channel_exit), entry_price, atr_entry
    """
    df = df.copy()
    df = calc_donchian(df, N, M)
    df = calc_atr(df, ATR_N=N)  # ATR 周期与通道周期一致（海龟惯例）

    df["signal"] = 0
    df["position"] = 0
    df["exit_reason"] = ""
    df["entry_price"] = np.nan
    df["atr_entry"] = np.nan

    position = 0
    entry_price = 0.0
    atr_entry = 0.0

    for i in range(len(df)):
        if position == 0:
            # 买入：突破 N 日高点
            up = df.at[i, "upper"]
            if not np.isnan(up) and df.at[i, "收盘价"] > up:
                df.at[i, "signal"] = 1
                position = 1
                entry_price = df.at[i, "收盘价"]
                atr_entry = df.at[i, "ATR"]
                df.at[i, "entry_price"] = entry_price
                df.at[i, "atr_entry"] = atr_entry
        else:
            # 卖出：先判止损（盘中触及），再判通道退出
            stop_price = entry_price - stop_mult * atr_entry
            if df.at[i, "最低价"] <= stop_price:
                df.at[i, "signal"] = -1
                df.at[i, "exit_reason"] = "stop_loss"
                position = 0
                entry_price = 0.0
                atr_entry = 0.0
            else:
                low = df.at[i, "lower"]
                if not np.isnan(low) and df.at[i, "收盘价"] < low:
                    df.at[i, "signal"] = -1
                    df.at[i, "exit_reason"] = "channel_exit"
                    position = 0
                    entry_price = 0.0
                    atr_entry = 0.0
        df.at[i, "position"] = position

    return df


# ========================================================================
# 第四部分：海龟回测引擎
# ========================================================================

def turtle_backtest(df: pd.DataFrame, initial_capital: float = INITIAL_CAPITAL,
                    risk_fraction: float = RISK_FRACTION,
                    stop_mult: float = STOP_MULT) -> pd.DataFrame:
    """
    模拟交易回测（ATR 单单位仓位管理）

    仓位管理（海龟核心）：
        每笔风险 = risk_fraction × 当前权益
        股数 = floor(每笔风险 / ATR_entry)   # 使 1 个 ATR 波动恰好对应 1% 权益风险
    止损：持仓中若当日最低价 ≤ 买入价 - 2×ATR，以止损价（买入价-2×ATR）成交离场。

    产出列（与 TASK3 calc_metrics 对齐，便于复用）：
        equity, shares, strategy_return, cumulative_return,
        portfolio_value, benchmark_value, drawdown
    """
    df = df.copy()
    equity = initial_capital
    cash = initial_capital
    shares = 0
    in_position = False
    entry_price = 0.0
    atr_entry = 0.0

    df["equity"] = initial_capital
    df["shares"] = 0

    for i in range(len(df)):
        sig = df.at[i, "signal"]
        close = df.at[i, "收盘价"]

        if not in_position:
            if sig == 1:
                atr_entry = df.at[i, "atr_entry"]
                if atr_entry and atr_entry > 0:
                    shares = math.floor((risk_fraction * equity) / atr_entry)
                else:
                    shares = 0
                if shares > 0:
                    cost = shares * close
                    cash = equity - cost
                    in_position = True
                    entry_price = close
                # shares == 0 时放弃本次建仓
        else:
            if sig == -1:
                if df.at[i, "exit_reason"] == "stop_loss":
                    exit_price = entry_price - stop_mult * atr_entry  # 盘中触及止损价
                else:
                    exit_price = close  # 通道退出，收盘价成交
                proceeds = shares * exit_price
                equity = cash + proceeds
                cash = equity
                shares = 0
                in_position = False
                entry_price = 0.0
                atr_entry = 0.0
            else:
                # 持仓盯市
                equity = cash + shares * close

        df.at[i, "equity"] = equity
        df.at[i, "shares"] = shares

    df["daily_return"] = df["equity"].pct_change().fillna(0.0)
    df["strategy_return"] = df["daily_return"]
    df["cumulative_return"] = (1 + df["strategy_return"]).cumprod() - 1
    df["portfolio_value"] = df["equity"]
    df["benchmark_value"] = initial_capital * (1 + df["收盘价"].pct_change().fillna(0)).cumprod()
    df["peak"] = df["portfolio_value"].cummax()
    df["drawdown"] = (df["portfolio_value"] - df["peak"]) / df["peak"]

    return df


# ========================================================================
# 第五部分：量化指标计算（复用 TASK3 逻辑）
# ========================================================================

def calc_metrics(df: pd.DataFrame, risk_free_rate: float = 0.03) -> dict:
    """
    计算策略评估指标（MDD、夏普比率、累计回报等）
    输入需含：strategy_return, drawdown, cumulative_return, signal, benchmark_value
    """
    cumulative_return = df["cumulative_return"].iloc[-1]
    n_days = len(df) - 1
    annual_return = (1 + cumulative_return) ** (252 / n_days) - 1 if n_days > 0 else 0.0

    mdd = df["drawdown"].min()

    daily_rf = risk_free_rate / 252
    excess_returns = df["strategy_return"] - daily_rf
    excess_returns = excess_returns.dropna()
    if len(excess_returns) > 0 and excess_returns.std() > 0:
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
    else:
        sharpe = 0.0

    buy_count = int((df["signal"] == 1).sum())
    sell_count = int((df["signal"] == -1).sum())
    stop_count = int((df["exit_reason"] == "stop_loss").sum())
    channel_count = int((df["exit_reason"] == "channel_exit").sum())

    benchmark_return = df["benchmark_value"].iloc[-1] / df["benchmark_value"].iloc[0] - 1
    benchmark_peak = df["benchmark_value"].cummax()
    benchmark_dd = (df["benchmark_value"] - benchmark_peak) / benchmark_peak
    benchmark_mdd = benchmark_dd.min()

    return {
        "cumulative_return": cumulative_return,
        "annual_return": annual_return,
        "mdd": mdd,
        "sharpe": sharpe,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "stop_count": stop_count,
        "channel_count": channel_count,
        "benchmark_return": benchmark_return,
        "benchmark_mdd": benchmark_mdd,
        "n_days": n_days,
    }


# ========================================================================
# 第六部分：可视化
# ========================================================================

def plot_price_channel_signals(df: pd.DataFrame, stock_name: str,
                               N: int, M: int, save_path: str) -> None:
    """图1：股价 + 唐奇安通道 + 买入/卖出信号标记"""
    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(df["交易日期"], df["收盘价"], color=COLOR_DARK, linewidth=1.2,
            label="收盘价", alpha=0.85)
    ax.plot(df["交易日期"], df["upper"], color=COLOR_UP, linewidth=1.3,
            label=f"上轨(前{N}日高)", alpha=0.9)
    ax.plot(df["交易日期"], df["lower"], color=COLOR_BLUE, linewidth=1.3,
            label=f"下轨(前{M}日低)", alpha=0.9)

    buys = df[df["signal"] == 1]
    ax.scatter(buys["交易日期"], buys["收盘价"], marker="^", color=COLOR_UP,
               s=110, zorder=5, label="买入信号(突破高点)")
    sells = df[df["signal"] == -1]
    ax.scatter(sells["交易日期"], sells["收盘价"], marker="v", color=COLOR_DOWN,
               s=110, zorder=5, label="卖出信号(止损/破低)")

    ax.set_title(f"{stock_name} 海龟策略：股价与唐奇安通道 (N={N}, M={M})",
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
                         N: int, M: int, save_path: str) -> None:
    """图2：策略净值曲线 vs 基准净值曲线"""
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP,
            linewidth=1.5, label="策略净值")
    ax.plot(df["交易日期"], df["benchmark_value"], color=COLOR_BLUE,
            linewidth=1.2, label="基准净值(持有不动)", alpha=0.7)
    ax.axhline(y=INITIAL_CAPITAL, color=COLOR_GRAY, linestyle="--", alpha=0.5, label="初始资金")

    ax.set_title(f"{stock_name} 海龟策略净值曲线 (N={N}, M={M})",
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
                  N: int, M: int, save_path: str) -> None:
    """图3：策略回撤曲线"""
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(df["交易日期"], df["drawdown"], 0,
                    color=COLOR_DOWN, alpha=0.4, label="回撤区域")
    ax.plot(df["交易日期"], df["drawdown"], color=COLOR_DOWN, linewidth=1.2)

    mdd_idx = df["drawdown"].idxmin()
    mdd_val = df["drawdown"].iloc[mdd_idx]
    mdd_date = df["交易日期"].iloc[mdd_idx]
    ax.annotate(f"MDD: {mdd_val:.2%}\n({mdd_date.strftime('%Y-%m-%d')})",
                xy=(mdd_date, mdd_val), xytext=(mdd_date, mdd_val * 0.7),
                fontsize=11, color=COLOR_DOWN, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=COLOR_DOWN))

    ax.set_title(f"{stock_name} 海龟策略回撤曲线 (N={N}, M={M})",
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
                             stock_name: str, N: int, M: int,
                             save_path: str) -> None:
    """图4：综合面板（价格+通道+信号 / ATR / 净值 / 回撤）"""
    fig = plt.figure(figsize=(16, 14))
    gs = GridSpec(4, 1, height_ratios=[2, 1, 1.2, 1.2], hspace=0.3)

    # 子图1：股价 + 通道 + 信号
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df["交易日期"], df["收盘价"], color=COLOR_DARK, linewidth=1, alpha=0.85)
    ax1.plot(df["交易日期"], df["upper"], color=COLOR_UP, linewidth=1.2, label=f"上轨(N={N})")
    ax1.plot(df["交易日期"], df["lower"], color=COLOR_BLUE, linewidth=1.2, label=f"下轨(M={M})")
    buys = df[df["signal"] == 1]
    sells = df[df["signal"] == -1]
    ax1.scatter(buys["交易日期"], buys["收盘价"], marker="^", color=COLOR_UP, s=80, label="买入")
    ax1.scatter(sells["交易日期"], sells["收盘价"], marker="v", color=COLOR_DOWN, s=80, label="卖出")
    ax1.set_title(f"{stock_name} 海龟策略综合面板 (N={N}, M={M})", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    # 子图2：ATR 曲线
    ax2 = fig.add_subplot(gs[1])
    ax2.plot(df["交易日期"], df["ATR"], color="#8E44AD", linewidth=1.2, label="ATR(平均真实波幅)")
    ax2.set_ylabel("ATR", fontsize=10)
    ax2.legend(loc="upper left", fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    # 子图3：净值曲线
    ax3 = fig.add_subplot(gs[2])
    ax3.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP, linewidth=1.2, label="策略净值")
    ax3.plot(df["交易日期"], df["benchmark_value"], color=COLOR_BLUE, linewidth=1,
             alpha=0.7, label="基准净值")
    ax3.axhline(y=INITIAL_CAPITAL, color=COLOR_GRAY, linestyle="--", alpha=0.4)
    ax3.set_ylabel("净值 (元)", fontsize=10)
    ax3.legend(loc="upper left", fontsize=9)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    # 子图4：回撤
    ax4 = fig.add_subplot(gs[3])
    ax4.fill_between(df["交易日期"], df["drawdown"], 0, color=COLOR_DOWN, alpha=0.4)
    ax4.plot(df["交易日期"], df["drawdown"], color=COLOR_DOWN, linewidth=1)
    ax4.set_ylabel("回撤幅度", fontsize=10)
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax4.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

    # 指标信息框
    info_text = (
        f"累计回报: {metrics['cumulative_return']:.2%}  |  "
        f"年化收益: {metrics['annual_return']:.2%}  |  "
        f"最大回撤: {metrics['mdd']:.2%}  |  "
        f"夏普比率: {metrics['sharpe']:.2f}  |  "
        f"买入: {metrics['buy_count']} 卖出: {metrics['sell_count']} "
        f"(止损:{metrics['stop_count']}/破低:{metrics['channel_count']})"
    )
    fig.text(0.5, 0.01, info_text, ha="center", fontsize=11, fontweight="bold",
             color="#2C3E50", bbox=dict(boxstyle="round,pad=0.5", facecolor="#ECF0F1", alpha=0.8))

    plt.subplots_adjust(top=0.95, bottom=0.08, hspace=0.3)
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")


def plot_multi_params(stock_name: str, stock_key: str, save_path: str) -> list:
    """图5：多参数对比（不同通道周期的策略表现）"""
    filepath = STOCK_FILES[stock_key]["path"]
    df_raw = load_stock_data(filepath)

    fig, axes = plt.subplots(len(PARAM_N_LIST), 2, figsize=(16, 4 * len(PARAM_N_LIST)))
    all_metrics = []
    for i, N in enumerate(PARAM_N_LIST):
        M = N // 2
        df_sig = calc_turtle_signals(df_raw, N, M)
        df_bt = turtle_backtest(df_sig)
        m = calc_metrics(df_bt)
        all_metrics.append({"N": N, "M": M, **m})

        # 左列：净值曲线
        ax_val = axes[i][0]
        ax_val.plot(df_bt["交易日期"], df_bt["portfolio_value"],
                    color=COLOR_UP, linewidth=1.2, label=f"策略 N={N}/M={M}")
        ax_val.plot(df_bt["交易日期"], df_bt["benchmark_value"],
                    color=COLOR_BLUE, linewidth=0.8, alpha=0.6, label="基准")
        ax_val.set_title(f"N={N}/M={M} 净值曲线", fontsize=11)
        ax_val.legend(fontsize=8)
        ax_val.grid(True, alpha=0.3)
        ax_val.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

        # 右列：回撤曲线
        ax_dd = axes[i][1]
        ax_dd.fill_between(df_bt["交易日期"], df_bt["drawdown"], 0,
                           color=COLOR_DOWN, alpha=0.4)
        ax_dd.plot(df_bt["交易日期"], df_bt["drawdown"], color=COLOR_DOWN, linewidth=1)
        ax_dd.set_title(f"N={N}/M={M} 回撤 (MDD={m['mdd']:.2%})", fontsize=11)
        ax_dd.grid(True, alpha=0.3)
        ax_dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    fig.suptitle(f"{stock_name} 海龟策略多通道周期对比", fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")
    return all_metrics


def plot_multi_stocks(N: int, M: int, save_path: str) -> dict:
    """图6：多股票对比（同一参数在不同股票上的表现）"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    all_metrics = {}
    stocks_list = ["宁德时代", "平安银行", "贵州茅台", "五粮液"]

    for i, sk in enumerate(stocks_list):
        filepath = STOCK_FILES[sk]["path"]
        df_raw = load_stock_data(filepath)
        df_sig = calc_turtle_signals(df_raw, N, M)
        df_bt = turtle_backtest(df_sig)
        m = calc_metrics(df_bt)
        all_metrics[sk] = m

        ax = axes[i // 2][i % 2]
        ax.plot(df_bt["交易日期"], df_bt["portfolio_value"],
                color=COLOR_UP, linewidth=1.2, label="策略净值")
        ax.plot(df_bt["交易日期"], df_bt["benchmark_value"],
                color=COLOR_BLUE, linewidth=0.8, alpha=0.6, label="基准净值")
        ax.set_title(f"{sk} N={N}/M={M} (回报={m['cumulative_return']:.2%}, 夏普={m['sharpe']:.2f})",
                     fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    fig.suptitle(f"海龟策略(N={N}/M={M}) 多股票对比", fontsize=14, fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")
    return all_metrics


def plot_metrics_bar(all_stocks_metrics: dict, N: int, M: int, save_path: str) -> None:
    """图7：多股票指标对比柱状图"""
    stocks = list(all_stocks_metrics.keys())
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    cr_vals = [all_stocks_metrics[s]["cumulative_return"] * 100 for s in stocks]
    colors = [COLOR_UP if v > 0 else COLOR_DOWN for v in cr_vals]
    axes[0].bar(stocks, cr_vals, color=colors, alpha=0.85)
    axes[0].set_title("累计回报 (%)", fontsize=12, fontweight="bold")
    axes[0].axhline(y=0, color=COLOR_GRAY, linewidth=0.5)
    for j, v in enumerate(cr_vals):
        axes[0].text(j, v + (1 if v >= 0 else -2), f"{v:.1f}", ha="center", fontsize=9)

    mdd_vals = [all_stocks_metrics[s]["mdd"] * 100 for s in stocks]
    axes[1].bar(stocks, mdd_vals, color=COLOR_DOWN, alpha=0.85)
    axes[1].set_title("最大回撤 MDD (%)", fontsize=12, fontweight="bold")
    for j, v in enumerate(mdd_vals):
        axes[1].text(j, v - 1, f"{v:.1f}", ha="center", fontsize=9)

    sharpe_vals = [all_stocks_metrics[s]["sharpe"] for s in stocks]
    colors = [COLOR_UP if v > 0 else COLOR_DOWN for v in sharpe_vals]
    axes[2].bar(stocks, sharpe_vals, color=colors, alpha=0.85)
    axes[2].set_title("夏普比率", fontsize=12, fontweight="bold")
    axes[2].axhline(y=0, color=COLOR_GRAY, linewidth=0.5)
    for j, v in enumerate(sharpe_vals):
        axes[2].text(j, v + (0.05 if v >= 0 else -0.12), f"{v:.2f}", ha="center", fontsize=9)

    fig.suptitle(f"海龟策略(N={N}/M={M}) 多股票指标对比", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save_path}")


# ========================================================================
# 第七部分：CSV 数据导出
# ========================================================================

def export_signal_csv(df: pd.DataFrame, stock_name: str, N: int, M: int) -> str:
    """导出信号+回测数据 CSV"""
    out_cols = ["交易日期", "收盘价", "upper", "lower", "ATR", "signal",
                "position", "exit_reason", "strategy_return",
                "cumulative_return", "portfolio_value", "drawdown"]
    df_out = df[out_cols].copy()
    df_out.columns = ["交易日期", "收盘价", f"上轨(前{N}日高)", f"下轨(前{M}日低)", "ATR",
                      "信号(1买/-1卖/0无)", "持仓(1/0)", "退出原因", "策略日收益率",
                      "累计收益率", "策略净值", "回撤幅度"]
    path = os.path.join(OUTPUT_DIR, f"{stock_name}_海龟策略_N{N}_回测数据.csv")
    df_out.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {path}")
    return path


def export_params_csv(all_params_metrics: list, stock_name: str) -> str:
    """导出多参数对比指标 CSV"""
    rows = []
    for m in all_params_metrics:
        rows.append({
            "通道参数": f"N{m['N']}/M{m['M']}",
            "买入周期N": m["N"],
            "卖出周期M": m["M"],
            "累计回报": f"{m['cumulative_return']:.4%}",
            "年化收益率": f"{m['annual_return']:.4%}",
            "最大回撤MDD": f"{m['mdd']:.4%}",
            "夏普比率": f"{m['sharpe']:.4f}",
            "买入次数": m["buy_count"],
            "卖出次数": m["sell_count"],
            "止损次数": m["stop_count"],
            "破低次数": m["channel_count"],
        })
    df_p = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, f"{stock_name}_多参数对比指标.csv")
    df_p.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {path}")
    return path


def export_metrics_csv(metrics_dict: dict, filename: str) -> str:
    """导出多股票指标汇总 CSV"""
    rows = []
    for stock_name, m in metrics_dict.items():
        rows.append({
            "股票": stock_name,
            "累计回报": f"{m['cumulative_return']:.4%}",
            "年化收益率": f"{m['annual_return']:.4%}",
            "最大回撤MDD": f"{m['mdd']:.4%}",
            "夏普比率": f"{m['sharpe']:.4f}",
            "买入次数": m["buy_count"],
            "卖出次数": m["sell_count"],
            "止损次数": m["stop_count"],
            "破低次数": m["channel_count"],
            "基准回报": f"{m['benchmark_return']:.4%}",
            "基准MDD": f"{m['benchmark_mdd']:.4%}",
        })
    df_m = pd.DataFrame(rows)
    path = os.path.join(OUTPUT_DIR, filename)
    df_m.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {path}")
    return path


# ========================================================================
# 第八部分：主流程
# ========================================================================

def run_core_analysis(N: int = DEFAULT_N):
    """核心分析：宁德时代 N=20 主案例，生成图1-4 与 CSV，返回指标"""
    print("\n>>> 第一部分：宁德时代核心分析 (N=%d/M=%d)" % (N, N // 2))
    nd_filepath = STOCK_FILES["宁德时代"]["path"]
    nd_raw = load_stock_data(nd_filepath)
    print(f"  加载宁德时代数据: {len(nd_raw)} 行, "
          f"{nd_raw['交易日期'].iloc[0].strftime('%Y-%m-%d')} ~ "
          f"{nd_raw['交易日期'].iloc[-1].strftime('%Y-%m-%d')}")

    nd_sig = calc_turtle_signals(nd_raw, N, N // 2)
    nd_bt = turtle_backtest(nd_sig)
    nd_metrics = calc_metrics(nd_bt)

    print(f"  累计回报: {nd_metrics['cumulative_return']:.2%}")
    print(f"  年化收益: {nd_metrics['annual_return']:.2%}")
    print(f"  最大回撤: {nd_metrics['mdd']:.2%}")
    print(f"  夏普比率: {nd_metrics['sharpe']:.2f}")
    print(f"  买入次数: {nd_metrics['buy_count']}, 卖出次数: {nd_metrics['sell_count']} "
          f"(其中止损:{nd_metrics['stop_count']}, 破低:{nd_metrics['channel_count']})")

    print("\n>>> 第二部分：绘制可视化图形")
    plot_price_channel_signals(nd_sig, "宁德时代", N, N // 2,
                               os.path.join(OUTPUT_DIR, "图1_股价_唐奇安通道_信号.png"))
    plot_portfolio_curve(nd_bt, "宁德时代", N, N // 2,
                         os.path.join(OUTPUT_DIR, "图2_策略净值曲线.png"))
    plot_drawdown(nd_bt, "宁德时代", N, N // 2,
                  os.path.join(OUTPUT_DIR, "图3_回撤曲线.png"))
    plot_comprehensive_panel(nd_bt, nd_metrics, "宁德时代", N, N // 2,
                             os.path.join(OUTPUT_DIR, "图4_综合面板.png"))

    print("\n>>> 第三部分：导出数据")
    export_signal_csv(nd_bt, "宁德时代", N, N // 2)

    return nd_metrics


def run_param_sweep():
    """多参数对比：N ∈ {10,20,55}"""
    print("\n>>> 第四部分：多参数对比 (N=10/20/55)")
    params_metrics = plot_multi_params("宁德时代", "宁德时代",
                                       os.path.join(OUTPUT_DIR, "图5_多参数对比.png"))
    export_params_csv(params_metrics, "宁德时代")
    return params_metrics


def run_multi_stock(N: int = DEFAULT_N):
    """多股票对比"""
    print("\n>>> 第五部分：多股票对比 (N=%d/M=%d)" % (N, N // 2))
    stocks_metrics = plot_multi_stocks(N, N // 2,
                                       os.path.join(OUTPUT_DIR, "图6_多股票对比.png"))
    plot_metrics_bar(stocks_metrics, N, N // 2,
                     os.path.join(OUTPUT_DIR, "图7_多股票指标柱状图.png"))
    export_metrics_csv(stocks_metrics, "多股票策略指标对比.csv")
    return stocks_metrics


def main():
    """运行完整分析流程"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=" * 60)
    print("TASK4 - 海龟交易策略分析")
    print("=" * 60)

    core_metrics = run_core_analysis(DEFAULT_N)
    param_metrics = run_param_sweep()
    stock_metrics = run_multi_stock(DEFAULT_N)

    print("\n" + "=" * 60)
    print("TASK4 分析全部完成！图表与 CSV 已输出至 TASK4 目录。")
    print("=" * 60)
    return core_metrics, param_metrics, stock_metrics


if __name__ == "__main__":
    main()
