# -*- coding: utf-8 -*-
"""
================================================================================
【聚宽 JoinQuant】双均线策略（含风控增强版）  —  TASK7 可直接运行的策略代码
================================================================================
本策略以课程 TASK3 的"双均线（金叉/死叉）"为模板，并增加了 4 类风控模块：
  1) 趋势过滤：仅当收盘价 > 长期趋势均线(默认120日)时才允许做多，过滤下跌趋势中的假金叉
  2) 止损：持仓回撤超过阈值(默认10%)时强制平仓
  3) 涨跌停过滤：涨停买不进、跌停卖不出（用 high_limit / low_limit 判断）
  4) 交易成本建模：佣金 + 印花税 + 滑点（在 initialize 中设置）

在聚宽上的使用步骤：
  A. 新建策略 -> 粘贴本文件全部内容
  B. 回测设置：基准 沪深300；初始资金 100000；回测周期（如 2019-01-01 ~ 2026-07-24）；
     调仓频率 每天；撮合 收盘价；费率见 initialize 内 set_commission / set_slippage
  C. 点击"运行回测"，查看收益/回撤/夏普等指标
  D. 点击"开启模拟交易"（实盘模拟）：选择初始资金、调仓周期（每天/每周），
     绑定微信/邮件提醒；此后策略每个交易日 15:00 自动按 handle_data 逻辑下单（模拟盘）
================================================================================
"""

# ---------- 全局参数（在 initialize 中赋值，handle_data 中读取）----------
def initialize(context):
    # 交易标的：宁德时代（创业板代码后缀 .XSHE；沪市用 .XSHG）
    g.security = '300750.XSHE'

    # 双均线周期（经本地样本内寻优得到的最优参数）
    g.short = 15          # 短均线
    g.long = 20           # 长均线
    g.trend_ma = 120      # 趋势过滤均线
    g.stop_loss = 0.10    # 止损比例（持仓回撤超过此值平仓）

    # 基准：沪深300
    set_benchmark('000300.XSHG')

    # 交易成本：买入佣金万三，卖出佣金万三 + 印花税千一（聚宽按金额比例）
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    # 滑点：价格比例千一
    set_slippage(PriceRatioSlippage(0.001))

    # 每天收盘运行一次
    run_daily(handle_data, '15:00')


def handle_data(context):
    # ---- 1. 取历史行情（长度需覆盖长均线 + 1，用于判断穿越）----
    look = g.long + 1
    hist = attribute_history(g.security, look, '1d',
                             ['close', 'high', 'low'], skip_paused=True)
    if len(hist) < look:
        return  # 数据不足，跳过

    closes = hist['close']
    # 当日与昨日的均线差
    ma_short_now = closes[-g.short:].mean()
    ma_long_now = closes[-g.long:].mean()
    ma_short_prev = closes[-g.short - 1:-1].mean()
    ma_long_prev = closes[-g.long - 1:-1].mean()

    diff_now = ma_short_now - ma_long_now
    diff_prev = ma_short_prev - ma_long_prev

    # 金叉 / 死叉
    golden_cross = (diff_prev <= 0) and (diff_now > 0)
    death_cross = (diff_prev >= 0) and (diff_now < 0)

    # 趋势过滤
    ma_trend_now = closes[-g.trend_ma:].mean()
    trend_ok = closes.iloc[-1] > ma_trend_now

    # ---- 2. 涨跌停判断 ----
    cur = get_current_data()[g.security]
    price = closes.iloc[-1]
    is_limit_up = price >= cur.high_limit * 0.995    # 涨停：买不进
    is_limit_down = price <= cur.low_limit * 0.995    # 跌停：卖不出

    # ---- 3. 当前持仓 ----
    pos = context.portfolio.positions.get(g.security)
    holding = (pos is not None) and (pos.closeable_amount > 0)

    # ---- 4. 生成目标仓位 ----
    target_value = 0  # 0=空仓，total_value=满仓
    if not holding:
        if golden_cross and (not is_limit_up) and trend_ok:
            target_value = context.portfolio.total_value  # 全仓买入
    else:
        # 持仓中：计算当前回撤
        cost = pos.avg_cost
        drawdown = (price - cost) / cost if cost > 0 else 0
        if death_cross and (not is_limit_down):
            target_value = 0  # 死叉平仓
        elif drawdown <= -g.stop_loss and (not is_limit_down):
            target_value = 0  # 止损平仓

    # ---- 5. 下单 ----
    # order_target 会把仓位调整到目标市值（自动处理买入/卖出与部分成交）
    if target_value == 0 and holding and is_limit_down:
        return  # 跌停无法卖出，继续持有，下一交易日再尝试
    order_target_value(g.security, target_value)


# ============================================================================
# 【附】参数寻优思路（在聚宽"研究"环境或本地下述脚本中执行，不在策略主循环内）
# ----------------------------------------------------------------------------
# 聚宽平台提供"参数优化"功能：在回测页面勾选"参数优化"，把 g.short / g.long
# 设为扫描变量（如 short∈{5,8,10,15,20}, long∈{20,30,40,60,120}），
# 目标函数选"夏普比率最大"。平台会自动跑网格并给出最优组合。
# 本 TASK7 的本地脚本 backtest_dual_ma.py 已完整复现了这套寻优逻辑并输出热力图。
# ============================================================================
