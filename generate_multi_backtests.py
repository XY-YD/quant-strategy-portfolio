#!/usr/bin/env python3
"""Generate full backtest CSVs for all parameter combinations in TASK3 and TASK4."""

import sys
import os

# Add project root to path so we can import task modules
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(PROJECT_DIR, "TASK3"))
sys.path.insert(0, os.path.join(PROJECT_DIR, "TASK4"))

import pandas as pd

# ============ TASK3: Dual MA ============

def gen_task3_backtests():
    """Generate backtest CSVs for all 3 MA parameter combos."""
    sys.path.insert(0, os.path.join(PROJECT_DIR, "TASK3"))
    from task3_strategy import load_stock_data, calc_ma_signals, backtest, export_signal_csv, STOCK_FILES, OUTPUT_DIR as T3_OUT

    nd_path = STOCK_FILES["宁德时代"]["path"]
    nd_raw = load_stock_data(nd_path)
    print(f"TASK3: 加载数据 {len(nd_raw)} 行")

    param_combos = [(5, 15), (10, 30), (20, 60)]
    for sw, lw in param_combos:
        print(f"  生成 MA{sw}/MA{lw} 回测数据...")
        nd_sig = calc_ma_signals(nd_raw.copy(), sw, lw)
        nd_bt = backtest(nd_sig)
        export_signal_csv(nd_bt, "宁德时代", sw, lw)
    print("TASK3 全部完成！")

# ============ TASK4: Turtle ============

def gen_task4_backtests():
    """Generate backtest CSVs for all 3 turtle parameter combos."""
    sys.path.insert(0, os.path.join(PROJECT_DIR, "TASK4"))
    # Need to reload with TASK4 path first
    import importlib
    import task4_turtle as t4

    nd_path = t4.STOCK_FILES["宁德时代"]["path"]
    nd_raw = t4.load_stock_data(nd_path)
    print(f"TASK4: 加载数据 {len(nd_raw)} 行")

    # param_N_list controls N values, M = N // 2
    for N in t4.PARAM_N_LIST:  # [10, 20, 55]
        M = N // 2
        print(f"  生成 N{N}/M{M} 回测数据...")
        nd_sig = t4.calc_turtle_signals(nd_raw.copy(), N, M)
        nd_bt = t4.turtle_backtest(nd_sig)
        t4.export_signal_csv(nd_bt, "宁德时代", N, M)
    print("TASK4 全部完成！")

if __name__ == "__main__":
    print("=" * 50)
    print("批量生成回测数据")
    print("=" * 50)
    gen_task3_backtests()
    print()
    gen_task4_backtests()
    print("\n全部回测数据生成完毕！")
