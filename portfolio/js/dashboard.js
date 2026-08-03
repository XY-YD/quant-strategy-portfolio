const DataLoader = {
  cache: {},

  async load(name) {
    if (this.cache[name]) return this.cache[name];
    try {
      const resp = await fetch(CONFIG.dataPath + name);
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      const data = await resp.json();
      this.cache[name] = data;
      return data;
    } catch (e) {
      console.error("Failed to load " + name + ": " + e.message);
      return null;
    }
  },

  async loadAll() {
    const files = [
      // TASK1
      "task1_daily.json",
      // TASK3 - per-param backtests + index + summary
      "task3_backtest_index.json", "task3_params.json", "task3_stocks.json",
      "task3_backtest_ma5_15.json", "task3_backtest_ma10_30.json", "task3_backtest_ma20_60.json",
      // TASK4 - per-param backtests + index + summary
      "task4_backtest_index.json", "task4_params.json", "task4_stocks.json",
      "task4_backtest_n10_m5.json", "task4_backtest_n20_m10.json", "task4_backtest_n55_m27.json",
      // TASK4_advanced
      "task4_advanced_backtest.json", "task4_advanced_params.json", "task4_advanced_stocks.json",
      // TASK6
      "task6_models.json",
      // TASK7
      "task7_optimization.json", "task7_comparison.json", "task7_sensitivity.json",
      // TASK8
      "task8_summary.json",
    ];
    const results = await Promise.all(files.map((f) => this.load(f)));
    const data = {};
    files.forEach((f, i) => { data[f.replace(".json", "")] = results[i]; });
    return data;
  },
};

const Dashboard = {
  data: null,
  currentTab: "dual-ma",
  // Track selected param index per tab
  currentParams: {
    "dual-ma": 0,
    "turtle": 0,
    "turtle-adv": 0,
    "ml-selection": "全部",
    "optimization": "sharpe",
  },

  // Map param index to backtest JSON key for each tab
  maBacktestKeys: ["task3_backtest_ma5_15", "task3_backtest_ma10_30", "task3_backtest_ma20_60"],
  turtleBacktestKeys: ["task4_backtest_n10_m5", "task4_backtest_n20_m10", "task4_backtest_n55_m27"],

  async init() {
    this.data = await DataLoader.loadAll();
    this.bindTabs();
    this.bindResize();
    await this.switchTab("dual-ma");
  },

  bindTabs() {
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        this.switchTab(btn.dataset.tab);
      });
    });
  },

  bindResize() {
    let timer;
    window.addEventListener("resize", () => {
      clearTimeout(timer);
      timer = setTimeout(() => Charts.resize(), 200);
    });
  },

  async switchTab(tabName) {
    this.currentTab = tabName;
    document.querySelectorAll(".tab-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.tab === tabName);
    });
    document.querySelectorAll(".tab-content").forEach((c) => {
      c.classList.toggle("active", c.id === "tab-" + tabName);
    });
    this.renderSidebar(tabName);
    await this.renderCharts(tabName);
    setTimeout(() => Charts.resize(), 100);
  },

  // --- Sidebar rendering ---

  renderSidebar(tabName) {
    const sidebar = document.getElementById("sidebar");
    const d = this.data;
    if (!d) return;

    if (tabName === "dual-ma") {
      this.renderMASidebar(sidebar, d);
    } else if (tabName === "turtle") {
      this.renderTurtleSidebar(sidebar, d);
    } else if (tabName === "turtle-adv") {
      this.renderAdvTurtleSidebar(sidebar, d);
    } else if (tabName === "ml-selection") {
      this.renderMLSidebar(sidebar, d);
    } else if (tabName === "optimization") {
      this.renderOptSidebar(sidebar, d);
    } else if (tabName === "comparison") {
      this.renderCmpSidebar(sidebar, d);
    } else if (tabName === "custom") {
      this.renderCustomSidebar(sidebar);
    }
  },

  renderMASidebar(sidebar, d) {
    const params = d.task3_params || [];
    const stocks = d.task3_stocks || [];
    const selIdx = this.currentParams["dual-ma"] || 0;
    const p = params[selIdx] || params[0] || {};
    const best = params.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), params[0] || {});
    sidebar.innerHTML = `
      <h3>策略概览</h3>
      <div class="sidebar-metrics" id="sidebar-ma-metrics">
        <div class="sidebar-metric"><div class="lbl">累计回报</div><div class="val ${p.return_pct >= 0 ? 'text-up' : 'text-down'}">${p.return_pct.toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">夏普比率</div><div class="val">${p.sharpe.toFixed(2)}</div></div>
        <div class="sidebar-metric"><div class="lbl">最大回撤</div><div class="val text-down">${p.mdd.toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">交易次数</div><div class="val">${p.buy_count || 0}</div></div>
        <div class="sidebar-metric"><div class="lbl">年化收益</div><div class="val ${p.annual_return >= 0 ? 'text-up' : 'text-down'}">${p.annual_return.toFixed(1)}%</div></div>
      </div>
      <div class="info-note">🏆 最优参数: ${best.name} (夏普${best.sharpe.toFixed(2)})</div>
      <h3>参数配置</h3>
      <div class="param-group">
        <label>均线参数 (切换后图表实时更新)</label>
        <select id="param-ma-select" onchange="Dashboard.onParamChange('dual-ma')">
          ${params.map((pm, i) => `<option value="${i}" ${i === selIdx ? 'selected' : ''}>${pm.name} (回报${pm.return_pct.toFixed(1)}% | 夏普${pm.sharpe.toFixed(2)})</option>`).join("")}
        </select>
      </div>
      <h3>数据来源</h3>
      <div class="param-group">
        <label>标的</label>
        <select disabled><option>宁德时代 300750.SZ</option></select>
      </div>
      <div class="param-group">
        <label>数据区间</label>
        <input type="text" value="2025-07-04 ~ 2026-07-03" readonly style="font-size:11px;">
      </div>
      <h3>多股票回测验证</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.8;">
        ${stocks.map(s => `${s.name}: <span class="${s.return_pct >= 0 ? 'text-up' : 'text-down'}">${s.return_pct.toFixed(1)}%</span> (夏普${s.sharpe.toFixed(2)})`).join("<br>")}
      </div>
    `;
  },

  renderTurtleSidebar(sidebar, d) {
    const params = d.task4_params || [];
    const stocks = d.task4_stocks || [];
    const selIdx = this.currentParams["turtle"] || 0;
    const p = params[selIdx] || params[0] || {};
    sidebar.innerHTML = `
      <h3>策略概览</h3>
      <div class="sidebar-metrics" id="sidebar-turtle-metrics">
        <div class="sidebar-metric"><div class="lbl">累计回报</div><div class="val ${p.return_pct >= 0 ? 'text-up' : 'text-down'}">${(p.return_pct || 0).toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">夏普比率</div><div class="val">${(p.sharpe || 0).toFixed(2)}</div></div>
        <div class="sidebar-metric"><div class="lbl">最大回撤</div><div class="val text-down">${(p.mdd || 0).toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">交易次数</div><div class="val">${p.buy_count || 0}</div></div>
        <div class="sidebar-metric"><div class="lbl">年化收益</div><div class="val ${(p.annual_return || 0) >= 0 ? 'text-up' : 'text-down'}">${(p.annual_return || 0).toFixed(1)}%</div></div>
      </div>
      <h3>通道参数</h3>
      <div class="param-group">
        <label>通道配置 (切换后图表实时更新)</label>
        <select id="param-turtle-select" onchange="Dashboard.onParamChange('turtle')">
          ${params.map((pm, i) => `<option value="${i}" ${i === selIdx ? 'selected' : ''}>${pm.name} (回报${(pm.return_pct || 0).toFixed(1)}% | 夏普${(pm.sharpe || 0).toFixed(2)})</option>`).join("")}
        </select>
      </div>
      <h3>退出原因统计</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.8;">
        ATR止损次数: <span class="text-down">${p.stop_loss_count || 0}</span><br>
        破低离场次数: <span class="text-up">${p.break_low_count || 0}</span><br>
        卖出次数: ${p.sell_count || 0}
      </div>
      <h3>多股票验证</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.8;">
        ${stocks.map(s => `${s.name}: <span class="${s.return_pct >= 0 ? 'text-up' : 'text-down'}">${s.return_pct.toFixed(1)}%</span> (夏普${s.sharpe.toFixed(2)})`).join("<br>")}
      </div>
    `;
  },

  renderAdvTurtleSidebar(sidebar, d) {
    const params = d.task4_advanced_params || [];
    const selIdx = this.currentParams["turtle-adv"] || 0;
    const p = params[selIdx] || params[0] || {};
    sidebar.innerHTML = `
      <h3>双系统海龟</h3>
      <div class="sidebar-metrics" id="sidebar-adv-metrics">
        <div class="sidebar-metric"><div class="lbl">累计回报</div><div class="val ${(p.return_pct || 0) >= 0 ? 'text-up' : 'text-down'}">${(p.return_pct || 0).toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">夏普比率</div><div class="val">${(p.sharpe || 0).toFixed(2)}</div></div>
        <div class="sidebar-metric"><div class="lbl">最大回撤</div><div class="val text-down">${(p.mdd || 0).toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">做多开仓</div><div class="val text-up">${p.long_open || 0}</div></div>
        <div class="sidebar-metric"><div class="lbl">做空开仓</div><div class="val text-down">${p.short_open || 0}</div></div>
      </div>
      <h3>系统配置</h3>
      <div class="param-group">
        <label>配置方案 (切换后图表实时更新)</label>
        <select id="param-adv-select" onchange="Dashboard.onParamChange('turtle-adv')">
          ${params.map((pm, i) => `<option value="${i}" ${i === selIdx ? 'selected' : ''}>${pm.name} (回报${(pm.return_pct || 0).toFixed(1)}% | 夏普${(pm.sharpe || 0).toFixed(2)})</option>`).join("")}
        </select>
      </div>
      <h3>S1系统(短线)</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);">
        入场: ${p.s1_entry || "-"}日 | 出场: ${p.s1_exit || "-"}日
      </div>
      <h3>S2系统(长线)</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);">
        入场: ${p.s2_entry || "-"}日 | 出场: ${p.s2_exit || "-"}日
      </div>
      <h3>交易详情</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.8;">
        多单加仓: ${p.long_add || 0}<br>
        空单加仓: ${p.short_add || 0}<br>
        平多: ${p.close_long || 0} | 平空: ${p.close_short || 0}
      </div>
    `;
  },

  renderMLSidebar(sidebar, d) {
    const models = d.task6_models || [];
    const selModel = this.currentParams["ml-selection"] || "全部";
    const best = models.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), models[0] || {});
    sidebar.innerHTML = `
      <h3>模型概览</h3>
      <div class="sidebar-metrics">
        <div class="sidebar-metric"><div class="lbl">最优模型</div><div class="val" style="font-size:13px;">${best.name || "-"}</div></div>
        <div class="sidebar-metric"><div class="lbl">最优夏普</div><div class="val text-up">${(best.sharpe || 0).toFixed(2)}</div></div>
        <div class="sidebar-metric"><div class="lbl">累计收益</div><div class="val text-up">${((best.cum_return || 0) * 100).toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">胜率</div><div class="val">${((best.win_rate || 0) * 100).toFixed(0)}%</div></div>
      </div>
      <h3>模型筛选</h3>
      <div class="param-group">
        <label>高亮模型</label>
        <select id="param-ml-select" onchange="Dashboard.onParamChange('ml-selection')">
          <option value="全部" ${selModel === '全部' ? 'selected' : ''}>全部模型</option>
          ${models.map(m => `<option value="${m.name}" ${selModel === m.name ? 'selected' : ''}>${m.name} (夏普${m.sharpe.toFixed(2)})</option>`).join("")}
        </select>
      </div>
      <h3>模型列表</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.8;">
        ${models.map(m => `${m.name}: <span class="${m.sharpe >= 0 ? 'text-up' : 'text-down'}">夏普${m.sharpe.toFixed(2)} | 收益${(m.cum_return * 100).toFixed(1)}%</span>`).join("<br>")}
      </div>
      <h3>风险提示</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.6;">
        模型指标高不代表可交易性强。应关注样本外表现和交易成本。
      </div>
    `;
  },

  renderOptSidebar(sidebar, d) {
    const opt = d.task7_optimization || [];
    const sens = d.task7_sensitivity || [];
    const cmp = d.task7_comparison || {};
    const sortBy = this.currentParams["optimization"] || "sharpe";
    const sorted = [...opt].sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
    const best = sorted[0] || {};
    sidebar.innerHTML = `
      <h3>寻优结果 Top1</h3>
      <div class="sidebar-metrics">
        <div class="sidebar-metric"><div class="lbl">短均线</div><div class="val">${best.short_ma || "-"}</div></div>
        <div class="sidebar-metric"><div class="lbl">长均线</div><div class="val">${best.long_ma || "-"}</div></div>
        <div class="sidebar-metric"><div class="lbl">最优夏普</div><div class="val text-up">${(best.sharpe || 0).toFixed(3)}</div></div>
        <div class="sidebar-metric"><div class="lbl">年化收益</div><div class="val text-up">${((best.annual_return || 0) * 100).toFixed(1)}%</div></div>
        <div class="sidebar-metric"><div class="lbl">最大回撤</div><div class="val text-down">${((best.mdd || 0) * 100).toFixed(1)}%</div></div>
      </div>
      <h3>排序依据</h3>
      <div class="param-group">
        <label>按指标排序</label>
        <select id="param-opt-sort" onchange="Dashboard.onParamChange('optimization')">
          <option value="sharpe" ${sortBy === 'sharpe' ? 'selected' : ''}>夏普比率</option>
          <option value="annual_return" ${sortBy === 'annual_return' ? 'selected' : ''}>年化收益率</option>
          <option value="calmar" ${sortBy === 'calmar' ? 'selected' : ''}>Calmar比率</option>
          <option value="sortino" ${sortBy === 'sortino' ? 'selected' : ''}>索提诺比率</option>
        </select>
      </div>
      <h3>风险指标 (最优参数)</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.8;">
        VaR95: <span class="text-down">${((best.var95 || 0) * 100).toFixed(2)}%</span><br>
        VaR99: <span class="text-down">${((best.var99 || 0) * 100).toFixed(2)}%</span><br>
        CVaR95: <span class="text-down">${((best.cvar95 || 0) * 100).toFixed(2)}%</span><br>
        Beta: ${(best.beta || 0).toFixed(3)}<br>
        Calmar: ${(best.calmar || 0).toFixed(3)}
      </div>
      <h3>成本敏感性</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.8;">
        ${sens.map(s => `滑点${s.slippage_pct.toFixed(1)}%: 夏普<span class="${s.sharpe >= 0.4 ? 'text-up' : 'text-down'}">${s.sharpe.toFixed(3)}</span>`).join("<br>")}
      </div>
    `;
  },

  renderCmpSidebar(sidebar, d) {
    // Extract comparison data from params
    const maParams = d.task3_params || [];
    const turtleParams = d.task4_params || [];
    const advParams = d.task4_advanced_params || [];
    const models = d.task6_models || [];
    const maBest = maParams.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), maParams[0] || {});
    const turtleBest = turtleParams.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), turtleParams[0] || {});
    const advBest = advParams.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), advParams[0] || {});
    const mlBest = models.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), models[0] || {});

    sidebar.innerHTML = `
      <h3>策略对比总览</h3>
      <div style="font-size:12px;line-height:2;">
        <strong>双均线(${maBest.name || 'MA5/15'})</strong><br>
        回报: <span class="${(maBest.return_pct || 0) >= 0 ? 'text-up' : 'text-down'}">${(maBest.return_pct || 0).toFixed(1)}%</span><br>
        夏普: ${(maBest.sharpe || 0).toFixed(2)} | 回撤: ${(maBest.mdd || 0).toFixed(1)}%<br><br>
        <strong>海龟(${turtleBest.name || 'N20/M10'})</strong><br>
        回报: <span class="${(turtleBest.return_pct || 0) >= 0 ? 'text-up' : 'text-down'}">${(turtleBest.return_pct || 0).toFixed(1)}%</span><br>
        夏普: ${(turtleBest.sharpe || 0).toFixed(2)} | 回辙: ${(turtleBest.mdd || 0).toFixed(1)}%<br><br>
        <strong>双系统海龟(${advBest.name || '标准'})</strong><br>
        回报: <span class="${(advBest.return_pct || 0) >= 0 ? 'text-up' : 'text-down'}">${(advBest.return_pct || 0).toFixed(1)}%</span><br>
        夏普: ${(advBest.sharpe || 0).toFixed(2)} | 回撤: ${(advBest.mdd || 0).toFixed(1)}%<br><br>
        <strong>ML选股(${mlBest.name || '梯度提升'})</strong><br>
        回报: <span class="${(mlBest.cum_return || 0) >= 0 ? 'text-up' : 'text-down'}">${((mlBest.cum_return || 0) * 100).toFixed(1)}%</span><br>
        夏普: ${(mlBest.sharpe || 0).toFixed(2)} | 回撤: ${((mlBest.mdd || 0) * 100).toFixed(1)}%
      </div>
      <h3>结论</h3>
      <div style="font-size:11px;color:var(--color-text-secondary);line-height:1.6;">
        各策略在不同市场环境下表现各异。趋势市中双均线和海龟占优，震荡市中ML选股和风控增强策略更具优势。
      </div>
      <h3>对比维度</h3>
      <div class="param-group">
        <label>雷达图维度</label>
        <select id="param-cmp-sort" onchange="Dashboard.refreshComparison()">
          <option value="all">综合对比(全部)</option>
          <option value="return">回报导向</option>
          <option value="risk">风险导向</option>
        </select>
      </div>
    `;
  },

  renderCustomSidebar(sidebar) {
    sidebar.innerHTML = `
      <h3>⚡ 自定义回测</h3>
      <div style="font-size:12px;line-height:1.8;color:var(--color-text-secondary);">
        <p>输入任意A股代码和策略参数，实时拉取最新数据并运行回测。</p>
      </div>
      <h3>使用步骤</h3>
      <div style="font-size:11px;line-height:1.8;color:var(--color-text-secondary);">
        <p>1. 确保本地 Flask 服务已启动</p>
        <p>2. 输入股票代码 (6位数字)</p>
        <p>3. 选择策略和参数</p>
        <p>4. 点击 "运行回测"</p>
      </div>
      <h3>命令行备选</h3>
      <div style="font-size:10px;color:var(--color-text-muted);line-height:1.6;">
        <code>python custom_backtest.py \\<br>
          --code 300750 \\<br>
          --strategy dual-ma \\<br>
          --params 5,15</code>
      </div>
      <h3>数据来源</h3>
      <div class="info-note">📡 Tushare Pro 实时拉取</div>
    `;
  },

  // --- Chart rendering ---

  async renderCharts(tabName) {
    const d = this.data;
    if (!d) return;
    await new Promise((r) => setTimeout(r, 50));

    if (tabName === "dual-ma") {
      const selIdx = this.currentParams["dual-ma"] || 0;
      const btKey = this.maBacktestKeys[selIdx] || this.maBacktestKeys[0];
      const bt = d[btKey];
      if (bt) Charts.renderMAPrice(bt);
      if (bt) Charts.renderNav(bt, "chart-ma-nav", "买入持有");
      if (bt) Charts.renderDrawdown(bt, "chart-ma-drawdown");
      if (d.task3_params) Charts.renderMAParams(d.task3_params);
      if (d.task3_stocks) Charts.renderMAStocks(d.task3_stocks);

    } else if (tabName === "turtle") {
      const selIdx = this.currentParams["turtle"] || 0;
      const btKey = this.turtleBacktestKeys[selIdx] || this.turtleBacktestKeys[0];
      const bt = d[btKey];
      if (bt) Charts.renderTurtlePrice(bt);
      if (bt) Charts.renderNav(bt, "chart-turtle-nav", "买入持有");
      if (bt) Charts.renderDrawdown(bt, "chart-turtle-drawdown");
      if (d.task4_params) Charts.renderTurtleParams(d.task4_params);

    } else if (tabName === "turtle-adv") {
      const bt = d.task4_advanced_backtest;
      if (bt) Charts.renderTurtleAdvPrice(bt);
      if (bt) Charts.renderNav(bt, "chart-turtle-adv-nav", "买入持有");
      if (bt) Charts.renderDrawdown(bt, "chart-turtle-adv-drawdown");
      if (d.task4_advanced_params) Charts.renderTurtleAdvParams(d.task4_advanced_params);

    } else if (tabName === "ml-selection") {
      const models = d.task6_models;
      if (models) {
        Charts.renderMLModels(models);
        Charts.renderMLReturns(models);
        Charts.renderMLRisk(models);
      }

    } else if (tabName === "optimization") {
      const sortBy = this.currentParams["optimization"] || "sharpe";
      const sorted = [...(d.task7_optimization || [])].sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
      if (sorted.length) Charts.renderOptHeatmap(sorted);
      if (d.task7_comparison) Charts.renderOptCompare(d.task7_comparison);
      if (d.task7_sensitivity) Charts.renderSensitivity(d.task7_sensitivity);

    } else if (tabName === "comparison") {
      this.renderComparisonCharts(d);
    } else if (tabName === "custom") {
      // Custom backtest tab — handled by CustomBacktest module
      // Re-check server connection when switching to this tab
      CustomBacktest.checkServer();
    }
  },

  renderComparisonCharts(d) {
    // Use per-param backtest data for comparison
    const ma = d.task3_backtest_ma5_15;
    const turtle = d.task4_backtest_n20_m10;
    const adv = d.task4_advanced_backtest;
    if (ma && turtle && adv) Charts.renderCmpNav(ma, turtle, adv);

    // Dynamic comparison data from params
    const maParams = d.task3_params || [];
    const turtleParams = d.task4_params || [];
    const advParams = d.task4_advanced_params || [];
    const models = d.task6_models || [];

    const maBest = maParams.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), maParams[0] || {});
    const turtleBest = turtleParams.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), turtleParams[0] || {});
    const advBest = advParams.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), advParams[0] || {});
    const mlBest = models.reduce((a, b) => (a.sharpe > b.sharpe ? a : b), models[0] || {});

    const cmp = {
      labels: ["双均线", "海龟", "双系统海龟", "ML选股"],
      returns: [maBest.return_pct || 0, turtleBest.return_pct || 0, advBest.return_pct || 0, (mlBest.cum_return || 0) * 100],
      sharpes: [maBest.sharpe || 0, turtleBest.sharpe || 0, advBest.sharpe || 0, mlBest.sharpe || 0],
      mdds: [maBest.mdd || 0, turtleBest.mdd || 0, advBest.mdd || 0, (mlBest.mdd || 0) * 100],
    };

    Charts.renderCmpRadar(cmp);
    Charts.renderCmpRisk(cmp);
  },

  refreshComparison() {
    if (this.currentTab === "comparison") {
      const d = this.data;
      if (d) this.renderComparisonCharts(d);
    }
  },

  // --- Unified param change handler ---

  onParamChange(tabName) {
    const d = this.data;
    if (!d) return;

    if (tabName === "dual-ma") {
      const sel = document.getElementById("param-ma-select");
      if (!sel) return;
      const idx = parseInt(sel.value);
      this.currentParams["dual-ma"] = idx;
      const params = d.task3_params || [];
      const p = params[idx];
      // Update sidebar metrics
      if (p) {
        const metrics = document.querySelectorAll("#sidebar-ma-metrics .sidebar-metric");
        const vals = [p.return_pct.toFixed(1) + "%", p.sharpe.toFixed(2), p.mdd.toFixed(1) + "%", String(p.buy_count || 0), p.annual_return.toFixed(1) + "%"];
        metrics.forEach((m, i) => { if (vals[i] !== undefined) m.querySelector(".val").textContent = vals[i]; });
      }
      // Re-render the 3 main charts with new param data
      const btKey = this.maBacktestKeys[idx];
      const bt = d[btKey];
      if (bt) {
        Charts.renderMAPrice(bt);
        Charts.renderNav(bt, "chart-ma-nav", "买入持有");
        Charts.renderDrawdown(bt, "chart-ma-drawdown");
      }
      Charts.resize();

    } else if (tabName === "turtle") {
      const sel = document.getElementById("param-turtle-select");
      if (!sel) return;
      const idx = parseInt(sel.value);
      this.currentParams["turtle"] = idx;
      const params = d.task4_params || [];
      const p = params[idx];
      if (p) {
        const metrics = document.querySelectorAll("#sidebar-turtle-metrics .sidebar-metric");
        const vals = [(p.return_pct || 0).toFixed(1) + "%", (p.sharpe || 0).toFixed(2), (p.mdd || 0).toFixed(1) + "%", String(p.buy_count || 0), (p.annual_return || 0).toFixed(1) + "%"];
        metrics.forEach((m, i) => { if (vals[i] !== undefined) m.querySelector(".val").textContent = vals[i]; });
      }
      const btKey = this.turtleBacktestKeys[idx];
      const bt = d[btKey];
      if (bt) {
        Charts.renderTurtlePrice(bt);
        Charts.renderNav(bt, "chart-turtle-nav", "买入持有");
        Charts.renderDrawdown(bt, "chart-turtle-drawdown");
      }
      Charts.resize();

    } else if (tabName === "turtle-adv") {
      const sel = document.getElementById("param-adv-select");
      if (!sel) return;
      const idx = parseInt(sel.value);
      this.currentParams["turtle-adv"] = idx;
      const params = d.task4_advanced_params || [];
      const p = params[idx];
      if (p) {
        const metrics = document.querySelectorAll("#sidebar-adv-metrics .sidebar-metric");
        const vals = [(p.return_pct || 0).toFixed(1) + "%", (p.sharpe || 0).toFixed(2), (p.mdd || 0).toFixed(1) + "%", String(p.long_open || 0), String(p.short_open || 0)];
        metrics.forEach((m, i) => { if (vals[i] !== undefined) m.querySelector(".val").textContent = vals[i]; });
      }
      Charts.resize();

    } else if (tabName === "ml-selection") {
      const sel = document.getElementById("param-ml-select");
      if (!sel) return;
      this.currentParams["ml-selection"] = sel.value;
      if (d.task6_models) Charts.renderMLModels(d.task6_models);
      Charts.resize();

    } else if (tabName === "optimization") {
      const sel = document.getElementById("param-opt-sort");
      if (!sel) return;
      this.currentParams["optimization"] = sel.value;
      const sortBy = sel.value;
      const sorted = [...(d.task7_optimization || [])].sort((a, b) => (b[sortBy] || 0) - (a[sortBy] || 0));
      if (sorted.length) Charts.renderOptHeatmap(sorted);
      Charts.resize();
    }
  },
};

// ═════════════════════════════════════════════════════════════
// Custom Backtest Module (Phase 3: Local Flask API integration)
// ═════════════════════════════════════════════════════════════

var CustomBacktest = {
  API_BASE: (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" || window.location.hostname.includes("onrender.com"))
    ? ""  // Same origin: local dev or Render
    : "https://quant-strategy-portfolio.onrender.com",  // Cross-origin: CloudStudio etc.
  serverConnected: false,
  currentResult: null,
  searchTimer: null,

  init() {
    this.checkServer();

    // Strategy switch
    var stratSel = document.getElementById("custom-strategy");
    if (stratSel) {
      stratSel.addEventListener("change", function() { CustomBacktest.onStrategyChange(this.value); });
    }

    // Stock code search (debounced)
    var codeInput = document.getElementById("custom-code");
    if (codeInput) {
      codeInput.addEventListener("input", function() {
        clearTimeout(CustomBacktest.searchTimer);
        CustomBacktest.searchTimer = setTimeout(function() {
          CustomBacktest.searchStock(codeInput.value);
        }, 400);
      });
    }
  },

  checkServer() {
    var statusEl = document.getElementById("custom-server-status");
    var self = this;
    fetch(this.API_BASE + "/api/health", { method: "GET", signal: AbortSignal.timeout(3000) })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        self.serverConnected = data.status === "ok";
        if (statusEl) {
          statusEl.className = "custom-status connected";
          statusEl.querySelector(".status-text").textContent = "服务已连接 — " + data.service + " v" + data.version;
        }
      })
      .catch(function() {
        self.serverConnected = false;
        if (statusEl) {
          statusEl.className = "custom-status disconnected";
          statusEl.querySelector(".status-text").textContent = "未连接 — 请在终端运行 python backtest_server.py --port 8081";
        }
      });
  },

  onStrategyChange(strategy) {
    var maParams = document.getElementById("params-dual-ma");
    var turtleParams = document.getElementById("params-turtle");
    if (strategy === "dual-ma") {
      if (maParams) maParams.classList.remove("hidden");
      if (turtleParams) turtleParams.classList.add("hidden");
    } else {
      if (maParams) maParams.classList.add("hidden");
      if (turtleParams) turtleParams.classList.remove("hidden");
    }
  },

  searchStock(keyword) {
    if (!keyword || keyword.length < 1) return;
    var resultsEl = document.getElementById("code-search-results");
    var self = this;
    fetch(this.API_BASE + "/api/stocks?q=" + encodeURIComponent(keyword))
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (!data.success || !data.results || !data.results.length) {
          if (resultsEl) resultsEl.classList.remove("show");
          return;
        }
        var html = "";
        data.results.forEach(function(s) {
          html += '<div class="code-search-item" data-code="' + s.symbol + '" data-name="' + s.name + '">' +
            s.name + '<span class="code">' + s.symbol + " " + (s.industry || "") + '</span></div>';
        });
        if (resultsEl) {
          resultsEl.innerHTML = html;
          resultsEl.classList.add("show");
          resultsEl.querySelectorAll(".code-search-item").forEach(function(item) {
            item.addEventListener("click", function() {
              var codeInput = document.getElementById("custom-code");
              var nameHint = document.getElementById("stock-name-hint");
              if (codeInput) codeInput.value = this.dataset.code;
              if (nameHint) nameHint.textContent = this.dataset.name;
              if (resultsEl) resultsEl.classList.remove("show");
            });
          });
        }
      })
      .catch(function() {
        if (resultsEl) resultsEl.classList.remove("show");
      });
  },

  run() {
    if (!this.serverConnected) {
      this.showError("请先启动本地 Flask 回测服务", true);
      return;
    }

    var code = document.getElementById("custom-code").value.trim();
    var strategy = document.getElementById("custom-strategy").value;
    var startDate = document.getElementById("custom-start").value;
    var endDate = document.getElementById("custom-end").value;
    var capital = parseFloat(document.getElementById("custom-capital").value) || 100000;

    if (!code) { alert("请输入股票代码"); return; }

    // Build params
    var params = {};
    if (strategy === "dual-ma") {
      params.short = parseInt(document.getElementById("param-ma-short").value) || 5;
      params.long = parseInt(document.getElementById("param-ma-long").value) || 15;
    } else {
      params.N = parseInt(document.getElementById("param-turtle-n").value) || 20;
      params.M = parseInt(document.getElementById("param-turtle-m").value) || 10;
      params.stop_mult = parseFloat(document.getElementById("param-turtle-stop").value) || 2.0;
    }

    // Show loading
    document.getElementById("custom-results").classList.add("hidden");
    document.getElementById("custom-error").classList.add("hidden");
    document.getElementById("custom-loading").classList.remove("hidden");
    var btn = document.getElementById("btn-run-backtest");
    if (btn) { btn.disabled = true; btn.textContent = "⏳ 运行中..."; }

    var self = this;
    fetch(this.API_BASE + "/api/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code, strategy: strategy, params: params, start_date: startDate, end_date: endDate, capital: capital }),
    })
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (btn) { btn.disabled = false; btn.textContent = "🚀 运行回测"; }
        document.getElementById("custom-loading").classList.add("hidden");

        if (!data.success) {
          self.showError(data.error || "回测失败", false);
          return;
        }

        self.currentResult = data;
        self.renderResults(data);
      })
      .catch(function(err) {
        if (btn) { btn.disabled = false; btn.textContent = "🚀 运行回测"; }
        document.getElementById("custom-loading").classList.add("hidden");
        self.showError("无法连接到本地服务: " + err.message, true);
      });
  },

  formatMetric(name, value) {
    if (value === null || value === undefined || (typeof value === "number" && isNaN(value))) return "—";
    if (typeof value !== "number") return String(value);
    // 次数类 → 整数
    if (name.indexOf("次数") > -1 || name.indexOf("天数") > -1) return Math.round(value);
    // 百分比类 → 2位小数 + %
    if (name.indexOf("回报") > -1 || name.indexOf("收益率") > -1 || name.indexOf("MDD") > -1 || name.indexOf("回撤") > -1 || name.indexOf("涨跌幅") > -1) {
      return Number(value).toFixed(2) + "%";
    }
    // 比率类 → 2位小数
    if (name.indexOf("比率") > -1 || name.indexOf("Ratio") > -1) return Number(value).toFixed(2);
    // 默认 → 2位小数
    return Number(value).toFixed(2);
  },

  renderResults(data) {
    document.getElementById("custom-results").classList.remove("hidden");
    document.getElementById("custom-error").classList.add("hidden");

    // Update title
    var title = document.getElementById("custom-result-title");
    if (title) title.textContent = data.code + " — " + data.strategy + " 回测结果 (参数: " + data.params + ")";

    // Render charts
    var d = data.data;
    var idx = data.indicators;

    // Price chart with signals
    var priceChart = echarts.init(document.getElementById("chart-custom-price"));
    var priceOpt = {
      tooltip: { trigger: "axis" },
      grid: { left: 60, right: 30, top: 20, bottom: 40 },
      xAxis: { type: "category", data: d.dates, axisLabel: { rotate: 30, fontSize: 10, formatter: function(v) { return v.substring(5); } } },
      yAxis: { type: "value", name: "价格(元)" },
      dataZoom: [{ type: "inside" }, { type: "slider", bottom: 5 }],
      series: [
        { name: "收盘价", type: "line", data: d.close, lineStyle: { color: "#333", width: 1 }, itemStyle: { color: "#333" }, symbol: "none" },
      ],
    };
    if (idx.ma_short && idx.ma_short.length > 0) {
      priceOpt.series.push({ name: "MA-短", type: "line", data: idx.ma_short, lineStyle: { color: "#e74c3c", width: 1 }, symbol: "none" });
      priceOpt.series.push({ name: "MA-长", type: "line", data: idx.ma_long, lineStyle: { color: "#3498db", width: 1 }, symbol: "none" });
    }
    if (idx.upper && idx.upper.length > 0) {
      priceOpt.series.push({ name: "上轨", type: "line", data: idx.upper, lineStyle: { color: "#e74c3c", type: "dashed", width: 0.8 }, symbol: "none" });
      priceOpt.series.push({ name: "下轨", type: "line", data: idx.lower, lineStyle: { color: "#27ae60", type: "dashed", width: 0.8 }, symbol: "none" });
    }
    // Signals as scatter
    var buyData = [], sellData = [];
    d.signals.forEach(function(s, i) {
      if (s === 1) buyData.push({ value: [d.dates[i], d.close[i]], symbol: "triangle", symbolSize: 10, itemStyle: { color: "#e74c3c" } });
      else if (s === -1) sellData.push({ value: [d.dates[i], d.close[i]], symbol: "triangle", symbolSize: 10, symbolRotate: 180, itemStyle: { color: "#27ae60" } });
    });
    if (buyData.length) priceOpt.series.push({ name: "买入", type: "scatter", data: buyData, z: 5 });
    if (sellData.length) priceOpt.series.push({ name: "卖出", type: "scatter", data: sellData, z: 5 });
    priceChart.setOption(priceOpt);

    // NAV chart
    var navChart = echarts.init(document.getElementById("chart-custom-nav"));
    navChart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: "category", data: d.dates, axisLabel: { rotate: 30, fontSize: 10, formatter: function(v) { return v.substring(5); } } },
      yAxis: { type: "value", name: "净值(元)" },
      series: [
        { name: "策略净值", type: "line", data: d.nav, lineStyle: { color: "#e74c3c", width: 1.5 }, areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: "rgba(231,76,60,0.3)" }, { offset: 1, color: "rgba(231,76,60,0.02)" }] } }, symbol: "none" },
      ],
    });

    // Drawdown chart
    var ddChart = echarts.init(document.getElementById("chart-custom-drawdown"));
    ddChart.setOption({
      tooltip: { trigger: "axis", valueFormatter: function(v) { return (v * 100).toFixed(2) + "%"; } },
      grid: { left: 50, right: 20, top: 20, bottom: 30 },
      xAxis: { type: "category", data: d.dates, axisLabel: { rotate: 30, fontSize: 10, formatter: function(v) { return v.substring(5); } } },
      yAxis: { type: "value", name: "回撤(%)", axisLabel: { formatter: function(v) { return (v * 100).toFixed(0) + "%"; } } },
      series: [
        { name: "回撤", type: "line", data: d.drawdown, lineStyle: { color: "#e74c3c", width: 1 }, areaStyle: { color: "rgba(231,76,60,0.2)" }, symbol: "none" },
      ],
    });

    // Metrics cards
    var metricsEl = document.getElementById("custom-metrics");
    if (metricsEl && data.metrics) {
      var html = "";
      Object.keys(data.metrics).forEach(function(k) {
        var v = data.metrics[k];
        var cls = "metric-card";
        if (typeof v === "number" && k.indexOf("回报") > -1 && v >= 0) cls += " positive";
        else if (typeof v === "number" && k.indexOf("回报") > -1 && v < 0) cls += " negative";
        html += '<div class="' + cls + '"><div class="metric-value">' + CustomBacktest.formatMetric(k, v) + '</div><div class="metric-label">' + k + '</div></div>';
      });
      metricsEl.innerHTML = html;
    }

    Charts.resize();
  },

  showError(msg, isSetup) {
    document.getElementById("custom-error").classList.remove("hidden");
    document.getElementById("custom-results").classList.add("hidden");
    document.getElementById("custom-error-msg").textContent = msg;
    var guide = document.getElementById("custom-setup-guide");
    if (guide) guide.style.display = isSetup ? "block" : "none";
  },

  updateData() {
    var code = document.getElementById("update-code").value.trim() || "300750";
    var btn = document.getElementById("btn-update-data");
    var statusEl = document.getElementById("update-status");
    if (btn) { btn.disabled = true; btn.textContent = "⏳ 更新中..."; }
    if (statusEl) statusEl.textContent = "正在连接 Tushare 获取最新数据...";

    fetch(this.API_BASE + "/api/update-data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code }),
    })
      .then(function(resp) {
        if (!resp.ok) return resp.json().then(function(e) { throw new Error(e.error || "HTTP " + resp.status); });
        return resp.json();
      })
      .then(function(result) {
        var msg = "";
        if (result.success && result.new_rows > 0) {
          msg = "✅ 新增 " + result.new_rows + " 条数据，最新日期: " + result.latest_date;
          if (result.json_rebuilt) msg += "，JSON 已重建";
        } else if (result.success && result.new_rows === 0) {
          msg = "✅ " + (result.message || "数据已是最新");
        } else {
          msg = "❌ " + (result.error || "更新失败");
        }
        if (statusEl) statusEl.textContent = msg;
        if (btn) { btn.disabled = false; btn.textContent = "🔄 更新数据"; }
      })
      .catch(function(err) {
        if (statusEl) statusEl.textContent = "❌ " + err.message;
        if (btn) { btn.disabled = false; btn.textContent = "🔄 更新数据"; }
      });
  },
};

document.addEventListener("DOMContentLoaded", function() {
  Dashboard.init();
  CustomBacktest.init();
});
