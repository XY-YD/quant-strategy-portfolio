#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TASK3 数据获取脚本 v3
===================
直接通过 urllib 调用 Tushare HTTP API 获取多股票日线数据，
转换并保存为标准格式 CSV，与 TASK1 宁德时代数据格式一致。

解决了 tushare Python 库的缓存和代理问题。
"""

import os
import json
import urllib.request
import ssl
import sys

# ===== 环境配置 =====
# certifi 证书路径（解决 Anaconda Python SSL 问题）
import certifi
CERT_PATH = certifi.where()
os.environ["SSL_CERT_FILE"] = CERT_PATH
os.environ["REQUESTS_CA_BUNDLE"] = CERT_PATH

# matplotlib 缓存目录（避免权限问题）
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_cache"

# ===== Tushare API 配置 =====
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.join(_os.path.dirname(__file__), "..", ".."))
try:
    from local_config import TUSHARE_TOKEN as TOKEN
except ImportError:
    TOKEN = _os.environ.get("TUSHARE_TOKEN", "")
API_URL = "https://api.tushare.pro"
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

# 请求字段列表
FIELDS = "ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount"


def fetch_daily(ts_code: str, name: str) -> list:
    """通过 Tushare HTTP API 获取日线数据"""
    print(f"正在获取 {name}({ts_code}) ...")
    
    payload = json.dumps({
        "api_name": "daily",
        "token": TOKEN,
        "params": {
            "ts_code": ts_code,
            "start_date": START_DATE,
            "end_date": END_DATE,
        },
        "fields": FIELDS,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    
    # 使用 certifi 证书直连（无需代理）
    ctx = ssl.create_default_context(cafile=CERT_PATH)
    
    try:
        resp = urllib.request.urlopen(req, timeout=30, context=ctx)
        result = json.loads(resp.read().decode("utf-8"))
        
        if result.get("code") != 0:
            print(f"  [错误] API 返回: {result}")
            return []
        
        data = result.get("data", {}).get("items", [])
        fields = result.get("data", {}).get("fields", [])
        print(f"  获取 {len(data)} 条记录")
        return data, fields
    
    except Exception as e:
        print(f"  [错误] {type(e).__name__}: {str(e)[:200]}")
        return [], []


def save_to_csv(ts_code: str, name: str, data: list, api_fields: list) -> None:
    """将 API 返回数据转换为标准 CSV"""
    if not data:
        return
    
    # 构建 DataFrame
    import pandas as pd
    df = pd.DataFrame(data, columns=api_fields)
    
    # 列映射
    df = df.rename(columns=COLUMN_MAP)
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
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    success = True
    for ts_code, name in STOCKS:
        result = fetch_daily(ts_code, name)
        if isinstance(result, tuple) and len(result) == 2:
            data, fields = result
            if data:
                save_to_csv(ts_code, name, data, fields)
            else:
                success = False
        else:
            success = False
    
    if success:
        print("\n全部获取并保存完成！")
    else:
        print("\n部分数据获取失败，请检查 API 限频或网络问题。")


if __name__ == "__main__":
    main()
