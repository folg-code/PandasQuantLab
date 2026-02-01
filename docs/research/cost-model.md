# Execution Cost Model

Execution costs are treated as **first-class components**
of the research and execution pipeline.

They are not post-hoc adjustments.

---

## Modeled cost types

### Spread
- Modeled as a deterministic cost at entry and exit.
- Applied symmetrically.

### Slippage
- Modeled as price deviation from intended execution.
- Can be static or policy-driven.

### Financing / holding cost
- Applied per time unit while a position is open.
- Explicit and configurable.

---

## Where costs are applied

Costs are applied during execution, not during reporting.

This ensures:
- correct interaction with position sizing
- correct aggregation at trade and portfolio level
- realistic stress behavior

---

## Determinism vs realism

- In backtests, costs are deterministic and reproducible.
- In live trading, costs reflect real execution feedback.

The same accounting model is used in both cases.

---

## Limitations

- Cost models are approximations.
- Real execution behavior may differ under extreme conditions.

The framework favors **transparent assumptions**
over hidden optimism.