#!/usr/bin/env python3
"""
新策略回测生成脚本
===================
为 portfolio 看板生成三种新策略的回测数据：
1. 布林带策略 (Bollinger Bands)
2. RSI 策略 (Relative Strength Index)
3. 动量策略 (Momentum)

输出：CSV 回测数据 + JSON 数据文件
"""

import csv
import json
import math
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "portfolio", "data")


def read_csv(path):
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def safe_float(val, default=None):
    if val is None or val == "" or val == "nan" or val == "NaN":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def calc_sma(values, period):
    """Simple Moving Average."""
    sma = []
    for i in range(len(values)):
        if i < period - 1:
            sma.append(None)
        else:
            sma.append(sum(values[i - period + 1:i + 1]) / period)
    return sma


def calc_std(values, period):
    """Rolling standard deviation."""
    std = []
    for i in range(len(values)):
        if i < period - 1:
            std.append(None)
        else:
            window = values[i - period + 1:i + 1]
            mean = sum(window) / period
            variance = sum((x - mean) ** 2 for x in window) / period
            std.append(math.sqrt(variance))
    return std


def calc_rsi(closes, period=14):
    """Calculate RSI."""
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = [None] * period  # first period entries have no value
    avg_loss = [None] * period
    # First average
    avg_gain.append(sum(gains[:period]) / period)
    avg_loss.append(sum(losses[:period]) / period)

    for i in range(period, len(gains)):
        avg_gain.append((avg_gain[-1] * (period - 1) + gains[i]) / period)
        avg_loss.append((avg_loss[-1] * (period - 1) + losses[i]) / period)

    rsi = []
    for i in range(len(avg_gain)):
        if avg_gain[i] is None or avg_loss[i] is None:
            rsi.append(None)
        elif avg_loss[i] == 0:
            rsi.append(100.0)
        else:
            rs = avg_gain[i] / avg_loss[i]
            rsi.append(100.0 - (100.0 / (1.0 + rs)))
    return rsi


def backtest(signals_df, initial_capital=100000):
    """Run a simple backtest given buy/sell signals.
    signals_df: list of dicts with keys: date, close, signal (1=buy, -1=sell, 0=hold)
    Returns: dict with nav, drawdown, and metrics.
    """
    dates = [r["date"] for r in signals_df]
    closes = [safe_float(r["close"]) for r in signals_df]
    signals = [int(safe_float(r.get("signal", 0), 0)) for r in signals_df]

    nav = []
    drawdown = []
    capital = initial_capital
    position = 0  # shares held
    peak = capital

    buy_count = 0
    sell_count = 0
    trade_returns = []

    for i in range(len(dates)):
        sig = signals[i] if i < len(signals) else 0
        price = closes[i]

        if sig == 1 and position == 0:
            # Buy all
            position = capital / price
            capital = 0
            buy_count += 1
            entry_price = price
        elif sig == -1 and position > 0:
            # Sell all
            capital = position * price
            trade_return = (price / entry_price - 1) * 100
            trade_returns.append(trade_return)
            position = 0
            sell_count += 1

        total_value = capital + position * price
        nav.append(total_value)

        # Drawdown
        if total_value > peak:
            peak = total_value
        dd = (total_value - peak) / peak * 100 if peak > 0 else 0
        drawdown.append(dd)

    # Final liquidation
    if position > 0 and len(closes) > 0:
        capital = position * closes[-1]
        trade_return = (closes[-1] / entry_price - 1) * 100
        trade_returns.append(trade_return)

    # Metrics
    final_nav = nav[-1] if nav else initial_capital
    total_return_pct = (final_nav / initial_capital - 1) * 100
    n_years = len(dates) / 252
    annual_return = ((final_nav / initial_capital) ** (1 / n_years) - 1) * 100 if n_years > 0 else 0
    max_dd = min(drawdown) if drawdown else 0

    # Sharpe (daily)
    daily_returns = []
    for i in range(1, len(nav)):
        if nav[i - 1] > 0:
            daily_returns.append((nav[i] / nav[i - 1]) - 1)
    if len(daily_returns) > 1:
        mean_ret = sum(daily_returns) / len(daily_returns)
        std_ret = (sum((r - mean_ret) ** 2 for r in daily_returns) / (len(daily_returns) - 1)) ** 0.5
        sharpe = (mean_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0
    else:
        sharpe = 0

    win_rate = sum(1 for r in trade_returns if r > 0) / len(trade_returns) * 100 if trade_returns else 0
    avg_return = sum(trade_returns) / len(trade_returns) if trade_returns else 0

    # Benchmark (buy-and-hold)
    bh_return = (closes[-1] / closes[0] - 1) * 100 if closes and closes[0] > 0 else 0
    bh_nav = [initial_capital * c / closes[0] for c in closes]
    bh_peak = initial_capital
    bh_dd = []
    for v in bh_nav:
        if v > bh_peak:
            bh_peak = v
        bh_dd.append((v - bh_peak) / bh_peak * 100 if bh_peak > 0 else 0)
    bh_max_dd = min(bh_dd) if bh_dd else 0

    return {
        "dates": dates,
        "close": closes,
        "nav": nav,
        "drawdown": drawdown,
        "signals": signals,
        "benchmark_nav": bh_nav,
        "benchmark_drawdown": bh_dd,
        "metrics": {
            "total_return_pct": round(total_return_pct, 2),
            "annual_return": round(annual_return, 2),
            "max_dd": round(max_dd, 2),
            "sharpe": round(sharpe, 2),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "total_trades": buy_count + sell_count,
            "win_rate": round(win_rate, 1),
            "avg_trade_return": round(avg_return, 2),
            "benchmark_return": round(bh_return, 2),
            "benchmark_mdd": round(bh_max_dd, 2),
        }
    }


def nan_to_none(obj):
    """Recursively replace NaN/Inf with None for valid JSON."""
    if isinstance(obj, dict):
        return {k: nan_to_none(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [nan_to_none(v) for v in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def save_json(filename, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(nan_to_none(data), f, ensure_ascii=False)
    print(f"  JSON -> {filename}")


# =========================================================
# Strategy 1: Bollinger Bands
# =========================================================

def bollinger_strategy(closes, period=20, std_mult=2.0):
    """Bollinger Bands strategy.
    Buy when price crosses below lower band (oversold).
    Sell when price crosses above upper band (overbought).
    """
    ma = calc_sma(closes, period)
    std = calc_std(closes, period)

    upper = []
    lower = []
    for i in range(len(closes)):
        if ma[i] is not None and std[i] is not None:
            upper.append(ma[i] + std_mult * std[i])
            lower.append(ma[i] - std_mult * std[i])
        else:
            upper.append(None)
            lower.append(None)

    signals = []
    position = 0
    for i in range(len(closes)):
        if i < period:
            signals.append(0)
            continue
        if lower[i] is None or upper[i] is None:
            signals.append(0)
            continue
        if position == 0 and closes[i] < lower[i]:
            signals.append(1)
            position = 1
        elif position == 1 and closes[i] > upper[i]:
            signals.append(-1)
            position = 0
        else:
            signals.append(0)
    return {"ma": ma, "upper": upper, "lower": lower, "signals": signals}


def generate_bollinger(dates, closes, stock_name, code):
    print("\n" + "=" * 60)
    print("📊 布林带策略回测")
    print("=" * 60)

    param_combos = [
        ("BB_20_2", 20, 2.0),
    ]

    all_backtests = {}
    for label, period, std_mult in param_combos:
        print(f"  参数: period={period}, std_mult={std_mult}")
        result = bollinger_strategy(closes, period, std_mult)

        # Build signals data for backtest
        signals_data = []
        for i in range(len(dates)):
            signals_data.append({
                "date": dates[i],
                "close": closes[i],
                "signal": result["signals"][i],
            })

        bt = backtest(signals_data)

        # Save CSV
        csv_filename = f"{stock_name}_{code}_布林带_{label}_回测数据.csv"
        csv_path = os.path.join(BASE_DIR, csv_filename)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["交易日期", "收盘价", "MA20", "上轨", "下轨", "信号(1买/-1卖/0无)", "策略净值", "回撤幅度"])
            for i in range(len(dates)):
                writer.writerow([
                    dates[i],
                    f"{closes[i]:.2f}",
                    f"{result['ma'][i]:.2f}" if result['ma'][i] else "",
                    f"{result['upper'][i]:.2f}" if result['upper'][i] else "",
                    f"{result['lower'][i]:.2f}" if result['lower'][i] else "",
                    result["signals"][i],
                    f"{bt['nav'][i]:.2f}",
                    f"{bt['drawdown'][i]:.2f}",
                ])
        print(f"  CSV -> {csv_filename}")

        # JSON
        bt_json = {
            "name": "布林带策略",
            "param": label,
            "period": period,
            "std_mult": std_mult,
            "stock": stock_name,
            "code": code,
            "dates": bt["dates"],
            "close": bt["close"],
            "ma": result["ma"],
            "upper": result["upper"],
            "lower": result["lower"],
            "signals": bt["signals"],
            "nav": bt["nav"],
            "drawdown": bt["drawdown"],
            "benchmark_nav": bt["benchmark_nav"],
            "benchmark_drawdown": bt["benchmark_drawdown"],
            "metrics": bt["metrics"],
        }
        json_filename = f"new_bollinger_{label}.json"
        save_json(json_filename, bt_json)
        all_backtests[label] = json_filename

        print(f"  指标: 回报={bt['metrics']['total_return_pct']}%, MDD={bt['metrics']['max_dd']}%, "
              f"夏普={bt['metrics']['sharpe']}, 交易={bt['metrics']['total_trades']}次")

    save_json("new_bollinger_index.json", all_backtests)
    return all_backtests


# =========================================================
# Strategy 2: RSI
# =========================================================

def rsi_strategy(closes, period=14, oversold=30, overbought=70):
    """RSI strategy.
    Buy when RSI crosses above oversold (exiting oversold).
    Sell when RSI crosses below overbought (exiting overbought).
    """
    rsi = calc_rsi(closes, period)
    signals = []
    position = 0
    for i in range(len(closes)):
        if rsi[i] is None or i < period + 1:
            signals.append(0)
            continue
        if position == 0 and rsi[i - 1] < oversold and rsi[i] >= oversold:
            signals.append(1)
            position = 1
        elif position == 1 and rsi[i - 1] > overbought and rsi[i] <= overbought:
            signals.append(-1)
            position = 0
        else:
            signals.append(0)
    return {"rsi": rsi, "signals": signals}


def generate_rsi(dates, closes, stock_name, code):
    print("\n" + "=" * 60)
    print("📈 RSI 策略回测")
    print("=" * 60)

    param_combos = [
        ("RSI_14_30_70", 14, 30, 70),
    ]

    all_backtests = {}
    for label, period, oversold, overbought in param_combos:
        print(f"  参数: period={period}, oversold={oversold}, overbought={overbought}")
        result = rsi_strategy(closes, period, oversold, overbought)

        signals_data = []
        for i in range(len(dates)):
            signals_data.append({
                "date": dates[i],
                "close": closes[i],
                "signal": result["signals"][i],
            })

        bt = backtest(signals_data)

        # Save CSV
        csv_filename = f"{stock_name}_{code}_RSI_{label}_回测数据.csv"
        csv_path = os.path.join(BASE_DIR, csv_filename)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["交易日期", "收盘价", "RSI", "信号(1买/-1卖/0无)", "策略净值", "回撤幅度"])
            for i in range(len(dates)):
                writer.writerow([
                    dates[i],
                    f"{closes[i]:.2f}",
                    f"{result['rsi'][i]:.2f}" if result['rsi'][i] is not None else "",
                    result["signals"][i],
                    f"{bt['nav'][i]:.2f}",
                    f"{bt['drawdown'][i]:.2f}",
                ])
        print(f"  CSV -> {csv_filename}")

        bt_json = {
            "name": "RSI策略",
            "param": label,
            "period": period,
            "oversold": oversold,
            "overbought": overbought,
            "stock": stock_name,
            "code": code,
            "dates": bt["dates"],
            "close": bt["close"],
            "rsi": result["rsi"],
            "signals": bt["signals"],
            "nav": bt["nav"],
            "drawdown": bt["drawdown"],
            "benchmark_nav": bt["benchmark_nav"],
            "benchmark_drawdown": bt["benchmark_drawdown"],
            "metrics": bt["metrics"],
        }
        json_filename = f"new_rsi_{label}.json"
        save_json(json_filename, bt_json)
        all_backtests[label] = json_filename

        print(f"  指标: 回报={bt['metrics']['total_return_pct']}%, MDD={bt['metrics']['max_dd']}%, "
              f"夏普={bt['metrics']['sharpe']}, 交易={bt['metrics']['total_trades']}次")

    save_json("new_rsi_index.json", all_backtests)
    return all_backtests


# =========================================================
# Strategy 3: Momentum
# =========================================================

def momentum_strategy(closes, lookback=20):
    """Momentum strategy.
    Buy when N-day momentum turns positive (close > close N days ago).
    Sell when momentum turns negative.
    """
    signals = []
    position = 0
    for i in range(len(closes)):
        if i < lookback:
            signals.append(0)
            continue
        moment = (closes[i] / closes[i - lookback] - 1) * 100
        prev_moment = (closes[i - 1] / closes[i - lookback - 1] - 1) * 100 if i > lookback else 0

        if position == 0 and moment > 0 and prev_moment <= 0:
            # Momentum just turned positive
            signals.append(1)
            position = 1
        elif position == 1 and moment < 0:
            # Momentum turned negative
            signals.append(-1)
            position = 0
        else:
            signals.append(0)
    return signals


def generate_momentum(dates, closes, stock_name, code):
    print("\n" + "=" * 60)
    print("🚀 动量策略回测")
    print("=" * 60)

    param_combos = [
        ("MOM_20", 20),
    ]

    all_backtests = {}
    for label, lookback in param_combos:
        print(f"  参数: lookback={lookback}")
        signals = momentum_strategy(closes, lookback)

        # Calculate momentum values for reference
        mom_values = []
        for i in range(len(closes)):
            if i < lookback:
                mom_values.append(None)
            else:
                mom_values.append((closes[i] / closes[i - lookback] - 1) * 100)

        signals_data = []
        for i in range(len(dates)):
            signals_data.append({
                "date": dates[i],
                "close": closes[i],
                "signal": signals[i],
            })

        bt = backtest(signals_data)

        # Save CSV
        csv_filename = f"{stock_name}_{code}_动量_{label}_回测数据.csv"
        csv_path = os.path.join(BASE_DIR, csv_filename)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["交易日期", "收盘价", "动量(%)", "信号(1买/-1卖/0无)", "策略净值", "回撤幅度"])
            for i in range(len(dates)):
                writer.writerow([
                    dates[i],
                    f"{closes[i]:.2f}",
                    f"{mom_values[i]:.2f}" if mom_values[i] is not None else "",
                    signals[i],
                    f"{bt['nav'][i]:.2f}",
                    f"{bt['drawdown'][i]:.2f}",
                ])
        print(f"  CSV -> {csv_filename}")

        bt_json = {
            "name": "动量策略",
            "param": label,
            "lookback": lookback,
            "stock": stock_name,
            "code": code,
            "dates": bt["dates"],
            "close": bt["close"],
            "momentum": mom_values,
            "signals": bt["signals"],
            "nav": bt["nav"],
            "drawdown": bt["drawdown"],
            "benchmark_nav": bt["benchmark_nav"],
            "benchmark_drawdown": bt["benchmark_drawdown"],
            "metrics": bt["metrics"],
        }
        json_filename = f"new_momentum_{label}.json"
        save_json(json_filename, bt_json)
        all_backtests[label] = json_filename

        print(f"  指标: 回报={bt['metrics']['total_return_pct']}%, MDD={bt['metrics']['max_dd']}%, "
              f"夏普={bt['metrics']['sharpe']}, 交易={bt['metrics']['total_trades']}次")

    save_json("new_momentum_index.json", all_backtests)
    return all_backtests


def main():
    print("=" * 60)
    print("📈 新策略回测数据生成")
    print("=" * 60)

    # Load stock data
    csv_path = os.path.join(BASE_DIR, "TASK1", "宁德时代_300750_日线数据.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: 数据文件不存在: {csv_path}")
        sys.exit(1)

    rows = read_csv(csv_path)
    print(f"加载 {len(rows)} 条日线数据")

    dates = [r["交易日期"] for r in rows]
    closes = [safe_float(r["收盘价"]) for r in rows]
    stock_name = "宁德时代"
    code = "300750"

    # Generate all strategies
    bb_index = generate_bollinger(dates, closes, stock_name, code)
    rsi_index = generate_rsi(dates, closes, stock_name, code)
    mom_index = generate_momentum(dates, closes, stock_name, code)

    # Strategy index
    strategy_index = {
        "bollinger": bb_index,
        "rsi": rsi_index,
        "momentum": mom_index,
    }
    save_json("new_strategies_index.json", strategy_index)

    print("\n" + "=" * 60)
    print("✅ 全部新策略回测数据生成完毕")
    print(f"   数据目录: {DATA_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
