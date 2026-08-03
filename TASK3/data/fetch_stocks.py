#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK3 数据获取脚本
==================
通过 tushare 获取多股票日线数据，统一保存为标准格式 CSV，
字段与 TASK1 的宁德时代数据保持一致。

股票列表（与宁德时代相同区间 2025-07-04 ~ 2026-07-03）：
- 000001.SZ 平安银行（银行 / 低波动价值股）
- 600519.SH 贵州茅台（白酒 / 蓝筹消费股）
- 000858.SZ 五粮液（白酒 / 成长消费股）
"""

import os
import sys

# tushare 默认会把 token 缓存写到用户主目录（~/tk.csv），
# 在受限环境下无写权限，这里把 HOME 临时重定向到可写目录。
_TUSHARE_HOME = "/tmp/tushare_home"
os.makedirs(_TUSHARE_HOME, exist_ok=True)
os.environ["HOME"] = _TUSHARE_HOME

import tushare as ts
import pandas as pd

# ===== 配置 =====
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", ".."))
try:
    from local_config import TUSHARE_TOKEN as TOKEN
except ImportError:
    TOKEN = _os.environ.get("TUSHARE_TOKEN", "")
START_DATE = "20250704"
END_DATE = "20260703"
OUTPUT_DIR = "/Users/wangyanfen/Desktop/量化策略课程/TASK3/data"

# 待获取股票：(代码, 名称)
STOCKS = [
    ("000001.SZ", "平安银行"),
    ("600519.SH", "贵州茅台"),
    ("000858.SZ", "五粮液"),
]

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


def fetch_one(ts_code: str, name: str) -> None:
    """获取单只股票并保存为标准格式 CSV"""
    print(f"正在获取 {name}({ts_code}) ...")
    df = ts.pro_api().daily(
        ts_code=ts_code,
        start_date=START_DATE,
        end_date=END_DATE,
    )
    if df is None or df.empty:
        print(f"  [警告] {name} 未返回数据")
        return

    # 列映射
    df = df.rename(columns=COLUMN_MAP)
    # 仅保留标准列
    std_cols = list(COLUMN_MAP.values())
    df = df[[c for c in std_cols if c in df.columns]]
    # 交易日期 YYYYMMDD -> YYYY-MM-DD
    df["交易日期"] = df["交易日期"].astype(str).str.slice(0, 4) + "-" + \
                     df["交易日期"].astype(str).str.slice(4, 6) + "-" + \
                     df["交易日期"].astype(str).str.slice(6, 8)
    # 按日期升序排序
    df = df.sort_values("交易日期").reset_index(drop=True)

    out_path = os.path.join(OUTPUT_DIR, f"{name}_{ts_code}_日线数据.csv")
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"  已保存 {out_path}（{len(df)} 行，区间 {df['交易日期'].iloc[0]} ~ {df['交易日期'].iloc[-1]}）")


def main():
    ts.set_token(TOKEN)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for code, name in STOCKS:
        fetch_one(code, name)
    print("全部获取完成。")


if __name__ == "__main__":
    main()
