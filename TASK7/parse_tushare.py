#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 Tushare MCP 返回的原始 JSON 文件，转为课程标准 CSV。"""
import json, os

BASE = "/Users/wangyanfen/Desktop/量化策略课程/TASK7"
RESULT_DIR = "/Users/wangyanfen/.workbuddy/projects/Users-wangyanfen-Desktop-量化策略课程/f25ee690-846b-4b82-b636-8a5fe5f50463/tool-results"

STOCK_FILE = os.path.join(RESULT_DIR, "mcp-connector-proxy-tushareMcp_daily-1784950997752-b398e7.txt")
IDX_FILE = os.path.join(RESULT_DIR, "mcp-connector-proxy-tushareMcp_index_daily-1784950997876-3dd7ac.txt")

def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save(df_rows, cols, out_path):
    import csv
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for r in df_rows:
            w.writerow(r)
    print(f"  保存 {out_path}: {len(df_rows)} 行")

# ---- 股票 ----
stock = load(STOCK_FILE)
stock_sorted = sorted(stock, key=lambda x: x["trade_date"])
stock_rows = []
for r in stock_sorted:
    stock_rows.append([
        r["trade_date"], r["open"], r["high"], r["low"], r["close"],
        r["pre_close"], r["change"], r["pct_chg"], r["vol"], r["amount"]
    ])
stock_cols = ["交易日期","开盘价","最高价","最低价","收盘价","前收盘价","涨跌额","涨跌幅(%)","成交量(手)","成交额(千元)"]
save(stock_rows, stock_cols, os.path.join(BASE, "宁德时代_300750_日线_2019_2026.csv"))
print(f"  股票日期范围: {stock_sorted[0]['trade_date']} ~ {stock_sorted[-1]['trade_date']}")

# ---- 指数 ----
idx = load(IDX_FILE)
idx_sorted = sorted(idx, key=lambda x: x["trade_date"])
idx_rows = []
for r in idx_sorted:
    idx_rows.append([
        r["trade_date"], r["open"], r["high"], r["low"], r["close"],
        r["pre_close"], r["change"], r["pct_chg"], r["vol"], r["amount"]
    ])
idx_cols = ["交易日期","开盘价","最高价","最低价","收盘价","前收盘价","涨跌额","涨跌幅(%)","成交量(手)","成交额(千元)"]
save(idx_rows, idx_cols, os.path.join(BASE, "沪深300_000300_日线_2019_2026.csv"))
print(f"  指数日期范围: {idx_sorted[0]['trade_date']} ~ {idx_sorted[-1]['trade_date']}")
