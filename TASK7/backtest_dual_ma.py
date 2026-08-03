#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK7 - 聚宽双均线策略：本地回测 + 参数寻优 + 样本外实盘模拟 + 风险暴露分析
=================================================================================
本脚本完整复现"在聚宽平台上实现并优化交易策略"的 5 个步骤（本地版本）：
  1) 使用双均线策略模板，并增加风控模块（趋势过滤 / 止损 / 涨跌停过滤 / 交易成本）
  2) 在样本内(2019-2024)做参数网格寻优，根据回测结果挑选最优参数
  3) 在样本外(2025-2026)做前向测试 = 模拟聚宽"实盘模拟/模拟交易"
  4) 评估样本内/样本外表现，分析风险暴露（波动/回撤/回撤时长/Beta/VaR/CVaR/换手/参数敏感性）
  5) 经验与教训总结（在 PDF 报告中呈现）

输出：
  - TASK7/双均线_样本内参数寻优.csv
  - TASK7/双均线_指标对比.csv
  - TASK7/figs/*.png
  - TASK7/metrics.json  (供 PDF 生成脚本读取)
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec

# ===== 环境配置 =====
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"
plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

# 红涨绿跌
C_UP = "#E74C3C"
C_DOWN = "#27AE60"
C_BLUE = "#3498DB"
C_GREY = "#95A5A6"

BASE = "/Users/wangyanfen/Desktop/量化策略课程/TASK7"
FIG_DIR = os.path.join(BASE, "figs")
os.makedirs(FIG_DIR, exist_ok=True)

# 交易成本模型（A股零售近似）
BUY_COST = 0.0003 + 0.0010   # 佣金0.03% + 滑点0.1%
SELL_COST = 0.0003 + 0.0010 + 0.0010  # 佣金0.03% + 滑点0.1% + 印花税0.1%
RISK_FREE = 0.03

STOCK_CSV = os.path.join(BASE, "宁德时代_300750_日线_2019_2026.csv")
INDEX_CSV = os.path.join(BASE, "沪深300_000300_日线_2019_2026.csv")

IN_SAMPLE_END = "2024-12-31"
OOS_START = "2025-01-01"

# 默认模板参数（TASK3 原版）
DEFAULT_SHORT = 5
DEFAULT_LONG = 15


def load(path):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df["交易日期"] = pd.to_datetime(df["交易日期"].astype(str), format="%Y%m%d")
    df = df.sort_values("交易日期").reset_index(drop=True)
    df["日收益率"] = df["收盘价"].pct_change()
    return df


# ========================================================================
# 回测引擎（事件循环，支持趋势过滤 / 止损 / 涨跌停过滤 / 成本）
# ========================================================================
def run_backtest(df, short, long, use_trend_filter=True, trend_ma=120,
                 stop_loss=0.10, buy_cost=BUY_COST, sell_cost=SELL_COST):
    """
    双均线 + 风控回测。
    返回含每日仓位 / 收益 / 净值 / 回撤 的 DataFrame。
    """
    n = len(df)
    close = df["收盘价"].values
    pct = df["涨跌幅(%)"].values / 100.0
    ma_s = df["收盘价"].rolling(short, min_periods=1).mean().values
    ma_l = df["收盘价"].rolling(long, min_periods=1).mean().values
    ma_t = df["收盘价"].rolling(trend_ma, min_periods=1).mean().values

    diff = ma_s - ma_l
    position = np.zeros(n)
    entry_price = np.zeros(n)
    strat_ret = np.zeros(n)
    trades = []

    min_look = max(long, trend_ma) if use_trend_filter else long
    prev_pos = 0
    for i in range(1, n):
        if i < min_look:
            position[i] = 0
            prev_pos = 0
            continue
        golden = (diff[i-1] <= 0) and (diff[i] > 0)
        death = (diff[i-1] >= 0) and (diff[i] < 0)
        limit_up = pct[i] >= 0.095
        limit_down = pct[i] <= -0.095
        trend_ok = (not use_trend_filter) or (close[i] > ma_t[i])

        target = prev_pos
        if prev_pos == 0:
            if golden and (not limit_up) and trend_ok:
                target = 1
        else:  # 持仓中
            drawdown = (close[i] - entry_price[i-1]) / entry_price[i-1] if entry_price[i-1] > 0 else 0
            if death and (not limit_down):
                target = 0
            elif stop_loss > 0 and drawdown <= -stop_loss and (not limit_down):
                target = 0

        position[i] = target
        # 成交成本
        cost = 0.0
        if target != prev_pos:
            if target == 1 and limit_up:
                position[i] = 0  # 涨停买不进
            elif target == 0 and limit_down:
                position[i] = 1  # 跌停卖不出，继续持有
            else:
                cost = buy_cost if target == 1 else sell_cost
                if target == 1:
                    entry_price[i] = close[i]
                trades.append((i, "BUY" if target == 1 else "SELL", close[i]))
        if position[i] == 1 and prev_pos == 1:
            entry_price[i] = entry_price[i-1]

        dr = df["日收益率"].values[i] if i > 0 else 0.0
        strat_ret[i] = position[i] * dr - cost
        prev_pos = position[i]

    out = df.copy()
    out["position"] = position
    out["strat_ret"] = strat_ret
    out["nav"] = (1 + pd.Series(strat_ret)).cumprod()
    out["bench_nav"] = (1 + df["日收益率"].fillna(0)).cumprod()
    peak = out["nav"].cummax()
    out["drawdown"] = (out["nav"] - peak) / peak
    return out, trades


# ========================================================================
# 指标计算
# ========================================================================
def calc_metrics(out, idx_ret=None):
    ret = out["strat_ret"].dropna()
    nav = out["nav"].values
    bench_ret = out["日收益率"].fillna(0).values[1:]
    n = len(ret)
    cum = nav[-1] - 1
    ann = (1 + cum) ** (252 / n) - 1 if n > 0 else 0
    vol = ret.std() * np.sqrt(252)
    excess = ret - RISK_FREE / 252
    sharpe = excess.mean() / ret.std() * np.sqrt(252) if ret.std() > 0 else 0
    downside = ret[ret < 0].std() * np.sqrt(252)
    sortino = excess.mean() / downside * np.sqrt(252) if downside > 0 else 0
    mdd = out["drawdown"].min()
    # 回撤时长
    peak = out["nav"].cummax().values
    dd = (out["nav"].values - peak) / peak
    cur = 0
    max_dd_dur = 0
    for v in dd:
        if v < 0:
            cur += 1
            max_dd_dur = max(max_dd_dur, cur)
        else:
            cur = 0
    # 基准
    bench_cum = (1 + pd.Series(bench_ret)).cumprod().iloc[-1] - 1
    bench_ann = (1 + bench_cum) ** (252 / n) - 1 if n > 0 else 0
    bench_vol = pd.Series(bench_ret).std() * np.sqrt(252)
    bench_mdd_series = (out["bench_nav"].values - out["bench_nav"].cummax().values) / out["bench_nav"].cummax().values
    bench_mdd = bench_mdd_series.min()
    # 交易次数 / 胜率(按笔)
    pos_changes = np.where(np.diff(out["position"].values) != 0)[0]
    n_trades = len(pos_changes)
    # 日胜率
    win_rate = (ret > 0).mean()
    # VaR / CVaR (日)
    var95 = np.percentile(ret, 5)
    var99 = np.percentile(ret, 1)
    cvar95 = ret[ret <= var95].mean()
    # Beta vs 沪深300
    beta = np.cov(ret, idx_ret)[0, 1] / np.var(idx_ret) if idx_ret is not None and np.var(idx_ret) > 0 else np.nan
    # 换手率（年度化）
    turnover = n_trades / (n / 252) if n > 0 else 0
    calmar = ann / abs(mdd) if mdd < 0 else np.nan

    return {
        "累计收益": cum, "年化收益": ann, "年化波动": vol, "夏普": sharpe,
        "索提诺": sortino, "最大回撤": mdd, "最大回撤时长(日)": max_dd_dur,
        "基准累计": bench_cum, "基准年化": bench_ann, "基准波动": bench_vol, "基准最大回撤": bench_mdd,
        "交易次数": n_trades, "日胜率": win_rate, "VaR95": var95,
        "VaR99": var99, "CVaR95": cvar95, "Beta": beta, "年化换手率": turnover,
        "Calmar": calmar,
    }


# ========================================================================
# 参数网格寻优（样本内）
# ========================================================================
def tune_parameters(stock_df, idx_ret_ins, shorts, longs):
    rows = []
    for s in shorts:
        for l in longs:
            if s >= l:
                continue
            out, _ = run_backtest(stock_df, s, l)
            m = calc_metrics(out, idx_ret_ins)
            rows.append({"短均线": s, "长均线": l, **m})
    res = pd.DataFrame(rows)
    return res


# ========================================================================
# 绘图
# ========================================================================
def fig_signals(out, short, long, title, save):
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(out["交易日期"], out["收盘价"], color="#34495E", lw=1.0, label="收盘价", alpha=0.8)
    ax.plot(out["交易日期"], out["收盘价"].rolling(short, min_periods=1).mean(), color=C_UP, lw=1.4, label=f"MA{short}")
    ax.plot(out["交易日期"], out["收盘价"].rolling(long, min_periods=1).mean(), color=C_BLUE, lw=1.4, label=f"MA{long}")
    buys = out[(out["position"].diff() == 1)]
    sells = out[(out["position"].diff() == -1)]
    ax.scatter(buys["交易日期"], buys["收盘价"], marker="^", color=C_UP, s=90, zorder=5, label="买入(金叉)")
    ax.scatter(sells["交易日期"], sells["收盘价"], marker="v", color=C_DOWN, s=90, zorder=5, label="卖出(死叉)")
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("价格 (元)", fontsize=11)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()


def fig_nav(out, title, save, compared=None):
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(out["交易日期"], out["nav"], color=C_UP, lw=1.6, label="策略净值")
    ax.plot(out["交易日期"], out["bench_nav"], color=C_BLUE, lw=1.1, alpha=0.7, label="基准(持有不动)")
    if compared is not None:
        ax.plot(compared["交易日期"], compared["nav"], color="#9B59B6", lw=1.3, ls="--", label="默认参数(5/15)")
    ax.axhline(1.0, color=C_GREY, ls="--", alpha=0.5)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("净值", fontsize=11)
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()


def fig_drawdown(out, title, save):
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.fill_between(out["交易日期"], out["drawdown"], 0, color=C_DOWN, alpha=0.4)
    ax.plot(out["交易日期"], out["drawdown"], color=C_DOWN, lw=1.1)
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_ylabel("回撤", fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()


def fig_heatmap(res, title, save):
    piv = res.pivot(index="长均线", columns="短均线", values="夏普")
    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(piv.values, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(piv.columns)))
    ax.set_xticklabels(piv.columns)
    ax.set_yticks(range(len(piv.index)))
    ax.set_yticklabels(piv.index)
    ax.set_xlabel("短均线周期", fontsize=11)
    ax.set_ylabel("长均线周期", fontsize=11)
    for i in range(len(piv.index)):
        for j in range(len(piv.columns)):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9,
                        color="black")
    ax.set_title(title, fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()


def fig_risk_compare(ins_m, oos_m, default_m, save):
    metrics = ["年化收益", "夏普", "年化波动", "最大回撤", "最大回撤时长(日)", "Beta"]
    labels = ["年化收益", "夏普", "年化波动", "最大回撤", "回撤时长", "Beta"]
    ins = [ins_m[k] for k in metrics]
    oos = [oos_m[k] for k in metrics]
    default = [default_m[k] for k in metrics]
    x = np.arange(len(metrics))
    w = 0.26
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x - w, ins, w, label="样本内(寻优)", color=C_UP, alpha=0.85)
    ax.bar(x, oos, w, label="样本外(实盘模拟)", color=C_BLUE, alpha=0.85)
    ax.bar(x + w, default, w, label="默认参数样本外", color=C_GREY, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_title("风险与收益指标对比：样本内 vs 样本外 vs 默认参数", fontsize=14, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()


def fig_sensitivity(stock_oos, best_s, best_l, save):
    """样本外参数敏感性：短/长均线扰动对样本外夏普与累计收益的影响。"""
    shorts = [max(3, best_s - 4 + k) for k in range(9)]
    longs = [max(best_l - 20 + 5 * k, best_s + 2) for k in range(9)]
    # 构造网格
    grid_s = [best_s - 3, best_s - 1, best_s, best_s + 2, best_s + 4]
    grid_l = [best_l - 20, best_l - 10, best_l, best_l + 20, best_l + 40]
    sharpe_mat = np.zeros((len(grid_l), len(grid_s)))
    for i, l in enumerate(grid_l):
        for j, s in enumerate(grid_s):
            if s >= l:
                sharpe_mat[i, j] = np.nan
                continue
            out, _ = run_backtest(stock_oos, s, l)
            idx_r = stock_oos["日收益率"].fillna(0).values
            m = calc_metrics(out, idx_r)
            sharpe_mat[i, j] = m["夏普"]
    piv = pd.DataFrame(sharpe_mat, index=grid_l, columns=grid_s)
    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(piv.values, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(grid_s)))
    ax.set_xticklabels(grid_s)
    ax.set_yticks(range(len(grid_l)))
    ax.set_yticklabels(grid_l)
    ax.set_xlabel("短均线周期", fontsize=11)
    ax.set_ylabel("长均线周期", fontsize=11)
    for i in range(len(grid_l)):
        for j in range(len(grid_s)):
            v = piv.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9)
    ax.set_title(f"样本外参数敏感性（夏普）\n最优={best_s}/{best_l}（红框）", fontsize=13, fontweight="bold")
    # 标注最优
    bi = grid_l.index(best_l); bj = grid_s.index(best_s)
    ax.add_patch(plt.Rectangle((bj-0.5, bi-0.5), 1, 1, fill=False, edgecolor="red", lw=2))
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(save, dpi=150, bbox_inches="tight")
    plt.close()


# ========================================================================
# 主流程
# ========================================================================
def main():
    print("=" * 70)
    print("TASK7 双均线策略：本地回测 / 参数寻优 / 样本外实盘模拟 / 风险分析")
    print("=" * 70)

    stock = load(STOCK_CSV)
    index = load(INDEX_CSV)
    # 对齐指数收益
    merged = pd.merge(stock[["交易日期", "日收益率"]], index[["交易日期", "日收益率"]],
                      on="交易日期", suffixes=("", "_idx"))
    idx_ret_all = merged["日收益率_idx"].fillna(0).values

    ins = stock[stock["交易日期"] <= IN_SAMPLE_END].reset_index(drop=True)
    oos = stock[stock["交易日期"] >= OOS_START].reset_index(drop=True).reset_index(drop=True)
    idx_ret_ins = merged[merged["交易日期"] <= IN_SAMPLE_END]["日收益率_idx"].fillna(0).values
    idx_ret_oos = merged[merged["交易日期"] >= OOS_START]["日收益率_idx"].fillna(0).values

    print(f"样本内: {ins['交易日期'].iloc[0].date()} ~ {ins['交易日期'].iloc[-1].date()} ({len(ins)} 天)")
    print(f"样本外: {oos['交易日期'].iloc[0].date()} ~ {oos['交易日期'].iloc[-1].date()} ({len(oos)} 天)")

    # ---- 步骤2：参数寻优（样本内）----
    print("\n>>> 步骤2：样本内参数网格寻优 ...")
    shorts = [5, 8, 10, 15, 20]
    longs = [20, 30, 40, 60, 120]
    res = tune_parameters(ins, idx_ret_ins, shorts, longs)
    res = res.sort_values("夏普", ascending=False).reset_index(drop=True)
    res.to_csv(os.path.join(BASE, "双均线_样本内参数寻优.csv"), index=False, encoding="utf-8-sig")
    print("  参数寻优 Top5 (按夏普):")
    print(res.head(5)[["短均线", "长均线", "年化收益", "夏普", "最大回撤", "交易次数"]].to_string(index=False))

    best = res.iloc[0]
    best_s, best_l = int(best["短均线"]), int(best["长均线"])
    print(f"  >> 最优参数: 短={best_s}, 长={best_l}")

    # ---- 步骤1/3：最优参数回测（样本内 & 样本外）----
    print("\n>>> 步骤3：样本外实盘模拟（前向测试，使用最优参数）...")
    ins_out, ins_trades = run_backtest(ins, best_s, best_l)
    oos_out, oos_trades = run_backtest(oos, best_s, best_l)
    # 默认参数样本外对照
    oos_def_out, _ = run_backtest(oos, DEFAULT_SHORT, DEFAULT_LONG)
    # 默认参数样本内（用于对比模板原版）
    ins_def_out, _ = run_backtest(ins, DEFAULT_SHORT, DEFAULT_LONG)

    ins_m = calc_metrics(ins_out, idx_ret_ins)
    oos_m = calc_metrics(oos_out, idx_ret_oos)
    oos_def_m = calc_metrics(oos_def_out, idx_ret_oos)
    ins_def_m = calc_metrics(ins_def_out, idx_ret_ins)

    # 汇总对比表
    cmp = pd.DataFrame({
        "指标": ["累计收益", "年化收益", "年化波动", "夏普", "索提诺", "最大回撤", "最大回撤时长(日)",
                "基准累计", "基准年化", "基准波动", "基准最大回撤", "交易次数", "日胜率",
                "VaR95", "VaR99", "CVaR95", "Beta", "年化换手率", "Calmar"],
        "样本内_最优": [ins_m[k] for k in ["累计收益","年化收益","年化波动","夏普","索提诺","最大回撤","最大回撤时长(日)","基准累计","基准年化","基准波动","基准最大回撤","交易次数","日胜率","VaR95","VaR99","CVaR95","Beta","年化换手率","Calmar"]],
        "样本外_最优": [oos_m[k] for k in ["累计收益","年化收益","年化波动","夏普","索提诺","最大回撤","最大回撤时长(日)","基准累计","基准年化","基准波动","基准最大回撤","交易次数","日胜率","VaR95","VaR99","CVaR95","Beta","年化换手率","Calmar"]],
        "样本外_默认5_15": [oos_def_m[k] for k in ["累计收益","年化收益","年化波动","夏普","索提诺","最大回撤","最大回撤时长(日)","基准累计","基准年化","基准波动","基准最大回撤","交易次数","日胜率","VaR95","VaR99","CVaR95","Beta","年化换手率","Calmar"]],
    })
    cmp.to_csv(os.path.join(BASE, "双均线_指标对比.csv"), index=False, encoding="utf-8-sig")
    print("\n  指标对比（小数）：")
    print(cmp.to_string(index=False))

    # ---- 步骤4：风险暴露分析用图 + 敏感性 ----
    print("\n>>> 步骤4：绘制图表 & 风险分析 ...")
    fig_signals(ins_out, best_s, best_l, f"宁德时代 双均线策略信号图 (样本内 MA{best_s}/MA{best_l})",
                os.path.join(FIG_DIR, "fig1_insample_signals.png"))
    fig_nav(ins_out, f"样本内策略净值曲线 (MA{best_s}/MA{best_l})",
            os.path.join(FIG_DIR, "fig2_insample_nav.png"))
    fig_drawdown(ins_out, f"样本内回撤曲线 (MA{best_s}/MA{best_l})",
                 os.path.join(FIG_DIR, "fig3_insample_drawdown.png"))
    fig_heatmap(res, "样本内参数寻优：夏普比率热力图",
                os.path.join(FIG_DIR, "fig4_param_heatmap.png"))
    fig_nav(oos_out, f"样本外(实盘模拟)策略净值 (MA{best_s}/MA{best_l})",
            os.path.join(FIG_DIR, "fig5_oos_nav.png"), compared=oos_def_out)
    fig_drawdown(oos_out, f"样本外(实盘模拟)回撤曲线 (MA{best_s}/MA{best_l})",
                 os.path.join(FIG_DIR, "fig6_oos_drawdown.png"))
    fig_risk_compare(ins_m, oos_m, oos_def_m, os.path.join(FIG_DIR, "fig7_risk_compare.png"))
    fig_sensitivity(oos, best_s, best_l, os.path.join(FIG_DIR, "fig8_sensitivity.png"))

    # ---- 成本敏感性（风险提示）----
    print("\n>>> 成本敏感性测试 ...")
    cost_tests = []
    for slip in [0.0, 0.001, 0.002, 0.003]:
        out, _ = run_backtest(oos, best_s, best_l, buy_cost=0.0003+slip, sell_cost=0.0003+slip+0.001)
        m = calc_metrics(out, idx_ret_oos)
        cost_tests.append({"滑点": slip, "年化收益": m["年化收益"], "夏普": m["夏普"], "最大回撤": m["最大回撤"]})
    cost_df = pd.DataFrame(cost_tests)
    cost_df.to_csv(os.path.join(BASE, "双均线_成本敏感性.csv"), index=False, encoding="utf-8-sig")
    print(cost_df.to_string(index=False))

    # ---- 保存指标 JSON 供 PDF ----
    metrics_json = {
        "best_short": best_s, "best_long": best_l,
        "in_sample_range": [str(ins['交易日期'].iloc[0].date()), str(ins['交易日期'].iloc[-1].date())],
        "oos_range": [str(oos['交易日期'].iloc[0].date()), str(oos['交易日期'].iloc[-1].date())],
        "insample": {k: float(v) for k, v in ins_m.items()},
        "oos": {k: float(v) for k, v in oos_m.items()},
        "oos_default": {k: float(v) for k, v in oos_def_m.items()},
        "insample_default": {k: float(v) for k, v in ins_def_m.items()},
        "tune_top5": res.head(5)[["短均线","长均线","年化收益","夏普","最大回撤","交易次数"]].to_dict(orient="records"),
        "cost_sensitivity": cost_tests,
        "n_ins": len(ins), "n_oos": len(oos),
    }
    with open(os.path.join(BASE, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_json, f, ensure_ascii=False, indent=2)
    print("\n[完成] 已生成指标与图表。metrics.json 供 PDF 生成。")
    print(f"最优参数: {best_s}/{best_l} | 样本内夏普={ins_m['夏普']:.3f} 年化={ins_m['年化收益']:.2%} | "
          f"样本外夏普={oos_m['夏普']:.3f} 年化={oos_m['年化收益']:.2%}")


if __name__ == "__main__":
    main()
