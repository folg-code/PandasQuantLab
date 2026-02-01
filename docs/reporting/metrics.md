# Metrics and Definitions

This document defines the core metrics used in reporting.

Metrics are computed **after execution completes**
and do not affect strategy behavior.

---

## Equity and returns

### Equity curve
- Time series of account value over time
- Includes realized PnL and modeled costs

### Net PnL
- Sum of realized trade results
- Includes:
  - price movement
  - spread
  - slippage
  - financing / holding costs

---

## Drawdown metrics

### Max drawdown
- Maximum peak-to-trough equity decline
- Computed on the equity curve

### Drawdown duration
- Time (or trades) spent below a previous equity peak

### Recovery time
- Time (or trades) required to exceed the previous peak

---

## Trade statistics

### Trade count
- Total number of executed trades

### Win rate
- Percentage of profitable trades
- Reported with total trade count (never standalone)

### Expectancy
- Average PnL per trade
- Reported together with distribution metrics

---

## Exposure and capital usage

### Exposure
- Amount of capital allocated over time
- Can be absolute or normalized

### Concurrent positions
- Number of open positions at the same time
- Used to reason about portfolio stress

---

## Execution cost attribution

Costs are decomposed into:
- spread cost
- slippage
- financing / holding cost

This allows inspection of where performance is gained or lost.

---

## Edge cases and safety

### Negative equity
- Metrics that assume positive equity (e.g. CAGR)
  are guarded against invalid input
- Invalid or undefined metrics are reported explicitly

### Sparse trades
- Metrics are reported even for low trade counts
- Interpretation responsibility is left to the user

---

## Interpretation guidance

Metrics describe **what happened**, not **why it happened**.

They should be used to:
- validate assumptions
- detect pathological behavior
- compare configurations under identical conditions

They should not be used in isolation to claim predictive power.