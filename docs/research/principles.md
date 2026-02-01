# Research Principles

This document defines the **research invariants** enforced by the framework.

The goal is to ensure that:
- research results are reproducible
- execution assumptions are explicit
- strategy logic does not diverge between environments

These principles are enforced by architecture, not convention.

---

## No lookahead bias

- Feature computation is strictly forward-only.
- All features are derived from data available at decision time.
- Warmup periods are explicit and enforced.

Lookahead bias is prevented **by construction**, not by discipline.

---

## Same code path across environments

- Research, backtesting and live trading use the same:
  - feature modules
  - strategy logic
  - execution engine contracts
- Environment-specific behavior is isolated behind adapters.

There is no separate “research-only” execution logic.

---

## Explicit execution assumptions

All execution-related assumptions are explicit:
- spread
- slippage
- financing / holding costs
- order execution rules

No hidden defaults or implicit broker behavior.

---

## Determinism and reproducibility

For identical inputs and policies:
- feature outputs are deterministic
- strategy intents are deterministic
- simulated execution results are reproducible

Non-determinism is isolated and documented.

---

## Measurement philosophy

- Net results include all modeled costs.
- Metrics describe realized behavior, not theoretical edge.
- Stress testing is preferred over curve fitting.

The framework optimizes for **research validity**, not optimistic results.

