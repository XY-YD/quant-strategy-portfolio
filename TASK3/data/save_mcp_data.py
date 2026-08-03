#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK3 数据保存脚本
==================
将已通过 Tushare MCP 获取的 JSON 数据转换为标准格式 CSV，
字段与 TASK1 的宁德时代数据保持一致。

数据来源：mcp__tushareMcp__daily 返回的 JSON
手动粘贴到下方字典中，然后运行本脚本转换保存。

用法：python save_mcp_data.py
"""

import os
import json
import pandas as pd

OUTPUT_DIR = "/Users/wangyanfen/Desktop/量化策略课程/TASK3/data"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# tushare 字段 -> 标准列名 映射
COLUMN_MAP = {
    "ts_code": "股票代码",
    "trade_date": "交易日期",
    "open": "开盘价",
    "high": "最高价",
    "low": "最低价",
    "close": "收盘价",
    "pre_close": "前收盘价",
    "change": "涨跌额",
    "pct_chg": "涨跌幅(%)",
    "vol": "成交量(手)",
    "amount": "成交额(千元)",
}

# ===== 已获取的数据（来自 Tushare MCP） =====
# 数据存放在同目录的 JSON 文件中
DATA_FILES = {
    "000001.SZ": "pingan_bank.json",
    "600519.SH": "maotai.json",
    "000858.SZ": "wuliangye.json",
}

STOCK_NAMES = {
    "000001.SZ": "平安银行",
    "600519.SH": "贵州茅台",
    "000858.SZ": "五粮液",
}


def convert_json_to_csv(ts_code: str, json_file: str) -> None:
    """读取 JSON 文件，转换为标准 CSV"""
    name = STOCK_NAMES[ts_code]
    json_path = os.path.join(OUTPUT_DIR, json_file)
    
    if not os.path.exists(json_path):
        print(f"  [跳过] {json_path} 不存在，请先获取数据")
        return
    
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    df = pd.DataFrame(data)
    # 列映射
    df = df.rename(columns=COLUMN_MAP)
    # 仅保留标准列
    std_cols = list(COLUMN_MAP.values())
    df = df[[c for c in std_cols if c in df.columns]]
    # 交易日期 YYYYMMDD -> YYYY-MM-DD
    df["交易日期"] = df["交易日期"].astype(str).apply(
        lambda x: f"{x[:4]}-{x[4:6]}-{x[6:8]}"
    )
    # 按日期升序排序
    df = df.sort_values("交易日期").reset_index(drop=True)
    
    out_path = os.path.join(OUTPUT_DIR, f"{name}_{ts_code}_日线数据.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {out_path}（{len(df)} 行，区间 {df['交易日期'].iloc[0]} ~ {df['交易日期'].iloc[-1]}）")


def main():
    print("开始转换 MCP 数据为标准 CSV ...")
    for ts_code, json_file in DATA_FILES.items():
        convert_json_to_csv(ts_code, json_file)
    print("全部转换完成。")


if __name__ == "__main__":
    main()
