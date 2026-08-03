# TASK3 双均线策略完整实现方案

## 一、项目概述

基于已完成的 TASK1（数据获取与可视化）和 TASK2（技术指标分析），TASK3 需要在 242 个交易日的宁德时代(300750.SZ)日线数据上实现双均线交易策略的完整回测，并产出 Python 脚本、可视化图表和 PDF 报告。

### 数据基础
- 数据文件：`TASK2/宁德时代_300750_含技术指标.csv`（优先使用，含技术指标列可供扩展分析）
- 备选数据：`TASK1/宁德时代_300750_日线数据.csv`
- 数据量：242 个交易日（2025-07-04 至 2026-07-03）
- 列名：股票代码,交易日期,开盘价,最高价,最低价,收盘价,前收盘价,涨跌额,涨跌幅(%),成交量(手),成交额(千元)

### 环境配置
- Python 路径：`/Applications/XYsPythonProject/anaconda3/bin/python`
- pandas 2.2.3 + matplotlib 3.10.0
- matplotlib 中文字体：`plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']`
- matplotlib 缓存：需设 `MPLCONFIGDIR=/tmp/matplotlib_cache`
- 图表颜色惯例：涨=红色(#DC143C)，跌=绿色(#228B22)

---

## 二、产出文件清单

所有文件输出到 `/Users/wangyanfen/Desktop/量化策略课程/TASK3/` 目录：

### 2.1 Python 脚本
| 文件名 | 用途 |
|--------|------|
| `task3_strategy.py` | **主脚本**：双均线策略回测全流程（加载数据 -> 计算均线 -> 生成信号 -> 回测 -> 可视化 -> 导出结果） |

### 2.2 CSV 数据文件
| 文件名 | 内容 |
|--------|------|
| `宁德时代_300750_双均线回测.csv` | 原始数据 + MA5/MA15/MA30 + 交易信号 + 持仓状态 + 每日收益率 + 累计净值 |
| `回测指标汇总.csv` | 回测指标汇总（总收益率、年化收益率、夏普比率、最大回撤、胜率等） |
| `多参数对比表.csv` | 不同均线组合(5-15/5-20/5-30/10-20/10-30/20-60)的回测结果对比 |
| `多股票对比表.csv` | 不同股票使用同一策略的回测结果对比（需要额外数据） |

### 2.3 PNG 图表文件
| 文件名 | 内容 |
|--------|------|
| `图1_股价与双均线.png` | 收盘价走势 + MA5 + MA15 + MA30 三条均线 |
| `图2_交易信号全景.png` | 收盘价 + 两条交易均线 + 金叉死叉标注 + 买入/卖出信号点标记 + 信号区域着色 |
| `图3_回测资金曲线.png` | 策略累计净值 vs 买入持有净值（双线对比） |
| `图4_回撤分析.png` | 策略回撤曲线 + 最大回撤标注 |
| `图5_综合面板.png` | 2x2 子图：信号图 + 资金曲线 + 回撤图 + 年度收益分布 |
| `图6_多参数对比.png` | 不同均线组合的累计收益率对比曲线 |
| `图7_多股票对比.png` | 不同股票的累计收益率对比图（横轴为交易日序号） |

### 2.4 PDF 报告文件
| 文件名 | 内容 |
|--------|------|
| `夏阳+TASK3.pdf` | 综合研究报告（见第六节报告大纲） |

---

## 三、Python 脚本详细设计

### 3.1 整体结构

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
量化策略课程 TASK3：双均线策略回测系统
======================================
股票：宁德时代(300750.SZ)
数据区间：2025-07-04 至 2026-07-03（242个交易日）
策略：短期均线上穿长期均线买入（金叉），下穿卖出（死叉）

作者：夏阳
日期：2026-07-08
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd
import matplotlib
# 解决 matplotlib 缓存权限问题
matplotlib.use('Agg')
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib_cache'
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

# ===== 全局配置 =====
warnings.filterwarnings('ignore')
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti SC', 'STHeiti', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.dpi'] = 150
plt.rcParams['savefig.dpi'] = 150
plt.rcParams['savefig.bbox'] = 'tight'

# 中国股市颜色惯例
COLOR_RED = '#DC143C'     # 涨（红色）
COLOR_GREEN = '#228B22'   # 跌（绿色）
COLOR_ORANGE = '#FF8C00'  # 买入信号
COLOR_PURPLE = '#8B008B'  # 卖出信号
COLOR_MA_SHORT = '#E63946' # 短均线
COLOR_MA_LONG = '#457B9D'  # 长均线

# 输出目录
OUTPUT_DIR = '/Users/wangyanfen/Desktop/量化策略课程/TASK3'
DATA_FILE = '/Users/wangyanfen/Desktop/量化策略课程/TASK2/宁德时代_300750_含技术指标.csv'

# 默认策略参数
SHORT_MA = 5    # 短期均线周期
LONG_MA = 15    # 长期均线周期
INIT_CAPITAL = 1000000  # 初始资金 100万元
COMMISSION_RATE = 0.0003  # 佣金费率 万分之三
```

### 3.2 函数划分

#### 模块 1：数据加载与预处理
```python
def load_data(filepath: str) -> pd.DataFrame:
    """加载股价数据，处理日期格式，返回清理后的 DataFrame"""
    # 1. 读取 CSV（UTF-8 with BOM）
    # 2. 转换日期列
    # 3. 按日期升序排序
    # 4. 重置索引
    # 5. 选择基础列（收盘价等）
    pass

def validate_data(df: pd.DataFrame) -> None:
    """数据验证：检查缺失值、日期连续性"""
    pass
```

#### 模块 2：均线计算与信号生成
```python
def compute_moving_averages(df: pd.DataFrame, short_window: int, long_window: int) -> pd.DataFrame:
    """计算短期和长期移动均线，生成交易信号"""
    # 1. 计算短均线 df['MA_short']
    # 2. 计算长均线 df['MA_long']
    # 3. 计算均线差值（用于识别交叉） df['MA_diff'] = df['MA_short'] - df['MA_long']
    # 4. 生成信号规则：
    #    - 金叉：前一天 diff <= 0 且 当天 diff > 0 → signal = 1 (买入)
    #    - 死叉：前一天 diff > 0 且 当天 diff <= 0 → signal = -1 (卖出)
    #    - 其他：signal = 0 (持有)
    #    注意：均线需要至少 long_window 个交易日才能计算，前 long_window-1 天 signal = 0
    pass

def generate_trade_signals(df: pd.DataFrame) -> pd.DataFrame:
    """在信号列的基础上生成买卖方向标识"""
    # 1. 添加 'trade' 列：
    #    - signal=1 → 'BUY'
    #    - signal=-1 → 'SELL'
    #    - signal=0 → 'WAIT'
    # 2. 添加 'position' 列：1=持仓，0=空仓
    #    - 遇到 BUY → position=1
    #    - 遇到 SELL → position=0
    #    - 使用前向填充
    # 3. 添加 'trade_price' 列：记录交易时的收盘价
    pass
```

#### 模块 3：回测引擎
```python
def run_backtest(df: pd.DataFrame, initial_capital: float, commission_rate: float) -> pd.DataFrame:
    """执行双均线策略回测"""
    # 核心思路：
    # 1. 遍历每一天交易信号
    # 2. BUY信号：用当前资金买入（考虑手续费）
    #    - 买入金额 = 持仓资金
    #    - 买入股数 = floor(买入金额 / (收盘价 * (1 + 手续费率)) / 100) * 100（A股100股为1手）
    #    - 手续费 = 买入金额 * 手续费率（最低5元）
    #    - 持仓成本 = 买入价
    # 3. SELL信号：卖出全部持仓
    #    - 卖出金额 = 持仓股数 * 收盘价 * (1 - 手续费率)
    #    - 手续费 = 卖出金额 * 手续费率（最低5元，印花税0.05%）
    # 4. 每日计算：
    #    - 持仓市值 = 持仓股数 * 当日收盘价
    #    - 现金余额
    #    - 总资产 = 持仓市值 + 现金余额
    #    - 当日收益率 = (总资产 - 前日总资产) / 前日总资产
    #    - 累计净值 = 总资产 / 初始资金
    #    - 买入持有净值 = 当日收盘价 / 第一天收盘价（用于对比）
    pass

def calculate_metrics(df: pd.DataFrame, risk_free_rate: float = 0.015) -> dict:
    """计算回测评估指标"""
    # 1. 总收益率 = (最终资产 - 初始资金) / 初始资金
    # 2. 年化收益率 = (1 + 总收益率)^(365/交易日数) - 1
    # 3. 波动率（年化）= 日收益率标准差 * sqrt(242)
    # 4. 夏普比率 = (年化收益率 - 无风险利率) / 年化波动率
    # 5. 最大回撤(MDD)计算：
    #    - 累计净值最高点曲线 cummax
    #    - 回撤 = (净值 - 累计最高) / 累计最高
    #    - MDD = min(回撤)（取最小值即最大回撤）
    #    - 记录回撤起止日期
    # 6. 胜率 = 盈利交易次数 / 总交易次数
    # 7. 盈亏比 = 平均盈利 / |平均亏损|
    # 8. 交易次数
    # 9. 持仓天数占比
    pass
```

#### 模块 4：可视化
```python
def plot_price_with_ma(df: pd.DataFrame, short_w: int, long_w: int) -> str:
    """图1：收盘价走势 + 三条均线"""
    # - 左侧 Y 轴：价格（元）
    # - X 轴：日期
    # - 收盘价（灰色线，半透明）
    # - MA_short（红色实线）
    # - MA_long（蓝色实线）
    # - 图例、标题、网格线
    pass

def plot_trade_signals(df: pd.DataFrame) -> str:
    """图2：交易信号全景图"""
    # - 上半部分：收盘价曲线 + 两条均线
    # - 下半部分：成交量柱状图
    # - 金叉区域标注（绿色半透明）
    # - 死叉区域标注（红色半透明）
    # - 买入信号：红色上三角标记
    # - 卖出信号：绿色下三角标记
    # - 图例、信号统计文本
    pass

def plot_equity_curve(df: pd.DataFrame) -> str:
    """图3：回测资金曲线"""
    # - 策略累计净值（红色实线）
    # - 买入持有累计净值（灰色虚线，用于对比）
    # - 基准线 1.0（灰色虚线）
    # - 标注超额收益
    # - 图例、最终收益率
    pass

def plot_drawdown(df: pd.DataFrame) -> str:
    """图4：回撤分析"""
    # - 回撤曲线（蓝色填充）
    # - 标注最大回撤点和日期
    # - Y 轴反转（向下显示回撤）
    # - 标注回撤百分比
    pass

def plot_dashboard(df: pd.DataFrame) -> str:
    """图5：综合面板（2x2布局）"""
    # - 左上：价格+均线+信号
    # - 右上：资金曲线对比
    # - 左下：回撤曲线
    # - 右下：月度收益热力图/柱状图
    pass

def plot_param_comparison(results: dict) -> str:
    """图6：多参数对比曲线"""
    # - 每条线代表一个均线组合
    # - 横轴：交易日序号，纵轴：累计收益率
    # - 不同颜色区分
    # - 标注最佳组合
    pass

def plot_stock_comparison(results: dict) -> str:
    """图7：多股票对比曲线"""
    # - 每条线代表一只股票
    # - 横轴：交易日序号，纵轴：累计收益率
    # - 标出最佳股票
    pass
```

#### 模块 5：多参数对比实验
```python
def param_optimization(df: pd.DataFrame, short_windows: list, long_windows: list) -> dict:
    """遍历短均线和长均线周期组合，返回回测结果"""
    # 参数组合列表：
    # - (5, 15)  -- 默认基准
    # - (5, 20)  -- 标准组合
    # - (5, 30)  -- 较长周期
    # - (10, 20) -- 中等周期
    # - (10, 30) -- 中等偏长
    # - (20, 60) -- 较长周期
    # 对每种组合运行完整回测，记录指标
    pass
```

#### 模块 6：多股票对比实验
```python
def multi_stock_comparison(stocks_config: list) -> dict:
    """对多只股票运行同一策略，对比结果"""
    # 股票列表（需用户通过 Tushare MCP 获取）：
    # 1. 000001.SZ 平安银行（银行股）
    # 2. 000858.SZ 五粮液（消费股）
    # 3. 600519.SH 贵州茅台（白酒龙头）
    # 4. 601318.SH 中国平安（保险股）
    # 5. 300750.SZ 宁德时代（新能源，基准）
    # 覆盖不同行业，观察策略适用性
    pass
```

#### 模块 7：结果导出
```python
def export_results(df: pd.DataFrame, metrics: dict) -> None:
    """导出 CSV 回测数据和指标汇总"""
    pass

def generate_report(metrics: dict, param_results: dict, stock_results: dict, charts: dict) -> str:
    """生成完整 PDF 报告"""
    # 使用 reportlab 生成
    # 字体：宋体（/System/Library/Fonts/Supplemental/Songti.ttc）
    # 格式：五号字(10.5pt)、1.5倍行距、两端对齐
    # 结构见第六节
    pass
```

#### 模块 8：主入口
```python
def main():
    """主执行流程"""
    # 步骤1：加载数据
    # 步骤2：数据验证
    # 步骤3：计算均线与信号（默认参数 5/15）
    # 步骤4：运行回测
    # 步骤5：计算评估指标
    # 步骤6：生成可视化图表（图1-5）
    # 步骤7：导出 CSV 结果
    # 步骤8：运行多参数对比实验 → 图6
    # 步骤9：运行多股票对比实验 → 图7
    # 步骤10：生成 PDF 报告
    # 步骤11：输出总结信息

if __name__ == '__main__':
    main()
```

---

## 四、回测逻辑详细设计

### 4.1 信号生成逻辑

```text
对每一天 t（t >= long_window）：
  计算 diff[t] = MA_short[t] - MA_long[t]
  计算 diff[t-1] = MA_short[t-1] - MA_long[t-1]

  如果 diff[t-1] <= 0 AND diff[t] > 0：
      信号 = "BUY"（金叉买入）
  如果 diff[t-1] > 0 AND diff[t] <= 0：
      信号 = "SELL"（死叉卖出）
  否则：
      信号 = "WAIT"（持有）
```

连续出现多个同向信号时，只执行第一个（因为已经持仓/空仓）。

### 4.2 交易执行逻辑

```text
初始状态：现金 = 初始资金，持仓股数 = 0

对每一天 t：
  如果 信号[t] == "BUY" AND 持仓股数 == 0：
    买入金额 = 现金 * 0.995  # 保留空间给手续费
    理论股数 = floor(买入金额 / (收盘价[t] * (1 + 手续费率)))
    实际股数 = floor(理论股数 / 100) * 100  # 取整到100股
    如果 实际股数 > 0：
      成交金额 = 实际股数 * 收盘价[t]
      手续费 = max(成交金额 * 手续费率, 5)  # 最低5元
      现金 = 现金 - 成交金额 - 手续费
      持仓股数 = 实际股数
      持仓成本 = 收盘价[t]

  如果 信号[t] == "SELL" AND 持仓股数 > 0：
    成交金额 = 持仓股数 * 收盘价[t]
    佣金 = max(成交金额 * 手续费率, 5)
    印花税 = 成交金额 * 0.0005  # A股卖出时收印花税万分之五
    现金 = 现金 + 成交金额 - 佣金 - 印花税
    持仓股数 = 0

  每日记录：
    持仓市值 = 持仓股数 * 收盘价[t]
    总资产 = 现金 + 持仓市值
    日收益率 = (总资产 - 前日总资产) / 前日总资产（第一日为0）
```

### 4.3 核心指标计算

| 指标 | 公式 | 说明 |
|------|------|------|
| 总收益率 | (最终资产 - 初始资金) / 初始资金 | 整个回测期间的累计收益 |
| 年化收益率 | (1 + 总收益率)^(365/N) - 1 | N=交易日数，标准化到年度 |
| 日波动率 | std(日收益率) | 每日收益的标准差 |
| 年化波动率 | 日波动率 * sqrt(242) | 242个交易日年化 |
| 夏普比率 | (年化收益率 - 无风险利率) / 年化波动率 | 0.015为一年期存款利率 |
| 最大回撤(MDD) | min((净值 - 累计最高净值) / 累计最高净值) | 从峰值到谷底的最大跌幅 |
| 胜率 | 盈利交易次数 / 总交易次数 | 盈利=卖出价>买入价 |
| 盈亏比 | 平均盈利金额 / 平均亏损金额的绝对值 | 衡量风险回报比 |

---

## 五、多股票/多参数对比实验方案

### 5.1 多参数对比

测试以下均线周期组合：

| 短周期 | 长周期 | 含义 |
|--------|--------|------|
| 5 | 15 | 默认基准（周线 vs 三周） |
| 5 | 20 | 周线 vs 月线 |
| 5 | 30 | 周线 vs 一个半月 |
| 10 | 20 | 双周 vs 月线 |
| 10 | 30 | 双周 vs 一个半月 |
| 20 | 60 | 月线 vs 季度线 |

对每个组合输出：总收益率、年化收益率、夏普比率、最大回撤、胜率、盈亏比、交易次数。

对比分析要点：
- 短周期越短，交易越频繁，信号越多
- 长周期越长，趋势跟踪越滞后，但假信号越少
- 不同参数在不同市场环境下表现各异

### 5.2 多股票对比

选取不同行业/风格的股票：

| 股票代码 | 名称 | 行业 | 检验点 |
|----------|------|------|--------|
| 300750.SZ | 宁德时代 | 新能源 | 高波动成长股 |
| 000001.SZ | 平安银行 | 银行 | 低波动价值股 |
| 600519.SH | 贵州茅台 | 白酒 | 蓝筹消费股 |
| 000858.SZ | 五粮液 | 白酒 | 成长消费股 |

对比分析要点：
- 趋势性强的股票（持续上涨）适合均线策略
- 震荡行情的股票容易产生多次假信号
- 低波动股票的均线策略收益空间有限

获取额外数据：通过 Tushare MCP `mcp__tushareMcp__daily` 接口获取。

---

## 六、PDF 报告大纲

### 封面
- 标题：TASK3 双均线策略回测分析报告
- 股票：宁德时代(300750.SZ)
- 作者：夏阳
- 日期：2026-07-08

### 第一章 双均线策略理论基础
1.1 什么是移动平均线（MA）
1.2 金叉（Golden Cross）与死叉（Death Cross）
1.3 双均线策略的交易逻辑
1.4 策略的优缺点分析

### 第二章 量化策略评估指标
2.1 累计收益率（Cumulative Return）
2.2 最大回撤（Maximum Drawdown, MDD）
2.3 夏普比率（Sharpe Ratio）
2.4 胜率与盈亏比
2.5 指标之间的关联与综合判断

### 第三章 Python 实现与回测结果
3.1 数据准备与均线计算
3.2 交易信号生成过程
3.3 回测执行逻辑
3.4 回测结果核心数据表
3.5 图表展示（嵌入图1-5）
3.6 结果分析

### 第四章 参数优化实验
4.1 不同均线周期组合测试
4.2 参数对比结果表
4.3 参数对比图（图6）
4.4 参数选择建议

### 第五章 多股票对比实验
5.1 测试股票选择说明
5.2 多股票对比结果表
5.3 多股票对比图（图7）
5.4 策略适用场景总结

### 第六章 结论与思考
6.1 双均线策略的有效性评估
6.2 策略的局限性
6.3 改进方向（引入止损、仓位管理等）
6.4 学习心得

---

## 七、数据获取（多股票对比）

经与用户确认，多股票对比需通过 Tushare MCP 获取额外股票数据。

### 7.1 获取方式
- 使用已配置的 Tushare MCP Server（`~/.workbuddy/.mcp.json`，服务名 `tushareMcp`）
- 调用 `mcp__tushareMcp__daily` 接口，参数：
  - `ts_code`：股票代码（如 `000001.SZ`）
  - `start_date`：`20250704`
  - `end_date`：`20260703`
- 与宁德时代使用**相同日期区间**（2025-07-04 至 2026-07-03），保证对比公平

### 7.2 获取股票清单（4只，覆盖不同行业/风格）
| 股票代码 | 名称 | 行业 | 风格 |
|----------|------|------|------|
| 300750.SZ | 宁德时代 | 新能源 | 高波动成长股（已有数据，基准） |
| 000001.SZ | 平安银行 | 银行 | 低波动价值股 |
| 600519.SH | 贵州茅台 | 白酒 | 蓝筹消费股 |
| 000858.SZ | 五粮液 | 白酒 | 成长消费股 |

### 7.3 数据保存
- 每只股票保存为 CSV 到 `TASK3/data/` 子目录（如 `TASK3/data/平安银行_000001_日线数据.csv`）
- 字段与 TASK1 的宁德时代 CSV 保持一致（股票代码,交易日期,开盘价,最高价,最低价,收盘价,前收盘价,涨跌额,涨跌幅(%),成交量(手),成交额(千元)），需对 Tushare 返回字段做映射与单位换算
- 多股票对比回测复用同一套回测引擎函数

---

## 八、执行计划

### 第一步：生成 Python 脚本 `task3_strategy.py`
- 文件路径：`/Users/wangyanfen/Desktop/量化策略课程/TASK3/task3_strategy.py`
- 包含上述所有函数模块
- 代码风格：充分的注释说明，适合教学场景
- 全局运行参数：SHORT_MA=5, LONG_MA=15, INIT_CAPITAL=1000000

### 第二步：通过 Tushare MCP 获取多股票数据
- 调用 `mcp__tushareMcp__daily` 获取 平安银行(000001.SZ)、贵州茅台(600519.SH)、五粮液(000858.SZ) 的日线数据
- 区间：2025-07-04 至 2026-07-03，与宁德时代保持一致
- 字段映射与单位换算，保存为 `TASK3/data/*.csv`

### 第三步：运行脚本生成图表和 CSV
- 执行命令：
```bash
MPLCONFIGDIR=/tmp/matplotlib_cache /Applications/XYsPythonProject/anaconda3/bin/python \
  /Users/wangyanfen/Desktop/量化策略课程/TASK3/task3_strategy.py
```
- 脚本内部依次完成：加载数据 → 计算均线信号 → 回测 → 指标计算 → 图1-5 → 导出CSV → 多参数对比(图6) → 多股票对比(图7) → PDF报告

### 第四步：生成 PDF 报告
- 使用 reportlab，格式与 TASK1/TASK2 保持一致
- 宋体五号字，1.5倍行距，两端对齐
- 嵌入所有图表（图1-图7）
- 署名：夏阳｜文件命名：`夏阳+TASK3.pdf`

---

## 八、注意事项

1. **BOM 处理**：CSV 文件为 UTF-8 with BOM，读取时需指定 `encoding='utf-8-sig'`
2. **日期格式**：交易日期列为字符串格式 `YYYY-MM-DD`，需转为 datetime
3. **手续费**：A股交易涉及佣金（最低5元）和卖出印花税（0.05%）
4. **整数手**：A股买入必须为100股的整数倍
5. **极端情况**：需处理买入时资金不足100股、卖出时无持仓等情况
6. **首笔交易**：策略从第 long_window 个交易日开始才能发出信号
7. **图表中文化**：确保所有图表标签、标题、图例使用中文，字体已配置
8. **与 TASK2 的关系**：TASK2 的 CSV 包含 MACD/DIF/DEA 等指标，TASK3 可选择性引用这些指标进行辅助分析，但核心逻辑仅使用价格数据和均线
