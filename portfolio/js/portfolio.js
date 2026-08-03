document.addEventListener("DOMContentLoaded", function () {
  renderHeroStats();
  renderTaskCards();
  renderSkillTags();
});

function renderHeroStats() {
  const totalCharts = CONFIG.tasks.reduce((sum, t) => sum + t.charts, 0);
  const totalTasks = CONFIG.tasks.length;
  const totalStrategies = 4;
  const stats = [
    { num: totalTasks, desc: "课程任务" },
    { num: totalCharts, desc: "可视化图表" },
    { num: totalStrategies, desc: "量化策略" },
    { num: "242", desc: "交易日数据" },
  ];
  const container = document.getElementById("hero-stats");
  container.innerHTML = stats
    .map(
      (s) =>
        `<div class="hero-stat"><div class="num">${s.num}</div><div class="desc">${s.desc}</div></div>`
    )
    .join("");
}

function renderTaskCards() {
  const grid = document.getElementById("task-grid");
  grid.innerHTML = CONFIG.tasks
    .map((task) => {
      const metricsHtml = task.metrics
        .map(
          (m) =>
            `<div class="task-metric"><div class="val ${m.up ? "text-up" : ""}">${m.val}</div><div class="lbl">${m.lbl}</div></div>`
        )
        .join("");
      const tagsHtml = task.tags
        .map((t) => `<span class="badge badge-accent">${t}</span>`)
        .join("");
      return `
        <div class="task-card" onclick="openTask('${task.id}', '${task.pdf}')">
          <div class="card-header">
            <div class="task-num">${typeof task.id === "number" ? task.id : "4+"}</div>
            <div class="task-title">${task.title}</div>
          </div>
          <img class="task-thumb" src="${task.img}" alt="${task.title}" loading="lazy"
            onerror="this.style.background='#f1f3f5';this.removeAttribute('src');">
          <div class="task-desc">${task.desc}</div>
          <div class="task-tags">${tagsHtml}</div>
          <div class="task-metrics">${metricsHtml}</div>
          <div class="task-links">
            <a href="${task.pdf}" onclick="event.stopPropagation()">查看PDF报告</a>
            <a href="${task.img}" onclick="event.stopPropagation()">查看图表</a>
          </div>
        </div>`;
    })
    .join("");
}

function renderSkillTags() {
  const container = document.getElementById("skill-tags");
  container.innerHTML = CONFIG.skills
    .map((s) => `<span class="skill-tag">${s}</span>`)
    .join("");
}

function openTask(id, pdf) {
  window.location.href = pdf;
}
