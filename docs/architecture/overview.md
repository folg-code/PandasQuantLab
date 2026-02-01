# Architecture overview

## Design goals
- **Determinism**: reproducible computation, explicit state and policies.
- **Execution realism**: research/backtest/live share the same pipeline contracts.
- **Testability**: clear module boundaries, minimal implicit coupling.

## High-level pipeline

```mermaid
flowchart LR
  A[Run]:::layer --> D[Data Layer]:::layer
  D -->|OHLCV + cache| S[Strategy Engine]:::layer
  S -->|signals + plans| E[Execution Engine]:::layer
  E -->|trades| R[Risk & Reporting]:::layer

  classDef layer fill:#f5f5f5,stroke:#333,stroke-width:1px;
```

## Modules (conceptually)
- Data layer: unified OHLCV ingestion + caching.
- Feature engines: dependency-aware computations (DAG).
- Strategy engine: produces entry signals and exit plans.
- Execution engine: simulates or executes trades with explicit policies.
- Reporting: metrics, tables, charts, dashboards.
- Non-goals
- This project does not attempt to market “alpha”.
- Focus is on correctness, realism and engineering quality.