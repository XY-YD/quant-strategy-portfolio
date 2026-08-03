#!/usr/bin/env python3
"""
Portfolio Data Converter
Reads CSV files from TASK1-TASK7 and converts to JSON for the web dashboard.
"""

import json
import os
import csv
import shutil
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

os.makedirs(DATA_DIR, exist_ok=True)


def read_csv(path):
    """Read CSV with proper encoding handling."""
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def safe_float(val, default=None):
    """Safely convert to float."""
    if val is None or val == "" or val == "nan" or val == "NaN":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def convert_task1():
    """TASK1: Daily price data for Ningde Times."""
    csv_path = os.path.join(BASE_DIR, "TASK1", "宁德时代_300750_日线数据.csv")
    rows = read_csv(csv_path)
    dates, close, open_p, high, low, volume = [], [], [], [], [], []
    for r in rows:
        dates.append(r.get("交易日期", ""))
        close.append(safe_float(r.get("收盘价"), 0))
        open_p.append(safe_float(r.get("开盘价"), 0))
        high.append(safe_float(r.get("最高价"), 0))
        low.append(safe_float(r.get("最低价"), 0))
        vol = safe_float(r.get("成交量(手)"), 0)
        volume.append(vol)
    result = {
        "stock": "宁德时代",
        "code": "300750.SZ",
        "dates": dates,
        "close": close,
        "open": open_p,
        "high": high,
        "low": low,
        "volume": volume,
        "count": len(dates),
    }
    save_json("task1_daily.json", result)


def convert_task3():
    """TASK3: Dual moving average strategy. Generates per-param backtest JSONs."""
    task_dir = os.path.join(BASE_DIR, "TASK3")

    # Generate individual backtest JSONs for each parameter combo
    param_combos = [
        ("MA5_MA15", 5, 15, "task3_backtest_ma5_15.json"),
        ("MA10_MA30", 10, 30, "task3_backtest_ma10_30.json"),
        ("MA20_MA60", 20, 60, "task3_backtest_ma20_60.json"),
    ]
    all_backtests = {}
    for label, sw, lw, filename in param_combos:
        bt_path = os.path.join(task_dir, f"宁德时代_双均线策略_{label}_回测数据.csv")
        if not os.path.exists(bt_path):
            print(f"  WARNING: {bt_path} not found, skipping")
            continue
        bt_rows = read_csv(bt_path)
        dates, close, ma_short, ma_long, signals, nav, drawdown = [], [], [], [], [], [], []
        for r in bt_rows:
            dates.append(r.get("交易日期", ""))
            close.append(safe_float(r.get("收盘价"), 0))
            ma_short.append(safe_float(r.get(f"MA{sw}")))
            ma_long.append(safe_float(r.get(f"MA{lw}")))
            sig = safe_float(r.get("信号(1买/-1卖/0无)"), 0)
            signals.append(sig)
            nav.append(safe_float(r.get("策略净值"), 100000))
            dd = safe_float(r.get("回撤幅度"), 0)
            drawdown.append(dd)
        bt_json = {
            "dates": dates, "close": close,
            f"ma{sw}": ma_short, f"ma{lw}": ma_long,
            "signals": signals, "nav": nav, "drawdown": drawdown,
        }
        save_json(filename, bt_json)
        all_backtests[label] = filename

    # Also save the default (MA5/MA15) as task3_backtest.json for backward compat
    # and a summary index
    save_json("task3_backtest_index.json", all_backtests)

    # Parameter comparison (summary metrics)
    param_path = os.path.join(task_dir, "宁德时代_多参数对比指标.csv")
    param_rows = read_csv(param_path)
    params = []
    for r in param_rows:
        params.append({
            "name": r.get("均线参数", ""),
            "short_ma": int(safe_float(r.get("短均线"), 0)),
            "long_ma": int(safe_float(r.get("长均线"), 0)),
            "return_pct": safe_float(r.get("累计回报", "").replace("%", "")) or 0,
            "annual_return": safe_float(r.get("年化收益率", "").replace("%", "")) or 0,
            "mdd": safe_float(r.get("最大回撤MDD", "").replace("%", "")) or 0,
            "sharpe": safe_float(r.get("夏普比率"), 0),
            "buy_count": int(safe_float(r.get("买入次数"), 0)),
            "sell_count": int(safe_float(r.get("卖出次数"), 0)),
        })
    save_json("task3_params.json", params)

    # Multi-stock comparison
    stock_path = os.path.join(task_dir, "多股票策略指标对比.csv")
    stock_rows = read_csv(stock_path)
    stocks = []
    for r in stock_rows:
        stocks.append({
            "name": r.get("股票", ""),
            "return_pct": safe_float(r.get("累计回报", "").replace("%", "")) or 0,
            "annual_return": safe_float(r.get("年化收益率", "").replace("%", "")) or 0,
            "mdd": safe_float(r.get("最大回撤MDD", "").replace("%", "")) or 0,
            "sharpe": safe_float(r.get("夏普比率"), 0),
            "buy_count": int(safe_float(r.get("买入次数"), 0)),
            "sell_count": int(safe_float(r.get("卖出次数"), 0)),
            "benchmark_return": safe_float(r.get("基准回报", "").replace("%", "")) or 0,
            "benchmark_mdd": safe_float(r.get("基准MDD", "").replace("%", "")) or 0,
        })
    save_json("task3_stocks.json", stocks)


def convert_task4():
    """TASK4: Turtle strategy. Generates per-param backtest JSONs."""
    task_dir = os.path.join(BASE_DIR, "TASK4")

    # Generate individual backtest JSONs for each parameter combo
    param_combos = [
        ("N10_M5", 10, 5, "task4_backtest_n10_m5.json"),
        ("N20_M10", 20, 10, "task4_backtest_n20_m10.json"),
        ("N55_M27", 55, 27, "task4_backtest_n55_m27.json"),
    ]
    all_backtests = {}
    for label, N, M, filename in param_combos:
        bt_path = os.path.join(task_dir, f"宁德时代_海龟策略_N{N}_回测数据.csv")
        if not os.path.exists(bt_path):
            print(f"  WARNING: {bt_path} not found, skipping")
            continue
        bt_rows = read_csv(bt_path)
        dates, close, upper, lower, atr, signals, nav, drawdown, exit_reasons = [], [], [], [], [], [], [], [], []
        upper_key = f"上轨(前{N}日高)"
        lower_key = f"下轨(前{M}日低)"
        for r in bt_rows:
            dates.append(r.get("交易日期", ""))
            close.append(safe_float(r.get("收盘价"), 0))
            upper.append(safe_float(r.get(upper_key)))
            lower.append(safe_float(r.get(lower_key)))
            atr.append(safe_float(r.get("ATR")))
            sig = safe_float(r.get("信号(1买/-1卖/0无)"), 0)
            signals.append(sig)
            nav.append(safe_float(r.get("策略净值"), 100000))
            dd = safe_float(r.get("回撤幅度"), 0)
            drawdown.append(dd)
            exit_reasons.append(r.get("退出原因", ""))
        bt_json = {
            "dates": dates, "close": close, "upper": upper, "lower": lower,
            "atr": atr, "signals": signals, "nav": nav, "drawdown": drawdown,
            "exit_reasons": exit_reasons, "N": N, "M": M,
        }
        save_json(filename, bt_json)
        all_backtests[label] = filename
    save_json("task4_backtest_index.json", all_backtests)

    # Parameter comparison
    param_path = os.path.join(task_dir, "宁德时代_多参数对比指标.csv")
    param_rows = read_csv(param_path)
    params = []
    for r in param_rows:
        params.append({
            "name": r.get("通道参数", ""),
            "buy_n": int(safe_float(r.get("买入周期N"), 0)),
            "sell_m": int(safe_float(r.get("卖出周期M"), 0)),
            "return_pct": safe_float(r.get("累计回报", "").replace("%", "")) or 0,
            "annual_return": safe_float(r.get("年化收益率", "").replace("%", "")) or 0,
            "mdd": safe_float(r.get("最大回撤MDD", "").replace("%", "")) or 0,
            "sharpe": safe_float(r.get("夏普比率"), 0),
            "buy_count": int(safe_float(r.get("买入次数"), 0)),
            "sell_count": int(safe_float(r.get("卖出次数"), 0)),
            "stop_loss_count": int(safe_float(r.get("止损次数"), 0)),
            "break_low_count": int(safe_float(r.get("破低次数"), 0)),
        })
    save_json("task4_params.json", params)

    # Multi-stock comparison
    stock_path = os.path.join(task_dir, "多股票策略指标对比.csv")
    stock_rows = read_csv(stock_path)
    stocks = []
    for r in stock_rows:
        stocks.append({
            "name": r.get("股票", ""),
            "return_pct": safe_float(r.get("累计回报", "").replace("%", "")) or 0,
            "annual_return": safe_float(r.get("年化收益率", "").replace("%", "")) or 0,
            "mdd": safe_float(r.get("最大回撤MDD", "").replace("%", "")) or 0,
            "sharpe": safe_float(r.get("夏普比率"), 0),
            "buy_count": int(safe_float(r.get("买入次数"), 0)),
            "sell_count": int(safe_float(r.get("卖出次数"), 0)),
            "stop_loss_count": int(safe_float(r.get("止损次数"), 0)),
            "break_low_count": int(safe_float(r.get("破低次数"), 0)),
            "benchmark_return": safe_float(r.get("基准回报", "").replace("%", "")) or 0,
            "benchmark_mdd": safe_float(r.get("基准MDD", "").replace("%", "")) or 0,
        })
    save_json("task4_stocks.json", stocks)


def convert_task4_advanced():
    """TASK4_advanced: Dual-system turtle strategy."""
    task_dir = os.path.join(BASE_DIR, "TASK4_advanced")

    # Backtest data
    bt_path = os.path.join(task_dir, "宁德时代_双系统海龟_回测数据.csv")
    bt_rows = read_csv(bt_path)
    dates, close, atr, nav, drawdown = [], [], [], [], []
    long_open, short_open, long_add, short_add = [], [], [], []
    close_long, close_short = [], []
    for r in bt_rows:
        dates.append(r.get("交易日期", ""))
        close.append(safe_float(r.get("收盘价"), 0))
        atr.append(safe_float(r.get("ATR(20)")))
        nav.append(safe_float(r.get("策略净值"), 1000000))
        dd = safe_float(r.get("回撤幅度"), 0)
        drawdown.append(dd)
        long_open.append(r.get("做多开仓", "") == "True")
        short_open.append(r.get("做空开仓", "") == "True")
        long_add.append(r.get("多单加仓", "") == "True")
        short_add.append(r.get("空单加仓", "") == "True")
        close_long.append(r.get("平多仓", "") == "True")
        close_short.append(r.get("平空仓", "") == "True")
    save_json("task4_advanced_backtest.json", {
        "dates": dates, "close": close, "atr": atr, "nav": nav, "drawdown": drawdown,
        "long_open": long_open, "short_open": short_open,
        "long_add": long_add, "short_add": short_add,
        "close_long": close_long, "close_short": close_short,
    })

    # Parameter comparison
    param_path = os.path.join(task_dir, "宁德时代_多参数对比指标.csv")
    param_rows = read_csv(param_path)
    params = []
    for r in param_rows:
        params.append({
            "name": r.get("配置", ""),
            "s1_entry": int(safe_float(r.get("S1入场"), 0)),
            "s1_exit": int(safe_float(r.get("S1出场"), 0)),
            "s2_entry": int(safe_float(r.get("S2入场"), 0)),
            "s2_exit": int(safe_float(r.get("S2出场"), 0)),
            "return_pct": safe_float(r.get("累计回报", "").replace("%", "")) or 0,
            "annual_return": safe_float(r.get("年化收益", "").replace("%", "")) or 0,
            "mdd": safe_float(r.get("最大回撤MDD", "").replace("%", "")) or 0,
            "sharpe": safe_float(r.get("夏普比率"), 0),
            "long_open": int(safe_float(r.get("做多开仓"), 0)),
            "short_open": int(safe_float(r.get("做空开仓"), 0)),
            "long_add": int(safe_float(r.get("多单加仓"), 0)),
            "short_add": int(safe_float(r.get("空单加仓"), 0)),
            "close_long": int(safe_float(r.get("平多"), 0)),
            "close_short": int(safe_float(r.get("平空"), 0)),
        })
    save_json("task4_advanced_params.json", params)

    # Multi-stock comparison
    stock_path = os.path.join(task_dir, "多股票策略指标对比.csv")
    stock_rows = read_csv(stock_path)
    stocks = []
    for r in stock_rows:
        stocks.append({
            "name": r.get("股票", ""),
            "return_pct": safe_float(r.get("累计回报", "").replace("%", "")) or 0,
            "annual_return": safe_float(r.get("年化收益", "").replace("%", "")) or 0,
            "mdd": safe_float(r.get("最大回撤MDD", "").replace("%", "")) or 0,
            "sharpe": safe_float(r.get("夏普比率"), 0),
            "long_open": int(safe_float(r.get("做多开仓"), 0)),
            "short_open": int(safe_float(r.get("做空开仓"), 0)),
            "long_add": int(safe_float(r.get("多单加仓"), 0)),
            "short_add": int(safe_float(r.get("空单加仓"), 0)),
            "close_long": int(safe_float(r.get("平多"), 0)),
            "close_short": int(safe_float(r.get("平空"), 0)),
            "benchmark_return": safe_float(r.get("基准回报", "").replace("%", "")) or 0,
            "benchmark_mdd": safe_float(r.get("基准MDD", "").replace("%", "")) or 0,
        })
    save_json("task4_advanced_stocks.json", stocks)


def convert_task6():
    """TASK6: ML stock selection backtest metrics."""
    csv_path = os.path.join(BASE_DIR, "TASK6", "backtest_metrics.csv")
    rows = read_csv(csv_path)
    models = []
    for r in rows:
        models.append({
            "name": r.get("模型", ""),
            "cum_return": safe_float(r.get("累计收益"), 0),
            "annual_return": safe_float(r.get("年化收益"), 0),
            "sharpe": safe_float(r.get("夏普比率"), 0),
            "mdd": safe_float(r.get("最大回撤"), 0),
            "win_rate": safe_float(r.get("胜率"), 0),
            "excess_sharpe": safe_float(r.get("超额夏普"), 0),
        })
    save_json("task6_models.json", models)


def convert_task7():
    """TASK7: Strategy optimization and out-of-sample testing."""
    task_dir = os.path.join(BASE_DIR, "TASK7")

    # Parameter optimization (sample-in)
    opt_path = os.path.join(task_dir, "双均线_样本内参数寻优.csv")
    opt_rows = read_csv(opt_path)
    optimizations = []
    for r in opt_rows:
        optimizations.append({
            "short_ma": int(safe_float(r.get("短均线"), 0)),
            "long_ma": int(safe_float(r.get("长均线"), 0)),
            "cum_return": safe_float(r.get("累计收益"), 0),
            "annual_return": safe_float(r.get("年化收益"), 0),
            "annual_vol": safe_float(r.get("年化波动"), 0),
            "sharpe": safe_float(r.get("夏普"), 0),
            "sortino": safe_float(r.get("索提诺"), 0),
            "mdd": safe_float(r.get("最大回撤"), 0),
            "mdd_days": int(safe_float(r.get("最大回撤时长(日)"), 0)),
            "trades": int(safe_float(r.get("交易次数"), 0)),
            "daily_win_rate": safe_float(r.get("日胜率"), 0),
            "var95": safe_float(r.get("VaR95"), 0),
            "var99": safe_float(r.get("VaR99"), 0),
            "cvar95": safe_float(r.get("CVaR95"), 0),
            "beta": safe_float(r.get("Beta"), 0),
            "calmar": safe_float(r.get("Calmar"), 0),
        })
    # Sort by sharpe descending
    optimizations.sort(key=lambda x: x["sharpe"], reverse=True)
    save_json("task7_optimization.json", optimizations[:50])

    # In-sample vs out-of-sample comparison
    cmp_path = os.path.join(task_dir, "双均线_指标对比.csv")
    cmp_rows = read_csv(cmp_path)
    comparison = {}
    for r in cmp_rows:
        metric = r.get("指标", "")
        comparison[metric] = {
            "in_sample_optimal": safe_float(r.get("样本内_最优")),
            "out_sample_optimal": safe_float(r.get("样本外_最优")),
            "out_sample_default": safe_float(r.get("样本外_默认5_15")),
        }
    save_json("task7_comparison.json", comparison)

    # Cost sensitivity
    cost_path = os.path.join(task_dir, "双均线_成本敏感性.csv")
    cost_rows = read_csv(cost_path)
    sensitivity = []
    for r in cost_rows:
        slippage = safe_float(r.get("滑点"), 0)
        sensitivity.append({
            "slippage": slippage,
            "slippage_pct": slippage * 100,
            "annual_return": safe_float(r.get("年化收益"), 0),
            "sharpe": safe_float(r.get("夏普"), 0),
            "mdd": safe_float(r.get("最大回撤"), 0),
        })
    save_json("task7_sensitivity.json", sensitivity)


def convert_task8_summary():
    """TASK8: Summary data for the comprehensive report."""
    summary = {
        "title": "量化策略课程 - 综合学习报告",
        "author": "夏阳",
        "pages": 30,
        "chapters": [
            {"title": "数据获取与可视化", "task": "TASK1", "desc": "宁德时代242个交易日数据获取与走势展示"},
            {"title": "技术指标分析", "task": "TASK2", "desc": "RSI/MACD/布林带/KDJ四大指标计算与可视化"},
            {"title": "双均线策略回测", "task": "TASK3", "desc": "金叉死叉信号，3组参数×4只股票对比"},
            {"title": "海龟交易策略", "task": "TASK4", "desc": "唐奇安通道+ATR止损，含双系统进阶版"},
            {"title": "ML分类实战", "task": "TASK5", "desc": "逻辑回归/决策树/随机森林分类对比"},
            {"title": "ML选股策略", "task": "TASK6", "desc": "4分类+5回归模型，季度截面选股"},
            {"title": "策略寻优与实盘模拟", "task": "TASK7", "desc": "1296组参数寻优，样本内外分离"},
            {"title": "综合学习报告", "task": "TASK8", "desc": "8条实战建议，全流程系统总结"},
        ],
        "total_tasks": 9,
        "total_charts": 57,
        "total_strategies": 4,
        "main_stock": "宁德时代(300750.SZ)",
        "suggestions": [
            "不要单独使用双均线策略，结合成交量、MACD等指标综合判断",
            "设置止损线，控制单笔亏损在可承受范围内",
            "根据市场环境调整参数：牛市用短参数，熊市用长参数",
            "选择趋势性强的标的，避开长期横盘震荡的股票",
            "海龟策略在趋势牛市中大放异彩，横盘震荡中持续亏损",
            "理解每种策略的适用边界，识别市场状态，果断执行",
            "模型指标高不代表可交易性强，应关注样本外表现",
            "预测模型转交易策略时，要额外考虑调仓频率和交易成本",
        ],
    }
    save_json("task8_summary.json", summary)


def copy_images():
    """Copy PNG images from TASK directories to portfolio/images/."""
    task_map = {
        "TASK1": "task1",
        "TASK2": "task2",
        "TASK3": "task3",
        "TASK4": "task4",
        "TASK4_advanced": "task4_advanced",
        "TASK5": "task5",
        "TASK6": "task6",
        "TASK7": "task7",
        "TASK8": "task8",
    }
    for task_dir, img_subdir in task_map.items():
        src_dir = os.path.join(BASE_DIR, task_dir)
        dst_dir = os.path.join(IMG_DIR, img_subdir)
        os.makedirs(dst_dir, exist_ok=True)
        # Search for PNGs in root and figs/ subdirectory
        pngs = glob.glob(os.path.join(src_dir, "*.png")) + glob.glob(os.path.join(src_dir, "figs", "*.png"))
        for png in sorted(pngs):
            fname = os.path.basename(png)
            dst = os.path.join(dst_dir, fname)
            shutil.copy2(png, dst)
            print(f"  Copied: {task_dir}/{fname}")
    print("Image copy complete.")


def save_json(name, data):
    path = os.path.join(DATA_DIR, name)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Generated: data/{name}")


def main():
    print("=" * 50)
    print("Portfolio Data Converter")
    print("=" * 50)

    print("\n[1/8] Converting TASK1 - Daily price data...")
    convert_task1()

    print("\n[2/8] Converting TASK3 - Dual MA strategy...")
    convert_task3()

    print("\n[3/8] Converting TASK4 - Turtle strategy...")
    convert_task4()

    print("\n[4/8] Converting TASK4_advanced - Dual-system turtle...")
    convert_task4_advanced()

    print("\n[5/8] Converting TASK6 - ML stock selection...")
    convert_task6()

    print("\n[6/8] Converting TASK7 - Strategy optimization...")
    convert_task7()

    print("\n[7/8] Converting TASK8 - Summary data...")
    convert_task8_summary()

    print("\n[8/8] Copying PNG images...")
    copy_images()

    print("\n" + "=" * 50)
    print("All data converted successfully!")
    print(f"Output: {DATA_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
