#!/usr/bin/env python3
"""
量化策略课程 — 数据更新工具
=============================
通过 Tushare API 获取最新日线数据，自动增量更新 CSV 并重新生成 JSON。

用法：
  python update_data.py                          # 更新宁德时代数据到最新交易日
  python update_data.py --code 600519            # 更新贵州茅台
  python update_data.py --code 300750,000001     # 批量更新多只股票
  python update_data.py --start 2025-01-01 --end 2026-08-03
  python update_data.py --code 300750 --output-dir TASK1  # 指定输出目录
  python update_data.py --rebuild                # 不拉新数据，仅重建 JSON
  python update_data.py --export-csv myfile.csv  # 导出为自定义文件名
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timedelta

try:
    from local_config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def safe_float(val, default=None):
    if val is None or val == "" or val == "nan" or val == "NaN":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def read_csv(path):
    """Read CSV with utf-8-sig encoding."""
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def write_csv(path, fieldnames, rows):
    """Write CSV with utf-8-sig encoding."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def get_last_date(csv_path):
    """Extract the latest date from a CSV file."""
    rows = read_csv(csv_path)
    if not rows:
        return None
    dates = [r.get("交易日期", "") for r in rows]
    dates = [d for d in dates if d]
    if not dates:
        return None
    return max(dates)


def fetch_tushare_daily(ts_code, start_date, end_date):
    """Fetch daily data from Tushare API.

    Returns list of dicts with keys matching the standard CSV format.
    """
    try:
        import tushare as ts
    except ImportError:
        print("错误: 请先安装 tushare SDK: pip install tushare")
        sys.exit(1)

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    start_str = start_date.replace("-", "") if start_date else None
    end_str = end_date.replace("-", "") if end_date else None

    print(f"  从 Tushare 拉取: {ts_code} | {start_str or '全部'} → {end_str or '最新'}")

    df = pro.daily(
        ts_code=ts_code,
        start_date=start_str,
        end_date=end_str,
        fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
    )

    if df is None or df.empty:
        print(f"  ⚠️  未获取到数据: {ts_code}")
        return []

    # Sort by date ascending (Tushare returns descending by default)
    df = df.sort_values("trade_date")

    rows = []
    for _, r in df.iterrows():
        date_str = str(r["trade_date"])
        # Format: YYYYMMDD → YYYY-MM-DD
        date_formatted = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
        row = {
            "股票代码": r["ts_code"],
            "交易日期": date_formatted,
            "开盘价": f"{r['open']:.2f}",
            "最高价": f"{r['high']:.2f}",
            "最低价": f"{r['low']:.2f}",
            "收盘价": f"{r['close']:.2f}",
            "前收盘价": f"{r['pre_close']:.2f}",
            "涨跌额": f"{r['change']:.2f}",
            "涨跌幅(%)": f"{r['pct_chg']:.4f}",
            "成交量(手)": f"{r['vol']:.0f}",
            "成交额(千元)": f"{r['amount']:.2f}",
        }
        rows.append(row)

    print(f"  ✅ 获取 {len(rows)} 条记录 ({rows[0]['交易日期']} → {rows[-1]['交易日期']})")
    return rows


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


def code_to_name(code):
    """Stock code → Chinese name mapping (common stocks)."""
    name_map = {
        "000001": "平安银行",
        "000333": "美的集团",
        "000858": "五粮液",
        "300750": "宁德时代",
        "600036": "招商银行",
        "600519": "贵州茅台",
        "601318": "中国平安",
        "601857": "中国石油",
    }
    return name_map.get(str(code).strip().zfill(6), f"股票{code}")


def update_single_stock(ts_code, code_short, start_date=None, end_date=None,
                         prefix=None, output_dir=None):
    """Update data for a single stock.

    Returns: (csv_path, is_new, row_count) or (None, False, 0) on failure.
    """
    stock_name = code_to_name(code_short)

    # Determine output file
    if output_dir:
        out_dir = output_dir
    else:
        out_dir = os.path.join(BASE_DIR, "TASK1")
    os.makedirs(out_dir, exist_ok=True)

    if prefix:
        filename = f"{prefix}_{code_short}_日线数据.csv"
    else:
        filename = f"{stock_name}_{code_short}_日线数据.csv"

    csv_path = os.path.join(out_dir, filename)

    # Check existing data
    last_date = get_last_date(csv_path)
    existing_rows = read_csv(csv_path)

    # Determine date range
    today_str = datetime.now().strftime("%Y-%m-%d")

    if start_date and end_date:
        fetch_start = start_date
        fetch_end = end_date
    elif last_date:
        # Incremental update: fetch from the day after last_date
        last_dt = datetime.strptime(last_date[:10], "%Y-%m-%d")
        fetch_start = (last_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        fetch_end = today_str
        print(f"  已有数据截止: {last_date}，增量拉取 {fetch_start} → {fetch_end}")
    else:
        # No existing data, fetch all
        fetch_start = "2019-01-01"
        fetch_end = today_str
        print(f"  无已有数据，全量拉取 {fetch_start} → {fetch_end}")

    # Fetch new data
    new_rows = fetch_tushare_daily(ts_code, fetch_start, fetch_end)

    if not new_rows and fetch_start == start_date:
        print(f"  ⚠️  指定区间 {start_date}~{end_date} 无交易数据")
        return csv_path, False, len(existing_rows)

    if not new_rows and fetch_start:
        print(f"  ℹ️  已是最新，无需更新")
        return csv_path, False, len(existing_rows)

    # Merge: existing rows + new rows, deduplicate by date
    existing_dates = set(r.get("交易日期", "") for r in existing_rows)
    all_rows = list(existing_rows)
    added = 0
    for r in new_rows:
        if r.get("交易日期", "") not in existing_dates:
            all_rows.append(r)
            existing_dates.add(r.get("交易日期", ""))
            added += 1

    # Sort by date
    all_rows.sort(key=lambda x: x.get("交易日期", ""))

    # Write CSV
    fieldnames = [
        "股票代码", "交易日期", "开盘价", "最高价", "最低价", "收盘价",
        "前收盘价", "涨跌额", "涨跌幅(%)", "成交量(手)", "成交额(千元)",
    ]
    write_csv(csv_path, fieldnames, all_rows)
    print(f"  📁 保存: {csv_path} ({added} 条新增, 总计 {len(all_rows)} 条)")
    return csv_path, added > 0, len(all_rows)


def run_convert_data():
    """Re-run the portfolio data converter."""
    convert_script = os.path.join(BASE_DIR, "portfolio", "convert_data.py")
    if os.path.exists(convert_script):
        print(f"\n🔄 重新生成 portfolio JSON 数据...")
        import subprocess
        r = subprocess.run(
            [sys.executable, convert_script],
            cwd=os.path.join(BASE_DIR, "portfolio"),
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            print("  ✅ JSON 数据更新成功")
        else:
            print(f"  ⚠️  转换脚本出错:\n{r.stderr}")
            if r.stdout:
                print(r.stdout)
    else:
        print("  ⚠️  convert_data.py 未找到，跳过 JSON 重建")


def update_long_period(code_short, ts_code, start_date=None, end_date=None):
    """Update the long-period CSV used by TASK7."""
    if start_date is None:
        start_date = "2019-01-01"
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")

    out_dir = os.path.join(BASE_DIR, "TASK7")
    os.makedirs(out_dir, exist_ok=True)

    stock_name = code_to_name(code_short)
    stock_filename = f"{stock_name}_{code_short}_日线_2019_2026.csv"

    # Also need to update 沪深300 index
    index_code = "000300"
    index_filename = f"沪深300_{index_code}_日线_2019_2026.csv"

    print(f"\n📊 更新 TASK7 长周期数据...")

    # Stock
    print(f"  [{stock_name}]")
    new_rows = fetch_tushare_daily(ts_code, start_date, end_date)
    if new_rows:
        # TASK7 uses YYYYMMDD date format, not YYYY-MM-DD
        for r in new_rows:
            r["交易日期"] = r["交易日期"].replace("-", "")
        fieldnames = [
            "股票代码", "交易日期", "开盘价", "最高价", "最低价", "收盘价",
            "前收盘价", "涨跌额", "涨跌幅(%)", "成交量(手)", "成交额(千元)",
        ]
        stock_path = os.path.join(out_dir, stock_filename)
        write_csv(stock_path, fieldnames, new_rows)
        print(f"  📁 保存: {stock_path} ({len(new_rows)} 条)")

    # Index
    print(f"  [沪深300]")
    idx_rows = fetch_tushare_daily(f"{index_code}.SH", start_date, end_date)
    if idx_rows:
        for r in idx_rows:
            r["交易日期"] = r["交易日期"].replace("-", "")
        idx_path = os.path.join(out_dir, index_filename)
        write_csv(idx_path, fieldnames, idx_rows)
        print(f"  📁 保存: {idx_path} ({len(idx_rows)} 条)")


def export_csv(codes, output_path, start_date, end_date):
    """Export single or multiple stocks to a combined CSV file."""
    all_rows = []
    for code in codes:
        ts_code = code_to_ts_code(code)
        rows = fetch_tushare_daily(ts_code, start_date, end_date)
        all_rows.extend(rows)
    if all_rows:
        fieldnames = [
            "股票代码", "交易日期", "开盘价", "最高价", "最低价", "收盘价",
            "前收盘价", "涨跌额", "涨跌幅(%)", "成交量(手)", "成交额(千元)",
        ]
        write_csv(output_path, fieldnames, all_rows)
        print(f"📁 导出: {output_path} ({len(all_rows)} 条)")
    else:
        print("⚠️  未获取到任何数据")


def main():
    parser = argparse.ArgumentParser(
        description="量化策略课程 — Tushare 数据更新工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python update_data.py                          # 更新宁德时代到最新
  python update_data.py --code 600519            # 更新贵州茅台
  python update_data.py --code 300750,000001     # 批量更新
  python update_data.py --start 2025-01-01       # 指定起始日期
  python update_data.py --rebuild                # 仅重建JSON
  python update_data.py --code 300750 --long-period  # 更新TASK7长周期数据
  python update_data.py --export-csv mydata.csv --code 300750,600519
        """,
    )
    parser.add_argument("--code", default="300750",
                        help="股票代码，逗号分隔 (默认: 300750 宁德时代)")
    parser.add_argument("--start", default=None,
                        help="起始日期 YYYY-MM-DD (默认: 自动检测)")
    parser.add_argument("--end", default=None,
                        help="结束日期 YYYY-MM-DD (默认: 今天)")
    parser.add_argument("--output-dir", default=None,
                        help="CSV 输出目录 (默认: TASK1)")
    parser.add_argument("--prefix", default=None,
                        help="CSV 文件名前缀 (默认: 股票名称)")
    parser.add_argument("--rebuild", action="store_true",
                        help="不拉取新数据，仅重建 portfolio JSON")
    parser.add_argument("--no-convert", action="store_true",
                        help="跳过 convert_data.py，不重建 JSON")
    parser.add_argument("--long-period", action="store_true",
                        help="同时更新 TASK7 长周期数据 (2019年起)")
    parser.add_argument("--export-csv", default=None,
                        help="导出为自定义 CSV 文件路径")

    args = parser.parse_args()

    print("=" * 60)
    print("📈 量化策略课程 — 数据更新工具")
    print("=" * 60)

    # If rebuild only
    if args.rebuild:
        run_convert_data()
        print("\n✅ 重建完成")
        return

    # If export only
    if args.export_csv:
        codes = [c.strip() for c in args.code.split(",")]
        export_csv(codes, args.export_csv, args.start, args.end)
        return

    # Update stock data
    codes = [c.strip() for c in args.code.split(",")]
    updated = False

    for code_short in codes:
        ts_code = code_to_ts_code(code_short)
        stock_name = code_to_name(code_short)
        print(f"\n🔍 {stock_name} ({ts_code}):")
        csv_path, is_new, count = update_single_stock(
            ts_code, code_short,
            start_date=args.start, end_date=args.end,
            prefix=args.prefix, output_dir=args.output_dir,
        )
        if is_new:
            updated = True

    # Update long period for TASK7
    if args.long_period:
        for code_short in codes:
            ts_code = code_to_ts_code(code_short)
            update_long_period(code_short, ts_code, args.start, args.end)
        updated = True

    # Re-run converter
    if not args.no_convert and updated:
        run_convert_data()

    print("\n" + "=" * 60)
    print("✅ 数据更新完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
