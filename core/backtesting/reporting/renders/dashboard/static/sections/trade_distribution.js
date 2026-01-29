function renderTradeDistribution(report) {
  const section =
    report["Trade Distribution & Payoff Geometry"] || {};

  const block = section["R-multiple distribution"];
  if (!block || !block.rows) return;

  const rows = block.rows;

  // ---------- BAR CHART ----------
  const x = rows.map(r => r["Bucket"]);
  const y = rows.map(r => r["Trades"]);

  Plotly.newPlot(
    "trade-distribution-chart",
    [
      {
        type: "bar",
        x: x,
        y: y,
        marker: { color: "#58a6ff" },
      }
    ],
    {
      margin: { t: 20 },
      paper_bgcolor: "#161b22",
      plot_bgcolor: "#161b22",
      font: { color: "#e6edf3" },
      yaxis: { title: "Trades" },
      xaxis: { title: "R bucket" },
    },
    { displayModeBar: false }
  );

  // ---------- TABLE ----------
  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th>Bucket</th>
        <th>Trades</th>
        <th>Share (%)</th>
      </tr>
    </thead>
    <tbody>
      ${rows.map(r => `
        <tr>
          <td>${r["Bucket"]}</td>
          <td>${r["Trades"]}</td>
          <td>${r["Share (%)"]}</td>
        </tr>
      `).join("")}
    </tbody>
  `;

  const container = document.getElementById("trade-distribution-table");
  if (container) {
    container.appendChild(table);
  }
}