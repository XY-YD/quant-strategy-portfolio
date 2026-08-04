const posts = [
  {
    id: 1,
    title: "双均线策略：从入门到参数优化",
    date: "2025-06-15",
    category: "strategy",
    categoryLabel: "策略",
    tags: ["双均线", "金叉死叉", "参数寻优", "回测"],
    excerpt: "双均线交叉是最经典的量化交易策略之一。本文从基本原理出发，讨论参数选择的影响，并分享在宁德时代上实盘寻优的经验。",
    body: `
<h2>1. 什么是双均线策略</h2>
<p>双均线策略（Dual Moving Average Crossover）是技术分析中最基础的趋势跟踪策略。它的核心思想是：<strong>利用短期和长期两条移动平均线的交叉信号来判断买卖时机</strong>。</p>

<div class="highlight-box">
  <strong>核心逻辑：</strong>短期均线反映近期价格趋势，长期均线反映中长期趋势。当短期线上穿长期线（金叉），说明短期趋势走强，发出买入信号；当短期线下穿长期线（死叉），说明短期趋势转弱，发出卖出信号。
</div>

<h2>2. 数学定义</h2>
<div class="formula">SMA(n) = (P₁ + P₂ + ... + Pₙ) / n</div>
<p>其中 P 为每日收盘价，n 为窗口天数。常用参数组合包括 MA5×MA15、MA5×MA20、MA10×MA30 等。</p>

<h2>3. 参数选择的经验</h2>
<p>在宁德时代（300750.SZ）2019-2025年数据上，我们对 60+ 组参数进行了网格搜索：</p>
<ul>
  <li><strong>短周期参数</strong>：3、5、7、10、15、20 天</li>
  <li><strong>长周期参数</strong>：15、20、30、40、50、60 天</li>
  <li><strong>优化目标</strong>：最大化夏普比率</li>
</ul>

<div class="highlight-box success">
  <strong>实验结果：</strong>MA(5, 15) 组合在样本内取得了最高的夏普比率（~1.8），且回撤控制在 20% 以内。但需注意，参数对市场环境敏感，样本内最优未必等于样本外最优。
</div>

<h2>4. 策略的局限</h2>
<ul>
  <li><strong>滞后性</strong>：均线是滞后指标，金叉发生时价格已经上涨一段</li>
  <li><strong>震荡市亏损</strong>：在横盘震荡行情中频繁产生假信号</li>
  <li><strong>参数过拟合</strong>：在历史数据上过度优化，导致实盘效果不佳</li>
</ul>

<h2>5. 改进方向</h2>
<p>可以通过以下方式增强双均线策略：</p>
<ul>
  <li>加入<strong>成交量确认</strong>：金叉时成交量放大才入场</li>
  <li>加入<strong>趋势过滤</strong>：使用 ADX 指标过滤震荡行情</li>
  <li>加入<strong>止损机制</strong>：设置固定百分比止损或移动止损</li>
</ul>
`
  },
  {
    id: 2,
    title: "海龟交易系统：经典趋势跟踪策略的Python实现",
    date: "2025-06-22",
    category: "strategy",
    categoryLabel: "策略",
    tags: ["海龟交易", "唐奇安通道", "趋势跟踪", "资金管理"],
    excerpt: "海龟交易系统是 Richard Dennis 著名的趋势跟踪策略。本文用 Python 实现完整的海龟系统，包含入场、加仓、止损和退出四大模块。",
    body: `
<h2>1. 海龟交易系统概述</h2>
<p>1983年，著名交易员 Richard Dennis 和 William Eckhardt 进行了一场著名的实验——招募普通人，教他们一套简单的交易规则，结果这些"海龟"们取得了惊人的回报。这套规则就是<strong>海龟交易系统</strong>。</p>

<h2>2. 核心组件</h2>
<p>海龟系统由四个模块组成：</p>
<ol>
  <li><strong>入场（Entry）</strong>：价格突破 N 日最高价时买入（做多），突破 N 日最低价时卖出（做空）</li>
  <li><strong>止损（Stop Loss）</strong>：每笔交易最大亏损不超过账户的 2%</li>
  <li><strong>加仓（Pyramiding）</strong>：价格每上涨 0.5N，加仓一次，最多加 4 次</li>
  <li><strong>退出（Exit）</strong>：价格反向突破 M 日最低/最高价时退出</li>
</ol>

<h2>3. N 值（ATR）的计算</h2>
<div class="formula">N = ATR(20) = EMA(TR, 20)</div>
<p>True Range（TR）取以下三者的最大值：</p>
<ul>
  <li>当日最高价 - 当日最低价</li>
  <li>|当日最高价 - 昨日收盘价|</li>
  <li>|当日最低价 - 昨日收盘价|</li>
</ul>

<div class="highlight-box success">
  <strong>实战心得：</strong>N 值是海龟系统的核心参数，它同时决定了仓位大小（波动性越高，仓位越小）和止损距离，天然具有风险控制功能。
</div>

<h2>4. Python 实现要点</h2>
<pre><code># 计算 ATR(N)
df['TR'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['N'] = df['TR'].ewm(span=20).mean()

# 入场信号：突破 N 日最高价
df['entry'] = df['high'] > df['high'].rolling(20).max().shift(1)

# 止损：价格跌破入场价 - 2N
df['stop'] = df['entry_price'] - 2 * df['N']</code></pre>

<h2>5. 回测表现</h2>
<p>在宁德时代（2019-2025）数据上，海龟系统（N=20, M=10）的夏普比率为 1.2，最大回撤 18%，胜率约 40%，盈亏比约 2.5:1。<strong>低胜率、高盈亏比</strong>是典型趋势跟踪策略的特征。</p>
`
  },
  {
    id: 3,
    title: "机器学习选股实战：从特征工程到模型评估",
    date: "2025-07-05",
    category: "ml",
    categoryLabel: "机器学习",
    tags: ["特征工程", "梯度提升", "随机森林", "选股", "ROC"],
    excerpt: "如何用机器学习预测股票未来收益？本文完整记录从数据清洗、特征构造、模型训练到评估的全流程，涵盖梯度提升和随机森林两种主流方法。",
    body: `
<h2>1. 问题定义</h2>
<p>机器学习选股本质上是一个<strong>二分类问题</strong>：给定某只股票的历史特征，预测未来 N 天是否会上涨（超过某个阈值）。在我们的实验中，目标变量 Y = 未来20日收益率是否为正。</p>

<h2>2. 特征工程</h2>
<p>我们从以下维度构造了 17 个特征：</p>
<ul>
  <li><strong>价格特征</strong>：5/10/20日动量、波动率、相对强弱指标（RSI）</li>
  <li><strong>成交量特征</strong>：量比、换手率变化、OBV 指标</li>
  <li><strong>均线特征</strong>：价格与 MA5/MA20/MA60 的偏离度</li>
  <li><strong>技术指标</strong>：MACD 线差、布林带位置、ATR</li>
</ul>

<div class="highlight-box warning">
  <strong>重要提醒：</strong>特征工程是机器学习选股最关键的步骤，往往比模型选择更重要。好的特征应该具有经济含义，而非纯粹的数学变换。
</div>

<h2>3. 模型对比</h2>
<table style="width:100%;border-collapse:collapse;margin:0.75rem 0;font-size:13px;">
  <tr style="background:var(--color-bg-tertiary);">
    <th style="padding:8px;text-align:left;">模型</th>
    <th style="padding:8px;text-align:right;">准确率</th>
    <th style="padding:8px;text-align:right;">AUC</th>
    <th style="padding:8px;text-align:right;">夏普</th>
  </tr>
  <tr><td style="padding:8px;">随机森林</td><td style="padding:8px;text-align:right;">67%</td><td style="padding:8px;text-align:right;">0.73</td><td style="padding:8px;text-align:right;">0.8</td></tr>
  <tr><td style="padding:8px;">梯度提升</td><td style="padding:8px;text-align:right;">70%</td><td style="padding:8px;text-align:right;">0.77</td><td style="padding:8px;text-align:right;">1.1</td></tr>
</table>

<p>梯度提升（Gradient Boosting）在各项指标上均优于随机森林，这符合预期——集成方法中的 Boosting 通常比 Bagging 在结构化数据上表现更好。</p>

<h2>4. 过拟合风险</h2>
<p>金融数据信噪比极低，过拟合是最大的敌人。我们采用了以下防护措施：</p>
<ul>
  <li><strong>时间序列交叉验证</strong>：使用 expanding window，而非随机 k-fold</li>
  <li><strong>样本外测试</strong>：严格使用未来数据评估，不包含任何未来信息</li>
  <li><strong>特征数量控制</strong>：17 个特征，避免维数灾难</li>
</ul>
`
  },
  {
    id: 4,
    title: "参数寻优的陷阱：过拟合与样本外验证",
    date: "2025-07-12",
    category: "backtest",
    categoryLabel: "回测方法",
    tags: ["过拟合", "样本外", "交叉验证", "参数寻优", "稳健性"],
    excerpt: "在历史数据上找到的最优参数组合，实盘往往表现平平。本文讨论参数优化中的过拟合问题，以及如何通过样本外验证评估策略的真实表现。",
    body: `
<h2>1. 参数优化的蜜月陷阱</h2>
<p>我们很容易陷入这样的循环：在历史数据上反复调整参数，直到回测曲线看起来完美——年化收益 50%，夏普 3.0，回撤不到 5%。然后兴冲冲地投入实盘……结果亏损。</p>

<div class="highlight-box warning">
  <strong>这就是过拟合（Overfitting）：</strong>策略"记住"了历史数据的噪声，而非真正的市场规律。参数越多，优化次数越多，过拟合风险越大。
</div>

<h2>2. 识别过拟合的方法</h2>
<p>以下是几个实用的检验方法：</p>
<ul>
  <li><strong>样本外测试</strong>：用训练期之后的数据评估，这是最直接的方法</li>
  <li><strong>参数敏感性分析</strong>：观察参数微小变化时，策略表现是否剧烈波动</li>
  <li><strong>随机打乱检验</strong>：将收益率序列随机打乱，看策略是否仍能盈利</li>
</ul>

<h2>3. 我们的实验</h2>
<p>在 TASK7 中，我们使用 2019-2023 为样本内训练期，2024-2025 为样本外实盘模拟期：</p>

<table style="width:100%;border-collapse:collapse;margin:0.75rem 0;font-size:13px;">
  <tr style="background:var(--color-bg-tertiary);">
    <th style="padding:8px;text-align:left;">策略</th>
    <th style="padding:8px;text-align:right;">样本内夏普</th>
    <th style="padding:8px;text-align:right;">样本外夏普</th>
    <th style="padding:8px;text-align:right;">衰减</th>
  </tr>
  <tr><td style="padding:8px;">双均线(5,15)</td><td style="padding:8px;text-align:right;">1.81</td><td style="padding:8px;text-align:right;">1.12</td><td style="padding:8px;text-align:right;color:var(--color-down);">-38%</td></tr>
  <tr><td style="padding:8px;">海龟(20,10)</td><td style="padding:8px;text-align:right;">1.45</td><td style="padding:8px;text-align:right;">1.08</td><td style="padding:8px;text-align:right;color:var(--color-down);">-26%</td></tr>
</table>

<p>虽然样本外表现有所衰减，但两个策略仍然保持了正的夏普比率，说明策略具有<strong>一定的稳健性</strong>。</p>

<div class="highlight-box success">
  <strong>关键认知：</strong>样本外表现衰减是正常的，关键在于衰减后的策略是否仍然可盈利。策略的核心逻辑比参数数值更重要。
</div>
`
  },
  {
    id: 5,
    title: "策略风险管理：止损、仓位与最大回撤控制",
    date: "2025-07-20",
    category: "risk",
    categoryLabel: "风险管理",
    tags: ["止损", "仓位管理", "最大回撤", "凯利公式", "VaR"],
    excerpt: "收益是市场给的，风险是自己控制的。本文系统梳理量化策略中的风险管理方法，包括止损设置、仓位计算和最大回撤监控。",
    body: `
<h2>1. 为什么风险管理是第一位的</h2>
<p>一个简单的数学事实：如果你的账户回撤 50%，需要盈利 100% 才能回到原点。这就是为什么专业交易员把风险管理放在首位——<strong>防守决定你能在市场活多久</strong>。</p>

<h2>2. 止损策略</h2>
<p>常见的止损方法有三类：</p>
<ul>
  <li><strong>固定百分比止损</strong>：亏损超过入场价的 X% 即平仓。简单但忽略市场波动性</li>
  <li><strong>ATR 止损</strong>：止损距离 = K × ATR(N)。波动大时止损放宽，避免被"噪声"踢出</li>
  <li><strong>移动止损（Trailing Stop）</strong>：止损线随价格上涨而上移，锁定利润</li>
</ul>

<div class="highlight-box">
  <strong>实践建议：</strong>在 A 股市场，由于涨跌停板限制，建议 ATR 止损的 K 值取 2~3。对于趋势跟踪策略，止损不宜过紧，否则容易被正常回调踢出。
</div>

<h2>3. 仓位管理</h2>
<div class="formula">凯利公式：f* = (p × b - q) / b</div>
<p>其中 p = 胜率，q = 1-p，b = 盈亏比。凯利公式给出理论最优仓位比例，但实盘中建议使用<strong>半凯利（Kelly/2）</strong>以应对参数估计误差。</p>

<h2>4. 最大回撤监控</h2>
<p>最大回撤（MDD）是最直观的风险指标。我们建议设置以下风控规则：</p>
<ul>
  <li>当日回撤超过 5%，降低次日仓位至 50%</li>
  <li>累计回撤超过 15%，暂停交易一周，复盘策略</li>
  <li>累计回撤超过 25%，停止策略，重新评估</li>
</ul>
`
  }
];

document.addEventListener("DOMContentLoaded", () => {
  const grid = document.getElementById("blog-grid");
  if (!grid) return;

  let expandedId = null;

  posts.forEach((post) => {
    const card = document.createElement("div");
    card.className = "blog-card fade-in";
    card.dataset.id = post.id;
    card.innerHTML = `
      <span class="card-category ${post.category}">${post.categoryLabel}</span>
      <span class="card-date">${post.date}</span>
      <div class="card-title">${post.title}</div>
      <div class="card-excerpt">${post.excerpt}</div>
      <div class="card-tags">
        ${post.tags.map(t => `<span class="tag">${t}</span>`).join("")}
      </div>
      <div class="article-body">${post.body}</div>
      <button class="close-btn">收起 ▲</button>
    `;

    card.addEventListener("click", (e) => {
      if (e.target.classList.contains("close-btn")) {
        card.classList.remove("expanded");
        expandedId = null;
        return;
      }

      // Close previously expanded card
      if (expandedId !== null && expandedId !== post.id) {
        const prev = grid.querySelector(`[data-id="${expandedId}"]`);
        if (prev) prev.classList.remove("expanded");
      }

      // Toggle current card
      if (card.classList.contains("expanded")) {
        card.classList.remove("expanded");
        expandedId = null;
      } else {
        card.classList.add("expanded");
        expandedId = post.id;
        // Scroll to the expanded article
        setTimeout(() => {
          card.scrollIntoView({ behavior: "smooth", block: "start" });
        }, 100);
      }
    });

    grid.appendChild(card);
  });
});
