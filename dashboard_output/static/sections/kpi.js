function renderKPI(report) {
  const root = document.getElementById("kpi-table");
  if (!root) return;

  const payload = report["Core Performance Metrics"];
  if (!payload) return;

  root.innerHTML = "";

  const kpis = [
    // Run info
    "Backtesting from",
    "Backtesting to",
    "Total trades",
    "Trades/day (avg)",

    // Capital
    "Starting balance",
    "Final balance",
    "Absolute profit",
    "Total return (%)",
    "CAGR (%)",

    // Performance
    "Profit factor",
    "Expectancy (USD)",
    "Win rate (%)",
    "Avg win",
    "Avg loss",
    "Avg win/loss",

    // Risk
    "Max drawdown ($)",
    "Max drawdown (%)",
    "Max daily loss ($)",
    "Max daily loss (%)",
    "Max consecutive wins",
    "Max consecutive losses",

    // Costs & execution (NEW)
    "Total costs (USD)",
    "Spread cost (USD)",
    "Slippage cost (USD)",
    "Costs (bps)",
    "Spread (bps)",
    "Slippage (bps)",
    "Avg cost/trade (USD)",
    "Traded volume (USD)",
    "Avg volume/trade (USD)",
    "Costs as % of gross PnL",
    "Entry market share (%)",
    "Exit market share (%)",
  ];

  const rows = kpis
    .filter(key => payload[key] !== undefined && payload[key] !== null)
    .map(key => ({
      Metric: key,
      Value: window.displayValue(payload[key]),
    }));

  const table = document.createElement("table");
  table.innerHTML = `
    <thead>
      <tr>
        <th>Metric</th>
        <th style="text-align:right;">Value</th>
      </tr>
    </thead>
    <tbody>
      ${rows
        .map(
          r => `
        <tr>
          <td>${r.Metric}</td>
          <td style="text-align:right;">${r.Value}</td>
        </tr>
      `
        )
        .join("")}
    </tbody>
  `;

  const wrap = document.createElement("div");
  wrap.className = "kpi-table";
  wrap.appendChild(table);
  root.appendChild(wrap);
}