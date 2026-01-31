function renderKPI(report) {
  const root = document.getElementById("kpi-table");
  if (!root) return;

  const payload = report["Core Performance Metrics"];
  if (!payload) return;

  root.innerHTML = "";

  const sections = [
    {
      title: "Run info & capital",
      metrics: [
        "Backtesting from",
        "Backtesting to",
        "Total trades",
        "Trades/day (avg)",
        "Starting balance",
        "Final balance",
        "Absolute profit",
        "Total return (%)",
        "CAGR (%)",
      ],
    },
    {
      title: "Performance & risk",
      metrics: [
        "Profit factor",
        "Expectancy (USD)",
        "Win rate (%)",
        "Avg win",
        "Avg loss",
        "Avg win/loss",
        "Max drawdown ($)",
        "Max drawdown (%)",
        "Max daily loss ($)",
        "Max daily loss (%)",
        "Max consecutive wins",
        "Max consecutive losses",
      ],
    },
    {
      title: "Costs & execution",
      metrics: [
        "Total costs (USD)",

        "Spread cost (USD)",
        "Slippage cost (USD)",
        "Overnight cost (USD)",
        "Overweekend cost (USD)",

        "Avg cost/trade (bps)",
        "Avg volume/trade (lots)",
      ],
    },
  ];

  const wrap = document.createElement("div");
  wrap.className = "bt-info-grid"; // reuse Backtest Info layout (3 cards side-by-side)

  sections.forEach(sec => {
    const rows = sec.metrics
      .filter(key => payload[key] !== undefined && payload[key] !== null)
      .map(key => ({
        Metric: key,
        Value: window.displayValue(payload[key]),
      }));

    if (!rows.length) return;

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