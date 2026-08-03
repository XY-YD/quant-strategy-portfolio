#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK4 进阶版 —— 经典双系统海龟交易策略（Classic Turtle, Dual-System）
==============================================================

在 TASK4 简化单系统版的基础上，忠实还原 Richard Dennis 原版"海龟"规则：

  1. 双系统并行：
       系统1 (S1)：突破 20 日高低点通道入场，跌破 10 日低 / 突破 10 日高 出场
       系统2 (S2)：突破 55 日高低点通道入场，跌破 20 日低 / 突破 20 日高 出场
       两系统在同一标的上独立建仓、独立风控，可同时持有多头与空头。
  2. 金字塔加仓（Pyramiding）：
       持仓后，价格每向有利方向推进 0.5×ATR，加 1 个单位；
       单系统最多 4 个单位（总风险 ≤ 4% 权益）。
  3. 对称做空逻辑：
       向下突破通道开空、向上突破通道平空，与做多完全对称。
  4. 2×ATR 机械止损：
       最新单位入场价反向偏离 2×ATR 时，盘中触及即平掉该系统的全部单位。
  5. ATR(20) 波动率仓位管理：
       每单位股数 = 1% 权益 ÷ ATR，使每笔风险恒定、自动适配波动。

复用 TASK4 的：数据加载、ATR 计算、股票文件映射、红涨绿跌/中文字体约定。

作者：夏阳
课程：量化策略课程 - TASK4（进阶：经典双系统 + 金字塔 + 做空）
"""

import os
import sys
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
COLOR_UP = "#E74C3C"     # 红色（做多 / 上涨）
COLOR_DOWN = "#27AE60"   # 绿色（做空 / 下跌）
COLOR_BLUE = "#3498DB"
COLOR_DARK = "#34495E"
COLOR_GRAY = "#95A5A6"
COLOR_PURPLE = "#8E44AD"

# ===== 路径配置 =====
BASE_DIR = "/Users/wangyanfen/Desktop/量化策略课程"
TASK4_DIR = os.path.join(BASE_DIR, "TASK4")
# 复用 TASK4 的数据加载 / ATR / 股票映射
sys.path.insert(0, TASK4_DIR)
from task4_turtle import load_stock_data, calc_atr, STOCK_FILES  # noqa: E402

OUTPUT_DIR = os.path.join(BASE_DIR, "TASK4_advanced")  # 本进阶版所有产出集中于此

# ===== 策略默认参数（经典海龟）=====
INITIAL_CAPITAL = 1_000_000.0   # 初始资金
RISK_FRACTION = 0.01            # 每单位风险占权益比例（1%）
ATR_N = 20                      # 海龟 N：ATR 周期固定为 20
S1_ENTRY = 20                   # 系统1 入场通道
S1_EXIT = 10                    # 系统1 出场通道
S2_ENTRY = 55                   # 系统2 入场通道
S2_EXIT = 20                    # 系统2 出场通道
PYRAMID_STEP = 0.5              # 金字塔加仓步长（×ATR）
MAX_UNITS = 4                   # 单系统最大单位数
STOP_MULT = 2.0                 # 止损倍数：2 × ATR
# 单系统持仓市值上限占权益比例（股票无杠杆约束，避免保证金透支）：
#   基础仓位按"1%风险"定，但当标的价高、ATR 相对价较小时，1%风险对应的市值会
#   远超本金；此处把单系统市值封顶为 50% 权益（双系统同向最多 100%，即满仓不杠杆）。
MAX_NOTIONAL_FRAC = 0.5

# 多参数对比的三套灵敏度配置（通道周期组合）
PARAM_CONFIGS = [
    {"name": "标准(经典)", "s1e": 20, "s1x": 10, "s2e": 55, "s2x": 20},
    {"name": "灵敏",       "s1e": 10, "s1x": 5,  "s2e": 40, "s2x": 20},
    {"name": "稳健",       "s1e": 55, "s1x": 27, "s2e": 100, "s2x": 50},
]


# ========================================================================
# 仓位计算辅助
# ========================================================================
def unit_shares(equity: float, n: float) -> int:
    """计算 1 个单位的股数 = 1% 权益 ÷ ATR（海龟仓位公式）"""
    if n is None or n <= 0 or equity <= 0:
        return 0
    s = int(math.floor((RISK_FRACTION * equity) / n))
    return max(s, 0)


# ========================================================================
# 单系统逐步状态机
# ========================================================================
def _step_system(cash, units, C, H, L, n,
                 entry_high, entry_low, exit_high, exit_low,
                 stop_mult, pyramid_step, max_units, risk_fraction,
                 total_equity):
    """
    处理单个系统（S1 或 S2）在某一天的状态转移。
    返回 (cash, units, event)：
        event ∈ {long_open, short_open, add_long, add_short,
                 exit_long, exit_short, None}
    规则优先级：止损(2×ATR) > 通道突破出场 > 金字塔加仓（每根K线至多一次加仓）。
    units 元素: {'side': +1/-1, 'entry': 入场价, 'n': 入场时ATR, 'shares': 股数(正)}
    注意：unit_shares 一律以"全盘真实权益 total_equity"为基准，避免做空回收现金导致
          的 cash 虚增、进而把金字塔单位放大的过度杠杆问题。
    """
    event = None

    # 计算"本系统可新增市值空间"（防止高股价下 1%风险单位市值透支保证金）
    sys_notional = sum(abs(u["shares"]) * C for u in units)
    room = MAX_NOTIONAL_FRAC * total_equity - sys_notional
    max_shares = int(room // C) if room > 0 else 0

    # ---- 空仓：寻找入场信号（仅当该系统完全空仓）----
    if not units:
        if not pd.isna(entry_high) and C > entry_high:
            sh = min(unit_shares(total_equity, n), max_shares)
            if sh > 0:
                cash -= sh * C                   # 做多：付出现金
                units.append({"side": 1, "entry": C, "n": n, "shares": sh})
                event = "long_open"
        elif not pd.isna(entry_low) and C < entry_low:
            sh = min(unit_shares(total_equity, n), max_shares)
            if sh > 0:
                cash += sh * C                   # 做空：收到现金（欠券）
                units.append({"side": -1, "entry": C, "n": n, "shares": sh})
                event = "short_open"
        return cash, units, event

    # ---- 持仓中 ----
    side = units[0]["side"]
    last = units[-1]

    # (1) 2×ATR 硬止损（盘中触及即平掉该系统全部单位）
    if side == 1:
        stop = last["entry"] - stop_mult * last["n"]
        if L <= stop:
            for u in units:
                cash += u["shares"] * stop       # 多头平仓回收现金
            return cash, [], "exit_long"
    else:
        stop = last["entry"] + stop_mult * last["n"]
        if H >= stop:
            for u in units:
                cash -= u["shares"] * stop       # 空头回补支付现金
            return cash, [], "exit_short"

    # (2) 通道突破出场（收盘价判定）
    if side == 1:
        if not pd.isna(exit_low) and C < exit_low:
            for u in units:
                cash += u["shares"] * C
            return cash, [], "exit_long"
    else:
        if not pd.isna(exit_high) and C > exit_high:
            for u in units:
                cash -= u["shares"] * C
            return cash, [], "exit_short"

    # (3) 金字塔加仓（每根K线至多 1 次，向上/下推进 0.5×ATR逐步）
    if len(units) < max_units:
        sh = min(unit_shares(total_equity, n), max_shares)   # 受市值上限约束
        if sh > 0:
            if side == 1 and C >= last["entry"] + pyramid_step * last["n"]:
                cash -= sh * C
                units.append({"side": 1, "entry": C, "n": n, "shares": sh})
                return cash, units, "add_long"
            if side == -1 and C <= last["entry"] - pyramid_step * last["n"]:
                cash += sh * C
                units.append({"side": -1, "entry": C, "n": n, "shares": sh})
                return cash, units, "add_short"

    return cash, units, event


# ========================================================================
# 双系统回测引擎
# ========================================================================
def turtle_dual_backtest(df: pd.DataFrame, initial_capital=INITIAL_CAPITAL,
                         risk_fraction=RISK_FRACTION, stop_mult=STOP_MULT,
                         atr_n=ATR_N, s1_entry=S1_ENTRY, s1_exit=S1_EXIT,
                         s2_entry=S2_ENTRY, s2_exit=S2_EXIT,
                         pyramid_step=PYRAMID_STEP, max_units=MAX_UNITS) -> pd.DataFrame:
    """
    经典双系统海龟回测。
    返回 DataFrame，含价格、各通道、ATR、多空/加仓/平仓标记、权益曲线、
    持仓单位数、净持仓股数、回撤等，供绘图与指标计算使用。
    """
    df = df.copy()
    # 计算 S1 / S2 所需的各通道（前 N 日，shift(1) 防未来函数）
    df["h20"] = df["最高价"].rolling(window=s1_entry, min_periods=s1_entry).max().shift(1)
    df["l20"] = df["最低价"].rolling(window=s1_entry, min_periods=s1_entry).min().shift(1)
    df["h10"] = df["最高价"].rolling(window=s1_exit, min_periods=s1_exit).max().shift(1)
    df["l10"] = df["最低价"].rolling(window=s1_exit, min_periods=s1_exit).min().shift(1)
    df["h55"] = df["最高价"].rolling(window=s2_entry, min_periods=s2_entry).max().shift(1)
    df["l55"] = df["最低价"].rolling(window=s2_entry, min_periods=s2_entry).min().shift(1)
    df = calc_atr(df, atr_n)  # 增加 TR、ATR（海龟 N）

    # 标记列
    for c in ["long_open", "short_open", "add_long", "add_short",
              "exit_long", "exit_short"]:
        df[c] = False
    df["n_units"] = 0
    df["net_shares"] = 0
    df["equity"] = initial_capital

    cash = initial_capital
    s1, s2 = [], []

    for i in range(len(df)):
        C = df.at[i, "收盘价"]
        H = df.at[i, "最高价"]
        L = df.at[i, "最低价"]
        n = df.at[i, "ATR"]

        # 全盘真实权益（现金 + 两系统持仓市值），用于本根 K 线的单位定仓
        te = cash + sum(u["side"] * u["shares"] * C for u in (s1 + s2))
        cash, s1, ev1 = _step_system(
            cash, s1, C, H, L, n,
            entry_high=df.at[i, "h20"], entry_low=df.at[i, "l20"],
            exit_high=df.at[i, "h10"], exit_low=df.at[i, "l10"],
            stop_mult=stop_mult, pyramid_step=pyramid_step,
            max_units=max_units, risk_fraction=risk_fraction,
            total_equity=te)
        # 步骤 S1 后刷新权益，再驱动 S2 定仓
        te = cash + sum(u["side"] * u["shares"] * C for u in (s1 + s2))
        cash, s2, ev2 = _step_system(
            cash, s2, C, H, L, n,
            entry_high=df.at[i, "h55"], entry_low=df.at[i, "l55"],
            exit_high=df.at[i, "h20"], exit_low=df.at[i, "l20"],
            stop_mult=stop_mult, pyramid_step=pyramid_step,
            max_units=max_units, risk_fraction=risk_fraction,
            total_equity=te)

        for ev in (ev1, ev2):
            if ev == "long_open":
                df.at[i, "long_open"] = True
            elif ev == "short_open":
                df.at[i, "short_open"] = True
            elif ev == "add_long":
                df.at[i, "add_long"] = True
            elif ev == "add_short":
                df.at[i, "add_short"] = True
            elif ev == "exit_long":
                df.at[i, "exit_long"] = True
            elif ev == "exit_short":
                df.at[i, "exit_short"] = True

        all_units = s1 + s2
        equity = cash + sum(u["side"] * u["shares"] * C for u in all_units)
        df.at[i, "equity"] = equity
        df.at[i, "n_units"] = len(all_units)
        df.at[i, "net_shares"] = sum(u["side"] * u["shares"] for u in all_units)

    # 收益率与回撤
    df["daily_return"] = df["equity"].pct_change().fillna(0.0)
    df["strategy_return"] = df["daily_return"]
    df["cumulative_return"] = (1 + df["strategy_return"]).cumprod() - 1
    df["portfolio_value"] = df["equity"]
    df["benchmark_value"] = initial_capital * (
        1 + df["收盘价"].pct_change().fillna(0)).cumprod()
    df["peak"] = df["portfolio_value"].cummax()
    df["drawdown"] = (df["portfolio_value"] - df["peak"]) / df["peak"]
    return df


# ========================================================================
# 量化指标计算
# ========================================================================
def calc_metrics_adv(df: pd.DataFrame, risk_free_rate: float = 0.03) -> dict:
    """计算双系统策略评估指标（适配多空与加仓）"""
    cumulative_return = df["cumulative_return"].iloc[-1]
    n_days = len(df) - 1
    annual_return = (1 + cumulative_return) ** (252 / n_days) - 1 if n_days > 0 else 0.0
    mdd = df["drawdown"].min()

    daily_rf = risk_free_rate / 252
    excess = (df["strategy_return"] - daily_rf).dropna()
    sharpe = excess.mean() / excess.std() * np.sqrt(252) if excess.std() > 0 else 0.0

    long_entries = int(df["long_open"].sum())
    short_entries = int(df["short_open"].sum())
    add_long = int(df["add_long"].sum())
    add_short = int(df["add_short"].sum())
    exit_long = int(df["exit_long"].sum())
    exit_short = int(df["exit_short"].sum())
    total_trades = exit_long + exit_short

    benchmark_return = df["benchmark_value"].iloc[-1] / df["benchmark_value"].iloc[0] - 1
    b_peak = df["benchmark_value"].cummax()
    b_dd = (df["benchmark_value"] - b_peak) / b_peak
    benchmark_mdd = b_dd.min()

    return {
        "cumulative_return": cumulative_return,
        "annual_return": annual_return,
        "mdd": mdd,
        "sharpe": sharpe,
        "long_entries": long_entries,
        "short_entries": short_entries,
        "add_long": add_long,
        "add_short": add_short,
        "exit_long": exit_long,
        "exit_short": exit_short,
        "total_trades": total_trades,
        "benchmark_return": benchmark_return,
        "benchmark_mdd": benchmark_mdd,
        "n_days": n_days,
    }


# ========================================================================
# 可视化
# ========================================================================
def plot_dual_signals(df, stock_name, save, cfg):
    """图1：股价 + 双系统通道 + 多空开仓/加仓/平仓信号"""
    fig, ax = plt.subplots(figsize=(15, 7.5))
    ax.plot(df["交易日期"], df["收盘价"], color=COLOR_DARK, lw=1.1,
            label="收盘价", alpha=0.8, zorder=1)
    ax.plot(df["交易日期"], df["h20"], color=COLOR_UP, ls="--", lw=1.1,
            alpha=0.8, label="S1上轨(前20日高)")
    ax.plot(df["交易日期"], df["l20"], color=COLOR_DOWN, ls="--", lw=1.1,
            alpha=0.8, label="S1下轨(前20日低)")
    ax.plot(df["交易日期"], df["h55"], color=COLOR_UP, ls=":", lw=1.4,
            alpha=0.9, label="S2上轨(前55日高)")
    ax.plot(df["交易日期"], df["l55"], color=COLOR_DOWN, ls=":", lw=1.4,
            alpha=0.9, label="S2下轨(前55日低)")

    lo = df[df["long_open"]]; so = df[df["short_open"]]
    al = df[df["add_long"]]; as_ = df[df["add_short"]]
    xl = df[df["exit_long"]]; xs = df[df["exit_short"]]
    ax.scatter(lo["交易日期"], lo["收盘价"], marker="^", color=COLOR_UP, s=140,
               zorder=5, label="做多开仓")
    ax.scatter(so["交易日期"], so["收盘价"], marker="v", color=COLOR_DOWN, s=140,
               zorder=5, label="做空开仓")
    ax.scatter(al["交易日期"], al["收盘价"], marker="D", color=COLOR_UP, s=45,
               zorder=5, label="多单加仓(+0.5N)")
    ax.scatter(as_["交易日期"], as_["收盘价"], marker="D", color=COLOR_DOWN, s=45,
               zorder=5, label="空单加仓(-0.5N)")
    ax.scatter(xl["交易日期"], xl["收盘价"], marker="x", color=COLOR_UP, s=75,
               zorder=5, label="平多仓")
    ax.scatter(xs["交易日期"], xs["收盘价"], marker="x", color=COLOR_DOWN, s=75,
               zorder=5, label="平空仓")

    ax.set_title(f"{stock_name} 经典双系统海龟：通道与多空信号 "
                 f"(S1={cfg['s1e']}/{cfg['s1x']}, S2={cfg['s2e']}/{cfg['s2x']})",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("价格 (元)", fontsize=12)
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save}")


def plot_equity(df, stock_name, save, cfg):
    """图2：策略净值 vs 基准净值"""
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP, lw=1.6,
            label="双系统海龟净值")
    ax.plot(df["交易日期"], df["benchmark_value"], color=COLOR_BLUE, lw=1.1,
            alpha=0.7, label="基准净值(买入持有)")
    ax.axhline(y=INITIAL_CAPITAL, color=COLOR_GRAY, ls="--", alpha=0.5,
               label="初始资金")
    ax.set_title(f"{stock_name} 双系统海龟净值曲线 "
                 f"(S1={cfg['s1e']}/{cfg['s1x']}, S2={cfg['s2e']}/{cfg['s2x']})",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("净值 (元)", fontsize=12)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save}")


def plot_drawdown(df, stock_name, save, cfg):
    """图3：回撤曲线"""
    fig, ax = plt.subplots(figsize=(15, 5))
    ax.fill_between(df["交易日期"], df["drawdown"], 0, color=COLOR_DOWN,
                    alpha=0.4, label="回撤区域")
    ax.plot(df["交易日期"], df["drawdown"], color=COLOR_DOWN, lw=1.2)
    mdd_idx = df["drawdown"].idxmin()
    mdd_val = df["drawdown"].iloc[mdd_idx]
    mdd_date = df["交易日期"].iloc[mdd_idx]
    ax.annotate(f"MDD: {mdd_val:.2%}\n({mdd_date.strftime('%Y-%m-%d')})",
                xy=(mdd_date, mdd_val), xytext=(mdd_date, mdd_val * 0.7),
                fontsize=11, color=COLOR_DOWN, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=COLOR_DOWN))
    ax.set_title(f"{stock_name} 双系统海龟回撤曲线", fontsize=14, fontweight="bold")
    ax.set_xlabel("日期", fontsize=12)
    ax.set_ylabel("回撤幅度", fontsize=12)
    ax.legend(loc="lower left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save}")


def plot_panel(df, metrics, stock_name, save, cfg):
    """图4：综合面板（价格+通道+信号 / 持仓单位数 / ATR / 净值 / 回撤）"""
    fig = plt.figure(figsize=(16, 16))
    gs = GridSpec(5, 1, height_ratios=[2.2, 0.8, 1, 1.2, 1.2], hspace=0.28)

    ax1 = fig.add_subplot(gs[0])
    ax1.plot(df["交易日期"], df["收盘价"], color=COLOR_DARK, lw=0.9, alpha=0.85)
    ax1.plot(df["交易日期"], df["h20"], color=COLOR_UP, lw=1.0, ls="--", label="S1上轨")
    ax1.plot(df["交易日期"], df["l20"], color=COLOR_DOWN, lw=1.0, ls="--", label="S1下轨")
    ax1.plot(df["交易日期"], df["h55"], color=COLOR_UP, lw=1.1, ls=":", label="S2上轨")
    ax1.plot(df["交易日期"], df["l55"], color=COLOR_DOWN, lw=1.1, ls=":", label="S2下轨")
    lo = df[df["long_open"]]; so = df[df["short_open"]]
    al = df[df["add_long"]]; as_ = df[df["add_short"]]
    xl = df[df["exit_long"]]; xs = df[df["exit_short"]]
    ax1.scatter(lo["交易日期"], lo["收盘价"], marker="^", color=COLOR_UP, s=70, label="多开")
    ax1.scatter(so["交易日期"], so["收盘价"], marker="v", color=COLOR_DOWN, s=70, label="空开")
    ax1.scatter(al["交易日期"], al["收盘价"], marker="D", color=COLOR_UP, s=30, label="多加")
    ax1.scatter(as_["交易日期"], as_["收盘价"], marker="D", color=COLOR_DOWN, s=30, label="空加")
    ax1.scatter(xl["交易日期"], xl["收盘价"], marker="x", color=COLOR_UP, s=50, label="平多")
    ax1.scatter(xs["交易日期"], xs["收盘价"], marker="x", color=COLOR_DOWN, s=50, label="平空")
    ax1.set_title(f"{stock_name} 双系统海龟综合面板", fontsize=13, fontweight="bold")
    ax1.legend(loc="upper left", fontsize=7, ncol=4)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    ax2 = fig.add_subplot(gs[1])
    ax2.fill_between(df["交易日期"], df["n_units"], 0, color=COLOR_PURPLE, alpha=0.4)
    ax2.plot(df["交易日期"], df["n_units"], color=COLOR_PURPLE, lw=1.0)
    ax2.set_ylabel("持仓单位数", fontsize=9)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    ax3 = fig.add_subplot(gs[2])
    ax3.plot(df["交易日期"], df["ATR"], color=COLOR_PURPLE, lw=1.2, label="ATR(20)")
    ax3.set_ylabel("ATR", fontsize=9)
    ax3.legend(loc="upper left", fontsize=8)
    ax3.grid(True, alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    ax4 = fig.add_subplot(gs[3])
    ax4.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP, lw=1.2, label="策略净值")
    ax4.plot(df["交易日期"], df["benchmark_value"], color=COLOR_BLUE, lw=0.9,
             alpha=0.7, label="基准净值")
    ax4.axhline(y=INITIAL_CAPITAL, color=COLOR_GRAY, ls="--", alpha=0.4)
    ax4.set_ylabel("净值 (元)", fontsize=9)
    ax4.legend(loc="upper left", fontsize=8)
    ax4.grid(True, alpha=0.3)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    ax5 = fig.add_subplot(gs[4])
    ax5.fill_between(df["交易日期"], df["drawdown"], 0, color=COLOR_DOWN, alpha=0.4)
    ax5.plot(df["交易日期"], df["drawdown"], color=COLOR_DOWN, lw=1)
    ax5.set_ylabel("回撤幅度", fontsize=9)
    ax5.grid(True, alpha=0.3)
    ax5.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax5.xaxis.set_major_locator(mdates.MonthLocator(interval=2))

    info = (f"累计回报: {metrics['cumulative_return']:.2%}  |  "
            f"年化: {metrics['annual_return']:.2%}  |  "
            f"MDD: {metrics['mdd']:.2%}  |  夏普: {metrics['sharpe']:.2f}  |  "
            f"多开:{metrics['long_entries']} 空开:{metrics['short_entries']} "
            f"多加:{metrics['add_long']} 空加:{metrics['add_short']} "
            f"平多:{metrics['exit_long']} 平空:{metrics['exit_short']}")
    fig.text(0.5, 0.012, info, ha="center", fontsize=10.5, fontweight="bold",
             color="#2C3E50",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#ECF0F1", alpha=0.85))
    plt.subplots_adjust(top=0.96, bottom=0.09, hspace=0.28)
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save}")


def plot_multi_params(stock_key, save):
    """图5：多参数（标准/灵敏/稳健）对比"""
    fig, axes = plt.subplots(len(PARAM_CONFIGS), 2,
                             figsize=(16, 4 * len(PARAM_CONFIGS)))
    all_metrics = []
    raw = load_stock_data(STOCK_FILES[stock_key]["path"])
    for i, cfg in enumerate(PARAM_CONFIGS):
        df = turtle_dual_backtest(raw, s1_entry=cfg["s1e"], s1_exit=cfg["s1x"],
                                  s2_entry=cfg["s2e"], s2_exit=cfg["s2x"])
        m = calc_metrics_adv(df)
        all_metrics.append({**cfg, **m})

        ax_v = axes[i][0]
        ax_v.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP, lw=1.2,
                  label="策略净值")
        ax_v.plot(df["交易日期"], df["benchmark_value"], color=COLOR_BLUE, lw=0.8,
                  alpha=0.6, label="基准")
        ax_v.set_title(f"{cfg['name']} (S1={cfg['s1e']}/{cfg['s1x']},"
                       f"S2={cfg['s2e']}/{cfg['s2x']}) 净值",
                       fontsize=11)
        ax_v.legend(fontsize=8)
        ax_v.grid(True, alpha=0.3)
        ax_v.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

        ax_d = axes[i][1]
        ax_d.fill_between(df["交易日期"], df["drawdown"], 0, color=COLOR_DOWN, alpha=0.4)
        ax_d.plot(df["交易日期"], df["drawdown"], color=COLOR_DOWN, lw=1)
        ax_d.set_title(f"{cfg['name']} 回撤 (MDD={m['mdd']:.2%}, "
                       f"累计={m['cumulative_return']:.2%})", fontsize=11)
        ax_d.grid(True, alpha=0.3)
        ax_d.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))

    fig.suptitle("经典双系统海龟：不同通道周期灵敏度对比（宁德时代）",
                 fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save}")
    return all_metrics


def plot_multi_stocks(save):
    """图6：多股票对比（经典配置）"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    all_metrics = {}
    stocks = ["宁德时代", "平安银行", "贵州茅台", "五粮液"]
    cfg = PARAM_CONFIGS[0]
    for i, sk in enumerate(stocks):
        raw = load_stock_data(STOCK_FILES[sk]["path"])
        df = turtle_dual_backtest(raw, s1_entry=cfg["s1e"], s1_exit=cfg["s1x"],
                                  s2_entry=cfg["s2e"], s2_exit=cfg["s2x"])
        m = calc_metrics_adv(df)
        all_metrics[sk] = m
        ax = axes[i // 2][i % 2]
        ax.plot(df["交易日期"], df["portfolio_value"], color=COLOR_UP, lw=1.2,
                label="策略净值")
        ax.plot(df["交易日期"], df["benchmark_value"], color=COLOR_BLUE, lw=0.8,
                alpha=0.6, label="基准净值")
        ax.set_title(f"{sk} (累计={m['cumulative_return']:.2%}, "
                     f"夏普={m['sharpe']:.2f}, MDD={m['mdd']:.2%})", fontsize=11)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.suptitle("经典双系统海龟（标准配置）多股票对比", fontsize=14,
                 fontweight="bold", y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save}")
    return all_metrics


def plot_metrics_bar(all_stocks_metrics, save):
    """图7：多股票指标对比柱状图"""
    stocks = list(all_stocks_metrics.keys())
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    cr = [all_stocks_metrics[s]["cumulative_return"] * 100 for s in stocks]
    colors = [COLOR_UP if v > 0 else COLOR_DOWN for v in cr]
    axes[0].bar(stocks, cr, color=colors, alpha=0.85)
    axes[0].set_title("累计回报 (%)", fontsize=12, fontweight="bold")
    axes[0].axhline(y=0, color=COLOR_GRAY, lw=0.5)
    for j, v in enumerate(cr):
        axes[0].text(j, v + (1 if v >= 0 else -2), f"{v:.1f}", ha="center", fontsize=9)

    mdd = [all_stocks_metrics[s]["mdd"] * 100 for s in stocks]
    axes[1].bar(stocks, mdd, color=COLOR_DOWN, alpha=0.85)
    axes[1].set_title("最大回撤 MDD (%)", fontsize=12, fontweight="bold")
    for j, v in enumerate(mdd):
        axes[1].text(j, v - 1, f"{v:.1f}", ha="center", fontsize=9)

    sh = [all_stocks_metrics[s]["sharpe"] for s in stocks]
    colors = [COLOR_UP if v > 0 else COLOR_DOWN for v in sh]
    axes[2].bar(stocks, sh, color=colors, alpha=0.85)
    axes[2].set_title("夏普比率", fontsize=12, fontweight="bold")
    axes[2].axhline(y=0, color=COLOR_GRAY, lw=0.5)
    for j, v in enumerate(sh):
        axes[2].text(j, v + (0.05 if v >= 0 else -0.12), f"{v:.2f}", ha="center", fontsize=9)

    fig.suptitle("经典双系统海龟 多股票指标对比", fontsize=13, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.93])
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  已保存 {save}")


# ========================================================================
# CSV 导出
# ========================================================================
def export_signal_csv(df, stock_name, save):
    cols = ["交易日期", "收盘价", "h20", "l20", "h55", "l55", "ATR",
            "long_open", "short_open", "add_long", "add_short",
            "exit_long", "exit_short", "n_units", "net_shares",
            "cumulative_return", "portfolio_value", "drawdown"]
    out = df[cols].copy()
    out.columns = ["交易日期", "收盘价", "S1上轨(20高)", "S1下轨(20低)", "S2上轨(55高)",
                   "S2下轨(55低)", "ATR(20)", "做多开仓", "做空开仓", "多单加仓",
                   "空单加仓", "平多仓", "平空仓", "持仓单位数", "净持仓股数",
                   "累计收益率", "策略净值", "回撤幅度"]
    out.to_csv(save, index=False, encoding="utf-8-sig")
    print(f"  已保存 {save}")
    return save


def export_params_csv(metrics_list, save):
    rows = []
    for m in metrics_list:
        rows.append({
            "配置": m["name"],
            "S1入场": m["s1e"], "S1出场": m["s1x"],
            "S2入场": m["s2e"], "S2出场": m["s2x"],
            "累计回报": f"{m['cumulative_return']:.4%}",
            "年化收益": f"{m['annual_return']:.4%}",
            "最大回撤MDD": f"{m['mdd']:.4%}",
            "夏普比率": f"{m['sharpe']:.4f}",
            "做多开仓": m["long_entries"], "做空开仓": m["short_entries"],
            "多单加仓": m["add_long"], "空单加仓": m["add_short"],
            "平多": m["exit_long"], "平空": m["exit_short"],
        })
    pd.DataFrame(rows).to_csv(save, index=False, encoding="utf-8-sig")
    print(f"  已保存 {save}")
    return save


def export_metrics_csv(metrics_dict, save):
    rows = []
    for sk, m in metrics_dict.items():
        rows.append({
            "股票": sk,
            "累计回报": f"{m['cumulative_return']:.4%}",
            "年化收益": f"{m['annual_return']:.4%}",
            "最大回撤MDD": f"{m['mdd']:.4%}",
            "夏普比率": f"{m['sharpe']:.4f}",
            "做多开仓": m["long_entries"], "做空开仓": m["short_entries"],
            "多单加仓": m["add_long"], "空单加仓": m["add_short"],
            "平多": m["exit_long"], "平空": m["exit_short"],
            "基准回报": f"{m['benchmark_return']:.4%}",
            "基准MDD": f"{m['benchmark_mdd']:.4%}",
        })
    pd.DataFrame(rows).to_csv(save, index=False, encoding="utf-8-sig")
    print(f"  已保存 {save}")
    return save


# ========================================================================
# 主流程
# ========================================================================
def run_all():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cfg = PARAM_CONFIGS[0]  # 经典标准配置
    print("=" * 64)
    print("TASK4 进阶：经典双系统海龟（S1/S2 + 金字塔加仓 + 做空）")
    print("=" * 64)

    # 第一部分：核心案例（宁德时代，经典配置）
    print("\n>>> 核心分析：宁德时代（经典 S1=20/10, S2=55/20）")
    raw = load_stock_data(STOCK_FILES["宁德时代"]["path"])
    df = turtle_dual_backtest(raw)
    m = calc_metrics_adv(df)
    print(f"  累计回报: {m['cumulative_return']:.2%}  年化: {m['annual_return']:.2%}")
    print(f"  最大回撤: {m['mdd']:.2%}  夏普: {m['sharpe']:.2f}")
    print(f"  做多开仓 {m['long_entries']} / 做空开仓 {m['short_entries']} "
          f"/ 多单加仓 {m['add_long']} / 空单加仓 {m['add_short']} "
          f"/ 平多 {m['exit_long']} / 平空 {m['exit_short']}")
    print(f"  基准回报(买入持有): {m['benchmark_return']:.2%}  基准MDD: {m['benchmark_mdd']:.2%}")

    print("\n>>> 绘制核心图表")
    plot_dual_signals(df, "宁德时代",
                      os.path.join(OUTPUT_DIR, "图1_双系统通道_多空信号.png"), cfg)
    plot_equity(df, "宁德时代",
                os.path.join(OUTPUT_DIR, "图2_策略净值曲线.png"), cfg)
    plot_drawdown(df, "宁德时代",
                  os.path.join(OUTPUT_DIR, "图3_回撤曲线.png"), cfg)
    plot_panel(df, m, "宁德时代",
               os.path.join(OUTPUT_DIR, "图4_综合面板.png"), cfg)
    export_signal_csv(df, "宁德时代",
                      os.path.join(OUTPUT_DIR, "宁德时代_双系统海龟_回测数据.csv"))

    # 第二部分：多参数对比
    print("\n>>> 多参数对比（标准 / 灵敏 / 稳健）")
    param_metrics = plot_multi_params("宁德时代",
                                      os.path.join(OUTPUT_DIR, "图5_多参数对比.png"))
    export_params_csv(param_metrics,
                      os.path.join(OUTPUT_DIR, "宁德时代_多参数对比指标.csv"))

    # 第三部分：多股票对比
    print("\n>>> 多股票对比（经典配置）")
    stock_metrics = plot_multi_stocks(
        os.path.join(OUTPUT_DIR, "图6_多股票对比.png"))
    plot_metrics_bar(stock_metrics,
                    os.path.join(OUTPUT_DIR, "图7_多股票指标柱状图.png"))
    export_metrics_csv(stock_metrics,
                       os.path.join(OUTPUT_DIR, "多股票策略指标对比.csv"))

    print("\n" + "=" * 64)
    print("TASK4 进阶分析全部完成！图表与 CSV 已输出至 TASK4_advanced 目录。")
    print("=" * 64)
    return m, param_metrics, stock_metrics


if __name__ == "__main__":
    run_all()
