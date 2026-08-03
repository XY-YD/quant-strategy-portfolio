#!/usr/bin/env python3
"""Rename non-ASCII image filenames to ASCII and update config.js references."""
import os
import re
import json

PORTFOLIO_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGES_DIR = os.path.join(PORTFOLIO_DIR, "images")

# Mapping: old filename -> new filename (per directory)
RENAME_MAP = {
    # task1
    "task1/宁德时代_收盘价曲线.png": "task1/ningde_close_price.png",
    # task2
    "task2/图_RSI.png": "task2/chart_rsi.png",
    "task2/图_KDJ.png": "task2/chart_kdj.png",
    "task2/图_布林带.png": "task2/chart_bollinger.png",
    "task2/图_四指标综合面板.png": "task2/chart_all_indicators.png",
    "task2/图_MACD.png": "task2/chart_macd.png",
    # task3
    "task3/图1_股价均线信号.png": "task3/fig1_price_ma_signal.png",
    "task3/图2_策略净值曲线.png": "task3/fig2_nav.png",
    "task3/图3_策略回撤曲线.png": "task3/fig3_drawdown.png",
    "task3/图4_综合面板.png": "task3/fig4_panel.png",
    "task3/图5_多参数对比.png": "task3/fig5_params_compare.png",
    "task3/图6_多股票对比.png": "task3/fig6_stocks_compare.png",
    "task3/图7_多股票指标柱状图.png": "task3/fig7_stocks_metrics.png",
    # task4
    "task4/图1_股价_唐奇安通道_信号.png": "task4/fig1_price_donchian_signal.png",
    "task4/图2_策略净值曲线.png": "task4/fig2_nav.png",
    "task4/图3_回撤曲线.png": "task4/fig3_drawdown.png",
    "task4/图4_综合面板.png": "task4/fig4_panel.png",
    "task4/图5_多参数对比.png": "task4/fig5_params_compare.png",
    "task4/图6_多股票对比.png": "task4/fig6_stocks_compare.png",
    "task4/图7_多股票指标柱状图.png": "task4/fig7_stocks_metrics.png",
    # task4_advanced
    "task4_advanced/图1_双系统通道_多空信号.png": "task4_advanced/fig1_dual_system_signal.png",
    "task4_advanced/图2_策略净值曲线.png": "task4_advanced/fig2_nav.png",
    "task4_advanced/图3_回撤曲线.png": "task4_advanced/fig3_drawdown.png",
    "task4_advanced/图4_综合面板.png": "task4_advanced/fig4_panel.png",
    "task4_advanced/图5_多参数对比.png": "task4_advanced/fig5_params_compare.png",
    "task4_advanced/图6_多股票对比.png": "task4_advanced/fig6_stocks_compare.png",
    "task4_advanced/图7_多股票指标柱状图.png": "task4_advanced/fig7_stocks_metrics.png",
    # task5
    "task5/confusion_matrix_股票收益数据.png": "task5/confusion_matrix_stock.png",
    "task5/roc_股票收益数据.png": "task5/roc_stock.png",
    "task5/metrics_乳腺癌数据.png": "task5/metrics_cancer.png",
    "task5/roc_乳腺癌数据.png": "task5/roc_cancer.png",
    "task5/confusion_matrix_乳腺癌数据.png": "task5/confusion_matrix_cancer.png",
    "task5/metrics_股票收益数据.png": "task5/metrics_stock.png",
}

# Step 1: Rename files
renamed = 0
errors = 0
for old_rel, new_rel in RENAME_MAP.items():
    old_path = os.path.join(IMAGES_DIR, old_rel)
    new_path = os.path.join(IMAGES_DIR, new_rel)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
        renamed += 1
        print(f"  Renamed: {old_rel} -> {new_rel}")
    else:
        # Check if already renamed
        if not os.path.exists(new_path):
            print(f"  MISSING: {old_rel}")
            errors += 1
        else:
            print(f"  Already renamed: {new_rel}")

print(f"\nRenamed {renamed} files, {errors} errors")

# Step 2: Update config.js
config_path = os.path.join(PORTFOLIO_DIR, "js", "config.js")
with open(config_path, "r", encoding="utf-8") as f:
    content = f.read()

for old_rel, new_rel in RENAME_MAP.items():
    old_ref = f"images/{old_rel}"
    new_ref = f"images/{new_rel}"
    if old_ref in content:
        content = content.replace(old_ref, new_ref)
        print(f"  Updated config.js: {old_ref} -> {new_ref}")

with open(config_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\nconfig.js updated!")

# Step 3: Verify no non-ASCII filenames remain
print("\n=== Remaining non-ASCII filenames ===")
found = False
for root, dirs, files in os.walk(IMAGES_DIR):
    for fname in files:
        try:
            fname.encode("ascii")
        except UnicodeEncodeError:
            print(f"  NON-ASCII: {os.path.relpath(os.path.join(root, fname), IMAGES_DIR)}")
            found = True
if not found:
    print("  None - all filenames are ASCII!")
