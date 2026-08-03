#!/usr/bin/env python3
"""
量化策略课程 — 本地回测 API 服务
==================================
轻量级 Flask HTTP 服务，接收前端请求执行回测并返回 JSON 结果。

启动：
  python backtest_server.py                 # 默认端口 8081
  python backtest_server.py --port 5000     # 自定义端口
  python backtest_server.py --host 0.0.0.0  # 允许局域网访问

API 接口：
  GET  /api/health                          # 健康检查
  POST /api/backtest                        # 执行回测
  GET  /api/stocks?q=宁                     # 股票搜索
  POST /api/stock-data                      # 获取股票日线数据
  GET  /api/recent/<code>                   # 获取最近一次回测缓存
"""

import json
import math
import os
import sys
import traceback
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add TASK dirs to path for strategy imports
for d in ["TASK3", "TASK4", "TASK7"]:
    p = os.path.join(BASE_DIR, d)
    if p not in sys.path:
        sys.path.insert(0, p)

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Allow requests from any origin

try:
    from local_config import TUSHARE_TOKEN
except ImportError:
    TUSHARE_TOKEN = os.environ.get("TUSHARE_TOKEN", "")

# In-memory cache for recent backtest results
_backtest_cache = {}


# ── Utility Functions ─────────────────────────────────────────

def code_to_ts_code(code):
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


def rows_to_dataframe(rows):
    import pandas as pd
    df = pd.DataFrame(rows)
    for col in ["开盘价", "收盘价", "最高价", "最低价", "前收盘价", "涨跌额", "涨跌幅(%)", "成交量(手)", "成交额(千元)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "交易日期" in df.columns:
        df["交易日期"] = pd.to_datetime(df["交易日期"], errors="coerce")
        df = df.sort_values("交易日期")
    return df


def fetch_tushare(ts_code, start_date, end_date):
    """Fetch stock daily data from Tushare."""
    try:
        import tushare as ts
    except ImportError:
        raise RuntimeError("tushare not installed. Run: pip install tushare")

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    start_s = start_date.replace("-", "")
    end_s = end_date.replace("-", "")

    df = pro.daily(
        ts_code=ts_code, start_date=start_s, end_date=end_s,
        fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
    )
    if df is None or df.empty:
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


def search_stocks(keyword):
    """Search stocks by keyword using Tushare."""
    try:
        import tushare as ts
    except ImportError:
        return []

    ts.set_token(TUSHARE_TOKEN)
    pro = ts.pro_api()

    # Try code first
    if keyword.isdigit() and len(keyword) == 6:
        df = pro.stock_basic(ts_code=code_to_ts_code(keyword))
    else:
        df = pro.stock_basic(name=keyword)

    if df is None or df.empty:
        return []

    results = []
    for _, r in df.head(20).iterrows():
        results.append({
            "ts_code": r["ts_code"],
            "symbol": r["symbol"],
            "name": r["name"],
            "area": r.get("area", ""),
            "industry": r.get("industry", ""),
            "list_date": r.get("list_date", ""),
        })
    return results


# ── Backtest Integration ──────────────────────────────────────

def run_dual_ma(rows, short, long, capital=100000.0):
    """Run dual MA backtest via TASK3 module."""
    import importlib.util

    task3_path = os.path.join(BASE_DIR, "TASK3", "task3_strategy.py")
    if not os.path.exists(task3_path):
        # Use inline fallback
        return _run_dual_ma_inline(rows, short, long, capital)

    spec = importlib.util.spec_from_file_location("task3_strategy", task3_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import pandas as pd
    df = pd.DataFrame(rows)
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期")
    for col in ["收盘价", "开盘价", "最高价", "最低价"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    sig_df = mod.calc_ma_signals(df.copy(), short, long)
    bt_df = mod.backtest(sig_df.copy(), capital)
    metrics = mod.calc_metrics(bt_df)

    return bt_df, metrics


def _run_dual_ma_inline(rows, short, long, capital=100000.0):
    """Inline dual MA implementation (no TASK3 dependency)."""
    import pandas as pd
    import numpy as np

    df = pd.DataFrame(rows)
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期")
    df["收盘价"] = pd.to_numeric(df["收盘价"], errors="coerce")

    df[f"MA{short}"] = df["收盘价"].rolling(short).mean()
    df[f"MA{long}"] = df["收盘价"].rolling(long).mean()
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
    peak = df["portfolio_value"].expanding().max()
    df["drawdown"] = (df["portfolio_value"] - peak) / peak

    total_return = (df["portfolio_value"].iloc[-1] / capital - 1) * 100
    years = (df["交易日期"].iloc[-1] - df["交易日期"].iloc[0]).days / 365.25
    annual_return = ((1 + total_return / 100) ** (1 / max(years, 0.1)) - 1) * 100
    mdd = df["drawdown"].min() * 100
    mean_ret = df["strategy_return"].mean()
    sharpe = np.sqrt(252) * mean_ret / max(df["strategy_return"].std(), 1e-8)

    metrics = {
        "累计回报": round(total_return, 2),
        "年化收���率": round(annual_return, 2),
        "最大回撤MDD": round(mdd, 2),
        "夏普比率": round(sharpe, 2),
        "买入次数": int((df["signal"].diff() > 0).sum()),
        "卖出次数": int((df["signal"].diff() < 0).sum()),
    }
    return df, metrics


def run_turtle(rows, N, M, stop_mult=2.0, capital=100000.0):
    """Run turtle backtest."""
    import pandas as pd
    import numpy as np

    df = pd.DataFrame(rows)
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期")
    for col in ["开盘价", "收盘价", "最高价", "最低价"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Donchian
    df["upper"] = df["最高价"].rolling(N).max()
    df["lower"] = df["最低价"].rolling(M).min()

    # ATR
    df["H_L"] = df["最高价"] - df["最低价"]
    df["H_Cp"] = abs(df["最高价"] - df["收盘价"].shift(1))
    df["L_Cp"] = abs(df["最低价"] - df["收盘价"].shift(1))
    df["TR"] = df[["H_L", "H_Cp", "L_Cp"]].max(axis=1)
    df["ATR"] = df["TR"].rolling(max(N, 20)).mean()

    df["signal"] = 0
    df["exit_reason"] = ""
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
            elif pd.notna(c["lower"]) and c["收盘价"] < df.iloc[i - 1]["lower"]:
                pos = 1
                entry = c["收盘价"]
                df.iloc[i, df.columns.get_loc("signal")] = 1
        elif pos == 1:
            stop_price = entry - stop_mult * atr
            if c["最低价"] <= stop_price:
                pos = 0
                df.iloc[i, df.columns.get_loc("signal")] = -1
                df.iloc[i, df.columns.get_loc("exit_reason")] = "止损"
            elif pd.notna(c["lower"]) and c["收盘价"] < c["lower"]:
                pos = 0
                df.iloc[i, df.columns.get_loc("signal")] = -1
                df.iloc[i, df.columns.get_loc("exit_reason")] = "破低"

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
    sharpe = np.sqrt(252) * mean_ret / max(df["strategy_return"].std(), 1e-8)

    metrics = {
        "累计回报": round(total_return, 2),
        "年化收益率": round(annual_return, 2),
        "最大回撤MDD": round(mdd, 2),
        "夏普比率": round(sharpe, 2),
        "买入次数": int((df["signal"] == 1).sum()),
        "卖出次数": int((df["signal"] == -1).sum()),
        "止损次数": int((df["exit_reason"] == "止损").sum()),
        "破低次数": int((df["exit_reason"] == "破低").sum()),
    }
    return df, metrics


def sanitize_for_json(obj):
    """Recursively replace NaN and Infinity with None (→ null in JSON)."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    return obj


def build_response(df, metrics, code, strategy, params, request_time):
    """Build JSON response from backtest result."""
    # Serialize time series
    dates = df["交易日期"].dt.strftime("%Y-%m-%d").tolist() if "交易日期" in df.columns else []
    close = df["收盘价"].fillna(0).tolist() if "收盘价" in df.columns else []
    nav = df["portfolio_value"].fillna(0).tolist() if "portfolio_value" in df.columns else []
    drawdown = df["drawdown"].fillna(0).tolist() if "drawdown" in df.columns else []
    signals = df["signal"].fillna(0).astype(int).tolist() if "signal" in df.columns else []

    # Extra series
    ma_short_vals = None
    ma_long_vals = None
    for col in df.columns:
        if col.startswith("MA") and col[2:].isdigit():
            n = int(col[2:])
            if n < 50:
                ma_short_vals = df[col].fillna(None).tolist()
            else:
                ma_long_vals = df[col].fillna(None).tolist()

    upper_vals = df["upper"].fillna(None).tolist() if "upper" in df.columns else None
    lower_vals = df["lower"].fillna(None).tolist() if "lower" in df.columns else None
    atr_vals = df["ATR"].fillna(None).tolist() if "ATR" in df.columns else None

    response = {
        "success": True,
        "code": code,
        "strategy": strategy,
        "params": params,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_time_ms": request_time,
        "data": {
            "dates": dates,
            "close": close,
            "nav": nav,
            "drawdown": drawdown,
            "signals": signals,
        },
        "indicators": {},
        "metrics": metrics,
    }

    if ma_short_vals:
        response["indicators"]["ma_short"] = ma_short_vals
    if ma_long_vals:
        response["indicators"]["ma_long"] = ma_long_vals
    if upper_vals:
        response["indicators"]["upper"] = upper_vals
    if lower_vals:
        response["indicators"]["lower"] = lower_vals
    if atr_vals:
        response["indicators"]["atr"] = atr_vals

    return sanitize_for_json(response)


# ── API Routes ────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "service": "backtest-server",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
    })


@app.route("/api/backtest", methods=["POST"])
def backtest():
    """Run a strategy backtest.

    Request body:
      {
        "code": "300750",
        "strategy": "dual-ma",
        "params": {"short": 5, "long": 15},
        "start_date": "2022-01-01",
        "end_date": "2026-08-03",
        "capital": 100000
      }

    Response:
      {
        "success": true,
        "data": { "dates": [...], "close": [...], "nav": [...], ... },
        "metrics": { ... },
        "indicators": { ... }
      }
    """
    import time
    t0 = time.time()

    try:
        body = request.get_json()
        if not body:
            return jsonify({"success": False, "error": "Request body required"}), 400

        code = body.get("code", "300750")
        strategy = body.get("strategy", "dual-ma")
        params = body.get("params", {})
        start_date = body.get("start_date", "2020-01-01")
        end_date = body.get("end_date", datetime.now().strftime("%Y-%m-%d"))
        capital = float(body.get("capital", 100000))

        # Validate
        if strategy not in ("dual-ma", "turtle"):
            return jsonify({"success": False, "error": f"Unknown strategy: {strategy}"}), 400

        ts_code = code_to_ts_code(code)

        # Fetch data
        rows = fetch_tushare(ts_code, start_date, end_date)
        if not rows:
            return jsonify({"success": False, "error": f"No data for {ts_code}"}), 404

        # Run strategy
        if strategy == "dual-ma":
            short = int(params.get("short", 5))
            long = int(params.get("long", 15))
            bt_df, metrics = run_dual_ma(rows, short, long, capital)
            params_str = f"short={short},long={long}"
        else:
            N = int(params.get("N", 20))
            M = int(params.get("M", 10))
            stop = float(params.get("stop_mult", 2.0))
            bt_df, metrics = run_turtle(rows, N, M, stop, capital)
            params_str = f"N={N},M={M},stop={stop}"

        elapsed = round((time.time() - t0) * 1000, 1)

        response = build_response(bt_df, metrics, code, strategy, params_str, elapsed)

        # Cache
        cache_key = f"{code}_{strategy}"
        _backtest_cache[cache_key] = response

        return jsonify(response)

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
        }), 500


@app.route("/api/stocks", methods=["GET"])
def search_stocks_handler():
    """Search stocks by keyword."""
    q = request.args.get("q", "")
    if not q or len(q) < 1:
        return jsonify({"success": False, "error": "Query required"}), 400

    results = search_stocks(q)
    return jsonify({"success": True, "count": len(results), "results": results})


@app.route("/api/stock-data", methods=["POST"])
def stock_data():
    """Fetch stock daily data without backtesting.

    Request body:
      { "code": "300750", "start_date": "...", "end_date": "..." }
    """
    import time
    t0 = time.time()

    try:
        body = request.get_json()
        if not body:
            return jsonify({"success": False, "error": "Request body required"}), 400

        code = body.get("code", "300750")
        start_date = body.get("start_date", "2020-01-01")
        end_date = body.get("end_date", datetime.now().strftime("%Y-%m-%d"))

        ts_code = code_to_ts_code(code)
        rows = fetch_tushare(ts_code, start_date, end_date)

        if not rows:
            return jsonify({"success": False, "error": "No data"}), 404

        elapsed = round((time.time() - t0) * 1000, 1)

        # Extract basic arrays
        dates = [r["交易日期"] for r in rows]
        close = [r["收盘价"] for r in rows]
        open_p = [r["开盘价"] for r in rows]
        high = [r["最高价"] for r in rows]
        low = [r["最低价"] for r in rows]
        volume = [r["成交量(手)"] for r in rows]

        return jsonify({
            "success": True,
            "code": code,
            "count": len(rows),
            "request_time_ms": elapsed,
            "data": {
                "dates": dates,
                "close": close,
                "open": open_p,
                "high": high,
                "low": low,
                "volume": volume,
            },
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/update-data", methods=["POST"])
def update_data():
    """Update stock daily data from Tushare and rebuild JSONs.

    Request body:
      { "code": "300750" }

    Response:
      { "success": true, "new_rows": 3, "latest_date": "2026-08-03",
        "csv_path": "...", "json_rebuilt": true }
    """
    import csv as csv_mod
    import subprocess

    try:
        body = request.get_json() or {}
        code = str(body.get("code", "300750")).strip().zfill(6)
    except Exception:
        code = "300750"

    ts_code = code_to_ts_code(code)
    today = datetime.now().strftime("%Y-%m-%d")

    # Determine CSV path
    csv_path = None
    for task_dir in ["TASK1", "TASK2", "TASK3", "TASK4", "TASK7"]:
        import glob as g2
        pattern = os.path.join(BASE_DIR, task_dir, f"*{code}*.csv")
        matches = g2.glob(pattern)
        if matches:
            csv_path = matches[0]
            break

    # Read existing CSV to find last date
    last_date = None
    existing_rows = []
    if csv_path and os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv_mod.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                existing_rows.append(row)
        if existing_rows:
            # Find max date
            date_col = None
            for col in ["交易日期", "trade_date", "日期"]:
                if col in (fieldnames or []):
                    date_col = col
                    break
            if date_col:
                dates = [r.get(date_col, "") for r in existing_rows]
                dates = [d for d in dates if d and len(d) >= 10]
                if dates:
                    last_date = max(dates)[:10]

    # If no CSV found, create one in TASK1
    if not csv_path:
        task1_dir = os.path.join(BASE_DIR, "TASK1")
        os.makedirs(task1_dir, exist_ok=True)
        csv_path = os.path.join(task1_dir, f"股票_{code}_日线数据.csv")
        fieldnames = ["股票代码", "交易日期", "开盘价", "最高价", "最低价", "收盘价",
                      "前收盘价", "涨跌额", "涨跌幅(%)", "成交量(手)", "成交额(千元)"]
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv_mod.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        last_date = None
        existing_rows = []

    # Fetch new data from Tushare
    start_date = "2020-01-01"
    if last_date:
        # Start from the day after last_date
        from datetime import timedelta
        ld = datetime.strptime(last_date, "%Y-%m-%d")
        start_date = (ld + timedelta(days=1)).strftime("%Y-%m-%d")

    if start_date > today:
        return jsonify({
            "success": True, "new_rows": 0,
            "latest_date": last_date,
            "message": f"数据已是最新 ({last_date})",
            "csv_path": csv_path,
            "json_rebuilt": False,
        })

    try:
        new_rows = fetch_tushare(ts_code, start_date, today)
    except Exception as e:
        return jsonify({"success": False, "error": f"Tushare API 失败: {str(e)}"}), 502

    if not new_rows:
        return jsonify({
            "success": True, "new_rows": 0,
            "latest_date": last_date or "无数据",
            "message": "当前已是最近交易日，暂无新数据",
            "csv_path": csv_path,
            "json_rebuilt": False,
        })

    # Append new rows to CSV
    with open(csv_path, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        for r in new_rows:
            writer.writerow(r)

    # Find latest date in new data
    new_dates = [r.get("交易日期", "")[:10] for r in new_rows]
    latest_date = max(new_dates) if new_dates else today

    # Rebuild JSONs
    json_rebuilt = False
    try:
        sys_path_saved = list(sys.path)
        if BASE_DIR not in sys.path:
            sys.path.insert(0, BASE_DIR)
        # Run convert_data.py
        convert_script = os.path.join(BASE_DIR, "portfolio", "convert_data.py")
        if os.path.exists(convert_script):
            result = subprocess.run(
                [sys.executable, convert_script],
                capture_output=True, text=True, timeout=60,
                cwd=BASE_DIR,
            )
            json_rebuilt = result.returncode == 0
        sys.path = sys_path_saved
    except Exception:
        json_rebuilt = False

    return jsonify({
        "success": True,
        "new_rows": len(new_rows),
        "latest_date": latest_date,
        "csv_path": csv_path,
        "json_rebuilt": json_rebuilt,
    })


@app.route("/api/recent/<code>", methods=["GET"])
def get_recent(code):
    """Get the most recent backtest result for a code from cache."""
    results = {}
    for key, val in _backtest_cache.items():
        if key.startswith(code):
            results[key] = {"strategy": val["strategy"], "metrics": val["metrics"]}

    if not results:
        return jsonify({"success": False, "error": "No cached results"}), 404

    return jsonify({"success": True, "results": results})


# ── 静态文件服务（同端口同时提供网页 + API）──
PORTFOLIO_DIR = os.path.join(BASE_DIR, "portfolio")


@app.route("/")
def serve_index():
    return send_from_directory(PORTFOLIO_DIR, "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory(PORTFOLIO_DIR, filename)


# ── Main ──────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="量化策略课程 — 回测 API 服务")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8081)), help="服务端口 (默认: 8081)")
    parser.add_argument("--host", default="0.0.0.0", help="绑定地址 (默认: 0.0.0.0)")
    parser.add_argument("--debug", action="store_true", help="调试模式")

    args = parser.parse_args()

    print("=" * 60)
    print("📈 量化策略课程 — 回测 API 服务")
    print("=" * 60)
    print(f"  地址: http://{args.host}:{args.port}")
    print(f"  健康检查: http://{args.host}:{args.port}/api/health")
    print(f"  回测接口: POST http://{args.host}:{args.port}/api/backtest")
    print(f"  股票搜索: GET  http://{args.host}:{args.port}/api/stocks?q=宁德")
    print(f"  网页入口: http://{args.host}:{args.port}/")
    print("=" * 60)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
