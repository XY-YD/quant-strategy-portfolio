const Charts = {
  instances: {},

  init(id) {
    if (this.instances[id]) this.instances[id].dispose();
    const el = document.getElementById(id);
    if (!el) return null;
    const chart = echarts.init(el);
    this.instances[id] = chart;
    return chart;
  },

  resize() {
    Object.values(this.instances).forEach((c) => c && c.resize());
  },

  renderMAPrice(data) {
    const chart = this.init("chart-ma-price");
    if (!chart) return;
    const dates = data.dates;
    const buySignals = [];
    const sellSignals = [];
    dates.forEach((d, i) => {
      if (data.signals[i] === 1) buySignals.push({ coord: [d, data.close[i]], value: "买" });
      if (data.signals[i] === -1) sellSignals.push({ coord: [d, data.close[i]], value: "卖" });
    });
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { data: ["收盘价", "MA5", "MA15"], top: 5 },
      grid: { left: 60, right: 30, top: 40, bottom: 60 },
      xAxis: { type: "category", data: dates, axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: { type: "value", scale: true },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 10 }],
      series: [
        { name: "收盘价", type: "line", data: data.close, lineStyle: { width: 1, color: "#888" }, symbol: "none" },
        { name: "MA5", type: "line", data: data.ma5, lineStyle: { width: 1.5, color: CONFIG.colors.up }, symbol: "none" },
        { name: "MA15", type: "line", data: data.ma15, lineStyle: { width: 1.5, color: CONFIG.colors.info }, symbol: "none",
          markPoint: { data: [...buySignals, ...sellSignals], symbolSize: 12,
            itemStyle: { color: function(p) { return p.value === "买" ? CONFIG.colors.down : CONFIG.colors.up; } },
            label: { show: true, formatter: "{value}", fontSize: 9, color: "#fff" } } },
      ],
    });
  },

  renderNav(data, containerId, benchmarkLabel) {
    const chart = this.init(containerId);
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: ["策略净值", benchmarkLabel || "基准"], top: 5 },
      grid: { left: 60, right: 30, top: 40, bottom: 30 },
      xAxis: { type: "category", data: data.dates, axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: { type: "value", scale: true },
      series: [
        { name: "策略净值", type: "line", data: data.nav, lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "none", areaStyle: { opacity: 0.05 } },
      ],
    });
  },

  renderDrawdown(data, containerId) {
    const chart = this.init(containerId);
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis" },
      grid: { left: 60, right: 30, top: 30, bottom: 30 },
      xAxis: { type: "category", data: data.dates, axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: { type: "value", max: 0 },
      series: [{
        type: "line", data: data.drawdown, lineStyle: { width: 1.5, color: CONFIG.colors.up },
        areaStyle: { color: CONFIG.colors.up, opacity: 0.1 }, symbol: "none",
      }],
    });
  },

  renderMAParams(params) {
    const chart = this.init("chart-ma-params");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["累计回报%", "年化收益%", "最大回撤%", "夏普比率"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: params.map(p => p.name) },
      yAxis: [
        { type: "value", name: "收益/回撤%", position: "left" },
        { type: "value", name: "夏普", position: "right" },
      ],
      series: [
        { name: "累计回报%", type: "bar", data: params.map(p => p.return_pct), itemStyle: { color: CONFIG.colors.up } },
        { name: "年化收益%", type: "bar", data: params.map(p => p.annual_return), itemStyle: { color: CONFIG.colors.accent } },
        { name: "最大回撤%", type: "bar", data: params.map(p => p.mdd), itemStyle: { color: CONFIG.colors.down } },
        { name: "夏普比率", type: "line", yAxisIndex: 1, data: params.map(p => p.sharpe), lineStyle: { width: 2, color: CONFIG.colors.warning }, symbol: "circle", symbolSize: 8 },
      ],
    });
  },

  renderMAStocks(stocks) {
    const chart = this.init("chart-ma-stocks");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["策略累计回报%", "基准回报%", "夏普比率"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: stocks.map(s => s.name) },
      yAxis: [
        { type: "value", name: "回报%" },
        { type: "value", name: "夏普", position: "right" },
      ],
      series: [
        { name: "策略累计回报%", type: "bar", data: stocks.map(s => s.return_pct), itemStyle: { color: function(p) { return p.value >= 0 ? CONFIG.colors.up : CONFIG.colors.down; } } },
        { name: "基准回报%", type: "bar", data: stocks.map(s => s.benchmark_return), itemStyle: { color: "#adb5bd" } },
        { name: "夏普比率", type: "line", yAxisIndex: 1, data: stocks.map(s => s.sharpe), lineStyle: { width: 2, color: CONFIG.colors.warning }, symbol: "circle", symbolSize: 8 },
      ],
    });
  },

  renderTurtlePrice(data) {
    const chart = this.init("chart-turtle-price");
    if (!chart) return;
    const dates = data.dates;
    const buySignals = [];
    const sellSignals = [];
    dates.forEach((d, i) => {
      if (data.signals[i] === 1) buySignals.push({ coord: [d, data.close[i]] });
      if (data.signals[i] === -1) {
        const reason = data.exit_reasons[i] || "";
        sellSignals.push({ coord: [d, data.close[i]], value: reason.includes("止损") ? "止损" : "离场" });
      }
    });
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { data: ["收盘价", "上轨(20日高)", "下轨(10日低)", "ATR"], top: 5 },
      grid: { left: 60, right: 60, top: 40, bottom: 60 },
      xAxis: { type: "category", data: dates, axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: [{ type: "value", scale: true, name: "价格" }, { type: "value", name: "ATR", position: "right" }],
      dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 10 }],
      series: [
        { name: "收盘价", type: "line", data: data.close, lineStyle: { width: 1, color: "#888" }, symbol: "none" },
        { name: "上轨(20日高)", type: "line", data: data.upper, lineStyle: { width: 1, color: CONFIG.colors.up, type: "dashed" }, symbol: "none" },
        { name: "下轨(10日低)", type: "line", data: data.lower, lineStyle: { width: 1, color: CONFIG.colors.down, type: "dashed" }, symbol: "none" },
        { name: "ATR", type: "bar", yAxisIndex: 1, data: data.atr, itemStyle: { color: "#fac775", opacity: 0.4 } },
        { type: "line", data: [], markPoint: { data: [...buySignals, ...sellSignals], symbolSize: 12,
          itemStyle: { color: function(p) { return p.value === "止损" ? CONFIG.colors.warning : (p.value === "离场" ? CONFIG.colors.down : CONFIG.colors.up); } },
          label: { show: true, formatter: "{value}", fontSize: 8, color: "#fff" } } },
      ],
    });
  },

  renderTurtleParams(params) {
    const chart = this.init("chart-turtle-params");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["累计回报%", "最大回撤%", "夏普比率", "止损次数", "破低次数"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: params.map(p => p.name) },
      yAxis: [
        { type: "value", name: "回报/回撤%" },
        { type: "value", name: "次数/夏普", position: "right" },
      ],
      series: [
        { name: "累计回报%", type: "bar", data: params.map(p => p.return_pct), itemStyle: { color: CONFIG.colors.up } },
        { name: "最大回撤%", type: "bar", data: params.map(p => p.mdd), itemStyle: { color: CONFIG.colors.down } },
        { name: "夏普比率", type: "line", yAxisIndex: 1, data: params.map(p => p.sharpe), lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "circle", symbolSize: 8 },
        { name: "止损次数", type: "bar", yAxisIndex: 1, data: params.map(p => p.stop_loss_count), itemStyle: { color: CONFIG.colors.warning } },
        { name: "破低次数", type: "bar", yAxisIndex: 1, data: params.map(p => p.break_low_count), itemStyle: { color: "#adb5bd" } },
      ],
    });
  },

  renderTurtleAdvPrice(data) {
    const chart = this.init("chart-turtle-adv-price");
    if (!chart) return;
    const dates = data.dates;
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { data: ["收盘价", "ATR", "净值"], top: 5 },
      grid: { left: 60, right: 60, top: 40, bottom: 60 },
      xAxis: { type: "category", data: dates, axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: [{ type: "value", scale: true, name: "价格/净值" }, { type: "value", name: "ATR", position: "right" }],
      dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 10 }],
      series: [
        { name: "收盘价", type: "line", data: data.close, lineStyle: { width: 1, color: "#888" }, symbol: "none" },
        { name: "净值", type: "line", data: data.nav, yAxisIndex: 0, lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "none", areaStyle: { opacity: 0.03 } },
        { name: "ATR", type: "bar", yAxisIndex: 1, data: data.atr, itemStyle: { color: "#fac775", opacity: 0.4 } },
      ],
    });
  },

  renderTurtleAdvParams(params) {
    const chart = this.init("chart-turtle-adv-params");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["累计回报%", "最大回撤%", "夏普", "做多开仓", "做空开仓"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: params.map(p => p.name) },
      yAxis: [
        { type: "value", name: "回报/回撤%" },
        { type: "value", name: "次数/夏普", position: "right" },
      ],
      series: [
        { name: "累计回报%", type: "bar", data: params.map(p => p.return_pct), itemStyle: { color: function(d) { return d.value >= 0 ? CONFIG.colors.up : CONFIG.colors.down; } } },
        { name: "最大回撤%", type: "bar", data: params.map(p => p.mdd), itemStyle: { color: CONFIG.colors.warning } },
        { name: "夏普", type: "line", yAxisIndex: 1, data: params.map(p => p.sharpe), lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "circle", symbolSize: 8 },
        { name: "做多开仓", type: "bar", yAxisIndex: 1, data: params.map(p => p.long_open), itemStyle: { color: CONFIG.colors.up, opacity: 0.6 } },
        { name: "做空开仓", type: "bar", yAxisIndex: 1, data: params.map(p => p.short_open), itemStyle: { color: CONFIG.colors.down, opacity: 0.6 } },
      ],
    });
  },

  renderMLModels(models) {
    const chart = this.init("chart-ml-models");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["累计收益%", "年化收益%", "夏普", "超额夏普"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: models.map(m => m.name) },
      yAxis: [
        { type: "value", name: "收益%" },
        { type: "value", name: "夏普", position: "right" },
      ],
      series: [
        { name: "累计收益%", type: "bar", data: models.map(m => (m.cum_return * 100).toFixed(2)), itemStyle: { color: function(p) { return p.value >= 0 ? CONFIG.colors.up : CONFIG.colors.down; } } },
        { name: "年化收益%", type: "bar", data: models.map(m => (m.annual_return * 100).toFixed(2)), itemStyle: { color: CONFIG.colors.accent, opacity: 0.7 } },
        { name: "夏普", type: "line", yAxisIndex: 1, data: models.map(m => m.sharpe), lineStyle: { width: 2, color: CONFIG.colors.warning }, symbol: "circle", symbolSize: 8 },
        { name: "超额夏普", type: "line", yAxisIndex: 1, data: models.map(m => m.excess_sharpe), lineStyle: { width: 2, color: CONFIG.colors.info, type: "dashed" }, symbol: "diamond", symbolSize: 8 },
      ],
    });
  },

  renderMLReturns(models) {
    const chart = this.init("chart-ml-returns");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: ["累计收益%", "夏普比率"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: models.map(m => m.name) },
      yAxis: [{ type: "value", name: "收益%" }, { type: "value", name: "夏普", position: "right" }],
      series: [
        { name: "累计收益%", type: "bar", data: models.map(m => (m.cum_return * 100).toFixed(2)), itemStyle: { color: CONFIG.colors.up }, barWidth: "40%" },
        { name: "夏普比率", type: "line", yAxisIndex: 1, data: models.map(m => m.sharpe), lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "circle", symbolSize: 10 },
      ],
    });
  },

  renderMLRisk(models) {
    const chart = this.init("chart-ml-risk");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: ["最大回撤%", "胜率%"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: models.map(m => m.name) },
      yAxis: [{ type: "value", name: "回撤%" }, { type: "value", name: "胜率%", position: "right", max: 100 }],
      series: [
        { name: "最大回撤%", type: "bar", data: models.map(m => (m.mdd * 100).toFixed(2)), itemStyle: { color: CONFIG.colors.down }, barWidth: "40%" },
        { name: "胜率%", type: "line", yAxisIndex: 1, data: models.map(m => (m.win_rate * 100).toFixed(1)), lineStyle: { width: 2, color: CONFIG.colors.up }, symbol: "circle", symbolSize: 10 },
      ],
    });
  },

  renderOptHeatmap(data) {
    const chart = this.init("chart-opt-heatmap");
    if (!chart) return;
    const shortSet = [...new Set(data.map(d => d.short_ma))].sort((a, b) => a - b);
    const longSet = [...new Set(data.map(d => d.long_ma))].sort((a, b) => a - b);
    const heatData = [];
    data.forEach(d => {
      const si = shortSet.indexOf(d.short_ma);
      const li = longSet.indexOf(d.long_ma);
      if (si >= 0 && li >= 0) heatData.push([li, si, parseFloat(d.sharpe.toFixed(3))]);
    });
    const maxVal = Math.max(...heatData.map(d => d[2]));
    const minVal = Math.min(...heatData.map(d => d[2]));
    chart.setOption({
      tooltip: { position: "top", formatter: function(p) {
        const idx = p.data;
        return `短均线: ${shortSet[idx[1]]}<br>长均线: ${longSet[idx[0]]}<br>夏普: ${idx[2]}`;
      }},
      grid: { left: 60, right: 30, top: 30, bottom: 50 },
      xAxis: { type: "category", data: longSet.map(String), name: "长均线", splitArea: { show: true } },
      yAxis: { type: "category", data: shortSet.map(String), name: "短均线", splitArea: { show: true } },
      visualMap: { min: minVal, max: maxVal, calculable: true, orient: "horizontal", left: "center", bottom: 0,
        inRange: { color: ["#27ae60", "#fac775", "#e74c3c"] } },
      series: [{
        type: "heatmap", data: heatData,
        label: { show: true, fontSize: 9 },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: "rgba(0,0,0,0.5)" } },
      }],
    });
  },

  renderOptCompare(data) {
    const chart = this.init("chart-opt-compare");
    if (!chart) return;
    const metrics = ["累计收益", "年化收益", "夏普", "最大回撤", "交易次数"];
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: ["样本内最优", "样本外最优", "样本外默认5/15"], top: 5 },
      grid: { left: 60, right: 30, top: 40, bottom: 30 },
      xAxis: { type: "category", data: metrics },
      yAxis: { type: "value" },
      series: [
        { name: "样本内最优", type: "bar", data: metrics.map(m => data[m] ? data[m].in_sample_optimal : 0), itemStyle: { color: CONFIG.colors.up } },
        { name: "样本外最优", type: "bar", data: metrics.map(m => data[m] ? data[m].out_sample_optimal : 0), itemStyle: { color: CONFIG.colors.accent } },
        { name: "样本外默认5/15", type: "bar", data: metrics.map(m => data[m] ? data[m].out_sample_default : 0), itemStyle: { color: CONFIG.colors.info } },
      ],
    });
  },

  renderSensitivity(data) {
    const chart = this.init("chart-opt-sensitivity");
    if (!chart) return;
    chart.setOption({
      tooltip: { trigger: "axis" },
      legend: { data: ["年化收益%", "夏普", "最大回撤%"], top: 5 },
      grid: { left: 60, right: 60, top: 40, bottom: 30 },
      xAxis: { type: "category", data: data.map(d => (d.slippage_pct).toFixed(1) + "%"), name: "滑点" },
      yAxis: [
        { type: "value", name: "收益/回撤%" },
        { type: "value", name: "夏普", position: "right" },
      ],
      series: [
        { name: "年化收益%", type: "line", data: data.map(d => (d.annual_return * 100).toFixed(2)), lineStyle: { width: 2, color: CONFIG.colors.up }, symbol: "circle", symbolSize: 8 },
        { name: "夏普", type: "line", yAxisIndex: 1, data: data.map(d => d.sharpe.toFixed(3)), lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "circle", symbolSize: 8 },
        { name: "最大回撤%", type: "line", data: data.map(d => (d.mdd * 100).toFixed(2)), lineStyle: { width: 2, color: CONFIG.colors.down }, symbol: "circle", symbolSize: 8 },
      ],
    });
  },

  renderCmpNav(dataMA, dataTurtle, dataTurtleAdv) {
    const chart = this.init("chart-cmp-nav");
    if (!chart) return;
    const dates = dataMA.dates;
    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { data: ["双均线(MA5/15)", "海龟(N20/M10)", "双系统海龟"], top: 5 },
      grid: { left: 60, right: 30, top: 40, bottom: 60 },
      xAxis: { type: "category", data: dates, axisLabel: { rotate: 30, fontSize: 10 } },
      yAxis: { type: "value", scale: true, name: "净值" },
      dataZoom: [{ type: "inside" }, { type: "slider", height: 20, bottom: 10 }],
      series: [
        { name: "双均线(MA5/15)", type: "line", data: dataMA.nav, lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "none" },
        { name: "海龟(N20/M10)", type: "line", data: dataTurtle.nav, lineStyle: { width: 2, color: CONFIG.colors.warning }, symbol: "none" },
        { name: "双系统海龟", type: "line", data: dataTurtleAdv.nav, lineStyle: { width: 2, color: CONFIG.colors.info }, symbol: "none" },
      ],
    });
  },

  renderCmpRadar(cmpData) {
    // cmpData: { labels: [str,...], returns: [num,...], sharpes: [num,...], mdds: [num,...] }
    const chart = this.init("chart-cmp-radar");
    if (!chart) return;
    // Build dynamic indicator max values
    const returns = cmpData ? cmpData.returns : [24.13, -0.02, -13.77];
    const sharpes = cmpData ? cmpData.sharpes : [0.76, -0.32, -0.95];
    const mdds = cmpData ? cmpData.mdds : [-14.20, -10.17, -26.44];
    const labels = cmpData ? cmpData.labels : ["双均线", "海龟", "双系统海龟"];

    const returnMax = Math.max(...returns.map(Math.abs), 30) * 1.3;
    const sharpeMax = Math.max(...sharpes.map(Math.abs), 1) * 1.5;
    const mddMax = Math.max(...mdds.map(Math.abs), 15) * 1.3;

    const colors = [CONFIG.colors.accent, CONFIG.colors.warning, CONFIG.colors.info, CONFIG.colors.success];

    chart.setOption({
      tooltip: {},
      legend: { data: labels.slice(0, 4), top: 5 },
      radar: {
        indicator: [
          { name: "累计收益%", max: returnMax },
          { name: "夏普比率", max: sharpeMax },
          { name: "最大回撤%", max: -mddMax },
        ],
      },
      series: [{
        type: "radar",
        data: [
          { value: [returns[0], sharpes[0], mdds[0]], name: labels[0], itemStyle: { color: colors[0] } },
          { value: [returns[1], sharpes[1], mdds[1]], name: labels[1], itemStyle: { color: colors[1] } },
          { value: [returns[2], sharpes[2], mdds[2]], name: labels[2], itemStyle: { color: colors[2] } },
          { value: [returns[3], sharpes[3], mdds[3]], name: labels[3], itemStyle: { color: colors[3] } },
        ],
      }],
    });
  },

  renderCmpRisk(cmpData) {
    // cmpData: { labels, returns, sharpes, mdds }
    const chart = this.init("chart-cmp-risk");
    if (!chart) return;
    const labels = cmpData ? cmpData.labels : ["双均线", "海龟", "双系统海龟"];
    const returns = cmpData ? cmpData.returns : [24.13, -0.02, -13.77];
    const sharpes = cmpData ? cmpData.sharpes : [0.76, -0.32, -0.95];
    const mdds = cmpData ? cmpData.mdds : [-14.20, -10.17, -26.44];

    chart.setOption({
      tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
      legend: { data: ["累计回报%", "最大回撤%", "夏普比率"], top: 5 },
      grid: { left: 50, right: 50, top: 40, bottom: 30 },
      xAxis: { type: "category", data: labels },
      yAxis: [
        { type: "value", name: "回报/回撤%" },
        { type: "value", name: "夏普", position: "right" },
      ],
      series: [
        { name: "累计回报%", type: "bar", data: returns, itemStyle: { color: function(p) { return p.value >= 0 ? CONFIG.colors.up : CONFIG.colors.down; } } },
        { name: "最大回撤%", type: "bar", data: mdds, itemStyle: { color: CONFIG.colors.warning } },
        { name: "夏普比率", type: "line", yAxisIndex: 1, data: sharpes, lineStyle: { width: 2, color: CONFIG.colors.accent }, symbol: "circle", symbolSize: 8 },
      ],
    });
  },
};
