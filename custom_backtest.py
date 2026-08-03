#!/usr/bin/env python3
"""
量化策略课程 — 自定义回测工具
===============================
支持任意股票 + 多种策略的本地回测，输出 CSV/JSON/PNG 图表。

用法：
  # 双均线策略
  python custom_backtest.py --code 300750 --strategy dual-ma --params 5,15

  # 海龟策略
  python custom_backtest.py --code 600519 --strategy turtle --params 20,10,2.0

  # 自定义日期区间
  python custom_backtest.py --code 000333 --strategy dual-ma --params 10,30 \
      --start 2022-01-01 --end 2025-12-31

  # 生成 JSON 供 portfolio dashboard 加载
  python custom_backtest.py --code 300750 --strategy turtle --params 55,27 \
      --export-json my_turtle_backtest.json

  # 输出到指定目录
  python custom_backtest.py --code 300750 --strategy dual-ma \
      --params 5,15 --output-dir ./my_backtests
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime

# Add TASK directories to path so we can import strategy modules
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for d in ["TASK3", "TASK4", "TASK7"]:
    p = os.path.join(BASE_DIR, d)
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from local_config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")


# ── Data Loading ──────────────────────────────────────────────

def code_to_ts_code(code):
    """Convert short code to Tushare TS code."""
    code = str(code).strip().zfill(6)
    if code.startswith(("6", "9")):
        return f"{code}.SH"
    elif code.startswith(("0", "3")):
        return f"{code}.SZ"
    elif code.startswith("8"):
        return f"{code}.BJ"
    return code


def safe_float(val, default=None):
    if val is None or val == "" or val == "nan" or val == "NaN":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def fetch_data_tushare(ts_code, start_date, end_date):
    """Fetch daily data via Tushare SDK."""
    try:
        import tushare as ts
    except ImportError:
        print("错误: 请安装 tushare: pip install tushare")
        sys.exit(1)

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    start_s = start_date.replace("-", "")
    end_s = end_date.replace("-", "")

    print(f"  拉取数据: {ts_code} | {start_s} → {end_s}")
    df = pro.daily(
        ts_code=ts_code, start_date=start_s, end_date=end_s,
        fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
    )
    if df is None or df.empty:
        print(f"  ⚠️  无数据")
        return []

    df = df.sort_values("trade_date")
    rows = []
    for _, r in df.iterrows():
        ds = str(r["trade_date"])
        rows.append({
            "股票代码": r["ts_code"],
            "交易日期": f"{ds[:4]}-{ds[4:6]}-{ds[6:8]}",
            "开盘价": float(r["open"]),
            "最高价": float(r["high"]),
            "最低价": float(r["low"]),
            "收盘价": float(r["close"]),
            "前收盘价": float(r["pre_close"]),
            "涨跌额": float(r["change"]),
            "涨跌幅(%)": float(r["pct_chg"]),
            "成交量(手)": float(r["vol"]),
            "成交额(千元)": float(r["amount"]),
        })
    return rows


def load_local_csv(csv_path):
    """Load a local CSV file."""
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def rows_to_dataframe(rows):
    """Convert list-of-dicts to pandas DataFrame."""
    import pandas as pd
    df = pd.DataFrame(rows)
    for col in ["开盘价", "收盘价", "最高价", "最低价", "前收盘价", "涨跌额", "涨跌幅(%)", "成交量(手)", "成交额(千元)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "交易日期" in df.columns:
        df["交易日期"] = pd.to_datetime(df["交易日期"], errors="coerce")
        df = df.sort_values("交易日期")
    return df


# ── Strategy Functions ────────────────────────────────────────

def run_dual_ma_backtest(df, short_window, long_window, initial_capital=100000.0):
    """Dual Moving Average strategy backtest.

    Returns: (result_df, metrics_dict)
    """
    import numpy as np
    import pandas as pd
    import importlib.util

    # Try to import from TASK3
    task3_path = os.path.join(BASE_DIR, "TASK3", "task3_strategy.py")
    if os.path.exists(task3_path):
        spec = importlib.util.spec_from_file_location("task3_strategy", task3_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        df["交易日期"] = pd.to_datetime(df["交易日期"])
        df = df.sort_values("交易日期")

        sig_df = mod.calc_ma_signals(df.copy(), short_window, long_window)
        bt_df = mod.backtest(sig_df.copy(), initial_capital)
        metrics = mod.calc_metrics(bt_df)
        return bt_df, metrics
    else:
        # Fallback: inline implementation
        return _run_dual_ma_fallback(df, short_window, long_window, initial_capital)


def _run_dual_ma_fallback(df, short, long, capital=100000.0):
    """Inline dual MA backtest (fallback)."""
    import numpy as np
    import pandas as pd
    df = df.copy()
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期")
    df[f"MA{short}"] = df["收盘价"].rolling(window=short).mean()
    df[f"MA{long}"] = df["收盘价"].rolling(window=long).mean()
    df["signal"] = 0
    df.loc[df[f"MA{short}"] > df[f"MA{long}"], "signal"] = 1
    df.loc[df[f"MA{short}"] <= df[f"MA{long}"], "signal"] = -1
    df["position"] = 0
    pos = 0
    for i in range(1, len(df)):
        if df.iloc[i]["signal"] > df.iloc[i - 1]["signal"]:
            pos = 1
        elif df.iloc[i]["signal"] < df.iloc[i - 1]["signal"]:
            pos = 0
        df.iloc[i, df.columns.get_loc("position")] = pos

    df["daily_return"] = df["收盘价"].pct_change()
    df["strategy_return"] = df["position"].shift(1) * df["daily_return"]
    df["portfolio_value"] = capital * (1 + df["strategy_return"]).cumprod()
    df["benchmark_value"] = capital * (1 + df["daily_return"].fillna(0)).cumprod()
    peak = df["portfolio_value"].expanding().max()
    df["drawdown"] = (df["portfolio_value"] - peak) / peak

    total_return = (df["portfolio_value"].iloc[-1] / capital - 1) * 100
    years = (df["交易日期"].iloc[-1] - df["交易日期"].iloc[0]).days / 365.25
    annual_return = ((1 + total_return / 100) ** (1 / max(years, 0.1)) - 1) * 100
    mdd = df["drawdown"].min() * 100
    mean_ret = df["strategy_return"].mean()
    std_ret = df["strategy_return"].std()
    sharpe = np.sqrt(252) * mean_ret / max(std_ret, 1e-8)
    buy_signals = (df["signal"].diff() > 0).sum()
    sell_signals = (df["signal"].diff() < 0).sum()

    metrics = {
        "累计回报": f"{total_return:.2f}%",
        "年化收益率": f"{annual_return:.2f}%",
        "最大回撤MDD": f"{mdd:.2f}%",
        "夏普比率": round(sharpe, 2),
        "买入次数": int(buy_signals),
        "卖出次数": int(sell_signals),
    }
    return df, metrics


def run_turtle_backtest(df, N, M, stop_mult=2.0, initial_capital=100000.0):
    """Turtle trading strategy backtest.

    Returns: (result_df, metrics_dict)
    """
    import sys
    import os
    sys.path.insert(0, os.path.join(BASE_DIR, "TASK4"))
    import importlib.util

    task4_path = os.path.join(BASE_DIR, "TASK4", "task4_turtle.py")
    if os.path.exists(task4_path):
        spec = importlib.util.spec_from_file_location("task4_turtle", task4_path)
        mod = importlib.util.module_from_spec(spec)
        if "matplotlib" not in sys.modules:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"]
            plt.rcParams["axes.unicode_minus"] = False
        spec.loader.exec_module(mod)
        import pandas as pd
        df["交易日期"] = pd.to_datetime(df["交易日期"])
        df = df.sort_values("交易日期")

        sig_df = mod.calc_turtle_signals(df.copy(), N=N, M=M, stop_mult=stop_mult)
        bt_df = mod.turtle_backtest(sig_df.copy(), initial_capital=initial_capital,
                                     stop_mult=stop_mult)
        metrics = mod.calc_metrics(bt_df)
        return bt_df, metrics
    else:
        return _run_turtle_fallback(df, N, M, stop_mult, initial_capital)


def _run_turtle_fallback(df, N, M, stop_mult=2.0, capital=100000.0):
    """Inline turtle backtest (fallback)."""
    import numpy as np
    import pandas as pd
    df = df.copy()
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期")

    # Donchian Channel
    df["upper"] = df["最高价"].rolling(N).max()
    df["lower"] = df["最低价"].rolling(M).min()

    # ATR
    df["H_L"] = df["最高价"] - df["最低价"]
    df["H_Cp"] = abs(df["最高价"] - df["收盘价"].shift(1))
    df["L_Cp"] = abs(df["最低价"] - df["收盘价"].shift(1))
    df["TR"] = df[["H_L", "H_Cp", "L_Cp"]].max(axis=1)
    atr_n = max(N, 20)
    df["ATR"] = df["TR"].rolling(atr_n).mean()

    # Signals
    df["signal"] = 0
    df["exit_reason"] = ""
    df["entry_price"] = 0.0
    df["atr_entry"] = 0.0

    pos = 0
    entry = 0
    for i in range(1, len(df)):
        c = df.iloc[i]
        atr = c["ATR"] or 0
        if pos == 0:
            if pd.notna(c["upper"]) and c["收盘价"] > df.iloc[i - 1]["upper"]:
                pos = 1
                entry = c["收盘价"]
                df.iloc[i, df.columns.get_loc("signal")] = 1
                df.iloc[i, df.columns.get_loc("entry_price")] = entry
                df.iloc[i, df.columns.get_loc("atr_entry")] = atr
            elif pd.notna(c["lower"]) and c["收盘价"] < df.iloc[i - 1]["lower"]:
                pos = 1
                entry = c["收盘价"]
                df.iloc[i, df.columns.get_loc("signal")] = 1
                df.iloc[i, df.columns.get_loc("entry_price")] = entry
                df.iloc[i, df.columns.get_loc("atr_entry")] = atr
        elif pos == 1:
            stop_price = entry - stop_mult * atr
            exit_reason = None
            if c["最低价"] <= stop_price:
                pos = 0
                exit_reason = "止损"
            elif pd.notna(c["lower"]) and c["收盘价"] < c["lower"]:
                pos = 0
                exit_reason = "破低"
            if pos == 0:
                df.iloc[i, df.columns.get_loc("signal")] = -1
                df.iloc[i, df.columns.get_loc("exit_reason")] = exit_reason or ""

    df["position"] = 0
    pos = 0
    for i in range(len(df)):
        s = df.iloc[i]["signal"]
        if s == 1:
            pos = 1
        elif s == -1:
            pos = 0
        df.iloc[i, df.columns.get_loc("position")] = pos

    df["daily_return"] = df["收盘价"].pct_change()
    df["strategy_return"] = df["position"].shift(1) * df["daily_return"]
    df["portfolio_value"] = capital * (1 + df["strategy_return"]).cumprod()
    peak = df["portfolio_value"].expanding().max()
    df["drawdown"] = (df["portfolio_value"] - peak) / peak

    total_return = (df["portfolio_value"].iloc[-1] / capital - 1) * 100
    years = (df["交易日期"].iloc[-1] - df["交易日期"].iloc[0]).days / 365.25
    annual_return = ((1 + total_return / 100) ** (1 / max(years, 0.1)) - 1) * 100
    mdd = df["drawdown"].min() * 100
    mean_ret = df["strategy_return"].mean()
    std_ret = df["strategy_return"].std()
    sharpe = np.sqrt(252) * mean_ret / max(std_ret, 1e-8)
    buy_signals = (df["signal"] == 1).sum()
    sell_signals = (df["signal"] == -1).sum()
    stops = (df["exit_reason"] == "止损").sum()
    breaks = (df["exit_reason"] == "破低").sum()

    metrics = {
        "累计回报": f"{total_return:.2f}%",
        "年化收益率": f"{annual_return:.2f}%",
        "最大回���MDD": f"{mdd:.2f}%",
        "夏普比率": round(sharpe, 2),
        "买入次数": int(buy_signals),
        "卖出次数": int(sell_signals),
        "止损次数": int(stops),
        "破低次数": int(breaks),
    }
    return df, metrics


# ── Output Functions ──────────────────────────────────────────

def export_backtest_csv(df, strategy_name, params_str, code, output_dir):
    """Export backtest data to CSV."""
    filename = f"backtest_{code}_{strategy_name}_{params_str}.csv"
    path = os.path.join(output_dir, filename)

    # Select key columns for CSV
    export_cols = ["交易日期", "收盘价"]
    if "MA5" in df.columns:
        export_cols.extend([c for c in df.columns if c.startswith("MA")])
    if "upper" in df.columns:
        export_cols.extend(["upper", "lower", "ATR"])
    export_cols.extend([c for c in ["signal", "position",
                        "strategy_return", "portfolio_value", "drawdown",
                        "exit_reason"] if c in df.columns])

    df_export = df[export_cols].copy()
    if "交易日期" in df_export.columns:
        df_export["交易日期"] = df_export["交易日期"].astype(str)
    df_export.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"  📁 CSV: {path}")
    return path


def export_backtest_json(df, metrics, strategy_name, params_str, code, output_dir):
    """Export backtest data as JSON (compatible with portfolio dashboard)."""
    filename = f"backtest_{code}_{strategy_name}_{params_str}.json"
    path = os.path.join(output_dir, filename)

    data = {
        "code": code,
        "strategy": strategy_name,
        "params": params_str,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metrics": metrics,
    }

    # Add time series data
    if "交易日期" in df.columns:
        data["dates"] = df["交易日期"].dt.strftime("%Y-%m-%d").tolist()
    if "收盘价" in df.columns:
        data["close"] = df["收盘价"].fillna(0).tolist()
    if "portfolio_value" in df.columns:
        data["nav"] = df["portfolio_value"].fillna(0).tolist()
    if "drawdown" in df.columns:
        data["drawdown"] = df["drawdown"].fillna(0).tolist()
    if "signal" in df.columns:
        data["signals"] = df["signal"].fillna(0).astype(int).tolist()

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  📁 JSON: {path}")
    return path


def plot_backtest_charts(df, metrics, strategy_name, code, output_dir):
    """Generate PNG charts for the backtest."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    plt.rcParams["font.sans-serif"] = ["PingFang SC", "Heiti SC", "STHeiti", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"{code} — {strategy_name} 回测结果", fontsize=14, fontweight="bold")

    # 1. Price + Signals
    ax = axes[0, 0]
    ax.plot(df["交易日期"], df["收盘价"], color="#333", linewidth=0.8, alpha=0.7, label="收盘价")
    if "MA5" in df.columns:
        ax.plot(df["交易日期"], df["MA5"], color="#e74c3c", linewidth=0.8, alpha=0.7, label="MA5")
        ax.plot(df["交易日期"], df["MA15"], color="#3498db", linewidth=0.8, alpha=0.7, label="MA15")
    if "upper" in df.columns:
        ax.plot(df["交易日期"], df["upper"], color="#e74c3c", linestyle="--", linewidth=0.6, alpha=0.5, label="Upper")
        ax.plot(df["交易日期"], df["lower"], color="#27ae60", linestyle="--", linewidth=0.6, alpha=0.5, label="Lower")
    buy_mask = df["signal"] == 1
    sell_mask = df["signal"] == -1
    if buy_mask.any():
        ax.scatter(df.loc[buy_mask, "交易日期"], df.loc[buy_mask, "收盘价"],
                   c="#e74c3c", marker="^", s=40, zorder=5, label="买入")
    if sell_mask.any():
        ax.scatter(df.loc[sell_mask, "交易日期"], df.loc[sell_mask, "收盘价"],
                   c="#27ae60", marker="v", s=40, zorder=5, label="卖出")
    ax.set_title("价格与交易信号")
    ax.legend(fontsize=7, loc="best")
    ax.tick_params(axis="x", rotation=30)

    # 2. NAV
    ax = axes[0, 1]
    if "portfolio_value" in df.columns:
        ax.plot(df["交易日期"], df["portfolio_value"], color="#e74c3c", linewidth=1, label="策略净值")
    if "benchmark_value" in df.columns:
        ax.plot(df["交易日期"], df["benchmark_value"], color="#95a5a6", linewidth=0.8, alpha=0.7, label="买入持有")
    ax.axhline(y=100000, color="#333", linestyle="--", linewidth=0.5, alpha=0.3)
    ax.set_title("策略净值")
    ax.legend(fontsize=7)
    ax.tick_params(axis="x", rotation=30)

    # 3. Drawdown
    ax = axes[1, 0]
    if "drawdown" in df.columns:
        ax.fill_between(df["交易日期"], 0, df["drawdown"] * 100, color="#e74c3c", alpha=0.3)
        ax.plot(df["交易日期"], df["drawdown"] * 100, color="#e74c3c", linewidth=0.8)
    ax.set_title("回撤曲线 (%)")
    ax.tick_params(axis="x", rotation=30)

    # 4. Metrics Table
    ax = axes[1, 1]
    ax.axis("off")
    metric_text = "关键指标:\n" + "-" * 30 + "\n"
    for k, v in metrics.items():
        metric_text += f"{k}: {v}\n"
    ax.text(0.05, 0.95, metric_text, transform=ax.transAxes,
            fontsize=9, verticalalignment="top", fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="#f8f9fa", alpha=0.8))

    plt.tight_layout()
    chart_path = os.path.join(output_dir, f"backtest_{code}_{strategy_name}.png")
    fig.savefig(chart_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    print(f"  📊 图表: {chart_path}")
    return chart_path


# ── Main CLI ──────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="量化策略课程 — 自定义回测工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
策略类型:
  dual-ma     双均线策略  (params: short,long  例: 5,15)
  turtle      海龟策略    (params: N,M[,stop]  例: 20,10,2.0)
  turtle-adv  双系统海龟  (使用 TASK4_advanced 参数)

示例:
  python custom_backtest.py --code 300750 --strategy dual-ma --params 5,15
  python custom_backtest.py --code 600519 --strategy turtle --params 20,10
  python custom_backtest.py --code 000333 --strategy dual-ma --params 10,30 \\
      --start 2022-01-01 --end 2025-12-31
  python custom_backtest.py --code 300750 --strategy turtle --params 55,27 \\
      --export-json turtle_output.json
        """,
    )
    parser.add_argument("--code", required=True, help="股票代码 (如 300750)")
    parser.add_argument("--strategy", required=True,
                        choices=["dual-ma", "turtle", "turtle-adv"],
                        help="策略类型")
    parser.add_argument("--params", required=True,
                        help="策略参数，逗号分隔 (如 5,15 或 20,10,2.0)")
    parser.add_argument("--start", default=None, help="起始日期 YYYY-MM-DD")
    parser.add_argument("--end", default=None, help="结束日期 YYYY-MM-DD")
    parser.add_argument("--capital", type=float, default=100000.0,
                        help="初始资金 (默认: 100000)")
    parser.add_argument("--output-dir", default=None,
                        help="输出目录 (默认: ./backtest_output)")
    parser.add_argument("--csv-path", default=None,
                        help="使用本地 CSV 文件 (跳过 Tushare 拉取)")
    parser.add_argument("--export-json", default=None,
                        help="导出 JSON 文件路径")
    parser.add_argument("--no-charts", action="store_true",
                        help="跳过图表生成")
    parser.add_argument("--json-only", action="store_true",
                        help="仅生成 JSON，不生成 CSV/图表")

    args = parser.parse_args()

    # Setup
    ts_code = code_to_ts_code(args.code)
    if args.output_dir:
        output_dir = args.output_dir
    else:
        output_dir = os.path.join(BASE_DIR, "backtest_output")
    os.makedirs(output_dir, exist_ok=True)

    # Parse params
    parts = [float(x) for x in args.params.split(",")]
    params_str = args.params.replace(",", "_")

    # Date range
    today = datetime.now().strftime("%Y-%m-%d")
    start_date = args.start or "2020-01-01"
    end_date = args.end or today

    # Strategy name for display
    strategy_names = {
        "dual-ma": "双均线策略",
        "turtle": "海龟策略",
        "turtle-adv": "双系统海龟策略",
    }
    strategy_display = strategy_names[args.strategy]

    print("=" * 60)
    print(f"📈 自定义回测: {args.code} — {strategy_display}")
    print("=" * 60)
    print(f"  参数: {args.params}")
    print(f"  区间: {start_date} → {end_date}")
    print(f"  资金: ¥{args.capital:,.0f}")

    # Load data
    if args.csv_path:
        print(f"\n📂 加载本地数据: {args.csv_path}")
        rows = load_local_csv(args.csv_path)
    else:
        print(f"\n📡 从 Tushare 拉取数据...")
        rows = fetch_data_tushare(ts_code, start_date, end_date)

    if not rows:
        print("❌ 无数据，退出")
        sys.exit(1)

    print(f"  共 {len(rows)} 条日线数据")

    df = rows_to_dataframe(rows)

    # Run backtest
    print(f"\n🔄 运行 {strategy_display} 回测...")
    if args.strategy == "dual-ma":
        short, long = int(parts[0]), int(parts[1])
        bt_df, metrics = run_dual_ma_backtest(df, short, long, args.capital)

    elif args.strategy == "turtle":
        N, M = int(parts[0]), int(parts[1])
        stop = float(parts[2]) if len(parts) >= 3 else 2.0
        bt_df, metrics = run_turtle_backtest(df, N, M, stop, args.capital)

    elif args.strategy == "turtle-adv":
        print("  ⚠️  双系统海龟策略需 TASK4_advanced 数据，暂不支持直接回测")
        print("  建议使用 TASK4 的海龟策略代替")
        sys.exit(1)

    # Print metrics
    print("\n📊 回测指标:")
    print("-" * 40)
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Export
    print(f"\n💾 输出文件 ({output_dir}):")
    if not args.json_only:
        export_backtest_csv(bt_df, args.strategy, params_str, args.code, output_dir)
        if not args.no_charts:
            plot_backtest_charts(bt_df, metrics, strategy_display, args.code, output_dir)

    json_path = export_backtest_json(
        bt_df, metrics, args.strategy, params_str, args.code, output_dir)

    if args.export_json:
        import shutil
        shutil.copy(json_path, args.export_json)
        print(f"  📁 JSON 已复制到: {args.export_json}")

    # Dashboard integration hint
    dashboard_dir = os.path.join(BASE_DIR, "portfolio", "data")
    if os.path.exists(dashboard_dir):
        custom_json = os.path.join(dashboard_dir, f"custom_backtest_{args.code}_{args.strategy}.json")
        if not args.json_only:
            import shutil
            shutil.copy(json_path, custom_json)
            print(f"\n📊 JSON 已复制到 portfolio dashboard: data/{os.path.basename(custom_json)}")
            print(f"  前端可通过 DataLoader 加载此文件")

    print("\n" + "=" * 60)
    print("✅ 回测完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
