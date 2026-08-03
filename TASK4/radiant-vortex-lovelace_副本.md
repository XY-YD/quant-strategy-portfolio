# TASK4 — 海龟交易策略（Turtle Trading Strategy）实现计划

## 0. 决策（基于推荐默认值）
- **策略深度**：简化但忠于原版（单系统）。突破 N 日高点买入、跌破 N/2 日低点卖出、2×ATR 硬止损、按 ATR 做单单位仓位管理。
- **交付形式**：完整报告包 —— Python 脚本 + 可视化 PNG + 回测/指标 CSV + 一份 `夏阳+TASK4.pdf` 图文报告（对齐 TASK1–TASK3）。
- **止损建模**：盘中触及即止损（当日 `最低价 ≤ 买入价 − 2×ATR` 即触发，以止损价成交）。

## 1. 背景与既有资产（已探查）
- **数据来源（已存储，直接复用，不重复拷贝）**：
  - 宁德时代：`TASK1/宁德时代_300750_日线数据.csv`（核心案例）
  - 平安银行：`TASK3/data/平安银行_000001.SZ_日线数据.csv`
  - 贵州茅台：`TASK3/data/贵州茅台_600519.SH_日线数据.csv`
  - 五粮液：`TASK3/data/五粮液_000858.SZ_日线数据.csv`
  - 统一列：`股票代码,交易日期,开盘价,最高价,最低价,收盘价,前收盘价,涨跌额,涨跌幅(%),成交量(手),成交额(千元)`；242 交易日（2025-07-04~2026-07-03）。
  - 加载：`pd.read_csv(path, encoding="utf-8-sig")`（含 BOM，必须用 utf-8-sig）。
- **可直接复用的 TASK3 代码范式**（`TASK3/task3_strategy.py`）：
  - `load_stock_data()`（L89）：UTF-8-SIG 加载 + 日期解析 + 排序。
  - `calc_metrics()`（L202）：MDD、Sharpe（年化 252、无风险 3%）、累计回报、年化收益、买卖次数、基准对比 —— **本任务原样复用**（其输入为 `strategy_return / drawdown / cumulative_return / signal / benchmark_value` 列，与海龟回测产出一致）。
  - 可视化约定：`COLOR_UP="#E74C3C"`(涨红)、`COLOR_DOWN="#27AE60"`(跌绿)；`plt.rcParams["font.sans-serif"]=["PingFang SC","Heiti SC","STHeiti","Arial Unicode MS"]`；`matplotlib.use("Agg")`；`os.environ["MPLCONFIGDIR"]="/tmp/matplotlib_cache"`。
  - `generate_pdf.py`：reportlab + Arial Unicode 字体（`/Library/Fonts/Arial Unicode.ttf`）+ 表格/图片封装函数，直接套用其版式。
- **运行环境**：Anaconda Python `/Applications/XYsPythonProject/anaconda3/bin/python`（pandas 2.2.3 + matplotlib 3.10.0）。若缺 `reportlab`，用该解释器 `pip install reportlab`。

## 2. 海龟策略核心设计（单系统）
| 要素 | 公式 / 规则 | 默认值 |
|---|---|---|
| 唐奇安上轨（买入通道） | `upper = 最高价.rolling(N).max().shift(1)`（前 N 日最高价，不含当日） | N=20 |
| 唐奇安下轨（卖出通道） | `lower = 最低价.rolling(M).min().shift(1)`（前 M 日最低价） | M=N/2=10 |
| ATR（真实波幅均值） | `TR=max(高-低,|高-昨收|,|低-昨收|)`；`ATR=TR.ewm(alpha=1/ATR_N,adjust=False).mean()`（Wilder 平滑） | ATR_N=N=20 |
| 买入信号 | 空仓且 `收盘价 > upper` → `signal=1`（突破 N 日高点） | — |
| 卖出信号 | 持仓且（`收盘价 < lower` **或** `最低价 ≤ 买入价−2×ATR_entry`）→ `signal=-1` | 止损=2×ATR |
| 退出原因 | 记录 `channel_exit`（破下轨）或 `stop_loss`（触 2×ATR 止损） | — |
| 仓位管理（单单位） | `shares = floor(0.01 × equity / ATR_entry)`（每笔风险 1% 权益）；`cash = equity − shares×entry` | 风险 1% |
| 净值 | 持仓日 `equity = cash + shares×收盘价`；`strategy_return = equity.pct_change()`；基准=`buy&hold` | 初始 100000 |

> 同时保留 `position` 列（0/1）以便复用 `calc_metrics`。

## 3. 交付物与文件结构
新建目录 `/Users/wangyanfen/Desktop/量化策略课程/TASK4/`：
- `task4_turtle.py` —— 主实现：加载 → 通道 → ATR → 信号 → 海龟回测 → 指标 → 绘图 → 导出 CSV。
- `task4_report.py` —— 复用 `generate_pdf.py` 版式，生成 `夏阳+TASK4.pdf`（引用上述 PNG/CSV）。
- 产出图表（`TASK4/` 下）：
  - `图1_股价_唐奇安通道_信号.png`（收盘价 + 上/下轨 + 买入^/卖出v 标记）
  - `图2_策略净值曲线.png`（策略 vs 基准）
  - `图3_回撤曲线.png`（MDD 标注）
  - `图4_综合面板.png`（4 子图：价格+通道+信号 / ATR 曲线 / 净值 / 回撤 + 指标文本框）
  - `图5_多参数对比.png`（通道周期 10/20/55 的净值+回撤）
  - `图6_多股票对比.png`（4 股票同参数净值）
  - `图7_多股票指标柱状图.png`（累计回报/MDD/Sharpe）
- 产出 CSV：
  - `宁德时代_海龟策略_N20_回测数据.csv`（含 上轨/下轨/ATR/信号/持仓/退出原因/净值/回撤…）
  - `宁德时代_多参数对比指标.csv`、`多股票策略指标对比.csv`

## 4. 执行步骤
1. **数据加载**：复用 `load_stock_data`，配置 `STOCK_FILES`（4 只股票路径见 §1）。
2. **通道 + ATR**：实现 `calc_donchian(df, N, M)` 与 `calc_atr(df, ATR_N)`。
3. **信号**：实现 `calc_turtle_signals(df, N, M)`，产出 `signal/position/exit_reason/entry_price/atr_entry`。
4. **海龟回测**：实现 `turtle_backtest(df, risk=0.01, stop_mult=2.0)`，产出 `equity/strategy_return/cumulative_return/portfolio_value/drawdown/benchmark_value`（列名对齐 TASK3 以复用 `calc_metrics`）。
5. **指标**：直接调用 TASK3 `calc_metrics`。
6. **可视化**：7 张图，样式严格沿用 TASK3 配色/字体/中文惯例；买入红^、卖出绿v。
7. **参数扫描**：`N∈{10,20,55}`（M=N/2）对比；多股票对比（4 只）。
8. **CSV 导出**：海龟回测明细 + 多参数 + 多股票指标。
9. **PDF 报告**（`task4_report.py`）：封面 + 六章（理论基础 / 核心概念解析 / 回测结果 / 参数优化 / 多股票对比 / 总结心得），图文混排，配色与 TASK3 一致。

## 5. 报告内容要点（对应任务 1/2/4 的文字要求）
- **任务1 核心思想与优势**：趋势跟随 + 波动率归一化仓位 + 严格止损；优势＝规则机械化可复制、风控量化（ATR 定止损与仓位）、捕捉大趋势、情绪中性。
- **任务2 概念解释**：高低点通道（唐奇安突破）、ATR（真实波幅均值，衡量波动）、2×ATR 止损（单笔最大风险锁定）。
- **任务4 适应场景总结**：强趋势/高波动品种（如宁德时代）表现好；震荡/低波动（如银行）易假突破亏损；长周期通道在强趋势中更优、交易少摩擦低；心得＝先看趋势再看参数、MDD/Sharpe 比累计回报更重要。

## 6. 验证清单
- [ ] 4 只股票 CSV 均能 `utf-8-sig` 正确加载，列齐全。
- [ ] 通道/ATR 无未来函数（均 `.shift(1)`）。
- [ ] 信号：买入后必有对应卖出，无悬空持仓；止损优先于通道退出。
- [ ] `calc_metrics` 复用无误，MDD≤0、Sharpe 合理。
- [ ] 7 张图均生成、中文正常、红涨绿跌。
- [ ] 3 个 CSV 导出、PDF 生成成功且图表/表格嵌入正确。
- [ ] 用 Anaconda Python 运行无报错。

## 7. 关键文件
- 新建：`/Users/wangyanfen/Desktop/量化策略课程/TASK4/task4_turtle.py`、`/Users/wangyanfen/Desktop/量化策略课程/TASK4/task4_report.py`
- 复用（只读）：`TASK3/task3_strategy.py`（`load_stock_data`/`calc_metrics` 逻辑）、`TASK3/generate_pdf.py`（PDF 版式）、`TASK1/宁德时代_300750_日线数据.csv`、`TASK3/data/*.csv`
