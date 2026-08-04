# 量化策略课程作品集

> 基于 Python 的 A 股量化交易策略回测系统，包含 8 个策略任务、交互式可视化看板和实时自定义回测 API。

## 在线访问

- **Vercel（推荐）**: https://quant-strategy-portfolio.vercel.app — CDN 加速，零冷启动
- **Render（全栈）**: https://quant-strategy-portfolio.onrender.com — 含自定义回测 API
- **CloudStudio（备份）**: https://03cd4b9750134b478a48257b546867ac.gz1.agentos-app.net
- **代码仓库**: https://github.com/XY-YD/quant-strategy-portfolio

## 项目结构

```
量化策略课程/
├── TASK1/              # 数据获取与基础分析（Tushare API + 数据探索）
├── TASK2/              # 技术指标计算（MA/EMA/MACD/RSI/BOLL/ATR）
├── TASK3/              # 双均线交叉策略（参数优化 + 回测引擎）
├── TASK4/              # 海龟交易策略（唐奇安通道 + 仓位管理）
├── TASK4_advanced/     # 海龟策略增强版（双系统 + 止损优化）
├── TASK5/              # 机器学习分类模型（逻辑回归/SVM/随机森林/XGBoost）
├── TASK6/              # ML 选股策略（多因子特征工程 + 模型选股）
├── TASK7/              # 策略寻优与实盘模拟（样本内外检验 + 参数敏感性）
├── TASK8/              # 综合学习报告（PDF 生成 + 策略总结）
├── portfolio/          # 交互式可视化网站
│   ├── index.html      # 作品集主页（项目展示 + 图表画廊）
│   ├── dashboard.html  # 交互看板（7 个 Tab + ECharts 图表）
│   ├── js/             # 前端逻辑（config.js / charts.js / portfolio.js / dashboard.js）
│   ├── css/            # 样式文件
│   └── data/           # 回测结果 JSON（由 convert_data.py 生成）
├── backtest_server.py  # Flask 回测 API 服务（自定义回测 + 数据更新）
├── custom_backtest.py  # 命令行回测工具
├── update_data.py      # Tushare 数据增量更新工具
├── convert_data.py     # CSV -> JSON 数据转换管线
└── requirements.txt    # Python 依赖
```

## 技术栈

| 层 | 技术 | 说明 |
|---|------|------|
| 数据采集 | Tushare Pro API | A 股日线行情数据（OHLCV） |
| 策略计算 | Python + pandas | 双均线/海龟/ML选股/参数寻优 |
| 图表生成 | matplotlib | 离线生成 PNG 策略报告图 |
| 数据转换 | convert_data.py | CSV → JSON 前端数据管线 |
| 前端图表 | ECharts 5.5.0 | 浏览器端交互式可视化 |
| 前端框架 | 原生 HTML/CSS/JS | 零构建依赖，轻量高效 |
| 后端 API | Flask | 实时回测 + 数据更新服务 |
| 部署 | CloudStudio / Render | 静态网站 + API 云端托管 |

## 快速开始

### 1. 环境准备

```bash
# 克隆仓库
git clone https://github.com/XY-YD/quant-strategy-portfolio.git
cd quant-strategy-portfolio

# 安装依赖
pip install -r requirements.txt

# 配置 Tushare Token
cp local_config.example.py local_config.py
# 编辑 local_config.py，填入你的 Tushare Token（从 https://tushare.pro/ 获取）
```

### 2. 启动本地服务

```bash
# 启动 Flask 服务（同时提供网页 + API）
python backtest_server.py --port 8081

# 浏览器打开
# http://localhost:8081/
```

### 3. 更新数据

```bash
# 命令行方式
python update_data.py --code 300750

# 或在网页"自定义回测"Tab 中点击"更新数据"按钮
```

## 策略概览

| 策略 | 任务 | 核心逻辑 |
|------|------|---------|
| 双均线交叉 | TASK3 | MA 短线穿越长线产生买卖信号 |
| 海龟交易 | TASK4 | 唐奇安通道突破 + ATR 仓位管理 |
| 海龟增强 | TASK4+ | 双系统（入场/离场）+ 动态止损 |
| ML 分类 | TASK5 | 逻辑回归/SVM/RF/XGBoost 对比 |
| ML 选股 | TASK6 | 多因子特征工程 + 模型预测涨跌 |
| 参数寻优 | TASK7 | 样本内网格寻优 + 样本外实盘模拟 |

## 交互看板功能

- **Tab 1-6**: 预计算策略结果展示，支持参数切换联动图表
- **Tab 7 (自定义回测)**: 实时输入股票代码 + 策略 + 参数，后端即时计算返回
- **数据更新**: 网页端一键拉取 Tushare 最新数据

## 作者

- GitHub: [@XY-YD](https://github.com/XY-YD)

## License

MIT
