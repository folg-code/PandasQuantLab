# Reporting Overview

Reporting is an integral part of the execution pipeline.

Its purpose is to:
- summarize realized system behavior
- expose execution and risk characteristics
- support post-run analysis and validation

Reporting never influences strategy or execution logic.

---

## Reporting pipeline

```mermaid
flowchart LR
  trades --> enrichment
  enrichment --> metrics
  metrics --> tables
  tables --> charts
```

## Data sources

Reporting operates on:
- executed trades
- execution context (costs, timing, sizing)
- position lifecycle metadata

No raw market data is modified during reporting.

## Reporting modes
The framework supports multiple output modes:

### Stdout (CLI)
- quick inspection during development
- deterministic, text-based summaries
- suitable for logs and CI artifacts

### HTML dashboards
- interactive charts and tables
- multi-section reports
- suitable for exploratory analysis and review

The same underlying metrics power both modes.

## Report structure (conceptual)
Typical sections include:
- equity and drawdown analysis
- execution cost attribution
- exposure and capital usage
- trade-level and aggregated statistics

Each section is generated independently and composed into a final report.

## Design principles
Reporting is designed to be:
- deterministic
- reproducible
- side-effect free
- independent from strategy execution
- 
This separation allows reporting to evolve
without affecting research or live trading logic.