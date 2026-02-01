function renderBacktestConfig(report) {
  const root = document.getElementById("backtest-info-table");
  if (!root) return;

  const payload = report["Backtest Configuration & Assumptions"];
  if (!payload) return;

  root.innerHTML = "";

  const sections = [
    { key: "Market & Data", title: "Market & Data" },
    { key: "Execution Model", title: "Execution Model" },
    { key: "Capital Model", title: "Capital Model" },
  ];

  const wrap = document.createElement("div");
  wrap.className = "bt-info-grid";

  sections.forEach(sec => {
    const block = payload[sec.key];
    if (!block) return;

    const rows = Object.keys(block).map(metric => ({
      Metric: metric,
      Value: window.displayValue(block[metric]),
    }));

    const card = document.createElement("div");
    card.className = "bt-info-card";

    const title = document.createElement("div");
    title.className = "bt-info-title";
    title.textContent = sec.title;

    const table = document.createElement("table");
    table.className = "bt-info-table";
    table.innerHTML = `
      <thead>
        <tr>
          <th>Metric</th>
          <th style="text-align:right;">Value</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map(r => `
          <tr>
            <td>${r.Metric}</td>
            <td style="text-align:right;">${r.Value}</td>
          </tr>
        `).join("")}
      </tbody>
    `;

    card.appendChild(title);
    card.appendChild(table);
    wrap.appendChild(card);
  });

  root.appendChild(wrap);
}