import json
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path

# =====================================================
# Paths
# =====================================================

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"

OUTPUT_DIR.mkdir(exist_ok=True)

# =====================================================
# Load data
# =====================================================

trades = pd.read_parquet(DATA_DIR / "trades.parquet")
trades["entry_time"] = pd.to_datetime(trades["entry_time"], utc=True)
trades["exit_time"] = pd.to_datetime(trades["exit_time"], utc=True)

with open(DATA_DIR / "report.json") as f:
    report = json.load(f)

core = report["Core Performance Metrics"]

# =====================================================
# Figure layout
# =====================================================

fig = make_subplots(
    rows=3,
    cols=4,
    row_heights=[0.18, 0.52, 0.30],
    specs=[
        [{"type": "indicator"}] * 4,
        [{"colspan": 4, "type": "xy"}, None, None, None],
        [{"colspan": 4, "type": "xy"}, None, None, None],
    ],
)

# =====================================================
# KPI Indicators (Row 1)
# =====================================================

def indicator(title, value, row, col, pct=False):
    fig.add_trace(
        go.Indicator(
            mode="number",
            value=value * 100 if pct else value,
            number={"suffix": "%" if pct else ""},
            title={"text": title},
        ),
        row=row,
        col=col,
    )


indicator("Total Return", core["Total return (%)"], 1, 1, pct=True)
indicator("CAGR", core["CAGR (%)"], 1, 2, pct=True)
indicator("Expectancy (USD)", core["Expectancy (USD)"], 1, 3)
indicator("Max Drawdown", core["Max drawdown (%)"], 1, 4, pct=True)

# =====================================================
# Equity Curve (Row 2)
# =====================================================

fig.add_trace(
    go.Scatter(
        x=trades["exit_time"],
        y=trades["equity"],
        name="Equity",
        line=dict(width=2),
    ),
    row=2,
    col=1,
)

fig.add_trace(
    go.Scatter(
        x=trades["exit_time"],
        y=trades["equity"].cummax(),
        name="Equity Peak",
        line=dict(width=1, dash="dot"),
    ),
    row=2,
    col=1,
)

# =====================================================
# Drawdown (Row 3)
# =====================================================

fig.add_trace(
    go.Scatter(
        x=trades["exit_time"],
        y=trades["drawdown"],
        fill="tozeroy",
        name="Drawdown",
        line=dict(width=1),
    ),
    row=3,
    col=1,
)

# =====================================================
# Layout styling
# =====================================================

fig.update_layout(
    template="plotly_dark",
    height=900,
    showlegend=True,
    hovermode="x unified",
    margin=dict(t=40, l=40, r=40, b=40),
)

fig.update_yaxes(title_text="Equity", row=2, col=1)
fig.update_yaxes(title_text="Drawdown", row=3, col=1)

# =====================================================
# Save output
# =====================================================

output_path = OUTPUT_DIR / "dashboard.html"
fig.write_html(output_path)

print(f"Dashboard written to {output_path}")